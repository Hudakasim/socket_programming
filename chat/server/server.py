import socket
import threading
import sys
sys.path.append("..")

from shared.protocol import *

# each entry will be (conn, addr, username)
clients = []
lock = threading.Lock()

pending_offers = {}

def get_conn_by_username(username):
    with lock:
        for conn, addr, uname in clients:
            if uname == username:
                return conn
    return None

def broadcast(packet: dict, exlude_conn=None):
    # send a message to every client except the sender
    with lock:
        for conn, addr, username in clients[:]:
            if conn == exlude_conn:
                continue
            try:
                send_packet(conn, packet)
            except:
                clients.remove((conn, addr, username))

def send_private(from_username, to_username, text, sender_conn):
    target_conn = get_conn_by_username(to_username)

    if not target_conn:
        # user not found
        return False

    send_packet(target_conn, {
        "type": TYPE_PRIVATE,
        "to": from_username,
        "text": text
    })

    send_packet(sender_conn, {
        "type": TYPE_PRIVATE,
        "from": "You",
        "to": to_username,
        "text": text
    })

    return True

# def forward_file_offer(packet, sender_conn, sender_username):
#     to = packet.get("to", "")
#     target_conn = get_conn_by_username(to)

#     if not target_conn:
#         send_packet(sender_conn, {
#             "type": TYPE_ERROR,
#             "text": f"User '{to}' not found"
#         })
#         return
#     packet["from"] = sender_username
#     send_packet(target_conn, packet)


# def forwa_response(packet, responder_username):
#     to = packet.get("to", "")
#     target_conn = get_conn_by_username(to)

#     if not target_conn:
#         return
#     packet["from"] = responder_username
#     send_packet(target_conn, packet)

def forward_file_chunks(sender_conn, receiver_conn, sender_username, filename, filesize, transfer_done):
    # target_conn = get_conn_by_username(to_username)
    # if not target_conn:
    #     send_packet(sender_conn, {"type": TYPE_ERROR, "text": "Recipient disconnected"})
    #     return

    bytes_forwarded = 0

    try:
        while bytes_forwarded < filesize:
            chunk = recv_chunk(sender_conn)
            if not chunk:
                print(f"[file] connection lost during transfer of {filename}")
                break
            send_chunk(receiver_conn, chunk)
            bytes_forwarded += len(chunk)
    except OSError as e:
        print(f"[file] transfer error during {filename}: {e}")

    try:
        send_packet(receiver_conn, {
            "type": TYPE_FILE_DONE,
            "filename": filename,
            "from": sender_username
        })
    except OSError:
        print(f"[file] could not notify receiver: {filename}")

    try:
        send_packet(sender_conn, {
            "type": TYPE_FILE_DONE,
            "filename": filename,
            "to": sender_username
        })
    except OSError:
        print(f"[file] could not notify sender: {filename}")

    print(f"[file] {sender_username} → {filename} ({bytes_forwarded}/{filesize} bytes)")
    transfer_done.set()


