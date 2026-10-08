"""OPPO wire facts implemented for Noctalia, without third-party dependencies."""
import struct
import time

NOISE_PAYLOADS = {
    "off": b"\x01\x01\x01", "anc": b"\x01\x01\x02",
    "transparency": b"\x01\x01\x04", "deep": b"\x01\x01\x10",
    "medium": b"\x01\x01\x20", "light": b"\x01\x01\x40",
    "smart": b"\x01\x01\x80", "adaptive": b"\x01\x01\x00\x08",
}
FEATURES = {"wear_detection": 0x04, "game_mode": 0x06,
            "hearing_enhancement": 0x0B, "dual_device": 0x11, "spatial_sound": 0x1B}
CODECS = {0: "SBC", 1: "LDAC", 2: "AAC", 3: "LHDC", 4: "LC3",
          5: "aptX", 6: "aptX HD", 7: "aptX Adaptive", 8: "LHDC"}
DEFAULT_FREQUENCIES = [62, 250, 1000, 4000, 8000, 16000]


def make_frame(command, seq=1, payload=b""):
    if len(payload) > 248:
        raise ValueError("Command payload exceeds the protocol frame limit")
    return struct.pack("<BBBBHBH", 0xAA, len(payload) + 7, 0, 0,
                       command, seq & 0xFF, len(payload)) + payload


class FrameDecoder:
    """Retain incomplete frames and never interpret payload bytes as new frames."""
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, chunk):
        self.buffer.extend(chunk)
        frames = []
        while self.buffer:
            try:
                start = self.buffer.index(0xAA)
            except ValueError:
                self.buffer.clear()
                break
            del self.buffer[:start]
            if len(self.buffer) < 9:
                break
            length = int.from_bytes(self.buffer[7:9], "little")
            if (length > 8192 or self.buffer[2:4] != b"\x00\x00"
                    or self.buffer[1] != (length + 7) & 0xFF):
                del self.buffer[0]
                continue
            if len(self.buffer) < 9 + length:
                break
            command = int.from_bytes(self.buffer[4:6], "little")
            frames.append((command, self.buffer[6], bytes(self.buffer[9:9 + length])))
            del self.buffer[:9 + length]
        return frames


def parse_frames(data):
    return FrameDecoder().feed(data)


def success(payload):
    return payload is not None and len(payload) > 0 and payload[0] == 0


def counted_pairs(payload, status=True):
    offset = 1 if status else 0
    if (status and not success(payload)) or payload is None or len(payload) < offset + 1:
        return None
    count = payload[offset]
    if len(payload) != offset + 1 + 2 * count:
        return None
    return {payload[i]: payload[i+1] for i in range(offset + 1, len(payload), 2)}


def decode_noise(payload, status=True):
    offset = 1 if status else 0
    if (status and not success(payload)) or payload is None or len(payload) < offset + 4:
        return None
    kind, encoding, low, high = payload[offset:offset+4]
    if kind not in (1, 4) or encoding != 1:
        return None
    setting = {(0x01, 0): "off", (0x08, 0): "off", (0x02, 0): "smart",
               (0x80, 0): "smart", (0x40, 0): "light", (0x20, 0): "medium",
               (0x10, 0): "deep", (0x04, 0): "transparency",
               (0, 1): "transparency", (0, 2): "transparency", (0, 8): "adaptive"}.get((low, high))
    if setting is None:
        return None
    level = setting if setting in ("smart", "light", "medium", "deep") else None
    return {"noise_mode": "anc" if level else setting,
            "noise_setting": "smart" if kind == 4 else setting,
            "noise_level": "smart" if kind == 4 else level,
            "noise_realtime": setting if kind == 4 else None,
            "noise_wire": bytes([low, high]).hex()}


def decode_equalizers(payload):
    if not success(payload) or len(payload) < 2:
        return None
    pos = 2
    result = []
    try:
        for _ in range(payload[1]):
            if pos + 5 > len(payload):
                return None
            selected, lower, upper, preset_id, size = payload[pos:pos+5]
            pos += 5
            if pos + size + 1 > len(payload):
                return None
            name = payload[pos:pos+size].decode("utf-8").rstrip("\x00")
            pos += size
            count = payload[pos]
            pos += 1
            if count > 32 or pos + 3 * count > len(payload):
                return None
            bands = []
            for _ in range(count):
                frequency, gain = struct.unpack_from("<Hb", payload, pos)
                bands.append({"frequency": frequency, "gain": gain})
                pos += 3
            lower, upper = struct.unpack("bb", bytes([lower, upper]))
            if lower > upper or any(b["gain"] < lower or b["gain"] > upper for b in bands):
                return None
            result.append({"id": preset_id, "name": name, "selected": bool(selected),
                           "minimum": lower, "maximum": upper, "bands": bands})
    except (UnicodeDecodeError, struct.error):
        return None
    return result if pos == len(payload) else None


