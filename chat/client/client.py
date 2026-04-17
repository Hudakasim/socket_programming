import socket
import threading
import queue
import sys
import time
sys.path.append("..")

from shared.protocol import *

# this queue is the bridge between the network thread and whatever UI you use
packet_queue = queue.Queue()

_sock = None
_username = None
_lock = threading.Lock()


def receive_loop(sock):
    # background thread - recv packets and puts them in the Q
    while True:
        packet = recv_packet(sock)
        if not packet:
            packet_queue.put({"type": "error", "text": "Lost connection to server"})
            # start reconnect attempt in a new thread
            thread = threading.Thread(target=reconnect_loop)
            thread.daemon = True
            thread.start()
            break
        packet_queue.put(packet)

def reconnect_loop():
    global _sock

    wait = RECONNECT_BASE

    for attempt in range(1, RECONNECT_ATTEMPTS + 1):
        packet_queue.put({
            "type": "reconnecting",
            "attempt": attempt,
            "max": RECONNECT_ATTEMPTS,
            "wait": wait
        })

        time.sleep(wait)
        try:
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.connect((CLIENT_HOST, PORT))

            send_packet(new_sock, {"type": TYPE_JOIN, "username": _username})

            with _lock:
                _sock = new_sock

            thread = threading.Thread(target=receive_loop, args=(new_sock,))
            thread.daemon = True
            thread.start()

            packet_queue.put({
                "type": TYPE_RECONNECTED,
                "text": f"Reconnected as {_username}"
            })
            return
        except Exception as e:
            print(f"[reconnect] attempt {attempt} failed: {e}")

            wait = min(wait * 2, RECONNECT_MAX)

    packet_queue.put({
        "type": TYPE_DISCONNECTED,
        "text": "Could not reconnect. please restart the app.",
        "fatal": True
    })


def send_message(sock, username, text):
    with _lock:
        active_sock = _sock
        if active_sock:
            # send a chat message packet
            send_packet(active_sock, {"type": TYPE_MESSAGE, "username": username, "text": text})


def send_private(sock, to_username, text):
    with _lock:
        active_sock = _sock
    if active_sock:
        send_packet(sock, {
            "type": TYPE_PRIVATE,
            "to": to_username,
            "text": text
        })

def connect(username) -> socket.socket:
    global _sock, _username
    # connect -> send join packet, start recv thread -> returns the socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((CLIENT_HOST, PORT))

    # first thing we send is always a join packet
    send_packet(sock, {"type": TYPE_JOIN, "username": username})

    _username = username
    _sock = sock
    # after send the JOIN packet we wait to see the response from server
    response = recv_packet(sock)

    if not response:
        sock.close()
        raise Exception("Server dropped the connection without answering.")

    if response.get("type") == "error":
        sock.close()
        raise Exception(response.get("text"))

    # no error the server accept the client:
    packet_queue.put(response)

    # start background recv thread
    recv_thread = threading.Thread(target=receive_loop, args=(sock,))
    recv_thread.daemon = True
    recv_thread.start()

    return sock
