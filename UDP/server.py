from socket import *

serverPort = 12000
serverSocket = socket(AF_INET, SOCK_DGRAM)

# sevrver assigned port number 12000 to this socket
# bu using the bind() method
serverSocket.bind(('', serverPort))
print("The server is ready to receive")

while True:
    message, clientAddress = serverSocket.recvfrom(2048)
    modifiedMessage = message.decode().upper()
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)
