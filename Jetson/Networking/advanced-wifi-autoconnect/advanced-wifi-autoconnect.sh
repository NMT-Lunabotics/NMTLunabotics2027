#!/usr/bin/env bash
set -u

CONF="${WIFI_AUTOCONNECT_CONF:-/etc/advanced-wifi-autoconnect.conf}"
if [[ ! -f "$CONF" ]]; then
    echo "[ERROR] Missing config: $CONF" >&2
    exit 1
fi
source "$CONF"

: "${WIFI_IFACE:=wlan0}"

: "${ENABLE_PRIORITY:=true}"
: "${ENABLE_WEBLOGIN:=true}"
: "${ENABLE_HOTSPOT:=true}"

: "${PRIORITY_SSID:=}"
: "${PRIORITY_PSK:=}"
: "${ROUTER_IP:=}"

: "${WEBLOGIN_SSID:=}"
: "${WEBLOGIN_PSK:=}"
: "${WEBLOGIN_URL:=}"
: "${WEBLOGIN_USERNAME_FIELD:=username}"
: "${WEBLOGIN_USERNAME:=}"
: "${WEBLOGIN_PASSWORD_FIELD:=password}"
: "${WEBLOGIN_PASSWORD:=}"
: "${WEBLOGIN_EXTRA_FIELDS:=}"

: "${HOTSPOT_SSID:=PiHotspot}"
: "${HOTSPOT_PASSWORD:=changeme123}"
: "${HOTSPOT_BAND:=bg}"
: "${HOTSPOT_CHANNEL:=}"            # empty = 6 for bg, 36 for a
: "${HOTSPOT_ADDRESS:=10.42.0.1/24}"
: "${HOTSPOT_CON_NAME:=Hotspot}"
: "${HOTSPOT_DELAY:=20}"
: "${HOTSPOT_RETRY_INTERVAL:=0}"    # 0 = sticky: never tear the hotspot down

: "${CHECK_INTERVAL:=5}"
: "${CONNECT_TIMEOUT:=10}"
: "${PING_TIMEOUT:=2}"
: "${FAILURE_THRESHOLD:=3}"
: "${PRIORITY_RECHECK_INTERVAL:=60}"
: "${INTERNET_CHECK_URL:=http://connectivitycheck.gstatic.com/generate_204}"
: "${INTERNET_CHECK_EXPECT:=204}"

if [[ -z "$HOTSPOT_CHANNEL" ]]; then
    [[ "$HOTSPOT_BAND" == "a" ]] && HOTSPOT_CHANNEL=36 || HOTSPOT_CHANNEL=6
fi

log() { echo "[advanced-wifi-autoconnect] $*"; }

enabled() {
    case "${1,,}" in
        true|yes|1|on) return 0 ;;
        *) return 1 ;;
    esac
}

nap() { sleep "$1" & wait $!; }

priority_usable() { enabled "$ENABLE_PRIORITY" && [[ -n "$PRIORITY_SSID" ]]; }
weblogin_usable() { enabled "$ENABLE_WEBLOGIN" && [[ -n "$WEBLOGIN_SSID" ]]; }
regular_enabled() { priority_usable || weblogin_usable; }

# ---------- NetworkManager control ----------
lock_autoconnect() {
    nmcli device set "$WIFI_IFACE" autoconnect no >/dev/null 2>&1 || true
    local uuid type auto
    while IFS=: read -r uuid type auto; do
        [[ "$type" == "802-11-wireless" && "$auto" == "yes" ]] || continue
        nmcli connection modify "$uuid" connection.autoconnect no >/dev/null 2>&1 || true
    done < <(nmcli -t -f UUID,TYPE,AUTOCONNECT connection show 2>/dev/null)
}

forget_profile() {
    [[ -z "$1" ]] && return
    while nmcli connection delete id "$1" >/dev/null 2>&1; do :; done
}

SCAN_RESULT=""
scan_ssids() {
    SCAN_RESULT=$(nmcli -t -f SSID dev wifi list ifname "$WIFI_IFACE" --rescan yes 2>/dev/null | sed 's/\\:/:/g')
}
seen() { grep -Fxq -- "$1" <<<"$SCAN_RESULT"; }

active_ssid() {
    nmcli -t -f ACTIVE,SSID dev wifi list ifname "$WIFI_IFACE" --rescan no 2>/dev/null \
        | sed -n 's/^yes://p' | head -n1 | sed 's/\\:/:/g'
}

hotspot_active() {
    nmcli -t -f NAME connection show --active 2>/dev/null | grep -Fxq "$HOTSPOT_CON_NAME"
}

current_mode() {
    if hotspot_active; then echo hotspot; return; fi
    local s
    s=$(active_ssid)
    if   [[ -z "$s" ]];                  then echo none
    elif [[ "$s" == "$PRIORITY_SSID" ]]; then echo priority
    elif [[ "$s" == "$WEBLOGIN_SSID" ]]; then echo weblogin
    else echo other
    fi
}

