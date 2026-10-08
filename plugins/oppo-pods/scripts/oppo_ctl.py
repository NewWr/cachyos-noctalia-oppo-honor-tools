#!/usr/bin/env python3
"""
OPPO / OnePlus / realme Earbuds Controller
Reverse-engineered Bluetooth RFCOMM protocol for Linux / Noctalia
Author: osp54
"""

import sys
import os
import json
import time
import socket
import argparse
import fcntl
import subprocess
import shutil

CACHE_DIR = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
STATE_FILE = os.path.join(CACHE_DIR, "oppo_pods_state.json")
CHANNEL_FILE = os.path.join(CACHE_DIR, "oppo_pods_channel.txt")
LOCK_FILE = os.path.join(CACHE_DIR, "oppo_pods_control.lock")
UUID_OPPO_SPP = "0000079a-d102-11e1-9b23-00025b00a5a5"

MEDIA_CACHE_DIR = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "noctalia", "oppo-pods")

# Noise modes
MODE_OFF = "off"
MODE_ANC = "anc"
MODE_TRANSPARENCY = "transparency"

CYCLE_MODES = [MODE_ANC, MODE_TRANSPARENCY, MODE_OFF]

# Product ID to model map (sample of most popular)
MODEL_NAMES = {
    "067C10": "OPPO Enco Air4 Pro",
    "069010": "OPPO Enco Air4",
    "064C10": "OPPO Enco Air3",
    "065C10": "OPPO Enco Air3 Pro",
    "063410": "OPPO Enco Air2",
    "063810": "OPPO Enco Air2 Pro",
    "066010": "OPPO Enco Free3",
    "068C10": "OPPO Enco Free4",
    "06C010": "OPPO Enco Free4 Dynaudio",
    "068010": "OPPO Enco Buds2 Pro",
    "06A450": "OPPO Enco Buds3",
    "046410": "OnePlus Buds Pro 2",
    "046810": "OnePlus Buds Pro 3",
    "045010": "OnePlus Buds 3",
    "045410": "OnePlus Buds Pro",
    "044810": "OnePlus Buds Z2",
    "055010": "realme Buds Air 5 Pro",
    "056010": "realme Buds Air 6 Pro",
    "054410": "realme Buds T300",
    "054810": "realme Buds T310",
}

# Keep protocol parsing independent from Bluetooth discovery and media downloads.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oppo_protocol import make_frame, parse_frames, FrameDecoder, decode_noise
from oppo_runtime import Session, query_device as _query_device, standalone, monitor, monitor_request, load_state


def read_response(connection, command, sequence, timeout=1.5):
    decoder = FrameDecoder()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        connection.settimeout(max(0.001, deadline - time.monotonic()))
        try:
            chunk = connection.recv(4096)
        except socket.timeout:
            return None
        if not chunk:
            return None
        for received, seq, payload in decoder.feed(chunk):
            if received == command and seq == sequence:
                return payload
    return None


def decode_noise_mode(payload):
    decoded = decode_noise(payload)
    return decoded["noise_mode"] if decoded else None

def find_connected_device():
    """Find connected OPPO/OnePlus/realme device MAC via bluetoothctl or DBus"""
    try:
        out = subprocess.check_output(["bluetoothctl", "devices", "Connected"], text=True, stderr=subprocess.DEVNULL)
        lines = [line.strip() for line in out.strip().split("\n") if line.strip()]
        for line in lines:
            parts = line.split(" ", 2)
            if len(parts) >= 3:
                mac = parts[1]
                name = parts[2]
                name_lower = name.lower()
                if any(k in name_lower for k in ("oppo", "enco", "oneplus", "buds", "realme", "dizo")):
                    return mac, name
        # If no specific name matched, check info on all connected devices
        for line in lines:
            parts = line.split(" ", 2)
            if len(parts) >= 2:
                mac = parts[1]
                info = subprocess.check_output(["bluetoothctl", "info", mac], text=True, stderr=subprocess.DEVNULL)
                if UUID_OPPO_SPP in info.lower() or "0000079a" in info.lower():
                    return mac, parts[2] if len(parts) >= 3 else "OPPO Pods"
    except Exception:
        pass
    return None, None

