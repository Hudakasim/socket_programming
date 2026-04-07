import socket

HOST = "127.0.0.1"
PORT = 7800 # the port used by the server

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    s.sendall(b"Merhaba benim adim HUDA")
    data = s.recv(1024)

print(f"Rececived {data!r}")
