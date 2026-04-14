import socket
import threading
import queue
import sys
sys.path.append("..")

from shared.protocol import CLIENT_HOST, PORT, BUFFER_SIZE

# this queue is the bridge between the network thread and whatever UI you use
message_queue = queue.Queue()


def receive_messages(sock):
    """Runs in a background thread — receives and queues incoming messages."""
    while True:
        try:
            message = sock.recv(BUFFER_SIZE)
            if not message:
                message_queue.put("[Server]: Connection closed.")
                break
            message_queue.put(message.decode())
        except:
            message_queue.put("[Server]: Lost connection.")
            break


def send_message(sock, message):
    """Call this to send a message to the server."""
    try:
        sock.send(message.encode())
    except:
        print("[!] Failed to send message.")


def connect(username):
    """
    Connect to the server and return the socket.
    Sends username immediately after connecting.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((CLIENT_HOST, PORT))

    # first thing we send is always the username
    sock.send(username.encode())

    # start background thread for receiving
    recv_thread = threading.Thread(target=receive_messages, args=(sock,))
    recv_thread.daemon = True
    recv_thread.start()

    return sock


if __name__ == "__main__":
    username = input("Enter your username: ")
    sock = connect(username)
    print(f"Connected as {username}. Type 'quit' to exit.\n")

    while True:
        msg = input()
        if msg.lower() == "quit":
            break
        send_message(sock, msg)
        print(f"[{username}]: {msg}")

    sock.close()