count_clients() {
    iw dev "$WIFI_IFACE" station dump 2>/dev/null | grep -c '^Station' || true
}

disconnect_wifi() {
    nmcli dev disconnect "$WIFI_IFACE" >/dev/null 2>&1 || true
}

connect_wifi() {
    local ssid="$1" psk="${2:-}" out rc
    log "Connecting to '$ssid'"
    forget_profile "$ssid"
    if [[ -n "$psk" ]]; then
        out=$(nmcli -w "$CONNECT_TIMEOUT" dev wifi connect "$ssid" password "$psk" ifname "$WIFI_IFACE" 2>&1); rc=$?
    else
        out=$(nmcli -w "$CONNECT_TIMEOUT" dev wifi connect "$ssid" ifname "$WIFI_IFACE" 2>&1); rc=$?
    fi
    if (( rc != 0 )); then
        log "nmcli error: $out"
        forget_profile "$ssid"
        disconnect_wifi
        return 1
    fi
    lock_autoconnect
    return 0
}

internet_ok() {
    local code
    code=$(curl -s -o /dev/null -m 5 --interface "$WIFI_IFACE" -w '%{http_code}' "$INTERNET_CHECK_URL" 2>/dev/null)
    [[ "$code" == "$INTERNET_CHECK_EXPECT" ]]
}

router_ok() {
    [[ -z "$ROUTER_IP" ]] && return 0
    ping -c 1 -W "$PING_TIMEOUT" "$ROUTER_IP" >/dev/null 2>&1
}

login_portal() {
    if [[ -z "$WEBLOGIN_URL" ]]; then
        log "WEBLOGIN_URL not set, skipping portal login"
        return 1
    fi
    log "Submitting captive portal login"
    local args=(-s -L -m 15 -o /dev/null -w '%{http_code}'
        --interface "$WIFI_IFACE"
        -c /tmp/wifi-portal.cookies -b /tmp/wifi-portal.cookies
        --data-urlencode "${WEBLOGIN_USERNAME_FIELD}=${WEBLOGIN_USERNAME}"
        --data-urlencode "${WEBLOGIN_PASSWORD_FIELD}=${WEBLOGIN_PASSWORD}")
    [[ -n "$WEBLOGIN_EXTRA_FIELDS" ]] && args+=(-d "$WEBLOGIN_EXTRA_FIELDS")
    local code
    code=$(curl "${args[@]}" "$WEBLOGIN_URL" 2>&1)
    log "Portal login HTTP result: $code"
}

start_hotspot() {
    log "Starting hotspot '$HOTSPOT_SSID' (band=$HOTSPOT_BAND channel=$HOTSPOT_CHANNEL)"
    local out
    nmcli connection delete "$HOTSPOT_CON_NAME" >/dev/null 2>&1 || true
    out=$(nmcli connection add type wifi ifname "$WIFI_IFACE" con-name "$HOTSPOT_CON_NAME" \
        autoconnect no ssid "$HOTSPOT_SSID" \
        802-11-wireless.mode ap 802-11-wireless.band "$HOTSPOT_BAND" \
        802-11-wireless.channel "$HOTSPOT_CHANNEL" \
        802-11-wireless.powersave 2 \
        ipv4.method shared ipv4.addresses "$HOTSPOT_ADDRESS" ipv6.method ignore \
        wifi-sec.key-mgmt wpa-psk wifi-sec.proto rsn \
        wifi-sec.pairwise ccmp wifi-sec.group ccmp \
        wifi-sec.psk "$HOTSPOT_PASSWORD" 2>&1) || { log "Hotspot profile error: $out"; return 1; }
    if out=$(nmcli connection up "$HOTSPOT_CON_NAME" ifname "$WIFI_IFACE" 2>&1); then
        log "Hotspot is up"
        return 0
    fi
    log "Failed to start hotspot: $out"
    return 1
}

stop_hotspot() {
    log "Stopping hotspot"
    nmcli connection down "$HOTSPOT_CON_NAME" >/dev/null 2>&1 || true
}