def encode_equalizer(action, entry):
    if action not in (1, 2, 3) or not isinstance(entry, dict):
        raise ValueError("Invalid EQ operation")
    name = entry.get("name", "")
    if not isinstance(name, str) or not name.strip() or any(ord(c) < 32 for c in name):
        raise ValueError("EQ name must be nonempty and contain no control characters")
    name_bytes = name.encode("utf-8")
    bands = entry.get("bands", [])
    minimum, maximum = entry.get("minimum", -6), entry.get("maximum", 6)
    preset_id = entry.get("id", 0)
    if (type(preset_id) is not int or not 0 <= preset_id <= 255
            or type(minimum) is not int or type(maximum) is not int
            or not -128 <= minimum <= maximum <= 127 or not 1 <= len(bands) <= 32):
        raise ValueError("Invalid EQ ID, gain range or band count")
    if action == 1 and preset_id != 0:
        raise ValueError("A new EQ must have ID 0")
    if action != 1 and preset_id == 0:
        raise ValueError("Editing or deleting requires an existing custom EQ ID")
    if len(name_bytes) + 6 + 3 * len(bands) > 248:
        raise ValueError("EQ name and bands exceed the protocol frame limit")
    payload = bytearray(struct.pack("<BbbBB", action, minimum, maximum, preset_id, len(name_bytes)))
    payload.extend(name_bytes)
    payload.append(len(bands))
    frequencies = set()
    for band in bands:
        frequency, gain = band.get("frequency"), band.get("gain")
        if (type(frequency) is not int or not 1 <= frequency <= 65535
                or frequency in frequencies or type(gain) is not int
                or not minimum <= gain <= maximum):
            raise ValueError("Invalid EQ frequency or gain")
        frequencies.add(frequency)
        payload.extend(struct.pack("<Hb", frequency, gain))
    if len(payload) > 248:
        raise ValueError("EQ name and bands exceed the protocol frame limit")
    return bytes(payload)


def decode_devices(payload):
    if not success(payload) or len(payload) < 2:
        return None
    pos, result = 2, []
    try:
        for _ in range(payload[1]):
            if pos + 10 > len(payload):
                return None
            address = ":".join(f"{b:02X}" for b in payload[pos:pos+6][::-1])
            pos += 6
            kind, status, flags, size = payload[pos:pos+4]
            pos += 4
            if pos + size > len(payload):
                return None
            name = payload[pos:pos+size].decode("utf-8").rstrip("\x00")
            pos += size
            result.append({"name": name or address, "address": address, "type": kind,
                           "connection_state": status, "active": bool(flags & 1)})
    except UnicodeDecodeError:
        return None
    return result if pos == len(payload) else None


def decode_firmware(payload):
    if not success(payload) or len(payload) < 3:
        return None
    try:
        parts = payload[2:].decode("ascii").rstrip("\x00 ").split(",")
        if len(parts) != payload[1] * 3:
            return None
        entries = [{"component": int(parts[i]), "type": int(parts[i+1]), "version": int(parts[i+2])}
                   for i in range(0, len(parts), 3)]
    except (ValueError, UnicodeDecodeError):
        return None
    return entries


def supports(bitmap, bit):
    return bit // 8 < len(bitmap) and bool(bitmap[bit // 8] & (1 << (bit % 8)))


