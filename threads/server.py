import socket
import threading

def handle_client(conn, addr):
    print(f"Client connected: {addr}")
    while True:
        try:
            # read up to 1024 bytes from the socket's receive buffer
            message = conn.recv(1024)

            # an empty byte string means the client gracefully closed the connection
            if not message:
                print(f"Client disconnected: {addr}")
                break
            print(f"[Client]: {message.decode()}")

            # get input from the srver admin and send it by the socket
            reply = input("[You]: ")
            conn.send(reply.encode())

        except ConnectionResetError:
            # handle client unexpected disconnections
            print(f"Client forcefully disconnected: {addr}")
            break
    # release the socket file descriptor back to the OS
    conn.close()

def start_server(host="127.0.0.1", port=9090):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # tells the OS to let you reuse the address immediately
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(1)  # only expect 1 client for now
    print(f"Server listening on {host}:{port}")

    # conn (new socketjust for that client) add (the address of the client)
    conn, addr = server.accept()  # blocks until a client connects

    # spawm a new worker thread to handle the client'd I/O operations
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()

    # blocks the Main Thread until the worker thread finishes.
    # remove it when u want to accept multiple clients
    thread.join()  # wait for the thread to finish before closing

    # close the main listening socket
    server.close()

start_server()
