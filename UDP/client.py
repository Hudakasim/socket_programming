from socket import *

serverName = '10.10.190.64'
serverPort = 12000

# create UDP socket for server
clientSocket = socket(AF_INET, SOCK_DGRAM)
# get user keyboard input
message = input('Input lowcase sentence:')
# uses sento() method to send the application layer message to the client socket
clientSocket.sendto(message.encode(), (serverName, serverPort))

# client reads a replay back from the server using recvfrom() method
# return the message & the sender's ip
modifiedMessage, serverAddress = clientSocket.recvfrom(2048)
print(modifiedMessage.decode())

clientSocket.close()

