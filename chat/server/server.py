import socket
import threading
import sys
sys.path.append("..")

from shared.protocol import SERVER_HOST, PORT, BUFFER_SIZE

# each entry will be (conn, addr, username)
clients = []
lock = threading.Lock()

def broadcast(message, sender_conn):
    # send a message to every client except the sender
    with lock:
        for conn, addr, username in clients:
            if conn != sender_conn:
                try:
                    conn.send(message)
                except:
                    clients.remove((conn, addr, username))

def handle_client(conn, addr):
    try:
        username = conn.recv(BUFFER_SIZE).decode()
    except:
        conn.close()
        return
    with lock:
        clients.append((conn, addr, username))

    print(f"{username} connected from {addr}. Total cients: {len(clients)}")
    broadcast(f"[Server]: {username} has joined the chat!".encode(), conn)

    while True:
        try:
            message = conn.recv(BUFFER_SIZE)
            if not message:
                break
            full_message = f"[{username}]: {message.decode()}"
            print(full_message)
            broadcast(full_message.encode(), conn)

        except ConnectionResetError:
            break

    with lock:
        clients.remove((conn, addr, username))
    conn.close()
    print(f"{username} disconnected. Total clients: {len(clients)}")
    broadcast(f"[Server]: {username} has left the chat.".encode(), conn)


def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((SERVER_HOST, PORT))
    server.listen()

    print(f"Server started on {SERVER_HOST}:{PORT}")
    print(f"Witing for connections....\n")

    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
        except KeyboardInterrupt:
            print("\n shutting down the server")
            break

    server.close()

start_server()


