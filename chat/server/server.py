import socket
import threading
import sys
sys.path.append("..")

from shared.protocol import (
    HOST, PORT, TYPE_MESSAGE, TYPE_JOIN, TYPE_SERVER, TYPE_ERROR, TYPE_PRIVATE,
    send_packet, recv_packet
)

# each entry will be (conn, addr, username)
clients = []
lock = threading.Lock()

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
    target_conn = None
    with lock:
        for conn, addr, username in clients:
            if username == to_username:
                target_conn = conn
                break

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

    broadcast({"type": TYPE_SERVER, 'text': f"{username} has joined teh chat!"}, exlude_conn=conn)

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
        else:
            print(f"[!] Unknown packet type from {username}: {packet_type}")

    # ======== cleanup when dicconnect =============
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


