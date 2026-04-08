import sys
import socket
import selectors
import types

sel = selectors.DefaultSelector()
messages = [b"merhabaa", b"benim adim Huda"]

def start_connection(host, port, num_conns):
    server_addr = (host, port)
    for i in range(0, num_conns):
        connid = i +1
        print(f"Starting connection {connid} to {server_addr}")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setblocking(False)
        sock.connect_ex(server_addr)
        events = selectors.EVENT_READ | selectors.EVENT_WRITE

        data = types.SimpleNamespace(
            addr=server_addr,
            connid = connid,
            msg_total = sum(len(m) for m in messages),
            recv_total = 0,
            messages = messages.copy(),
            outb=b"",
        )
        sel.register(sock, events, data=data)

# GELEN GIDEN VERILER
def service_connection(key, mask):
    sock = key.fileobj
    data = key.data

    # EVENT_READ --> socket okunmaya hazir
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)
        if recv_data:
            print(f"Received {recv_data} from connection {data.connid}")
        # client baglantiyi kesti
        if not recv_data or data.recv_total == data.msg_total:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock) # selector ile takbini kaldiririz
            sock.close()
    # EVENT_WRITE --> socket veri gondermeye acik
    if mask & selectors.EVENT_WRITE:
        if not data.outb and data.messages:
            data.outb = data.messages.pop(0)
        if data.outb:
            print(f"Sending {data.outb} to connection {data.addr}")
            sent = sock.send(data.outb) # veriyi gonderoiriz ve kac byte oldugunu dondurur
            data.outb = data.outb[sent:] # gonderileni hafizadan siliyoruz ki bi daha gonderilmesin

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Kullanım: python {sys.argv[0]} <host> <port> <baglanti_sayisi>")
        sys.exit(1)

    host, port, num_conns = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])

    # 1. Önce bağlantıları başlat
    start_connection(host, port, num_conns)

    # 2. Sonsuz radar döngüsüne gir
    try:
        while True:
            events = sel.select(timeout=1)

            # Eğer tüm soketler kapandıysa (liste boşaldıysa) programı bitir
            if not sel.get_map():
                print("Tüm bağlantılar tamamlandı. İstemci kapanıyor.")
                break

            for key, mask in events:
                service_connection(key, mask)

    except KeyboardInterrupt:
        print("Kullanıcı tarafından durduruldu.")
    finally:
        sel.close()
