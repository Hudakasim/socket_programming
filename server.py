import socket
import threading

def handle_client(conn, addr):
    print(f"[+] Client connected: {addr}")
    while True:
        try:
            message = conn.recv(1024)
            if not message:
                print(f"[-] Client disconnected: {addr}")
                break
            print(f"[Client]: {message.decode()}")

            reply = input("[You]: ")
            conn.send(reply.encode())

        except ConnectionResetError:
            print(f"[-] Client forcefully disconnected: {addr}")
            break

    conn.close()

def start_server(host="127.0.0.1", port=9090):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)  # only expect 1 client for now
    print(f"[*] Server listening on {host}:{port}")

    conn, addr = server.accept()  # blocks until a client connects

    # handle the client in a thread (good habit before 1-to-many)
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()
    thread.join()  # wait for the thread to finish before closing

    server.close()

start_server()
