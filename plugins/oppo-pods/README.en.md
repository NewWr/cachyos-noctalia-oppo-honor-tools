# OPPO Pods

[简体中文](README.md) · [Collection](../../README.en.md)

A Noctalia bar widget for earbud connection status and controls. ID `osp54/oppo-pods`, original version `1.1.2`, API `24`. It controls devices already paired and connected; BlueZ and the desktop audio system handle initial pairing and audio routing.

## Features

- Left/right/case battery, reported charging and wear states, and low-battery notifications.
- Left-click opens the panel; right-click cycles available listening modes.
- Free4 extension: off, transparency, adaptive, and smart/light/medium/deep ANC; dual-device connection, game latency, spatial sound, wear detection and personalized hearing switches.
- Factory and existing earbud EQ presets; create/edit/delete six-band custom EQ. Saving writes to the earbuds. Select another preset before deleting the active one.
- Model, firmware, current codec and saved-device list. Saved does not mean currently connected.
- Pause MPRIS players actually routed to these earbuds on removal. Resume on stable rewear only when the plugin owns the pause and the user has not changed relevant playback state.

Case battery may be unknown with the lid closed. Firmware may reject noise changes when both earbuds are removed. Personalized hearing uses existing earbud data rather than performing a new hearing test. Codec information is read-only; this tool does not negotiate LDAC/LHDC.

Find-earbud sound remains experimental. The controller requires both earbuds removed, schedules a stop 10 seconds after acceptance, and sends a stop on rewear. Historical notes do not establish audible operation; protocol acceptance is not sound verification.

Unimplemented: gesture/call bindings, complete fit tests, prompt volume, active-device switching, AI translation, phone camera control and firmware upgrades.

## Supported devices and systems

| Item | Scope |
| --- | --- |
| System | Linux + Wayland + Noctalia Luau plugin API 24; inspected environment CachyOS / Noctalia 5.2.1 |
| Historically verified extension | OPPO Enco Free4 standard edition, product `068C10`, firmware 138 |
| Other models | Some OPPO Enco, OnePlus Buds and realme Buds names are mapped in code. A name map is not certification; extended operations require a known model and actual capability fields |
| Free4 Dynaudio | Product `06C010` differs from the standard edition; complete standard-edition controls are not promised |
| Core requirements | Python 3, BlueZ, `bluetoothctl`, Linux RFCOMM; Python 3.11+ recommended for repository checks |
| Playback bridge | `busctl`, `pactl`, user D-Bus, PipeWire-Pulse or PulseAudio, MPRIS players |

No administrator privileges or API key are required. Other hardware/distributions were not retested during packaging.

## Install and use

Register the source and enable the plugin using the [collection guide](../../README.en.md#install-the-plugins). Pair and connect through the system Bluetooth UI first, then add **OPPO Pods** in Noctalia Settings → Bar → Widgets. It hides while disconnected by default; disable that setting during troubleshooting.

| Setting | Default | Meaning |
| --- | --- | --- |
| `device_mac` | empty | Auto-detect a connected device, or select a target in local settings; do not commit the address |
| `pause_on_remove` | `true` | Removal pause and rewear resume, retaining the original setting key |
| `low_battery_notifications` | `true` | Notify at 20%/10%; reset after charging or recovery above 25% |
| Widget `hide_when_disconnected` | `true` | Hide while disconnected |

Playback matching uses audio-client PIDs to avoid affecting speaker/other-headphone playback. Wear events are debounced; unknown, stale or disconnected state does not trigger a new pause. Manual playback changes, track/seek changes, routing changes and process changes cancel automatic resume. Pause ownership is in-memory; a plugin restart cannot start playback. When event monitoring is unavailable, removal pause can remain available while resume is manual.

## Local operation and privacy

`service.luau` starts the persistent `scripts/oppo_ctl.py` monitor. It keeps one RFCOMM session, receives local commands through a private Unix socket, subscribes to notifications and polls as fallback. Writes require accepted responses and state readback.

Runtime files use `$XDG_RUNTIME_DIR` (the original fallback is `/tmp`): `oppo_pods_state.json`, `oppo_pods_channel.txt`, the control lock and socket. They may contain Bluetooth addresses, saved-device lists and state. Use a normal desktop session with `XDG_RUNTIME_DIR` set and keep runtime files outside Git.

The upload copy removes the remote image signing credential and network downloader. Local icons remain. An optional PNG can be supplied locally at `$XDG_CACHE_HOME/noctalia/oppo-pods/<PRODUCT_ID>.png` (under `~/.cache` by default); do not commit personal caches. Without it, the UI falls back to bundled artwork. The bundled Enco Air4 Pro illustration is not an accurate automatic render for every model.

## Troubleshooting and verification

```bash
bluetoothctl devices Connected
noctalia plugins lint plugins/oppo-pods
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/oppo-pods/tests -v
noctalia msg panel-toggle osp54/oppo-pods:panel
```

Run from the repository root. If detection fails, confirm connection and an OPPO control service, the selected plugin source, and absence of another RFCOMM controller. Audio connectivity alone does not establish control-service availability. For playback issues, confirm MPRIS and usable `busctl`/`pactl` in the same user session.

Offline tests use mock sockets/players and anonymized payloads without contacting real earbuds. Historical functional validation and current packaging checks are distinguished in the [verification report](../../docs/VERIFICATION.en.md).

## Remove and license

```bash
noctalia msg plugins disable osp54/oppo-pods
```

Remove its bar entry in Settings. Keep the `device-toolkit` source if other collection plugins remain in use. After stopping the plugin, local OPPO caches can be cleaned separately; uninstalling the panel does not require deleting BlueZ pairing data.

MIT, preserving `osp54` attribution. See [LICENSE](LICENSE) and [third-party notices](../../THIRD_PARTY.en.md).
