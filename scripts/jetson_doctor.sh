#!/usr/bin/env bash
set -u

printf 'Host: %s\n' "$(hostname)"
printf 'Architecture: %s\n' "$(uname -m)"

if [[ -r /etc/os-release ]]; then
    . /etc/os-release
    printf 'OS: %s\n' "${PRETTY_NAME:-unknown}"
fi

if [[ -r /etc/nv_tegra_release ]]; then
    printf 'JetPack/L4T release file:\n'
    sed -n '1,3p' /etc/nv_tegra_release
else
    printf 'JetPack/L4T: not detected (this may be a development workstation)\n'
fi

if command -v docker >/dev/null 2>&1; then
    docker --version
    if docker info --format 'Docker server: {{.ServerVersion}}' 2>/dev/null; then
        :
    else
        printf 'Docker daemon is unavailable to this user.\n' >&2
    fi
else
    printf 'Docker is not installed.\n' >&2
fi

printf '\nSerial device links:\n'
if [[ -d /dev/serial/by-id ]]; then
    find /dev/serial/by-id -maxdepth 1 -type l -printf '%f -> %l\n'
else
    printf 'No /dev/serial/by-id directory found.\n'
fi

printf '\nVideo device nodes:\n'
shopt -s nullglob
video_devices=(/dev/video*)
if ((${#video_devices[@]})); then
    ls -l "${video_devices[@]}"
else
    printf 'No /dev/video* nodes found.\n'
fi

printf '\nDocker image:\n'
if command -v docker >/dev/null 2>&1 \
    && docker image inspect nmtlunabotics2027/ros2:humble \
        --format '{{.Os}}/{{.Architecture}} {{.Id}}' 2>/dev/null; then
    :
else
    printf 'nmtlunabotics2027/ros2:humble is not built.\n'
fi