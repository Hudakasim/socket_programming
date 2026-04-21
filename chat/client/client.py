import socket
import threading
import queue
import sys
import time
import os
sys.path.append("..")

from shared.protocol import *

# this queue is the bridge between the network thread and whatever UI you use
packet_queue = queue.Queue()

_sock = None
_username = None
_lock = threading.Lock()


DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

_pending_files = {}

def receive_loop(sock):
    # background thread - recv packets and puts them in the Q
    while True:
        # check if we need to start receiving a file inline
        if not _file_accept_queue.empty():
            from_username, filename, filesize = _file_accept_queue.get()

            sock.settimeout(None)
            send_packet(sock, {
                "type": TYPE_FILE_ACCEPT,
                "to": from_username,
                "filename": filename,
                "filesize": filesize
            })
            
            receive_file_chunks(sock, filename, filesize, from_username)
            continue

        # set a timeout so we can check the queue periodically
        sock.settimeout(0.1)
        try:
            packet = recv_packet(sock)
        except:
            continue   # timeout — loop back and check _file_accept_queue again

        sock.settimeout(None)  # restore blocking mode after successful read

        if not packet:
            packet_queue.put({"type": TYPE_DISCONNECTED, "text": "Lost connection to server"})
            # start reconnect attempt in a new thread
            thread = threading.Thread(target=reconnect_loop)
            thread.daemon = True
            thread.start()
            break

        packet_type = packet.get("type")

        if packet_type == TYPE_FILE_ACCEPT:
            thread = threading.Thread(
                target = send_file_chunks,
                args = (sock, packet.get("filename"), packet.get("filesize"), packet.get("from"))
            )
            thread.daemon = True
            thread.start()
        else:
            packet_queue.put(packet)

def send_file_offer(to_username, filepath):
    with _lock:
        sock = _sock
    filename = os.path.basename(filepath)
    filesize = os.path.getsize(filepath)
    _pending_files[filename] = filepath

    send_packet(sock, {
            "type": TYPE_FILE_OFFER,
            "to": to_username,
            "filename": filename,
            "filesize": filesize,
            "filepath": filepath
        })

    packet_queue.put({
            "type": "file_waiting",
            "filename": filename,
            "to": to_username
        })

def send_file_chunks(sock, filename, filesize, to_username):
    filepath = _pending_files.get(filename)
    if not filepath or not os.path.exists(filepath):
        packet_queue.put({"type": "error", "text": f"file not found: {filename}"})
        return

    filesize = os.path.getsize(filepath)
    bytes_sent = 0

    packet_queue.put({
        "type": "file_progress",
        "filename": filename,
        "to": to_username,
        "percent": 0
    })

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            send_chunk(sock, chunk)
            bytes_sent += len(chunk)
            percent = int(bytes_sent / filesize * 100)

            packet_queue.put({
                "type": "file_progress",
                "filename": filename,
                "to": to_username,
                "percent": percent
            })

    packet_queue.put({
        "type": "'file_sent",
        "filename": filename,
        "to": to_username
    })


def receive_file_chunks(sock, filename, filesize, from_username):
    filepath = os.path.join(DOWNLOADS_DIR, filename)
    bytes_recv = 0

    print(f"[recv] starting — expecting {filesize} bytes")

    packet_queue.put({
        "type": "file_progress",
        "filename": filename,
        "from": from_username,
        "percent": 0
    })

    try:
        with open(filepath, "wb") as f:
            while bytes_recv < filesize:
                chunk = recv_chunk(sock)
                if not chunk:
                    print(f"[recv] recv_chunk returned None at {bytes_recv}/{filesize}")
                    break

                f.write(chunk)
                bytes_recv += len(chunk)
                percent = int(bytes_recv / filesize * 100)
                print(f"[recv] got chunk {len(chunk)} bytes, total {bytes_recv}/{filesize} ({percent}%)")

                packet_queue.put({
                    "type": "file_progress",
                    "filename": filename,
                    "from": from_username,
                    "percent": percent
                })
        print(f"[recv] done — {bytes_recv}/{filesize} bytes")

    except Exception as e:
        packet_queue.put({"type": "error", "text": f"File receive error: {e}"})
        return

    packet_queue.put({
        "type"    : "file_received",
        "filename": filename,
        "from"    : from_username,
        "filepath": filepath
    })

    done = recv_packet(sock)
    if done:
        packet_queue.put(done)

def accept_file(from_username, filename, filesize):
    # with _lock:
    #     sock = _sock

    # send_packet(sock, {
    #     "type": TYPE_FILE_ACCEPT,
    #     "to": from_username,
    #     "filename": filename,
    #     "filesize": filesize
    # })

    _file_accept_queue.put((from_username, filename, filesize))

def reject_file(from_username, filename):
    with _lock:
        sock = _sock
    send_packet(sock, {
        "type": TYPE_FILE_REJECT,
        "to": from_username,
        "filename": filename
    })

_file_accept_queue = queue.Queue()

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