try_connect_cycle() {
    regular_enabled || return 1

    scan_ssids

    if priority_usable; then
        if seen "$PRIORITY_SSID"; then
            if connect_wifi "$PRIORITY_SSID" "$PRIORITY_PSK"; then
                log "Connected to priority network '$PRIORITY_SSID'"
                return 0
            fi
            log "Failed to connect to '$PRIORITY_SSID'"
        else
            log "Priority network '$PRIORITY_SSID' not in range"
        fi
    fi

    if weblogin_usable; then
        if seen "$WEBLOGIN_SSID"; then
            if connect_wifi "$WEBLOGIN_SSID" "$WEBLOGIN_PSK"; then
                sleep 2
                internet_ok || login_portal
                sleep 1
                if internet_ok; then
                    log "Connected to '$WEBLOGIN_SSID' with internet access"
                    return 0
                fi
                log "No internet on '$WEBLOGIN_SSID' after portal login"
                forget_profile "$WEBLOGIN_SSID"
                disconnect_wifi
            else
                log "Failed to connect to '$WEBLOGIN_SSID'"
            fi
        else
            log "Weblogin network '$WEBLOGIN_SSID' not in range"
        fi
    fi

    return 1
}

fails=0
no_net_since=0
last_hotspot_retry=0
last_priority_check=0

handle_priority() {
    no_net_since=0
    if router_ok; then
        fails=0
    else
        fails=$((fails + 1))
        log "Router not responding ($fails/$FAILURE_THRESHOLD)"
        if (( fails >= FAILURE_THRESHOLD )); then
            log "Dropping priority connection"
            disconnect_wifi
            fails=0
        fi
    fi
}

handle_weblogin() {
    no_net_since=0
    if ! internet_ok; then
        login_portal
        sleep 1
    fi
    if internet_ok; then
        fails=0
    else
        fails=$((fails + 1))
        log "No internet on weblogin network ($fails/$FAILURE_THRESHOLD)"
        if (( fails >= FAILURE_THRESHOLD )); then
            disconnect_wifi
            fails=0
            return
        fi
    fi

    if priority_usable; then
        local now; now=$(date +%s)
        if (( now - last_priority_check >= PRIORITY_RECHECK_INTERVAL )); then
            last_priority_check=$now
            scan_ssids
            if seen "$PRIORITY_SSID"; then
                log "Priority network is back, switching"
                connect_wifi "$PRIORITY_SSID" "$PRIORITY_PSK" || log "Switch failed, will retry"
            fi
        fi
    fi
}

handle_none() {
    if ! regular_enabled; then
        if enabled "$ENABLE_HOTSPOT"; then
            start_hotspot || nap 10  
        else
            log "Nothing enabled (priority, weblogin, hotspot all off)"
            nap 30
        fi
        return
    fi

    local now; now=$(date +%s)
    (( no_net_since == 0 )) && no_net_since=$now

    if try_connect_cycle; then
        no_net_since=0
        fails=0
        return
    fi

    now=$(date +%s)
    if (( now - no_net_since >= HOTSPOT_DELAY )); then
        if enabled "$ENABLE_HOTSPOT"; then
            log "No network after $((now - no_net_since))s, starting hotspot"
            start_hotspot && last_hotspot_retry=$(date +%s)
            no_net_since=0
        else
            log "No network found (hotspot disabled), still trying"
        fi
    fi
}

handle_hotspot() {
    no_net_since=0

    if ! enabled "$ENABLE_HOTSPOT"; then
        stop_hotspot
        return
    fi
    (( HOTSPOT_RETRY_INTERVAL <= 0 )) && return
    regular_enabled || return

    local now; now=$(date +%s)
    (( now - last_hotspot_retry < HOTSPOT_RETRY_INTERVAL )) && return
    last_hotspot_retry=$now

    if [[ "$(count_clients)" -eq 0 ]]; then
        log "Hotspot idle, checking for regular networks"
        stop_hotspot
        if try_connect_cycle; then
            return
        fi
        start_hotspot
        last_hotspot_retry=$(date +%s)
    fi
}

cleanup() {
    hotspot_active && stop_hotspot
    exit 0
}
trap cleanup TERM INT

lock_autoconnect
log "Started (priority=$ENABLE_PRIORITY weblogin=$ENABLE_WEBLOGIN hotspot=$ENABLE_HOTSPOT iface=$WIFI_IFACE retry_interval=$HOTSPOT_RETRY_INTERVAL)"

while true; do
    mode=$(current_mode)

    if [[ "$mode" == "priority" ]] && ! enabled "$ENABLE_PRIORITY"; then
        log "Priority network disabled, disconnecting"
        forget_profile "$PRIORITY_SSID"; disconnect_wifi; mode=none
    elif [[ "$mode" == "weblogin" ]] && ! enabled "$ENABLE_WEBLOGIN"; then
        log "Weblogin network disabled, disconnecting"
        forget_profile "$WEBLOGIN_SSID"; disconnect_wifi; mode=none
    elif [[ "$mode" == "other" ]]; then
        log "Connected to an unmanaged network, disconnecting"
        disconnect_wifi; mode=none
    fi

    case "$mode" in
        priority) handle_priority ;;
        weblogin) handle_weblogin ;;
        hotspot)  handle_hotspot ;;
        *)        handle_none ;;
    esac

    nap "$CHECK_INTERVAL"
done