def get_cached_channel():
    if os.path.exists(CHANNEL_FILE):
        try:
            with open(CHANNEL_FILE, "r") as f:
                ch = int(f.read().strip())
                if 1 <= ch <= 30:
                    return ch
        except Exception:
            pass
    return 12  # Default on most OPPO Enco Air4 / Air3

def connect_rfcomm(mac, timeout=1.5):
    # Enco Free4 advertises its 079a control service on channel 15.
    # Prefer the last working channel, retaining the legacy 12/13 fallbacks.
    cached_channel = get_cached_channel()
    channels = list(dict.fromkeys([cached_channel, 15, 12, 13]))
    for ch in channels:
        s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
        s.settimeout(timeout)
        try:
            s.connect((mac, ch))
            if ch != cached_channel:
                try:
                    with open(CHANNEL_FILE, "w") as f:
                        f.write(str(ch))
                except OSError:
                    pass
            return s, ch
        except Exception:
            s.close()
    return None, None

def ensure_device_image(product_id):
    """Use only a local image cache; no remote credentials or network downloads."""
    if not product_id or not all(c in "0123456789abcdefABCDEF" for c in product_id):
        return None
    out_file = os.path.join(MEDIA_CACHE_DIR, f"{product_id}.png")
    if os.path.isfile(out_file) and os.path.getsize(out_file) > 1000:
        return out_file
    return None


def host_functions():
    return {"connect": connect_rfcomm, "find_device": find_connected_device,
            "image": ensure_device_image, "models": MODEL_NAMES,
            "state_file": STATE_FILE, "lock_file": LOCK_FILE}


def query_device(mac, device_name=None):
    return _query_device(host_functions(), mac, device_name)


def set_anc_mode(mac, target_mode):
    return standalone(host_functions(), mac, "set-anc", target_mode)


def read_cache():
    return load_state(STATE_FILE) or {"connected": False}


def main():
    import re
    parser = argparse.ArgumentParser(description="OPPO Pods controller")
    parser.add_argument("command", choices=["status", "cached", "monitor", "request", "set-anc", "cycle-anc"])
    parser.add_argument("value", nargs="?")
    parser.add_argument("--mac")
    parser.add_argument("--no-desktop-pause", action="store_true")
    args = parser.parse_args()
    host = host_functions()
    mac = args.mac or os.environ.get("OPPO_MAC")
    if mac and not re.fullmatch(r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}", mac):
        print(json.dumps({"success": False, "error_code": "invalid", "error": "Invalid Bluetooth address"}))
        return
    if mac:
        mac = mac.upper()
    if args.command == "cached":
        print(json.dumps(read_cache(), ensure_ascii=False))
        return
    if args.command == "monitor":
        monitor(host, mac, desktop_pause=not args.no_desktop_pause)
        return
    action, value = args.command, args.value
    if action == "request":
        try:
            request = json.loads(value)
            action, value = request["action"], request.get("value")
            if not isinstance(action, str):
                raise ValueError("Invalid action")
        except (ValueError, TypeError, KeyError):
            print(json.dumps({"success": False, "error_code": "invalid", "error": "Invalid request JSON"}))
            return
    result = monitor_request(host, mac, action, value)
    if result is None:
        name = None
        if not mac:
            mac, name = find_connected_device()
        if not mac:
            result = {"success": False, "error_code": "connection", "error": "No connected OPPO earbuds"}
        else:
            # Re-check the command socket while waiting for a monitor to finish startup.
            with open(LOCK_FILE, "a") as lock:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        try:
                            result = standalone(host, mac, action, value, name)
                        finally:
                            time.sleep(0.5)
                        break
                    except BlockingIOError:
                        result = monitor_request(host, mac, action, value)
                        if result is not None:
                            break
                        if time.monotonic() > deadline:
                            result = {"success": False, "error_code": "busy", "error": "Earbuds controller is busy"}
                            break
                        time.sleep(0.1)
    if args.command == "status":
        result = result.get("snapshot") or {"connected": False, "error": result.get("error", "Unknown error")}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
