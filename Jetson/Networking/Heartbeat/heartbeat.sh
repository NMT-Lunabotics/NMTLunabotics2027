#!/bin/bash

CONFIG_FILE="${HEARTBEAT_CONFIG:-/etc/heartbeat.conf}"

source "$CONFIG_FILE" 2>/dev/null || { echo "Cannot load config: $CONFIG_FILE" >&2; exit 1; }
HEARTBEAT="${PREFIX}:${SSH_USER}"

while true; do
    if echo -n "$HEARTBEAT" | socat - UDP-DATAGRAM:${BROADCAST_ADDR}:${PORT},broadcast; then
        echo "Sent: $HEARTBEAT"
    else
        echo "Send failed" >&2
    fi
    sleep "$INTERVAL"
done