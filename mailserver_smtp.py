import socket
import threading
import json
import os
from datetime import datetime

# The address of the SMTP server, defaults to the localhost or loopback address
HOST_IP = input("Specify address for SMTP server (default 127.0.0.1): ") or "127.0.0.1"

# The port of the SMTP server
# The default value for the SMTP port is 25, because we use non-encrypted traffic
# Since this one is already taken by the real SMTP, we use 6666
SMTP_PORT = int(input('Specify port number for SMTP server (default 6666): ') or 6666)

# Maximum number of concurrent client connections
MAX_QUEUE_LENGTH = 5

# Create a socket with TCP connection => SOCK_STREAM
# Bind the socket to a specific ip and port defined above
# Start listening for connections
# print statement as in RFC 821, Page 15
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind((HOST_IP, SMTP_PORT))
serverSocket.listen(MAX_QUEUE_LENGTH)
print('Simple Mail Transfer Service ready and listening on port: ', SMTP_PORT)

# Helper function that reconstructs the JSON from the data-string and places it in the mailbox of the receiver
def storeInMailbox(data, receiver, sender):
    mailboxPath = "users/{}/my_mailbox.json".format(receiver)
    mailboxContent = []

    if os.path.exists(mailboxPath):
        if os.path.getsize(mailboxPath) > 0:
            with open(mailboxPath, 'r') as file:
                mailboxContent = json.load(file)      
    
    splitData = data.split("\r\n")
    jsonData = {
        "sender": sender,
        "receiver": receiver,
        "subject": splitData[2].split(' ')[1],
        "content": datetime.now().strftime("%d/%m/%Y %H:%M:%S") + "\r\n" + "\r\n".join(splitData[3:])
    }
    mailboxContent.append(json.dumps(jsonData))  # Convert JSON object to string before appending
    with open(mailboxPath, 'w') as file:
        json.dump(mailboxContent, file, indent=4)
            
def authenticate(username, password):
    authFile = "userinfo.txt"

    if os.path.exists(authFile):
        with open(authFile, 'r') as file:
            entries = file.read().split('\n')
            for entry in entries:
                listOfEntry = entry.split(' ')
                if listOfEntry[0] == username and listOfEntry[1] == password:
                    return True
        return False


# What follows are all the methods used to handle all the incoming commands. These speak for themselves

# HELO {senderDomain}
def handleHELO(clientSocket, address, data):
    domain = None
    if len(data.split(" ")) > 1:
        domain = data.split(" ")[1]
        if domain != address[0]:
            clientSocket.send(b'501 HELO handshake failed, entry mismatched\r\n')

    if domain != "HELO" or domain is not None:
        clientSocket.send('250 {} \r\n'.format(HOST_IP).encode())
        return True
    else:
        clientSocket.send(b'504 Please specify your client domain.\r\n')
        return False


def handleMAIL(clientSocket, data):
    sender = data.split(' ')[-1]
    if sender == '':
        clientSocket.send(b'504 No arguments given\r\n')
        return None

    if sender == 'MAIL' or sender == 'FROM:':
        clientSocket.send(b'501 Syntax error, sender@domain must be sent after MAIL FROM:\r\n')
        return None

    if len(sender.split('@')) == 2:
        sender = sender.split('@')[0]

    clientSocket.send(b'250 ok\r\n')
    return sender

def handleRCPT(clientSocket, data):
    receiver = data.split(' ')[-1]
    if receiver == '':
        clientSocket.send(b'504 No arguments given\r\n')
        return None

    if receiver == 'RCPT' or receiver == 'TO:':
        clientSocket.send(b'501 Syntax error, recipient@domain must be sent after RCPT TO:\r\n')
        return None

    if len(receiver.split('@')) == 2:
        receiver = receiver.split('@')[0]

    mailboxPath = "users/{}/my_mailbox.json".format(receiver)
    if os.path.exists(mailboxPath):
        clientSocket.send(b'250 ok\r\n')
    else: 
        clientSocket.send(b'550 No such user here\r\n')
    return receiver

def handleDATA(clientSocket, receiver, sender):
    clientSocket.send(b'354 send the mail data, end with .\r\n')

    data = ""
    while True:
        receivedData = clientSocket.recv(1024).decode()
        if receivedData == ".":
            break
        data += receivedData
    clientSocket.send(b'250 ok\r\n')
    storeInMailbox(data, receiver, sender)


def handleQUIT(clientSocket):
    clientSocket.send('221 {} Service closing transmission channel\r\n'.format(HOST_IP).encode())

# Function that handles all requests from users.
def handleRequest(clientSocket, address):
    heloHappened = False
    receiver = None
    sender = None

    try:
        while True:
            data = clientSocket.recv(1024).decode().strip()
            if not data:
                break

            if data.startswith("HELO"):
                heloHappened = handleHELO(clientSocket, address, data)

            elif data.startswith("MAIL") and heloHappened:
                sender = handleMAIL(clientSocket, data)
            elif data.startswith("MAIL") and not heloHappened:
                clientSocket.send(b'503 Transactions are not in the right order, HELO did not happen\r\n')

            elif data.startswith("RCPT") and heloHappened and sender is not None:
                receiver = handleRCPT(clientSocket, data)
            elif data.startswith("RCPT") and not heloHappened or data.startswith("RCPT") and sender is None:
                clientSocket.send(b'503 Transactions are not in the right order\r\n')

            elif data.startswith("DATA") and heloHappened and sender is not None and receiver is not None:
                handleDATA(clientSocket, receiver, sender)
            elif data.startswith("DATA") and not heloHappened or data.startswith("RCPT") and sender is None or data.startswith("RCPT") and receiver is None:
                clientSocket.send(b'503 Transactions are not in the right order\r\n')

            elif data.startswith("QUIT") and heloHappened:
                handleQUIT(clientSocket)
            elif data.startswith("QUIT") and not heloHappened:
                clientSocket.send(b'503 Transactions are not in the right order, HELO did not happen\r\n')

            else:
                # Unknown command, send an error message
                clientSocket.send(b'500 Command not recognized\r\n')
    except Exception as e:
        print("An error occurred:", e)
    finally:
        clientSocket.shutdown(socket.SHUT_RDWR)
        clientSocket.close()
    
# Main code to be run on repeat while server operates, new users will jump to function "handleRequest".
# After redirecting a client to handleRequest, the server keeps listening and accepting new users due to threading.
while True:
    (clientSocket, address) = serverSocket.accept()
    thread = threading.Thread(target=handleRequest, args=(clientSocket, address))
    thread.start()