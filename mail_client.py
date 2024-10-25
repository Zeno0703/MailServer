import socket
import json

# The address of the SMTP and POP3 server which the user wishes to connect to.
# We set the default address to the localhost or loopback address
HOST_IP = input("Specify address for SMTP and POP server (default 127.0.0.1): ") or "127.0.0.1"

# The ports of the SMTP and POP3 server which the user wishes to connect to.
# The default value for the SMTP port is 25, because we use non-encrypted traffic
# Since this one is already taken by the real SMTP, we use 6666
SMTP_PORT = int(input("Specify port number for SMTP server (default 6666): ") or 6666)
# The default value for the POP3 port is 110, because we use non-encrypted traffic
# Since this one is already taken by the real POP3, we use 6667
POP3_PORT = int(input("Specify port number for POP3 server (default 6667): ") or 6667)


# Let the user graphically construct the e-mail they want to send
# Place the input in JSON format
def constructMail():
    sender = input("From: ")
    receiver = input("To:   ")

    # Maximum length of subject can be 150 characters
    subject = ""
    while 0 == len(subject) or len(subject) > 150:
        subject = input("Subject (Max. 150 characters): ")

    # Maximum amount of lines in content can be 50
    # Automatically cuts off at the maximum (50)
    content, line = "", ""
    counter = 1
    while line != "." and counter <= 50:
        line = input("")
        content = content + "\r\n" + line if counter > 1 else line
        counter += 1

    data = json.dumps({
        "sender": sender,
        "receiver": receiver,
        "subject": subject,
        "content": content
    })
    return data

# Function that handles the mail sending
# Performed when the user specifies the mail sending option
def sendMail(mail):
    mail_data = json.loads(mail)

    # Communication with the SMTP server will start with a 'HELO'-command
    # Given with the HELO command is the IP address <domain> of the client as specified in RFC 821
    # clientSocket.getpeername() returns a tuple (ip, port), hence we select the first value
    domainName = clientSocket.getpeername()[0]
    clientSocket.send('HELO {} \r\n'.format(domainName).encode())
    response = clientSocket.recv(1024).decode().strip()
    # if the response from the server does not start with status code 250, we return, since the requested action has not been completed
    if not response.startswith('250'):  
        print(response)    
        return

    # Effectuating the 'MAIL FROM:' command
    # Given is the sender field from the constructed mail
    clientSocket.send('MAIL FROM: {}'.format(mail_data["sender"]).encode())
    response = clientSocket.recv(1024).decode().strip()
    # if the response from the server does not start with status code 250, we return, since the requested action has not been completed
    if not response.startswith('250'):
        print(response)        
        return

    # Effectuating the 'RCPT TO:' command
    # Given is the receiver field, the recipient, from the constructed mail
    clientSocket.send('RCPT TO: {}'.format(mail_data["receiver"]).encode())
    response = clientSocket.recv(1024).decode().strip()
    # if the response from the server does not start with status code 250, we return, since the requested action has not been completed
    if not response.startswith('250'):
        print(response)          
        return

    # Effectuating the 'DATA' command
    # Nothing else is given, since the server should first reply that it is ready to receive the data
    clientSocket.send('DATA'.encode())
    response = clientSocket.recv(1024).decode().strip()
    # if the response from the server does not start with status code 354, we return, since the server is not ready to receive data
    if not response.startswith('354'):
        print(response)        
        return

    # Sending the actual data
    # Data is a string, since the SMTP server should not be bothered with JSON
    data = "FROM: " + mail_data["sender"] + "\r\nTO: " + mail_data["receiver"] + "\r\nSUBJECT: " + mail_data["subject"] + "\r\n" + mail_data["content"]
    clientSocket.send(data.encode()[:1024])
    clientSocket.send(b".")
    response = clientSocket.recv(1024).decode().strip()
    # if the response from the server does not start with status code 250, we return, since the requested action has not been completed
    if not response.startswith('250'):
        print(response)         
        return

    # Request the server to close the transmission channel
    clientSocket.send('QUIT'.encode())
    response = clientSocket.recv(1024).decode().strip()
    # if the response from the server does not start with status code 250, we return, since the server is not closing the connection
    if not response.startswith('221'):
        print(response)        
        return

