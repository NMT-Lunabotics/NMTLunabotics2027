#!/usr/bin/env python3

# Imports needed to monitor robot heartbeat
import re, socket, threading, time

# Config options, make these match the robot heartbeat settings
PORT=10000
PREFIX="NMT26"

# Initalization, some code to initialize a new heartbeat socket
PATTERN=re.compile(rf"{re.escape(PREFIX)}:([A-Za-z0-9_.-]+)")
heartbeat_socket=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
heartbeat_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
heartbeat_socket.bind(("", PORT))

# Loop to listion to heartbeat. This is multi-threaded so that it is not blocking. Only while True: loop is needed if threading is not needed
def listen():
    while True:
        # Pull all socket data from PORT, and pattern match that to PATTERN
        data, (src_ip, src_port)=heartbeat_socket.recvfrom(1024)
        match=PATTERN.search(data.decode("utf-8", errors="ignore"))

        # If pattern matches print time, ip, port, prefix, and ssh username 
        if match: print(f"{time.strftime('%H:%M:%S')} | {src_ip} | {src_port} | {PREFIX} | {match.group(1)}")

# Start thread for the listen() function
threading.Thread(target=listen, daemon=True).start()

# During regular your regular program will keep the pythan script alive, but in this sample this loop does that job, so this will likely not be needed
while True:
    time.sleep(1)