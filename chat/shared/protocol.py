import json
import struct


# ===== Connections ========
HOST = "0.0.0.0"
CLIENT_HOST = "10.10.190.64"
PORT = 9090
BUFFER_SIZE = 4096

# ====== Message Types ======
TYPE_MESSAGE = "message"
TYPE_JOIN = "join"
TYPE_LEAVE = "leave"
TYPE_SERVER = "server"
TYPE_ERROR = "error"

# ===== Packet Helper =======

def send_packet(sock, packet: dict):
    # py dict -> json b-> calc it's length
    raw = json.dumps(packet).encode("utf-8")

    # packs the length into 4 byte header
    length = struct.pack("!I", len(raw))

    sock.sendall(length + raw)


def recv_packet(sock) -> dict:
    # reads 4 bytes -> to figure out how long is the message packet
    raw_length = _recv_exactly(sock, 4)
    if not raw_length:
        return None

    # reads the packet and converts back to dict
    length = struct.unpack("!I", raw_length)[0]
    raw = _recv_exactly(sock, length)
    if not raw:
        return None

    return json.loads(raw.decode("utf-8"))


# keep reading until we have exactly n bytes
# prevent the app from crush if a msg arrived in pieces!!!
def _recv_exactly(sock, n: int) -> bytes:
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data
