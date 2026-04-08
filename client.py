"""
=============================================================
  CMPT 371 - Assignment 3: Chat Client (Network Layer)
=============================================================
  File    : client.py
  Purpose : Handles all TCP socket communication with the
            server. Imported and used by gui_client.py.
  Usage   : python client.py  (CLI mode for quick testing)
=============================================================
"""

import socket
import threading
import argparse
import sys
from typing import Optional

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9090
BUFFER_SIZE  = 4096


class ChatClient:
    """
    Manages the TCP connection to the chat server.
    The GUI drives it via connect(), send_message(), disconnect().
    Incoming messages are delivered via the on_message callback.
    """

    def __init__(self, on_message=None, on_disconnect=None):
        self.sock: Optional[socket.socket] = None
        self.username      = None
        self.connected     = False
        self.on_message    = on_message    or (lambda msg: print(msg))
        self.on_disconnect = on_disconnect or (lambda: None)
        self._recv_thread  = None

    def connect(self, host: str, port: int, username: str):
        """
        Open TCP connection and complete username handshake.
        Returns (True, "") on success or (False, error_string) on failure.
        """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((host, port))
            self.sock.settimeout(None)
        except OSError as e:
            return False, f"Cannot reach server: {e}"

        # Receive USERNAME_REQUEST from server
        try:
            prompt = self._recv_line()
        except OSError as e:
            return False, f"Handshake failed: {e}"

        if prompt != "USERNAME_REQUEST":
            return False, f"Unexpected server response: {prompt!r}"

        # Send chosen username
        self._send_raw(username)

        # Receive server's verdict
        try:
            response = self._recv_line()
        except OSError as e:
            return False, f"Handshake error: {e}"

        if response == "USERNAME_TAKEN":
            self.sock.close()
            return False, "Username already taken. Please choose another."
        if response == "USERNAME_INVALID":
            self.sock.close()
            return False, "Username invalid (empty or too long)."
        if response != "USERNAME_OK":
            self.sock.close()
            return False, f"Unknown server response: {response!r}"

        # Success — start background receive thread
        self.username  = username
        self.connected = True
        self._recv_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._recv_thread.start()
        return True, ""

    def send_message(self, text: str) -> None:
        """Send a message or command to the server."""
        text = text.strip()
        if not text or not self.connected:
            return
        self._send_raw(text)

    def disconnect(self) -> None:
        """Gracefully disconnect from the server."""
        if self.connected:
            self.send_message("/quit")
        self._handle_disconnect()

    def _send_raw(self, text: str) -> None:
        sock = self.sock
        if sock is None:
            self._handle_disconnect()
            return
        try:
            sock.sendall((text + "\n").encode("utf-8"))
        except OSError:
            self._handle_disconnect()

    def _recv_line(self) -> str:
        """Read one newline-terminated line (used during handshake)."""
        sock = self.sock
        if sock is None:
            raise OSError("Socket is not connected.")
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(BUFFER_SIZE)
            if not chunk:
                raise OSError("Server closed connection.")
            buf += chunk
        return buf.split(b"\n")[0].decode("utf-8").strip()

    def _receive_loop(self) -> None:
        """
        Background thread: reads data continuously and delivers
        complete lines to on_message(). Handles TCP fragmentation
        by accumulating a buffer and splitting on newlines.
        """
        sock = self.sock
        if sock is None:
            self._handle_disconnect()
            return
        buf = ""
        while self.connected:
            try:
                chunk = sock.recv(BUFFER_SIZE)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk.decode("utf-8")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if line:
                    self.on_message(line)
        self._handle_disconnect()

    def _handle_disconnect(self) -> None:
        sock = self.sock
        self.sock = None
        if not self.connected and sock is None:
            return
        self.connected = False
        try:
            if sock is not None:
                sock.close()
        except OSError:
            pass
        self.on_disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    username = input("Enter username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)

    def on_msg(msg):
        parts = msg.split("|")
        kind  = parts[0] if parts else ""
        if kind == "MSG" and len(parts) == 4:
            print(f"[{parts[3]}] {parts[1]}: {parts[2]}")
        elif kind == "SYSTEM" and len(parts) >= 2:
            print(f"*** {parts[1]} ***")
        else:
            print(msg)

    def on_disc():
        print("Disconnected.")
        sys.exit(0)

    c = ChatClient(on_message=on_msg, on_disconnect=on_disc)
    ok, err = c.connect(args.host, args.port, username)
    if not ok:
        print(f"Failed: {err}")
        sys.exit(1)

    print(f"Connected as '{username}'. Type /quit to exit.")
    try:
        while True:
            line = input()
            if line.strip() == "/quit":
                c.disconnect()
                break
            c.send_message(line)
    except (EOFError, KeyboardInterrupt):
        c.disconnect()