# Function that handles the mail management
# Performed when the user specifies the mail management option with a specified action
def manageMails(action):

    # When the specified action is the STAT command, we send STAT to the POP3 server and await response
    # When the repsonse arrives we return it in a clean formatted manner
    if action == "STAT":
        clientSocket.send(b'STAT')
        response = clientSocket.recv(1024).decode().strip()
        # if the response from the server does not start with code +OK, we return, since the action failed
        if not response.startswith('+OK'):
            print(response)
            return
        else:
            return {"number of mails": response.split(' ')[1], "mailbox size": response.split(' ')[2]}

    # When the specified action is the LIST command, we send LIST to the POP3 server and await response
    # The LIST command can be accompanied by a message-number, then the case below is performed
    # When the repsonse arrives we return it in a clean formatted manner
    if action == "LIST":
        clientSocket.send(b'LIST')
        response = clientSocket.recv(1024).decode().strip()
        # if the response from the server does not start with code +OK, we return, since the action failed
        if not response.startswith('+OK'):
            print(response)
            return
        else:
            returnData = {"number of mails": response.split(' ')[1], "mailbox size": response.split(' ')[2]}
            while not '.' in response:
                response = clientSocket.recv(1024).decode()
                if "mails" in returnData.keys():
                    returnData["mails"] = returnData["mails"] + response
                else:
                    returnData["mails"] = response
            return returnData
        
    elif action.startswith("LIST"):
        clientSocket.send(action.encode())
        response = clientSocket.recv(1024).decode().strip()
        # if the response from the server does not start with code +OK, we return, since the action failed
        if not response.startswith('+OK'):
            print(response)
            return
        else:
            return {"mail index": response.split(' ')[1], "mail size": response.split(' ')[2]}

    # When the specified action is the RETR command, we send RETR to the POP3 server with the specified message-number and await response
    # When the repsonse arrives we return it in a clean formatted manner
    if action.startswith("RETR"):
        clientSocket.send(action.encode())
        response = clientSocket.recv(1024).decode().strip()
        # if the response from the server does not start with code +OK, we return, since the action failed
        if not response.startswith('+OK'):
            print(response)
            return
        else:
            mail = clientSocket.recv(1024).decode().strip()
            clientSocket.recv(1024).decode().strip()
            return {"mail size": response.split(' ')[1], "mail": mail}

    # When the specified action is the DELE command, we send DELE to the POP3 server with the specified message-number and await response
    if action.startswith("DELE"):
        clientSocket.send(action.encode())
        response = clientSocket.recv(1024).decode().strip()
        # if the response from the server does not start with code +OK, we return, since the action failed
        if not response.startswith('+OK'):
            print(response)
            return

    # When the specified action is the RSET command, we send RSET to the POP3 server and await response
    if action == "RSET":
        clientSocket.send(b'RSET')
        response = clientSocket.recv(1024).decode().strip()
        # if the response from the server does not start with code +OK, we return, since the action failed
        if not response.startswith('+OK'):
            print(response)
            return

    # When the specified action is the QUIT command, we send QUIT to the POP3 server, await response and close the connection
    if action == "QUIT":
        clientSocket.send(b'QUIT')
        response = clientSocket.recv(1024).decode().strip()
        print(response)
        return
    
    return

# Function that handles the mail searching
# Performed when the user specifies the mail searching option with a specified base (word/sentence/time/address) and key