def handle_client(conn, addr):
    packet = recv_packet(conn)

    # ========== recv the JOIN packet ===============
    if not packet or packet.get("type") != TYPE_JOIN:
        send_packet(conn, {"type": TYPE_ERROR, "text": "text: First message must be a join packet"})
        conn.close()
        return

    username = packet.get("username", "").strip()

    # ========= validate username ==================
    with lock:
        taken = any(u == username for _, _, u in clients)

        # for conn, addr, u in clients:
        #     if u == username:
        #         taken = True
        #         break

    if not username or taken:
        send_packet(conn, {
            "type": TYPE_ERROR,
            "text": "Username is empty or already taken"
        })
        conn.close()
        return

    # ======== register client and announce it ==========
    with lock:
        clients.append((conn, addr, username))

    print(f"[+] {username} connected from {addr}. Total: {len(clients)}")

    broadcast({"type": TYPE_SERVER, 'text': f"{username} has joined the chat!"}, exlude_conn=conn)

    send_packet(conn, {"type": TYPE_SERVER, "text": f"Welcom {username} ({len(clients)-1} user(s) online)"})

    while True:
        packet = recv_packet(conn)

        # recv_packet return empty -> while loop breaks
        if not packet:
            break

        packet_type = packet.get("type")

        if packet_type == TYPE_MESSAGE:
            text = packet.get("text", "")
            print(f"[{username}]: {text}")

            # broadcast to everyone (except the sender)
            broadcast({"type": TYPE_MESSAGE, "username": username, "text": text}, exlude_conn=conn)

        elif packet_type == TYPE_PRIVATE:
            to = packet.get("to", "").strip()
            text = packet.get("text", "")

            if to == username:
                send_packet(conn, {"type": TYPE_ERROR, "text": "You can't message yourself"})
                continue

            success = send_private(username, to, text, conn)

            if not success:
                send_packet(conn, {"type": TYPE_ERROR, "text": f"User 'to' not found or not online"})

        elif packet_type == TYPE_FILE_OFFER:
            to       = packet.get("to", "")
            filename = packet.get("filename")
            filesize = packet.get("filesize")

            target_conn = get_conn_by_username(to)
            if not target_conn:
                send_packet(conn, {"type": TYPE_ERROR, "text": f"User '{to}' not found."})
                continue

            transfer_done = threading.Event()

            # store the offer so we can look it up when receiver accepts
            pending_offers[(username, filename)] = {
                "filesize": filesize,
                "sender_conn": conn,
                "to": to,
                "transfer_done": transfer_done
            }

            # forward offer to receiver
            send_packet(target_conn, {
                "type": TYPE_FILE_OFFER,
                "from": username,
                "filename": filename,
                "filesize": filesize
            })
            # BLOCK the sender's loop here until transfer is done or rejected
            print(f"[file] {username} offering '{filename}' to {to} — sender paused")
            transfer_done.wait()
            print(f"[file] sender {username} resumed after '{filename}'")

        elif packet_type == TYPE_FILE_ACCEPT:
            # this runs in the RECEIVER's thread
            from_username = packet.get("to")
            filename = packet.get("filename")
            filesize = packet.get("filesize")

            offer_key = (from_username, filename)
            offer = pending_offers.pop(offer_key, None)

            if not offer:
                send_packet(conn, {"type": TYPE_ERROR, "text": "File offer not found or expired."})
                continue

            sender_conn = offer["sender_conn"]
            transfer_done = offer["transfer_done"]

            # tell sender to start sending chunks
            send_packet(sender_conn, {
                "type": TYPE_FILE_ACCEPT,
                "from": username,
                "filename": filename,
                "filesize": filesize
            })

            # NOW block this thread to forward chunks
            # recv_packet() won't be called again until this returns
            forward_file_chunks(sender_conn, conn, from_username, filename, filesize, transfer_done)

        elif packet_type == TYPE_FILE_REJECT:
            from_username = packet.get("to")
            filename = packet.get("filename")

            offer_key = (from_username, filename)
            offer = pending_offers.pop(offer_key, None)

            sender_conn = get_conn_by_username(from_username)
            if sender_conn:
                send_packet(sender_conn, {
                    "type": TYPE_FILE_REJECT,
                    "from": username,
                    "filename": filename
                })
            # unblock the sender's loop even on rejection
            if offer:
                offer["transfer_done"].set()
        else:
            print(f"[!] Unknown packet type from {username}: {packet_type}")

    # ======= cleanup when dicconnect =========
    with lock:
        if (conn, addr, username) in clients:
            clients.remove((conn, addr, username))

    conn.close()
    print(f"[-] {username} disconnected. Total: {len(clients)}")

    broadcast({"type": TYPE_SERVER, "text": f"{username} has left the chat."})

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()

    print(f"Server started on {HOST}:{PORT}")
    print(f"Waiting for connections....\n")

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


