"""One RFCOMM session, verified writes, and a local monitor command socket."""
import base64
import contextlib
import fcntl
import json
import os
import re
import select
import signal
import socket
import time
from oppo_media import WearPlaybackBridge

from oppo_protocol import (FEATURES, NOISE_PAYLOADS, FrameDecoder, apply_frame,
                           capability_state, counted_pairs, decode_equalizers, encode_equalizer,
                           make_frame, success, supports)


class ControlError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def load_state(path):
    try:
        with open(path) as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    temporary = path + "." + str(os.getpid()) + ".tmp"
    with open(temporary, "w") as stream:
        json.dump(state, stream, ensure_ascii=False)
    os.replace(temporary, path)


class Session:
    def __init__(self, host, mac, name=None):
        self.host, self.mac, self.name = host, mac, name
        cached = load_state(host["state_file"])
        self.state = cached if cached.get("mac") == mac else {}
        # Never carry feature availability across connection attempts.
        for key in ("features", "capabilities", "notifications_active"):
            self.state.pop(key, None)
        for key in FEATURES:
            self.state.pop(key, None)
        self.state.pop("noise_mode_name", None)
        self.state.pop("finding", None)
        for key in ("wear_left", "wear_right", "wear_observed_at", "desktop_pause"):
            self.state.pop(key, None)
        self.state.update({"mac": mac, "connected": False,
                           "device_name": name or self.state.get("device_name", "OPPO Earbuds")})
        for side in ("left", "right", "case"):
            self.state.setdefault("battery_" + side, -1)
        self.decoder = FrameDecoder()
        self.connection = None
        self.sequence = 0
        self.find_deadline = None
        self.pending_refresh = False

    def __enter__(self):
        self.connection, channel = self.host["connect"](self.mac, timeout=2)
        if self.connection is None:
            raise ControlError("connection", "Cannot open the earbuds control channel")
        try:
            hello = self.request(0x0100)
            if not success(hello):
                raise ControlError("handshake", "Earbuds did not accept the handshake")
            self.state.update({"connected": True, "channel": channel, "stale": False})
            self.state.pop("error", None)
            self.state.pop("error_code", None)
            self.request(0x0103)
            model = self.host["models"].get(self.state.get("product_id"))
            self.state["model_name"] = model or self.name or self.state["device_name"]
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, *_args):
        self.close()

    def close(self):
        if self.connection:
            if self.find_deadline is not None:
                with contextlib.suppress(Exception):
                    self.request(0x0400, b"\x00")
            self.connection.close()
            self.connection = None
        self.find_deadline = None

    def receive(self, timeout):
        self.connection.settimeout(timeout)
        try:
            chunk = self.connection.recv(4096)
        except socket.timeout:
            return []
        if not chunk:
            raise ControlError("connection", "Earbuds closed the control channel")
        frames = self.decoder.feed(chunk)
        for command, _seq, payload in frames:
            apply_frame(self.state, command, payload)
            if command == 0x0504 or (command == 0x0204 and payload and payload[0] in (5, 8, 0xF2)):
                self.pending_refresh = True
        return frames

    def request(self, command, payload=b"", sequence=None, timeout=1.5):
        if sequence is None:
            self.sequence = self.sequence % 239 + 1
            sequence = self.sequence
        self.connection.sendall(make_frame(command, sequence, payload))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for received, seq, value in self.receive(max(0.001, deadline - time.monotonic())):
                if received == command | 0x8000 and seq == sequence:
                    return value
        raise ControlError("timeout", f"No matching response for command {command:04x}")

    def optional(self, command, payload=b"", sequence=None):
        try:
            return self.request(command, payload, sequence)
        except ControlError as error:
            if error.code != "timeout":
                raise
            return None

    def refresh_features(self):
        ids = list(FEATURES.values()) + [0x28]
        return self.request(0x010D, bytes([len(ids), *ids]), sequence=0)

    def refresh(self, full=False):
        if not success(self.request(0x0106)):
            raise ControlError("rejected", "Battery query was rejected")
        bitmap = bytes.fromhex(self.state.get("command_bitmap", ""))
        if supports(bitmap, 8):
            self.optional(0x010C, b"\x01\x01")
        if supports(bitmap, 7):
            self.refresh_features()
        if supports(bitmap, 4):
            self.optional(0x0109)
        if full:
            for bit, command, payload in [(0, 0x0105, b""), (17, 0x0114, b""),
                                          (10, 0x010F, b""), (34, 0x0122, b"\x01\x05"),
                                          (29, 0x0112, b""), (19, 0x0115, b"")]:
                if supports(bitmap, bit):
                    self.optional(command, payload)
            image = self.host["image"](self.state.get("product_id"))
            if image:
                self.state["device_image"] = image
        return self.persist()

    def persist(self):
        capability_state(self.state)
        self.state["timestamp"] = int(time.time())
        save_state(self.host["state_file"], self.state)
        return self.state

    def subscribe(self):
        self.optional(0x0200)
        codes = [code for code in self.state.get("notification_ids", []) if code < 0xF0]
        registered = set()
        if codes:
            acknowledgement = self.optional(0x0205, bytes([len(codes), *codes]), sequence=0xF0)
            if acknowledgement == b"" or success(acknowledgement):
                registered.update(codes)
            elif (acknowledgement and len(acknowledgement) >= 2 and acknowledgement[0] == 1
                    and len(acknowledgement) == 2 + 2 * acknowledgement[1]):
                # Free4 reports [batch=1, count, event, result ...].
                # The leading 1 is a format tag, not an error status.
                for index in range(2, len(acknowledgement), 2):
                    if acknowledgement[index] in codes and acknowledgement[index+1] == 0:
                        registered.add(acknowledgement[index])
            for code in codes:
                if code not in registered:
                    reply = self.optional(0x0201, bytes([code]), sequence=0xF0)
                    if success(reply):
                        registered.add(code)
        self.state["registered_notifications"] = sorted(registered)
        self.state["notifications_active"] = bool(registered)
        self.persist()

    def require(self, capability):
        if not self.state.get("capabilities", {}).get(capability):
            raise ControlError("unsupported", "This device has not confirmed the requested capability")

    def write(self, command, payload):
        reply = self.request(command, payload)
        if not success(reply):
            raise ControlError("rejected", f"Earbuds rejected command {command:04x}")

    def set_noise(self, setting):
        if setting not in NOISE_PAYLOADS:
            raise ControlError("invalid", "Invalid listening mode")
        if setting in ("smart", "light", "medium", "deep"):
            self.require("noise_levels")
        elif setting == "adaptive":
            self.require("adaptive")
        if self.state.get("noise_setting") == setting:
            reply = self.request(0x010C, b"\x01\x01")
            if success(reply) and self.state.get("noise_setting") == setting:
                return {"mode": self.state["noise_mode"], "setting": setting}
        if (self.state.get("product_id") == "068C10"
                and self.state.get("wear_left") in ("removed", "in_case")
                and self.state.get("wear_right") in ("removed", "in_case")):
            raise ControlError("wear_required", "Wear the earbuds before changing the listening mode")
        self.write(0x0404, NOISE_PAYLOADS[setting])
        reply = self.request(0x010C, b"\x01\x01")
        observed = self.state.get("noise_setting")
        matches = self.state.get("noise_mode") == "anc" if setting == "anc" else observed == setting
        if not success(reply) or not matches:
            raise ControlError("mismatch", f"Listening mode readback did not match {setting}")
        return {"mode": self.state["noise_mode"], "setting": self.state.get("noise_setting")}

    def set_feature(self, name, enabled):
        if name not in FEATURES or type(enabled) is not bool:
            raise ControlError("invalid", "Invalid feature or switch value")
        self.require(name)
        feature = self.state.get("game_feature", 0x06) if name == "game_mode" else FEATURES[name]
        # Free4 accepts a generic sequence but ignores the game-mode write.
        # The documented fixed F0 sequence is required for this feature.
        if name == "game_mode":
            reply = self.request(0x0403, bytes([feature, int(enabled)]), sequence=0xF0)
            if not success(reply):
                raise ControlError("rejected", "Earbuds rejected the game mode command")
        else:
            self.write(0x0403, bytes([feature, int(enabled)]))
        for _ in range(8 if name == "game_mode" else 3):
            time.sleep(0.2 if name == "game_mode" else 0.08)
            response = self.refresh_features()
            if success(response) and self.state.get("features", {}).get(name) is enabled:
                return {"feature": name, "enabled": enabled}
        raise ControlError("mismatch", "Feature readback did not match the requested state")

    def set_eq(self, preset_id):
        self.require("eq")
        if type(preset_id) is not int or preset_id not in {p["id"] for p in self.state.get("eq_presets", [])}:
            raise ControlError("invalid", "Unknown EQ preset")
        self.write(0x0406, bytes([preset_id]))
        reply = self.request(0x010F)
        if not success(reply) or self.state.get("eq_current") != preset_id:
            raise ControlError("mismatch", "EQ readback did not match the requested preset")
        return {"preset_id": preset_id}

    def custom_eq(self, action, entry):
        self.require("custom_eq")
        existing = {p["id"]: p for p in self.state.get("custom_equalizers", [])}
        preset_id = entry.get("id", 0)
        if action in (2, 3) and preset_id not in existing:
            raise ControlError("invalid", "Only an existing custom EQ may be edited or deleted")
        if action == 3 and preset_id == self.state.get("eq_current"):
            raise ControlError("active_eq", "Select another preset before deleting the current EQ")
        if action == 3:
            entry = existing[preset_id]
        elif action == 2:
            old = existing[preset_id]
            if (entry.get("minimum") != old["minimum"] or entry.get("maximum") != old["maximum"]
                    or [b["frequency"] for b in entry.get("bands", [])] != [b["frequency"] for b in old["bands"]]):
                raise ControlError("invalid", "Keep the device's EQ frequency and gain range")
        elif any(p["name"] == entry.get("name") for p in existing.values()):
            raise ControlError("duplicate_eq", "An EQ with this name already exists")
        try:
            payload = encode_equalizer(action, entry)
        except (ValueError, TypeError, KeyError) as error:
            raise ControlError("invalid", str(error)) from error
        self.write(0x0418, payload)
        reply = self.request(0x0122, b"\x01\x05")
        decoded = decode_equalizers(reply)
        if decoded is None:
            raise ControlError("mismatch", "Cannot read back the custom EQ list")
        if action == 3:
            if any(p["id"] == preset_id for p in decoded):
                raise ControlError("mismatch", "Deleted EQ still appears in the list")
        else:
            candidates = [p for p in decoded if (p["id"] not in existing if action == 1 else p["id"] == preset_id)]
            found = next((p for p in candidates if p["name"] == entry["name"] and p["bands"] == entry["bands"]), None)
            if found is None:
                raise ControlError("mismatch", "Custom EQ readback did not match the saved values")
            preset_id = found["id"]
        self.request(0x010F)
        return {"preset_id": preset_id, "eq_action": action}

    def find(self, enabled, persistent=False):
        self.require("find_device")
        if type(enabled) is not bool:
            raise ControlError("invalid", "Invalid find value")
        if enabled:
            # A cached wear event can be older than the user's last action.
            # Require a fresh response immediately before any audible command.
            reply = self.request(0x0109)
            wear = counted_pairs(reply)
            if not wear or any(wear.get(side) not in (1, 4, 5) for side in (1, 2)):
                raise ControlError("remove_earbuds", "Cannot confirm that both earbuds are removed")
        if enabled and (not persistent or any(self.state.get("wear_" + side) not in ("removed", "in_case") for side in ("left", "right"))):
            raise ControlError("remove_earbuds", "Remove both earbuds before playing the find sound")
        self.write(0x0400, bytes([int(enabled)]))
        self.find_deadline = time.monotonic() + 10 if enabled else None
        self.state["finding"] = enabled
        return {"finding": enabled}

    def execute(self, action, value=None, persistent=False):
        try:
            if action in ("status", "refresh"):
                self.refresh(full=True)
                result = {}
            elif action == "set-anc":
                result = self.set_noise(str(value).lower())
            elif action == "cycle-anc":
                modes = ["anc", "transparency", "off"]
                if self.state.get("capabilities", {}).get("adaptive"):
                    modes.insert(1, "adaptive")
                current = self.state.get("noise_mode")
                target = modes[(modes.index(current) + 1) % len(modes)] if current in modes else "anc"
                result = self.set_noise(target)
            elif action == "set-feature":
                result = self.set_feature(value["name"], value["enabled"])
            elif action == "set-eq":
                result = self.set_eq(value)
            elif action in ("save-eq", "delete-eq"):
                eq_action = 3 if action == "delete-eq" else (2 if value.get("id", 0) else 1)
                result = self.custom_eq(eq_action, value)
            elif action == "find":
                result = self.find(value, persistent)
            else:
                raise ControlError("invalid", "Unknown command")
            self.persist()
            return {"success": True, **result, "snapshot": self.state}
        except (ControlError, ValueError, TypeError, KeyError, OSError) as error:
            self.persist()
            return {"success": False, "error": str(error),
                    "error_code": getattr(error, "code", "invalid"), "snapshot": self.state}


