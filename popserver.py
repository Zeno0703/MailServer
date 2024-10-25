import socket
import threading
import os
import json

# The address of the POP3 server, defaults to the localhost or loopback address
HOST_IP = input("Specify address for SMTP server (default 127.0.0.1): ") or "127.0.0.1"

# The port of the POP3 server
# The default value for the POP3 port is 110, because we use non-encrypted traffic
# Since this one is already taken by the real POP3, we use 6667
POP3_PORT = int(input("Specify port number for POP3 server (default 6667): ") or 6667)

# Maximum number of concurrent client connections
MAX_QUEUE_LENGTH = 5

# Create a socket with TCP connection => SOCK_STREAM
# Bind the socket to a specific ip and port defined above
# Start listening for connections
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind((HOST_IP, POP3_PORT))
serverSocket.listen(MAX_QUEUE_LENGTH)
print('Post Office (POP3) initiated and listening on port: ', POP3_PORT)

userInfo = "userinfo.txt"

localVar = threading.local()

# The function that handles the USER command
# Looks up whether the specified name is in the userinfo.txt
def handleUSER(clientSocket, data):
    if len(data.split(' ')) < 2:
        clientSocket.send(b'-ERR Please enter username')
    else:    
        username = data[len("USER: ") - 1:]
        if os.path.exists(userInfo):
            with open(userInfo, 'r') as file:
                entries = file.read().split('\n')
                for entry in entries:
                    splittedEntry = entry.split(' ')
                    if splittedEntry[0] == username:
                        clientSocket.send(b'+OK username known')
                        return username
                clientSocket.send(b'-ERR Username or password is incorrect')
    return None
            
# The function that handles the PASS command
# Looks up whether the specified name-password combination is in the userinfo.txt
def handlePASS(clientSocket, data, username):
    if len(data.split(' ')) < 2:
        clientSocket.send(b'-ERR Please Enter password')
    else:    
        password = data.split(' ')[1]
        if os.path.exists(userInfo):
            with open(userInfo, 'r') as file:
                entries = file.read().split('\n')
                for entry in entries:
                    splittedEntry = entry.split(' ')
                    if splittedEntry[0] == username and splittedEntry[1] == password:
                        clientSocket.send(b'+OK password correct')
                        return True
                clientSocket.send(b'-ERR Username or password is incorrect')
                return False

# Helper function that returns the indices of the e-mails that are marked as deleted
def getIndicesOfDeletedMails(mailbox):
    indices = []
    for i in range(len(mailbox)):
        if json.loads(mailbox[i]) in localVar.deletedMails:
            indices.append(i)
    return indices

# Helper function that returns the size of the mailbox and the amount of bytes in the mailbox
# Does not include the messages that are marked as deleted
def getSize(mailbox):
    deletedIndices = getIndicesOfDeletedMails(mailbox)
    totalBytes = 0
    for i in range(len(mailbox)):
        if i not in deletedIndices:
            totalBytes += len(json.loads(mailbox[i])['content'].encode('utf-8'))
    return len(mailbox) - len(deletedIndices), totalBytes

# The function that handles the STAT command
# Using the getSize()-function this returns the total amount of e-mails in the mailbox, and the total byte size of the mailbox
def handleSTAT(clientSocket, username):
    mailboxPath = "users/{}/my_mailbox.json".format(username)
    if os.path.exists(mailboxPath):
        with open(mailboxPath, 'r') as mailbox:
            numberOfMails, mailboxSize = getSize(json.load(mailbox))
        clientSocket.send("+OK {} {}".format(numberOfMails, mailboxSize).encode())
    else:
        clientSocket.send(b'- ERR FAILED')

    return None

# The function that handles the LIST command
# Could be either with or without a specified message-number
# This function returns:
#                           The total size of the mailbox, followed by a listing of the message-number and byte size per e-mail in the mailbox
#                           The message-number followed by the size of the e-mail
def handleLIST(clientSocket, data, username):
    mailboxPath = "users/{}/my_mailbox.json".format(username)
    if os.path.exists(mailboxPath):
        if len(data.split(' ')) == 1:
            with open(mailboxPath, 'r') as mailbox:
                numberOfMails, mailboxSize = getSize(json.load(mailbox))
                clientSocket.send("+OK {} {}".format(numberOfMails, mailboxSize).encode())
                
            with open(mailboxPath, 'r') as mailbox:
                inbox = json.load(mailbox)
                for i in range(len(inbox)):
                    if i not in getIndicesOfDeletedMails(inbox):
                        clientSocket.send("\r\n {} {}".format(i + 1, len(json.loads(inbox[i])['content'].encode('utf-8'))).encode())
                clientSocket.send(b'\r\n .')
        else:
            index = int(data.split(' ')[1])
            with open(mailboxPath, 'r') as mailbox:
                inbox = json.load(mailbox)
                if index not in getIndicesOfDeletedMails(inbox):
                    if index > len(inbox):
                        clientSocket.send("-ERR No such message, only {} in mailbox.".format(len(inbox)).encode())
                    else:
                        mail = inbox[index - 1]
                        clientSocket.send("{} {}".format(str(index), len(json.loads(mail)['content'].encode('utf-8'))).encode())
                else:
                    clientSocket.send(b'-ERR No such message.')
    else:
        clientSocket.send("-ERR".encode())
    return None


