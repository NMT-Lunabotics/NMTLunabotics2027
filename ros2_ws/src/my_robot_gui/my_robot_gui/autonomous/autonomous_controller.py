from .excavation import get_sequence as get_excavation_sequence
from .dump import get_sequence as get_dump_sequence
from .transverse import get_sequence as get_transverse_sequence
from typing import List, Optional, Tuple
import threading
import time
from arduino.serial_communication import serialCommands

SEND_RATE_HZ = 40.0
MAX_DRIVE_OUTPUT = 127

def clamp_drive(value: int) -> int:
    return max(-MAX_DRIVE_OUTPUT, min(MAX_DRIVE_OUTPUT, value))


AUTO_PROGRAMS = {
    "excavation": get_excavation_sequence,
    "dump": get_dump_sequence,
    "transverse": get_transverse_sequence,
}

def _maybe_start_auto(shared: dict, now: float) -> None:
    with shared["lock"]:
        requested = shared.get("auto_requested")
        if not requested:
            return
        if shared.get("auto_active"):
            return
        sequence_loader = AUTO_PROGRAMS.get(str(requested))
        try:
            sequence = list(sequence_loader()) if sequence_loader else []
        except Exception as exc:
            shared["serial_status"] = f"auto load failed: {exc}"
            shared["auto_requested"] = None
            return
        if not sequence:
            shared["serial_status"] = f"auto unavailable: {requested}" if requested else "auto unavailable"
            shared["auto_requested"] = None
            return
        shared["auto_requested"] = None
        shared["auto_sequence"] = sequence
        shared["auto_total_steps"] = len(sequence)
        shared["auto_step"] = 0
        shared["auto_step_start"] = 0.0
        shared["auto_step_end"] = 0.0
        shared["auto_step_initialized"] = False
        shared["auto_active"] = True
        shared["auto_m_values"] = [0, 0]
        shared["auto_a_values"] = [0, 0, 0, 0, 0, 0]
        shared["auto_command"] = ""
        shared["auto_values"] = []
        shared["auto_time_remaining"] = 0.0
        shared["auto_program"] = str(requested)
        shared["control_mode"] = "auto"
        shared["serial_status"] = f"running {requested}"


def _stop_auto(shared: dict, reason: str) -> None:
    with shared["lock"]:
        shared["auto_active"] = False
        shared["auto_requested"] = None
        shared["control_mode"] = "manual"
        shared["serial_status"] = reason
        shared["auto_time_remaining"] = 0.0
        shared["auto_command"] = ""
        shared["auto_values"] = []
        shared["auto_m_values"] = [0, 0]
        shared["auto_a_values"] = [0, 0, 0, 0, 0, 0]
        shared["auto_step_initialized"] = False
        shared["auto_step_start"] = 0.0
        shared["auto_step_end"] = 0.0
        shared["auto_step"] = shared.get("auto_total_steps", 0)
        shared["auto_program"] = ""


def _update_auto_state(shared: dict, now: float) -> Optional[Tuple[List[int], List[int]]]:
    while True:
        stop_reason: Optional[str] = None
        continue_loop = False
        result: Optional[Tuple[List[int], List[int]]] = None

        with shared["lock"]:
            if not shared.get("auto_active"):
                return None

            sequence = shared.get("auto_sequence", [])
            idx = shared.get("auto_step", 0)

            if idx >= len(sequence):
                stop_reason = "autonomous complete"
            else:
                entry = sequence[idx]
                initialized = shared.get("auto_step_initialized", False)

                if not initialized:
                    duration = float(entry.get("duration", 0.0) or 0.0)
                    command = entry.get("command")
                    values = entry.get("values", [])

                    shared["auto_step_start"] = now
                    shared["auto_step_end"] = now + duration
                    shared["auto_step_initialized"] = True

                    if command == "M":
                        shared["auto_m_values"] = list(values)
                    elif command == "A":
                        shared["auto_a_values"] = list(values)

                    shared["auto_command"] = command or ""
                    shared["auto_values"] = list(values) if command else []
                    shared["auto_step"] = idx
                    shared["auto_time_remaining"] = max(0.0, shared["auto_step_end"] - now)

                    if duration == 0.0:
                        shared["auto_step"] = idx + 1
                        shared["auto_step_initialized"] = False
                        continue_loop = True
                    else:
                        result = (
                            list(shared.get("auto_m_values", [0, 0])),
                            list(shared.get("auto_a_values", [0, 0, 0, 0, 0, 0])),
                        )
                else:
                    step_end = shared.get("auto_step_end", now)
                    if now >= step_end:
                        shared["auto_step"] = idx + 1
                        shared["auto_step_initialized"] = False
                        continue_loop = True
                    else:
                        shared["auto_time_remaining"] = max(0.0, step_end - now)
                        result = (
                            list(shared.get("auto_m_values", [0, 0])),
                            list(shared.get("auto_a_values", [0, 0, 0, 0, 0, 0])),
                        )

        if stop_reason:
            _stop_auto(shared, stop_reason)
            return None
        if continue_loop:
            continue
        return result