def query_device(host, mac, name=None):
    try:
        with Session(host, mac, name) as session:
            return session.refresh(full=True)
    except (ControlError, OSError) as error:
        state = {"connected": False, "mac": mac, "error": str(error),
                 "error_code": getattr(error, "code", "connection"), "timestamp": int(time.time())}
        save_state(host["state_file"], state)
        return state


def standalone(host, mac, action, value=None, name=None):
    try:
        with Session(host, mac, name) as session:
            session.refresh(full=True)
            return session.execute(action, value)
    except (ControlError, OSError) as error:
        return {"success": False, "error": str(error), "error_code": getattr(error, "code", "connection")}


def command_socket_path(host):
    return os.path.join(os.path.dirname(host["state_file"]), "oppo_pods_commands.sock")


def configured_mac(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}", value):
        raise ValueError("Invalid Bluetooth address")
    return value.upper()


def monitor_request(host, mac, action, value=None):
    """None means no monitor exists; timeouts never trigger a duplicate write."""
    channel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        channel.settimeout(0.5)
        try:
            channel.connect(command_socket_path(host))
        except (FileNotFoundError, ConnectionRefusedError):
            return None
        channel.settimeout(25)
        packet = json.dumps({"mac": mac, "action": action, "value": value}, ensure_ascii=False).encode() + b"\n"
        channel.sendall(packet)
        data = bytearray()
        while len(data) <= 65536 and not data.endswith(b"\n"):
            chunk = channel.recv(4096)
            if not chunk:
                break
            data.extend(chunk)
        return json.loads(data)
    except (OSError, ValueError) as error:
        return {"success": False, "error": str(error), "error_code": "timeout"}
    finally:
        channel.close()


