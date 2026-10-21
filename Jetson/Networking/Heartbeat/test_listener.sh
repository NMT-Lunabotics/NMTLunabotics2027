#!/bin/bash

CONFIG_FILE="${HEARTBEAT_CONFIG:-/etc/heartbeat.conf}"
source "$CONFIG_FILE"

echo "Listening for UDP broadcasts on port $PORT..."
echo "Press Ctrl+C to stop"
echo "----------------------------------------"

src_ip=""
src_port=""

sudo tcpdump -n -i any udp port "$PORT" -l -A 2>/dev/null | while IFS= read -r line; do
    if [[ "$line" =~ IP\ ([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\.([0-9]+)\ \> ]]; then
        src_ip="${BASH_REMATCH[1]}"
        src_port="${BASH_REMATCH[2]}"
    elif [[ "$line" =~ ${PREFIX}:([A-Za-z0-9_.-]+) ]]; then
        printf "%-15s | %-15s | %-5s | %-12s | %s\n" \
            "$(date +"%H:%M:%S")" "$src_ip" "$src_port" "$PREFIX" "${BASH_REMATCH[1]}"
    fi
done