def create_shared_state():
    return{
        "lock": threading.Lock(),
        "auto_requested": None,
        "auto_active": False,
        "auto_sequence": [],
        "auto_total_steps": 0,
        "auto_step": 0,
        "auto_step_start": 0.0,
        "auto_step_end": 0.0,
        "auto_step_initialized": False,
        "auto_time_remaining": 0.0,
        "auto_command": "",
        "auto_values": [],
        "auto_m_values": [0, 0],
        "auto_a_values": [0, 0, 0, 0, 0, 0],
        "auto_program": "",
        "control_mode": "manual",
        "serial_status": "ready",
    }

def request_auto(shared, program):
    with shared["lock"]:
        if shared["auto_active"] or shared["auto_requested"]:
            return False
        shared["auto_requested"] = program
        return True

def update_controller(shared):
    now = time.monotonic()
    _maybe_start_auto(shared, now)
    return _update_auto_state(shared, now)

def _open_link(shared: dict, stop_event: threading.Event) -> Optional[serialCommands]:
    while not stop_event.is_set():
        try:
            link = serialCommands()
        except Exception as exc:
            with shared["lock"]:
                shared["serial_status"] = f"Arduino not found: {exc}"
            stop_event.wait(1.0)
            continue
        with shared["lock"]:
            shared["serial_status"] = "connected"
        return link
    return None

def _sender(shared: dict, stop_event: threading.Event) -> None:
    period = 1.0 / SEND_RATE_HZ
    next_send = time.monotonic()
    link: Optional[serialCommands] = None
    try:
        while not stop_event.is_set():
            now = time.monotonic()
            sleep_for = next_send - now
            if sleep_for > 0:
                stop_event.wait(sleep_for)
                continue
            next_send = now + period

            if link is None:
                link = _open_link(shared, stop_event)
                if link is None:
                    break

            _maybe_start_auto(shared, now)
            auto_outputs = _update_auto_state(shared, now)
            if auto_outputs is None:
                send_m, send_a = auto_outputs or ([0, 0], [0, 0, 0, 0, 0, 0])
                send_m = list(send_m)
                send_a = list(send_a)
                if not send_m:
                    send_m = [0, 0]
                elif len(send_m) == 1:
                    send_m.append(0)
                if len(send_m) < 2:
                    send_m = (send_m + [0, 0])[:2]
                if len(send_a) < 6:
                    send_a = (send_a + [-1, -1, -1, -1, 0, 0])[:6]

                send_m = [clamp_drive(int(v)) for v in send_m]

                with shared["lock"]:
                    shared["stale"] = False
                    shared["outputs_enabled"] = True
                    shared["last_send_dt"] = 0.0
                    shared["motor_left"] = send_m[0]
                    shared["motor_right"] = send_m[1]
                    shared["arm_cmd"] = send_a[4]
                    shared["bucket_cmd"] = send_a[5]
                    shared["control_mode"] = "auto"
                    limiter = shared.get("drive_limiter")
                    if limiter:
                        limiter.reset(0.0, 0.0)

            try: 
                link.send_command("M", send_m)
                link.send_command("A", send_a)
                lines = link.read_serial()
            except Exception as exc:
                with shared["lock"]:
                    shared["serial_status"] = f"Serial send failed: {exc}"
                try:
                    if link is not None:
                        link.close_serial()
                except Exception:
                    pass
                link = None
                next_send = time.monotonic() + period
                continue

            if lines:
                last_line = lines[-1]
                if not isinstance(last_line, str):
                    last_line = repr(last_line)
                with shared["lock"]:
                    shared["serial_rx"] = last_line
    finally:
        if link is not None:
            try:
                link.close_serial()
            except Exception:
                pass
        with shared["lock"]:
            shared["serial_status"] = "disconnected"