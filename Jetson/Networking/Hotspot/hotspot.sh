#!/usr/bin/env bash
set -u

source /etc/hotspot.conf

CON_NAME="Hotspot"
BAND="bg"
FAIL_THRESHOLD=3
RETRY_INTERVAL=60
RETRY_WAIT=20

log() { echo "[hotspot] $*"; }

hotspot_active() {
    nmcli -t -f NAME connection show --active | grep -Fxq "$CON_NAME"
}

has_network() {
    local dev type state con
    while IFS=: read -r dev type state con; do
        case "$type" in
            wifi|ethernet) ;;
            *) continue ;;
        esac
        case "$state" in
            connected*) ;;
            *) continue ;;
        esac
        [ "$con" = "$CON_NAME" ] && continue
        return 0
    done < <(nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device 2>/dev/null)
    return 1
}

count_clients() {
    iw dev "$WIFI_IFACE" station dump 2>/dev/null | grep -c '^Station' || true
}

start_hotspot() {
    log "No network connection, starting hotspot '$HOTSPOT_SSID'"
    nmcli connection delete "$CON_NAME" >/dev/null 2>&1 || true
    nmcli connection add type wifi ifname "$WIFI_IFACE" con-name "$CON_NAME" \
        autoconnect no ssid "$HOTSPOT_SSID" \
        802-11-wireless.mode ap 802-11-wireless.band "$BAND" \
        ipv4.method shared ipv4.addresses "$ADDRESS" ipv6.method ignore \
        wifi-sec.key-mgmt wpa-psk wifi-sec.proto rsn \
        wifi-sec.pairwise ccmp wifi-sec.group ccmp \
        wifi-sec.psk "$HOTSPOT_PASSWORD" >/dev/null
    if nmcli connection up "$CON_NAME" ifname "$WIFI_IFACE" >/dev/null 2>&1; then
        log "Hotspot is up"
    else
        log "Failed to start hotspot"
    fi
}

stop_hotspot() {
    log "Stopping hotspot"
    nmcli connection down "$CON_NAME" >/dev/null 2>&1 || true
}

retry_regular_network() {
    log "Checking whether a known network is available"
    stop_hotspot
    nmcli device connect "$WIFI_IFACE" >/dev/null 2>&1 || true
    local waited=0
    while [ "$waited" -lt "$RETRY_WAIT" ]; do
        sleep 1
        waited=$((waited + 1))
        if has_network; then
            log "Reconnected to a regular network"
            return 0
        fi
    done
    log "No known network found"
    start_hotspot
}

cleanup() {
    hotspot_active && stop_hotspot
    exit 0
}
trap cleanup TERM INT

fails=0
last_retry=$(date +%s)

while true; do
    if has_network; then
        fails=0
        if hotspot_active; then
            log "Regular network detected"
            stop_hotspot
        fi
    elif hotspot_active; then
        now=$(date +%s)
        if [ $((now - last_retry)) -ge "$RETRY_INTERVAL" ]; then
            [ "$(count_clients)" -eq 0 ] && retry_regular_network
            last_retry=$(date +%s)
        fi
    else
        fails=$((fails + 1))
        if [ "$fails" -ge "$FAIL_THRESHOLD" ]; then
            start_hotspot
            fails=0
            last_retry=$(date +%s)
        fi
    fi

    sleep "$CHECK_INTERVAL" &
    wait $!
done