def emit(state):
    print(json.dumps(state, ensure_ascii=False), flush=True)


def monitor(host, mac_override=None, desktop_pause=True):
    """A stream process owned by Noctalia; commands share its one connection."""
    path = command_socket_path(host)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    session = None
    playback = WearPlaybackBridge(desktop_pause)
    def stop(_signum, _frame):
        raise KeyboardInterrupt
    previous_term_handler = signal.signal(signal.SIGTERM, stop)
    with open(host["lock_file"], "a") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            server.close()
            signal.signal(signal.SIGTERM, previous_term_handler)
            return
        try:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(path)
            server.bind(path)
            os.chmod(path, 0o600)
            server.listen(4)
            next_connect = next_fast = next_full = next_emit = 0
            last_state = {"connected": False}
            while True:
                now = time.monotonic()
                if session is None and now >= next_connect:
                    mac, name = (mac_override, None) if mac_override else host["find_device"]()
                    if mac:
                        candidate = Session(host, mac, name)
                        try:
                            candidate.__enter__()
                            candidate.refresh(full=True)
                            candidate.subscribe()
                            session = candidate
                            last_state = session.state
                            next_fast, next_full = now + 15, now + 60
                        except (ControlError, OSError) as error:
                            candidate.close()
                            last_state = {"connected": False, "error": str(error), "timestamp": int(time.time())}
                    else:
                        last_state = {"connected": False, "timestamp": int(time.time())}
                    next_connect = time.monotonic() + 3
                    save_state(host["state_file"], last_state)
                readers = [server] + ([session.connection] if session else [])
                readable, _, _ = select.select(readers, [], [], 0.2)
                try:
                    if session and session.connection in readable:
                        session.receive(0.2)
                        session.persist()
                    if server in readable:
                        client, _ = server.accept()
                        with client:
                            client.settimeout(0.7)
                            request = bytearray()
                            while len(request) < 8192 and not request.endswith(b"\n"):
                                chunk = client.recv(4096)
                                if not chunk:
                                    break
                                request.extend(chunk)
                            try:
                                value = json.loads(request)
                                if value.get("action") == "configure":
                                    # A settings change is serialized with all other commands.
                                    config = value.get("value")
                                    new_mac = configured_mac(config.get("mac") if isinstance(config, dict) else config)
                                    if isinstance(config, dict) and "pause_on_remove" in config:
                                        if type(config["pause_on_remove"]) is not bool:
                                            raise ValueError("Invalid desktop pause setting")
                                        playback.enabled = config["pause_on_remove"]
                                    playback.reset()
                                    if session:
                                        session.close()
                                    session = None
                                    mac_override = new_mac
                                    next_connect = 0
                                    last_state = {"connected": False, "timestamp": int(time.time())}
                                    save_state(host["state_file"], last_state)
                                    result = {"success": True, "snapshot": last_state}
                                elif session and value.get("mac") in (None, session.mac):
                                    result = session.execute(value.get("action"), value.get("value"), persistent=True)
                                else:
                                    result = {"success": False, "error_code": "connection", "error": "Earbuds are not connected"}
                            except (ValueError, TypeError, AttributeError):
                                result = {"success": False, "error_code": "invalid", "error": "Invalid request"}
                            with contextlib.suppress(OSError):
                                client.sendall(json.dumps(result, ensure_ascii=False).encode() + b"\n")
                    now = time.monotonic()
                    if session:
                        if session.find_deadline is not None and (now >= session.find_deadline
                                or "worn" in (session.state.get("wear_left"), session.state.get("wear_right"))):
                            session.execute("find", False, persistent=True)
                        if session.pending_refresh or now >= next_full:
                            session.refresh(full=True)
                            session.pending_refresh = False
                            next_full = time.monotonic() + 60
                            next_fast = time.monotonic() + 15
                        elif now >= next_fast:
                            session.refresh()
                            next_fast = time.monotonic() + 15
                        last_state = session.state
                except (ControlError, OSError) as error:
                    if session:
                        session.close()
                    session = None
                    next_connect = time.monotonic() + 1
                    last_state = {"connected": False, "error": str(error), "timestamp": int(time.time())}
                    save_state(host["state_file"], last_state)
                playback.update(last_state)
                if time.monotonic() >= next_emit:
                    if session:
                        session.persist()
                    emit(last_state)
                    next_emit = time.monotonic() + 1
        except (BrokenPipeError, KeyboardInterrupt):
            pass
        finally:
            playback.reset()
            if session:
                session.close()
            server.close()
            with contextlib.suppress(FileNotFoundError):
                os.unlink(path)
            signal.signal(signal.SIGTERM, previous_term_handler)
