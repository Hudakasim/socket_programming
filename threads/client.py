import socket
import threading

def receive_messages(sock):
    while True:
        try:
            message = sock.recv(1024)

            # empty byte string means the server gracefully terminated the connection
            if not message:
                print("Server closed the connection.")
                break
            print(f"\n[Server]: {message.decode()}")

            print("[You]: ", end="", flush=True)  # re-print prompt nicely

        except ConnectionResetError:
            # handle unexpected connection drops
            print("Lost connection to server.")
            break

def start_client(host="127.0.0.1", port=9090):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    print(f"Connected to server at {host}:{port}")

    # receive in background so we can type at the same time
    recv_thread = threading.Thread(target=receive_messages, args=(client,))

    # daemon --> the OS will forcefully kill this thread when the mian thread exits
    recv_thread.daemon = True
    recv_thread.start()

    while True:
        try:
            # block execution here waiting for standard input
            msg = input("[You]: ")

            # graceful exit condition
            if msg.lower() == "quit":
                print("Disconnecting...")
                break

            # push the msg to the socket's send buffer
            client.send(msg.encode())

        except KeyboardInterrupt:
            # handle ctrl+c
            break

    # release the socket resource back to the OS
    client.close()

start_client()
