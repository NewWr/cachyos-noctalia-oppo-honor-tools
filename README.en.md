# CachyOS / Noctalia OPPO Earbuds and HONOR Laptop Tools

English · [简体中文](README.md)

**Noctalia** plugins for **CachyOS / Linux**: **OPPO Enco Free4** Bluetooth earbud battery, active noise cancellation (ANC), EQ and wear/playback integration; **HONOR MagicBook Pro 14 (FMB-P)** fan RPM, temperature monitoring, keyboard backlight and battery charge thresholds. Includes complete source, installers and Chinese/English documentation.

Each tool can be enabled independently. Other earbuds expose partial controls according to known protocol capabilities; HONOR features require matching hardware interfaces. This is a community/local project, not an official vendor release.

Repository: [NewWr/cachyos-noctalia-oppo-honor-tools](https://github.com/NewWr/cachyos-noctalia-oppo-honor-tools).

```bash
git clone https://github.com/NewWr/cachyos-noctalia-oppo-honor-tools.git
cd cachyos-noctalia-oppo-honor-tools
```


## The three tools

| Tool | Plugin ID / source | Entry and purpose | Hardware scope |
| --- | --- | --- | --- |
| OPPO Pods | `osp54/oppo-pods` · [source and guide](plugins/oppo-pods/README.en.md) | Bar widget for battery, noise modes, EQ, device settings and wear/playback integration | Extended controls were historically verified on OPPO Enco Free4 standard edition, product `068C10`, firmware 138; other models expose a subset according to protocol capabilities |
| HONOR Hardware | `dc/honor-fan` · [source and guide](plugins/honor-fan/README.en.md) | Control Center home shortcut “HONOR 硬件”; two fan speeds, temperatures and three keyboard backlight levels | HONOR MagicBook Pro 14, DMI vendor `HONOR`, product `FMB-P` |
| HONOR Battery Profiles | `dc/honor-battery-profile` · [source and guide](plugins/honor-battery-profile/README.en.md) | Control Center “充电 40/70” etc.; optional bar widget; charge threshold selection | HONOR FMB-P with working `huawei-wmi` charge thresholds and `BAT0` interfaces |

HONOR Hardware declares a home shortcut, with no independent bar widget. The battery plugin declares both a shortcut and an optional bar widget. Battery profiles select charging thresholds, not CPU performance modes or charging wattage.

## System and compatibility

The environment inspected for this package was **CachyOS (Arch family), Linux 7.2.9-1-cachyos, Noctalia 5.2.1, HONOR FMB-P / M1030**. These are system/model identifiers, not serial numbers.

- Linux, Wayland and Noctalia's **Luau/TOML plugin system** are required. The installed shell reports 5.2.1. OPPO declares plugin API 24; the HONOR plugins declare API 22. Use a shell supporting API 24 and compatibility with API 22.
- These are not GNOME extensions, KDE widgets, Waybar modules or legacy QML Noctalia plugins. Windows and macOS are unsupported.
- Other Linux distributions may be portable targets, but this package does not claim validation on Ubuntu, Debian, Fedora or other HONOR models.
- The Python controller uses the standard library. Repository checks require Python **3.11+** for `tomllib`. OPPO requires BlueZ/`bluetoothctl`; wear/playback integration additionally needs `busctl`, `pactl` and MPRIS players.
- HONOR drivers require headers matching the running kernel, DKMS and a compiler toolchain. The battery backend requires Bash, systemd, sudo and util-linux `flock`.

## Layout

```text
plugins/
  oppo-pods/                 # Complete plugin, icons, translations and offline tests
  honor-fan/                 # Hardware service, home shortcut and panel
  honor-battery-profile/     # Battery service, shortcut, optional bar widget and panel
backends/
  honor-hardware/            # C source for two optional DKMS modules
  honor-battery/             # Helper, boot unit, resume hook, defaults, permission template
scripts/                    # Installers, offline checks and public-content scanner
examples/                   # UI fragments with no personal configuration
docs/                       # Chinese/English publishing, privacy and verification guides
LICENSES/                   # Full MIT and GPL-2.0-only texts
```

## Install the plugins

Install and start a compatible Noctalia first. From the repository root, as the desktop user:

```bash
bash scripts/install-plugins.sh --dry-run
bash scripts/install-plugins.sh
```

The installer copies to `$XDG_DATA_HOME/noctalia-device-toolkit/plugins` (under `~/.local/share` by default), registers the `device-toolkit` path source, and enables all three IDs. It does not rewrite desktop settings and refuses an existing destination. IPC must be reachable in the user session running Noctalia. If copying succeeds but registration fails, the script prints a recovery registration command.

Then use Noctalia Settings:

1. Bar → Widgets: add **OPPO Pods**.
2. Control Center → Home shortcuts: add **HONOR Hardware** and **HONOR Battery Profiles**. The current HONOR UI text is Chinese.
3. Optionally add the battery plugin's `battery-profile` bar widget.

Original plugin IDs are preserved. If a community OPPO copy or older HONOR path source is already installed, select this repository's source in plugin settings and disable/remove the duplicate local source. A matching display name does not establish which implementation is loaded. Keep the community source available if you want to revert.

For a single tool, register the `plugins` directory directly and enable only its ID:

```bash
noctalia msg plugins source add device-toolkit path "$(pwd)/plugins"
noctalia msg plugins enable osp54/oppo-pods
```

Keep the repository at that path when using direct registration. Do not also run the installer to register the same source name.

## HONOR backends

**The inspected machine already has the required backends; packaging does not require reinstalling them.** On another machine, verify DMI and sysfs interfaces first using the individual guides. System installers support `--dry-run` and refuse existing target files.

```bash
# Only for an FMB-P lacking the matching drivers; reboot after installation.
bash scripts/install-hardware-drivers.sh --dry-run
sudo bash scripts/install-hardware-drivers.sh

# Preview first. Replace YOUR_DESKTOP_USER with the actual desktop account.
bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER --dry-run
sudo bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER
```

The battery installer enables the next-boot service without changing the current thresholds. Optional desktop authorization uses the `honor-charge` group and allows only three exact preset commands. Log out and back in after group membership changes. Without `--desktop-user`, no passwordless rule is installed; use `sudo honor-battery-profile set ...` manually, and panel writes cannot run without authorization.

This repository includes no BIOS/ACPI dumps, precompiled DSDT or generic firmware patcher. Resolve machine-specific firmware/kernel support first if the charge interfaces are missing. A panel cannot create those interfaces. Do not copy ACPI tables from another computer as a compatibility workaround.

## Check and publish

```bash
bash scripts/check.sh
```

Checks include a public-content scan; Python, TOML, JSON and Shell syntax; OPPO offline regression tests; and plugin lint when Noctalia is installed. The scanner reports locations and categories without printing suspected credential values.

See the [verification report](docs/VERIFICATION.en.md) and [GitHub upload guide](docs/GITHUB_UPLOAD.en.md). This folder is ready to become one repository root and contains no original machine Git history or remote authentication settings.

## Privacy and maintenance

The upload copy removes the original remote earbud-image signing credential and download code. Local icons and an optional local image cache remain; earbud controls do not need that remote service. Test addresses are fictional. User settings, Bluetooth pairing keys, playback history, OEM product keys and hardware serial numbers are excluded.

The plugin still creates local runtime caches containing device addresses/state. These are not source files. See the [privacy guide](docs/PRIVACY.en.md) and [public-file/history audit](docs/SECRET_AUDIT.en.md). `.gitignore` cannot protect sensitive files already committed; rescan and review the staged content before each new publication.

To update, disable the relevant plugin, back up its installed directory outside the repository, copy the new source and re-enable it. To remove the plugins, disable the IDs, remove the `device-toolkit` source and remove the UI entries in Settings. Backend removal is documented in the individual guides.

## Licenses and origins

Plugins and repository scripts/docs use MIT. The two kernel modules under `backends/honor-hardware/` retain **GPL-2.0-only**. OPPO author `osp54`, original namespaces and module author notices are preserved. `dc` is the original HONOR plugin's public namespace, not a desktop username that installers require. See [LICENSE](LICENSE) and [third-party notices](THIRD_PARTY.en.md).
