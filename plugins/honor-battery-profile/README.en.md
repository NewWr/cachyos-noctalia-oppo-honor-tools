# HONOR Battery Profiles

[简体中文](README.md) · [Collection](../../README.en.md)

A Noctalia Control Center home shortcut displaying thresholds such as “充电 40/70”. ID `dc/honor-battery-profile`, version `1.0.0`, API `22`. It also provides an optional `battery-profile` bar widget.

## Features and presets

The panel shows charge level, charging status and thresholds, and selects three firmware presets:

| Preset | Start threshold | Stop threshold | Typical use |
| --- | --- | --- | --- |
| Home `home` | 40% | 70% | Long-term AC use at a lower battery charge level |
| Office `office` | 70% | 90% | AC use and short unplugged sessions |
| Travel `travel` | 95% | 100% | Near-full battery for unplugged runtime |

These are battery thresholds, not wattage limits or CPU performance modes. A lower stop threshold does not actively discharge an already fuller battery. The adapter can continue powering the computer. Firmware controls actual charging; readings can round or lag.

The backend writes the paired `huawei-wmi` interface and confirms readback. Manual selections can persist and are reapplied on resume. **Every reboot applies the configured default, initially `home` (40/70).** The boot service uses `boot`; the resume hook uses `apply`, with different semantics.

## Compatibility and requirements

Writes in this package are limited to **HONOR FMB-P (MagicBook Pro 14)**, inspected product version `M1030`. Packaging environment: CachyOS, Linux 7.2.9-1-cachyos, Noctalia 5.2.1. Other models, distributions and BIOS revisions were not validated here.

Required existing interfaces and tools:

- Noctalia Luau plugins with API 22 compatibility.
- Linux `huawei_wmi` and writable `/sys/devices/platform/huawei-wmi/charge_control_thresholds`.
- `BAT0/charge_control_start_threshold` and `charge_control_end_threshold` under `/sys/class/power_supply/` for UI reads.
- `/usr/local/bin/honor-battery-profile`, Bash, sudo, systemd and `flock`.
- Optional exact-command sudoers authorization for desktop buttons, or explicit terminal sudo for manual changes.

An empty manifest `dependencies=[]` does not mean standalone hardware control: the backend and sysfs interfaces are prerequisites. Missing interfaces may require firmware, kernel or machine-specific ACPI work. No ACPI dumps or automatic patcher are included.

## Installation and permissions

Check the machine and interfaces without writing:

```bash
cat /sys/class/dmi/id/sys_vendor /sys/class/dmi/id/product_name
cat /sys/devices/platform/huawei-wmi/charge_control_thresholds
cat /sys/class/power_supply/BAT0/charge_control_start_threshold
cat /sys/class/power_supply/BAT0/charge_control_end_threshold
```

Reuse an already installed backend. On a new FMB-P with working interfaces, from the repository root, replace the placeholder with the desktop account:

```bash
bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER --dry-run
sudo bash scripts/install-battery-backend.sh --desktop-user YOUR_DESKTOP_USER
```

Installed files: command/menu helpers, `/etc/default/honor-battery-profile`, boot unit, resume hook and optional permission rule. Existing targets cause the installer to stop. It enables the next-boot service without changing the current profile.

The optional `honor-charge` group rule permits only these three root commands, with **no argument wildcard, unrestricted passwordless sudo or hardcoded local username**:

```text
/usr/local/bin/honor-battery-profile set 40/70
/usr/local/bin/honor-battery-profile set 70/90
/usr/local/bin/honor-battery-profile set 95/100
```

Log out and back in after group changes. Helpers/config must be root-owned and unwritable by ordinary users. The helper uses `sudo -n` for ordinary-user calls so panel actions cannot hang waiting for terminal authentication. Omit `--desktop-user` for backend-only installation; panel writes will not have passwordless authorization and manual terminal use requires explicit sudo.

Install the UI using the [collection guide](../../README.en.md#install-the-plugins), then add its Control Center home shortcut. Current HONOR UI text is Chinese.

## CLI, configuration and state

```bash
honor-battery-profile status
honor-battery-profile list
sudo honor-battery-profile set home
sudo honor-battery-profile set 70/90
sudo honor-battery-profile set 95/100
sudo honor-battery-profile default
```

`default` uses `DEFAULT_PROFILE`, initially `home`. Administrators can edit `/etc/default/honor-battery-profile` to change the boot default. `PERSIST_SELECTION=no` disables saving/reading manual selections; boot still applies the default.

State: `/var/lib/honor-battery-profile/profile`; lock: `/var/lib/honor-battery-profile/.lock`. These runtime files do not belong in Git. The configuration is sourced by Bash and must remain administrator-controlled.

## Troubleshooting and checks

```bash
noctalia plugins lint plugins/honor-battery-profile
systemctl status honor-battery-profile.service
honor-battery-profile status
noctalia msg panel-toggle dc/honor-battery-profile:panel
```

Missing UI interface: inspect `BAT0` and `huawei_wmi`. Failed buttons: inspect backend installation, refreshed group membership and root file permissions. Returning to 40/70 at reboot is the default policy. Resume failures require checking the system-sleep hook and system logs.

Changing thresholds affects the real battery. Packaging used read-only commands and static checks; it did not switch the current machine's profile or run privileged installation. See [verification](../../docs/VERIFICATION.en.md).

## Removal

Disable the UI and remove its shortcut/widget in Settings:

```bash
noctalia msg plugins disable dc/honor-battery-profile
```

If this collection **newly installed** the backend, disable its boot service and remove the five corresponding files plus the optional rule:

```bash
sudo systemctl disable --now honor-battery-profile.service
sudo rm /etc/systemd/system/honor-battery-profile.service
sudo rm /usr/lib/systemd/system-sleep/honor-battery-profile
sudo rm /usr/local/bin/honor-battery-profile /usr/local/bin/honor-battery-profile-menu
sudo rm /etc/default/honor-battery-profile
# Only if the optional rule was installed:
sudo rm /etc/sudoers.d/honor-battery-profile
sudo systemctl daemon-reload
```

To revoke desktop membership, use `sudo gpasswd -d YOUR_DESKTOP_USER honor-charge`. Runtime state can be cleaned separately. Uninstalling does not automatically reset thresholds; explicitly select the desired preset before deleting the helper. Do not delete an existing backend maintained by another project/administrator.

## License and attribution

The plugin and local battery scripts use MIT. The original `dc` namespace is preserved. “Firmware preset” describes hardware behavior, not official HONOR authorship or certification of this plugin.
