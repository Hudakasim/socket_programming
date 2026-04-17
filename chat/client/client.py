import socket
import threading
import queue
import sys
sys.path.append("..")

from shared.protocol import (
    CLIENT_HOST, PORT,
    TYPE_JOIN, TYPE_MESSAGE,
    send_packet, recv_packet
    )

# this queue is the bridge between the network thread and whatever UI you use
packet_queue = queue.Queue()


def receive_loop(sock):
    # background thread - recv packets and puts them in the Q
    while True:
        packet = recv_packet(sock)
        if not packet:
            packet_queue.put({"type": "error", "text": "Lost connection to server"})
            break
        packet_queue.put(packet)


def send_message(sock, username, text):
    # send a chat message packet
    send_packet(sock, {"type": TYPE_MESSAGE, "username": username, "text": text})


def connect(username) -> socket.socket:
    # connect -> send join packet, start recv thread -> returns the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((CLIENT_HOST, PORT))

    # first thing we send is always a join packet
    send_packet(sock, {"type": TYPE_JOIN, "username": username})

    # start background recv thread
    recv_thread = threading.Thread(target=receive_loop, args=(sock,))
    recv_thread.daemon = True
    recv_thread.start()

    return sock
