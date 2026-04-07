"""
=============================================================
  CMPT 371 - Assignment 3: Multi-Client TCP Chat Server
=============================================================
  File    : server.py
  Purpose : Accepts multiple client connections over TCP,
            manages usernames, and broadcasts messages to
            all connected clients.
  Usage   : python server.py [--host HOST] [--port PORT]
=============================================================
"""

import socket
import threading
import argparse
import datetime
import sys


DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 9090
BUFFER_SIZE  = 4096
MAX_USERNAME_LEN = 24

clients_lock = threading.Lock()
clients      = {}   # socket -> username
addresses    = {}   # socket -> (ip, port)


def timestamp() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def broadcast(message: str, exclude_socket=None) -> None:
    """Send message to every connected client except exclude_socket."""
    encoded = message.encode("utf-8")
    with clients_lock:
        targets = list(clients.keys())
    for sock in targets:
        if sock is exclude_socket:
            continue
        try:
            sock.sendall(encoded)
        except OSError:
            pass


def send_private(message: str, target_socket: socket.socket) -> None:
    """Send message to one specific client only."""
    try:
        target_socket.sendall(message.encode("utf-8"))
    except OSError:
        pass


def register_client(conn: socket.socket, addr: tuple):
    """
    Username handshake:
      1. Server sends USERNAME_REQUEST
      2. Client replies with desired username
      3. Server replies USERNAME_OK, USERNAME_TAKEN, or USERNAME_INVALID
    Returns the accepted username, or None if client disconnected.
    """
    conn.sendall(b"USERNAME_REQUEST\n")

    while True:
        try:
            raw = conn.recv(BUFFER_SIZE)
        except OSError:
            return None
        if not raw:
            return None

        username = raw.decode("utf-8").strip()

        if not username or len(username) > MAX_USERNAME_LEN:
            conn.sendall(b"USERNAME_INVALID\n")
            continue

        with clients_lock:
            taken = username in clients.values()
            if not taken:
                clients[conn]   = username
                addresses[conn] = addr

        if taken:
            conn.sendall(b"USERNAME_TAKEN\n")
        else:
            conn.sendall(b"USERNAME_OK\n")
            return username


def remove_client(conn: socket.socket):
    """Remove client from shared state and close socket."""
    with clients_lock:
        username = clients.pop(conn, None)
        addresses.pop(conn, None)
    try:
        conn.close()
    except OSError:
        pass
    return username


def handle_client(conn: socket.socket, addr: tuple) -> None:
    """Thread entry point — manages one client for its entire session."""
    print(f"[{timestamp()}] New connection from {addr[0]}:{addr[1]}")

    username = register_client(conn, addr)
    if username is None:
        remove_client(conn)
        return

    print(f"[{timestamp()}] '{username}' joined")

    # Announce join to everyone else
    broadcast(f"SYSTEM|{username} joined the chat.|{timestamp()}\n", exclude_socket=conn)

    # Welcome message + current online roster for the new user
    with clients_lock:
        online = list(clients.values())
    send_private(
        f"SYSTEM|Welcome, {username}! {len(online)} user(s) online.|{timestamp()}\n",
        conn
    )
    for existing_user in online:
        if existing_user != username:
            send_private(f"USERLIST|{existing_user}|{timestamp()}\n", conn)

    # Main receive loop
    while True:
        try:
            raw = conn.recv(BUFFER_SIZE)
        except OSError:
            break
        if not raw:
            break

        text = raw.decode("utf-8").strip()

        if text == "/quit":
            break

        elif text == "/list":
            with clients_lock:
                online = list(clients.values())
            send_private(
                f"SYSTEM|Online users: {', '.join(online)}|{timestamp()}\n",
                conn
            )

        elif text.startswith("/msg "):
            parts = text.split(" ", 2)
            if len(parts) < 3:
                send_private(f"SYSTEM|Usage: /msg <username> <message>|{timestamp()}\n", conn)
                continue
            target_name  = parts[1]
            private_text = parts[2]
            with clients_lock:
                target_sock = next(
                    (s for s, n in clients.items() if n == target_name), None
                )
            if target_sock is None:
                send_private(f"SYSTEM|User '{target_name}' not found.|{timestamp()}\n", conn)
            else:
                send_private(f"PRIVATE|{username}|{private_text}|{timestamp()}\n", target_sock)
                send_private(f"PRIVATE_SENT|{target_name}|{private_text}|{timestamp()}\n", conn)

        else:
            # Regular message — broadcast to everyone including sender
            broadcast(f"MSG|{username}|{text}|{timestamp()}\n")
            print(f"[{timestamp()}] {username}: {text}")

    # Cleanup on disconnect
    departed = remove_client(conn)
    if departed:
        print(f"[{timestamp()}] '{departed}' disconnected.")
        broadcast(f"SYSTEM|{departed} left the chat.|{timestamp()}\n")


def start_server(host: str, port: int) -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(10)

    print("=" * 50)
    print("  CMPT 371 Chat Server")
    print(f"  Listening on {host}:{port}")
    print("  Press Ctrl+C to stop.")
    print("=" * 50)

    try:
        while True:
            conn, addr = server_sock.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Server shutting down.")
    finally:
        server_sock.close()
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    start_server(args.host, args.port)