def capability_state(state):
    """Extra controls are gated by this tested model and the reported commands."""
    known = state.get("product_id") == "068C10"
    bitmap = bytes.fromhex(state.get("command_bitmap", ""))
    state["has_anc"] = supports(bitmap, 8)
    reported = state.get("features", {})
    caps = {"noise_levels": known and supports(bitmap, 8),
            "adaptive": known and supports(bitmap, 8),
            "eq": known and supports(bitmap, 10),
            "custom_eq": known and supports(bitmap, 34),
            "find_device": known and supports(bitmap, 5),
            "wear_status": supports(bitmap, 4),
            "device_list": known and supports(bitmap, 29)}
    for name in FEATURES:
        caps[name] = known and supports(bitmap, 7) and name in reported
    state["capabilities"] = caps
    presets = [{"id": 0, "name": "至臻原音", "key": "original"},
               {"id": 1, "name": "纯享人声", "key": "vocals"},
               {"id": 2, "name": "澎湃低音", "key": "bass"}] if caps["eq"] else []
    versions = [e["version"] for e in state.get("firmware", []) if e["component"] in (1, 2) and e["type"] == 2]
    if len(versions) == 2 and min(versions) >= 118 and caps["eq"]:
        presets.append({"id": 7, "name": "活力动感", "key": "energetic"})
    for entry in state.get("custom_equalizers", []):
        presets.append({"id": entry["id"], "name": entry["name"], "custom": True})
    state["eq_presets"] = presets
    for preset in presets:
        if preset["id"] == state.get("eq_current"):
            state["eq_name"] = preset["name"]
            break
    else:
        state["eq_name"] = str(state.get("eq_current", "—"))
    return state


def apply_frame(state, command, payload):
    """Merge only validated responses; unsolicited updates may be partial."""
    event = None
    if command == 0x0204 and payload:
        event, payload = payload[0], payload[1:]
    elif command == 0x8202 and success(payload) and len(payload) >= 2:
        event, payload = payload[1], payload[2:]
    if command == 0x8100 and success(payload):
        state["command_bitmap"] = payload[1:].hex()
    elif command == 0x8103 and success(payload) and len(payload) == 4:
        state["product_id"] = f"{int.from_bytes(payload[1:], 'little'):06X}"
    elif command == 0x8106 or event == 1:
        values = counted_pairs(payload, status=event is None)
        if values is not None:
            for component, value in values.items():
                name = {1: "left", 2: "right", 3: "case"}.get(component)
                if name and (value & 127) <= 100:
                    state["battery_" + name] = value & 127
                    state["charging_" + name] = bool(value & 128)
                    if name == "case":
                        state["case_offline"] = False
    elif command == 0x8109 or event == 2:
        values = counted_pairs(payload, status=event is None)
        if values is not None:
            for component, value in values.items():
                name = {1: "left", 2: "right"}.get(component)
                if name:
                    state["wear_raw_" + name] = value
                    state["wear_observed_at"] = time.time()
                    state["wear_" + name] = {0: "disconnected", 1: "removed", 5: "removed",
                                           3: "worn", 7: "worn", 4: "in_case"}.get(value, "unknown")
    elif command == 0x810C or event == 3:
        mode = decode_noise(payload, status=event is None)
        if mode:
            if mode["noise_setting"] == "smart" and mode["noise_realtime"] is None and state.get("noise_setting") == "smart":
                mode["noise_realtime"] = state.get("noise_realtime")
            state.update(mode)
    elif command == 0x810D:
        values = counted_pairs(payload)
        if values is not None:
            features = {}
            for name, feature in FEATURES.items():
                if feature in values and values[feature] in (0, 1):
                    features[name] = bool(values[feature])
            if 0x28 in values and values[0x28] in (0, 1):
                features["game_mode"] = bool(values[0x28])
                state["game_feature"] = 0x28
            elif 0x06 in values:
                state["game_feature"] = 0x06
            state["features"] = features
            for name, enabled in features.items():
                state[name] = enabled
    elif command == 0x810F and success(payload) and len(payload) == 2:
        state["eq_current"] = payload[1]
    elif command == 0x8122:
        entries = decode_equalizers(payload)
        if entries is not None:
            state["custom_equalizers"] = entries
    elif command == 0x8105:
        entries = decode_firmware(payload)
        if entries is not None:
            state["firmware"] = entries
            software = {e["component"]: str(e["version"]) for e in entries if e["type"] == 2}
            state["firmware_version"] = ".".join(software[key] for key in sorted(software))
    elif command == 0x8114 and success(payload) and len(payload) == 2:
        state["codec"] = CODECS.get(payload[1], f"Codec {payload[1]}")
    elif command == 0x8112 or event == 6:
        # Device event omits the success byte present in a query response.
        entries = decode_devices(b"\x00" + payload if event == 6 else payload)
        if entries is not None:
            state["devices"] = entries
    elif command == 0x8115 and success(payload) and len(payload) > 2:
        state["hearing_profile_present"] = True
    elif command == 0x8200 and success(payload) and len(payload) == 2 + payload[1]:
        state["notification_ids"] = list(payload[2:])
    return state