# The function that handles the RETR command
# Using the specified message-number, the method looks in the mailbox of the user to retrieve the wanted e-mail
# Sends the e-mail back to the user in string format
def handleRETR(clientSocket, data, username):
    mailboxPath = "users/{}/my_mailbox.json".format(username)
    if len(data.split(' ')) < 2:
        clientSocket.send(b'-ERR Please specify mail index')
    else:    
        index = int(data.split(' ')[1]) - 1
        if os.path.exists(mailboxPath):
            with open(mailboxPath, 'r') as mailbox:
                inbox = json.load(mailbox)
                if index not in getIndicesOfDeletedMails(inbox):
                    if index >= len(inbox):
                        clientSocket.send(b'-ERR Invalid message index')
                        return
                    else:
                        mail = json.loads(inbox[index])
                        clientSocket.send("+OK {}".format(len(mail['content'].encode('utf-8'))).encode())
                        data = "FROM: " + mail["sender"] + "\r\nTO: " + mail["receiver"] + "\r\nSUBJECT: " + mail["subject"] + "\r\n" + mail["content"]
                        clientSocket.send(data.encode())
                        clientSocket.send(".".encode())
                else:
                    clientSocket.send(b'-ERR No such message')
        else:
            clientSocket.send(b'-ERR')

    return None

# The function that handles the DELE command
# Using the specified message-number, the method looks in the mailbox of the user to mark the specified e-mail as deleted
# This also adds the specified message to localVar.deletedMails, used for the QUIT and RSET commands
def handleDELE(clientSocket, data, username):
    mailboxPath = "users/{}/my_mailbox.json".format(username)
    if len(data.split(' ')) < 2:
        clientSocket.send(b'-ERR Please specify mail index')
    else:    
        index = int(data.split(' ')[1]) - 1

        if os.path.exists(mailboxPath):
            with open(mailboxPath, 'r') as mailbox:
                inbox = json.load(mailbox)
                
                if index >= len(inbox):
                    clientSocket.send(b'-ERR Invalid message index')
                    return
                    
                mail = json.loads(inbox[index])

                if mail in localVar.deletedMails:
                    clientSocket.send(b'-ERR Message has already been marked as deleted')
                else:
                    localVar.deletedMails.append(mail)
                    clientSocket.send(b'+OK Message marked as deleted')
        else:
            clientSocket.send(b'-ERR')

    return None

# The function that handles the RSET command
# Flushes the localVar.deletedMails
def handleRSET(clientSocket, username):
    mailboxPath = "users/{}/my_mailbox.json".format(username)

    if os.path.exists(mailboxPath):
        with open(mailboxPath, 'r') as mailbox:
            inbox = json.load(mailbox)
            localVar.deletedMails = []
            clientSocket.send("+OK Mailbox has {} messages".format(len(inbox)).encode())
    else:
        clientSocket.send(b'-ERR')
        
    return None

# The function that handles the QUIT command
# Deletes all the e-mails in the mailbox that are also present in the localVar.deletedMails
def handleQUIT(clientSocket, username):
    mailboxPath = "users/{}/my_mailbox.json".format(username)

    if os.path.exists(mailboxPath):
        with open(mailboxPath, 'r') as mailbox:
            inbox = json.load(mailbox)

            for i in range((len(inbox))):
                if i < len(inbox):
                    mail = json.loads(inbox[i])
                    if mail in localVar.deletedMails:
                        del inbox[i]
                        localVar.deletedMails.remove(mail)
                else:
                    break
        
        with open(mailboxPath, 'w') as mailbox:
            json.dump(inbox, mailbox, indent=4)

        if len(localVar.deletedMails) > 0:
            clientSocket.send(b'-ERR Some deleted messages not removed')
        else:
            with open(mailboxPath, 'r') as mailbox:
                inbox = json.load(mailbox)
                clientSocket.send("+OK POP3 server signing off ({} mails in mailbox)".format(len(inbox)).encode())
    else:
        clientSocket.send(b'-ERR')

    return None

# Function that handles all requests from users.
def handleRequest(clientSocket, address):
    localVar.username = None
    localVar.authenticated = False
    localVar.deletedMails = []
    
    try:
        while True:
            data = clientSocket.recv(1024).decode().strip()
            if not data:
                break

            if data.startswith("USER"):
                localVar.username = handleUSER(clientSocket, data)
            elif data.startswith("PASS"):
                localVar.authenticated = handlePASS(clientSocket, data, localVar.username)
                if not localVar.authenticated:
                    localVar.username = None

            elif data.startswith("STAT") and localVar.authenticated:
                handleSTAT(clientSocket, localVar.username)
            elif data.startswith("LIST") and localVar.authenticated:
                handleLIST(clientSocket, data, localVar.username)
            elif data.startswith("RETR") and localVar.authenticated:
                handleRETR(clientSocket, data, localVar.username)
            elif data.startswith("DELE") and localVar.authenticated:
                handleDELE(clientSocket, data, localVar.username)
            elif data.startswith("RSET") and localVar.authenticated:
                handleRSET(clientSocket, localVar.username)
            elif data.startswith("QUIT"):
                handleQUIT(clientSocket, localVar.username)
            else:
                print(data, localVar.authenticated)
                clientSocket.send(b'-ERR Command not recognized\r\n')
    except Exception as e:
        print("An error occurred:", e)
    finally:
        clientSocket.close()

# Main code to be run on repeat while server operates, new users will jump to function "handleRequest".
# After redirecting a client to handleRequest, the server keeps listening and accepting new users due to threading.
while True:
    (clientSocket, address) = serverSocket.accept()
    thread = threading.Thread(target=handleRequest, args=(clientSocket, address))
    thread.start()