# HONOR Hardware

[简体中文](README.md) · [Collection](../../README.en.md)

The **HONOR 硬件** shortcut on the Control Center home page. ID `dc/honor-fan`, version `1.1.4`, API `22`. The historical `fan` ID also covers temperature and keyboard backlight controls; it does not provide manual fan control.

## Features and entry

- Left-click opens two fan RPM values, CPU package/core maximum temperatures and available NVMe, Wi-Fi and ACPI temperatures.
- Keyboard backlight buttons: off, low, high; use Noctalia's native `keyboard-backlight-set`, reflect current state and refresh about every two seconds.
- Right-click opens Control Center's Monitor section for system display brightness.
- No bar widget is declared. The obsolete, undeclared `widget.luau` is excluded from this package.

Firmware retains fan control. The panel reads sensors; the optional keyboard driver writes model-specific EC registers and is not a generic driver for all HONOR laptops.

## Compatibility

Target: **HONOR MagicBook Pro 14 (DMI `HONOR` / `FMB-P`)**, inspected product version `M1030`. Packaging environment: CachyOS, kernel 7.2.9-1-cachyos, Noctalia 5.2.1.

| Interface / requirement | Purpose |
| --- | --- |
| hwmon `honor_fmbp`, `fan1_input`/`fan2_input` | Fan RPM, usually from the included `honor-fmbp-hwmon` module |
| `coretemp` | Intel CPU temperatures; AMD/other sensor names are not assumed compatible |
| `nvme`, `iwlwifi*`, `acpitz*` | Optional temperatures, shown when probes exist |
| `/sys/class/leds/huawei::kbd_backlight/`, `max_brightness=2` | Three-level keyboard LED |
| Noctalia API 22 compatibility and native backlight IPC | Panel, state updates and controls |
| `lm_sensors` | Declared dependency and manual diagnostics; the service itself reads sysfs through Shell |

Linux Wayland and native Noctalia Luau plugins are required. Other distributions/models were not validated. Sensor nodes must be readable. Native Noctalia/system policy handles backlight authorization; the panel does not directly request sudo.

## Installation

Follow the [collection guide](../../README.en.md#install-the-plugins), then add **HONOR Hardware** to Control Center home shortcuts. Current UI text is Chinese.

Check the machine and existing interfaces:

```bash
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
sensors honor_fmbp-isa-0000 coretemp-isa-0000
cat /sys/class/leds/huawei::kbd_backlight/max_brightness
```

Reuse working installed drivers. For another FMB-P missing them, two source directories are included:

- `backends/honor-hardware/honor-fmbp-hwmon-1.0`: read-only fan tachometers, DMI-gated `honor_fmbp` device.
- `backends/honor-hardware/honor-fmbp-kbdlight-1.1`: three-level LED; loading sets low brightness. Default mode is reactive; the panel changes brightness, not steady/reactive mode.

From the repository root:

```bash
bash scripts/install-hardware-drivers.sh --dry-run
sudo bash scripts/install-hardware-drivers.sh
```

Install DKMS, make and headers/toolchain **matching the running kernel** first. A Clang kernel also needs the matching LLVM tools. The installer builds both modules and configures loading at the next boot without loading them immediately. It refuses existing source directories, boot configuration or an existing keyboard LED provider. If only one module is missing, manage it individually with DKMS instead of running the combined installer.

Secure Boot requires your own module signing/trust configuration; no signing private keys are distributed. Preserve the original DMI checks and the installer's `HONOR` / `FMB-P` guard rather than forcing installation on a different model.

## Troubleshooting and checks

```bash
noctalia plugins lint plugins/honor-fan
noctalia msg panel-toggle dc/honor-fan:panel
dkms status
```

Missing readings: inspect `honor_fmbp`, `coretemp` and other hwmon nodes. Zero RPM is normal for stopped fans but can also appear without data; it alone does not prove detection. Disabled backlight buttons: check the exact LED name and `max_brightness=2`. Failed writes: check native Noctalia commands and system authorization instead of making sysfs world-writable.

Lint/build checks do not establish hardware behavior on another machine. See the [verification report](../../docs/VERIFICATION.en.md).

## Removal

```bash
noctalia msg plugins disable dc/honor-fan
```

Remove the home shortcut in Settings. If the drivers were **newly installed by this collection** and no other feature needs them, remove this collection's `/etc/modules-load.d/honor-device-toolkit.conf`, then:

```bash
sudo dkms remove honor-fmbp-hwmon/1.0 --all
sudo dkms remove honor-fmbp-kbdlight/1.1 --all
```

Reboot to stop loading them. After successful removal, the corresponding two `/usr/src` source directories can be removed. Do not delete another installer's boot configuration or pre-existing drivers.

## License

The plugin is MIT. The kernel modules preserve GPL-2.0-only headers and `MagicBook Linux project` authorship. See [third-party notices](../../THIRD_PARTY.en.md).
