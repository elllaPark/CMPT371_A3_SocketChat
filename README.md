# CMPT371 A3 SocketChat

A simple TCP-based multi-client chat application built in Python using socket programming.

## Course Information

- Course: CMPT 371 - Data Communications and Networking
- Assignment: Assignment 3 - Socket Programming Project
- Semester: Spring 2026
- Instructor: Mirza Zaeem Baig

## Group Members

| Name         | Student ID | Email         |
| ------------ | ---------- | ------------- |
| Sinhee Park  | 301608438  | spa250@sfu.ca |
| Khalid Karim | 301581950  | kka164@sfu.ca |

## 1. Project Overview

This project is a real-time chat application that uses a client-server architecture over TCP.

- `server.py` accepts multiple clients, manages usernames, and routes messages.
- `client.py` handles the client socket connection and message receiving.
- `gui_client.py` provides the Tkinter GUI for login, chat, private messaging, and the online users list.
  Main supported features:
- multiple clients connected at the same time
- unique username login
- public chat messages
- private messages with `/msg`
- online users sidebar
- instant online user list on login
- join and leave notifications
- `/list` and `/quit` commands
- emoji picker in the GUI

## 2. Limitations and Edge Cases

- The server uses one thread per client. This is fine for a class project, but not ideal for very large-scale systems.
- Chat history is not saved permanently. If the server closes, the current session is lost.
- There is no password or account system. Users are identified only by unique usernames.
- Messages are not encrypted. This project is for socket programming practice, not secure communication.
- The easiest setup is local testing using `127.0.0.1`. Remote use requires correct IP and firewall settings.
- The protocol is simple text over TCP, which is easy to debug but less robust than a production protocol.
- The server validates usernames and basic command format, but it is not designed for malicious traffic.

## 3. Prerequisites

- Python 3.10 or newer
- Tkinter available in your Python installation
  No third-party packages are required. This project uses only Python standard library modules.

## 4. Step-by-Step Run Guide

Open a terminal in the project folder.

### Step 1: Start the server

```bash
python server.py
```

Default server settings:

- Host: `0.0.0.0`
- Port: `9090`

### Step 2: Start the first client

Open a new terminal and run:

```bash
python gui_client.py
```

Then enter:

- Host: `127.0.0.1`
- Port: `9090`
- Username: for example `Khalid`

### Step 3: Start more clients

Open additional terminals and run:

```bash
python gui_client.py
```

Use different usernames such as:

- `Ace`
- `Julia`

### Step 4: Test chat features

- Send a normal message and confirm all connected users receive it.
- Send a private message using:

```text
/msg Ace hello
```

- Show the online user list using:

```text
/list
```

- Disconnect using:

```text
/quit
```

## 5. Optional CLI Client

You can also run the terminal client for quick testing:

```bash
python client.py --host 127.0.0.1 --port 9090
```

## 6. Protocol Summary

Handshake messages:

- `USERNAME_REQUEST`
- `USERNAME_OK`
- `USERNAME_TAKEN`
- `USERNAME_INVALID`
  Chat/event messages:
- `MSG|sender|text|timestamp`
- `SYSTEM|text|timestamp`
- `PRIVATE|from|text|timestamp`
- `PRIVATE_SENT|to|text|timestamp`
- `USERLIST|username|timestamp`

## 7. Suggested Demo Flow

1. Start the server.
2. Connect `Khalid`.
3. Connect `Ace`.
4. Show that users appear instantly in the online list.
5. Connect `Julia`.
6. Send a public message.
7. Send a private message with `/msg`.
8. Use `/list`.
9. Use `/quit` and show the online list updates.

## 8. Video Demo

- Demo link: https://youtu.be/lZaWy4VLZ4w

## 9. Academic Integrity and References

### GenAI Usage

- OpenAI ChatGPT/Codex was used for debugging help, small code fixes, and README polishing.

### References

- Python Socket Programming HOWTO: https://docs.python.org/3/howto/sockets.html
- Python `socket` documentation: https://docs.python.org/3/library/socket.html
- Python `threading` documentation: https://docs.python.org/3/library/threading.html
- Python `tkinter` documentation: https://docs.python.org/3/library/tkinter.html
