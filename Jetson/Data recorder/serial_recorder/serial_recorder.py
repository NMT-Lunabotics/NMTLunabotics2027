#!/usr/bin/env python3

import configparser
import os
import re
import signal
import sys
import time
from datetime import datetime

import serial
import serial.tools.list_ports

CONF_PATH = os.environ.get("SERIAL_RECORDER_CONF", "/etc/serial_recorder.conf")
WHITESPACE = re.compile(rb"\s+")

running = True


def handle_stop(signum, frame):
    global running
    running = False


def load_conf(path):
    cp = configparser.ConfigParser()
    if not cp.read(path):
        raise SystemExit(f"Could not read config: {path}")
    s = cp["recorder"]
    ids = [i.strip() for i in s.get("record_ids", "").split(",") if i.strip()]
    if not ids:
        raise SystemExit("record_ids is empty in config")
    return {
        "port": s.get("port", "auto").strip(),
        "baudrate": s.getint("baudrate", 115200),
        "save_dir": os.path.expanduser(s.get("save_dir", "/var/log/serial_recorder")),
        "record_ids": set(ids),
        "extension": s.get("extension", "csv").strip().lstrip("."),
    }


def find_arduino():
    for p in serial.tools.list_ports.comports():
        if "arduino" in p.description.lower() or p.vid is not None:
            return p.device
    return None


class Writer:
    def __init__(self, save_dir, ext):
        self.save_dir = save_dir
        self.ext = ext
        self.handles = {}
        os.makedirs(save_dir, exist_ok=True)

    def write(self, rec_id, data):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        cur = self.handles.get(rec_id)
        if cur is None or cur[0] != date_str:
            if cur is not None:
                cur[1].close()
            path = os.path.join(self.save_dir, f"{rec_id}_{date_str}.{self.ext}")
            cur = (date_str, open(path, "a", buffering=1))
            self.handles[rec_id] = cur
        ts = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        cur[1].write(f"{ts},{data}\n")

    def close(self):
        for _, f in self.handles.values():
            f.close()
        self.handles.clear()


def process_token(token, conf, writer):
    text = token.decode("utf-8", errors="replace")
    if ":" not in text:
        return
    rec_id, data = text.split(":", 1)
    if rec_id in conf["record_ids"] and data:
        writer.write(rec_id, data)


def record(conf, writer):
    port = conf["port"]
    if port.lower() == "auto":
        port = find_arduino()
        if port is None:
            raise RuntimeError("Arduino not found")
    print(f"Opening {port} at {conf['baudrate']} baud", flush=True)
    ser = serial.Serial(port=port, baudrate=conf["baudrate"], timeout=0.1)
    time.sleep(2)
    ser.reset_input_buffer()
    print("Recording...", flush=True)

    buf = b""
    try:
        while running:
            chunk = ser.read(ser.in_waiting or 1)
            if not chunk:
                continue
            buf += chunk
            parts = WHITESPACE.split(buf)
            buf = parts.pop()
            for token in parts:
                if token:
                    process_token(token, conf, writer)
            if len(buf) > 4096:
                buf = b""
    finally:
        ser.close()


def main():
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    conf = load_conf(CONF_PATH)
    writer = Writer(conf["save_dir"], conf["extension"])
    print(f"Recording IDs {sorted(conf['record_ids'])} to {conf['save_dir']}", flush=True)

    try:
        while running:
            try:
                record(conf, writer)
            except (serial.SerialException, OSError, RuntimeError) as e:
                print(f"Serial error: {e}. Retrying in 3s...", file=sys.stderr, flush=True)
                for _ in range(30):
                    if not running:
                        break
                    time.sleep(0.1)
    finally:
        writer.close()
        print("Stopped.", flush=True)


if __name__ == "__main__":
    main()