# This method retrieves the mailbox of the user via the POP3 server using the known STAT and RETR commands
# The specific search is then done client-side
def searchMails(base, search):
    mails = []
    noOfMails = int(manageMails("STAT")["number of mails"])
    for i in range(1, noOfMails + 1):
        mails.append(manageMails("RETR {}".format(i))["mail"][:-1])
    
    matchedMails = []    
    if base == "1)":
        for mail in mails:
            if search in " ".join(mail.split("\r\n")[4:]):
                matchedMails.append(mail)
    if base == "2)":
        for mail in mails:
            if search in mail.split("\r\n")[3]:
                matchedMails.append(mail)           
    elif base == "3)":
        for mail in mails:
            if search in mail.split("\r\n")[0]:
                matchedMails.append(mail)
                
    if len(matchedMails) == 0:
        print("No mails matching search criteria found.")
    else:
        for mail in matchedMails:
            print(mail)
            print("-----------")
    return


# Helper function that lets the user authenticate using the POP3 server
def authenticate(clientSocket):
    authenticated = False
    
    while not authenticated:
        username = input("Please enter your username (or QUIT): ")
        if username.upper() == 'QUIT':
            break
        password = input("Please enter your password: ")

        clientSocket.send('USER {}'.format(username).encode())
        response = clientSocket.recv(1024).decode().strip()
        if response.startswith('+OK'):
            clientSocket.send('PASS {}'.format(password).encode())
            response = clientSocket.recv(1024).decode().strip()
            if response.startswith('+OK'):
                authenticated = True
            else:
                print(response)
        else:
            print(response)
    
    return authenticated

# Helper function that graphically shows the given data
def printData(data):
    for key in data.keys():
        if ":" in key:
            print(key + "" + data[key])
        else:
            print(key + ": " + data[key])

def connectToServer(port):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.settimeout(5)  # Set a timeout of 5 seconds for connection attempts
    try:
        clientSocket.connect((HOST_IP, port))
    except socket.timeout:
        print("Connection attempt timed out.")
        return None
    except Exception as e:
        print("An error occurred:", e)
        return None
    return clientSocket

# Authenticate function remains unchanged

# The continuous loop that lets the user performs the actions it wants
# Every option is accompanied by an authentication
while True:
    option = input("Please choose an option: Mail Sending/Mail Management/Mail Searching/Exit: ").upper()

    try:
        if option == "MAIL SENDING":
            clientSocket = connectToServer(POP3_PORT)
            if clientSocket:
                authenticated = authenticate(clientSocket)
                clientSocket.shutdown(socket.SHUT_RDWR)
                clientSocket.close()

                if authenticated:
                    print("LOGGED IN")
                    mail = constructMail()
                    clientSocket = connectToServer(SMTP_PORT)
                    if clientSocket:
                        sendMail(mail)
                        clientSocket.shutdown(socket.SHUT_RDWR)
                        clientSocket.close()
                    else:
                        print("Cannot connect to SMTP socket.")
            else:
                print("Cannot connect to POP3 server socket.")

        elif option == "MAIL MANAGEMENT":
            clientSocket = connectToServer(POP3_PORT)
            if clientSocket:
                if authenticate(clientSocket):
                    print("LOGGED IN")
                    while True:
                        action = input("Please choose an action to perform (STAT, LIST, RETR, DELE, RSET, QUIT): ").upper()
                        response = manageMails(action)
                        if response:
                            printData(response)
                        if action == "QUIT":
                            break
                    clientSocket.shutdown(socket.SHUT_RDWR)
                    clientSocket.close()
            else:
                print("Cannot connect to POP3 server socket.")

        elif option == "MAIL SEARCHING":
            clientSocket = connectToServer(POP3_PORT)
            if clientSocket:
                if authenticate(clientSocket):
                    print("LOGGED IN")
                    while True:
                        base = input("Search related e-mails based on ([1)] Words/sentences, [2)] Time, [3)] Address / QUIT): ")
                        if base != "1)" and base != "2)" and base != "3)":
                            break
                        search = input("Enter the look-up for your e-mail: ")
                        searchMails(base, search)
                    clientSocket.shutdown(socket.SHUT_RDWR)
                    clientSocket.close()
            else:
                print("Cannot connect to POP3 server socket.")

        elif option == "EXIT":
            break

        else:
            print("That is not a valid command.")
    except Exception as e:
        print("An error occurred:", e)

