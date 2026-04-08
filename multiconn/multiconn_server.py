import sys
import socket
import selectors
import types

# create selector to monitor sockets
sel = selectors.DefaultSelector()

host, port = sys.argv[1], int(sys.argv[2])


# YENI BAGLANTI KURMA
def accept_wrapper(sock):
    conn, addr = sock.accept()
    print(f"Accepted connection from {addr}")
    conn.setblocking(False)

    # client icin hafizada ozel bir nesne olusturmak
    # inb --> cliend'ten okuncak verileri
    # outb --> client'e gondericegimiz veriler
    data = types.SimpleNamespace(addr = addr, inb=b"", outb=b"")

    # bu socketi hem veri geldi mi (READ),
    # hem de veri yazmaya musait mi (WRITE) diye takip etmek istiyoruz
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


# GELEN GIDEN VERILER
def service_connection(key, mask):
    sock = key.fileobj
    data = key.data

    # EVENT_READ --> socket okunmaya hazir
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)
        if recv_data:
            data.outb += recv_data.upper()
        # client baglantiyi kesti
        else:
            print(f"Closing connection to {data.addr}")
            sel.unregister(sock) # selector ile takbini kaldiririz
            sock.close()
    # EVENT_WRITE --> socket veri gondermeye acik
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(f"Echoing {data.outb} to {data.addr}")
            sent = sock.send(data.outb) # veriyi gonderoiriz ve kac byte oldugunu dondurur
            data.outb = data.outb[sent:] # gonderileni hafizadan siliyoruz ki bi daha gonderilmesin


# lsock --> TCP socket
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")

# make teh socket non-blocking
# socket default is blocking
lsock.setblocking(False)

# tell the selector about new clients
# EVENT_READ = baglanti istegi
# data = None --> ana socket oldugunu ayirt etmek icin
sel.register(lsock, selectors.EVENT_READ, data=None)

try:
    while True:
        # selector'un izledigi tum socketleri kontrol ettigi yerdir
        events = sel.select(timeout=None)
        for key, mask in events:
            # sockette bir hareket varsa
            # ve o hareketin gelidigi socketin datasi None ise (ana socket)
            if key.data is None:
                accept_wrapper(key.fileobj)
            # hareketli socket ana socket degil (daha once baglanmis bir client)
            else:
                service_connection(key, mask)
except KeyboardInterrupt:
    print("Caught keyboard interrupt, exiting")
finally:
    sel.close()


