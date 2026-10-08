#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SRC="$ROOT/backends/honor-battery"
desktop_user=''
dry_run=false
while (( $# )); do
    case "$1" in
        --dry-run) dry_run=true; shift ;;
        --desktop-user) [[ $# -ge 2 ]] || exit 2; desktop_user=$2; shift 2 ;;
        --help) echo 'Usage: sudo bash scripts/install-battery-backend.sh [--desktop-user USER] [--dry-run]'; exit 0 ;;
        *) echo 'Invalid arguments.' >&2; exit 2 ;;
    esac
done
targets=(
    /usr/local/bin/honor-battery-profile
    /usr/local/bin/honor-battery-profile-menu
    /etc/default/honor-battery-profile
    /etc/systemd/system/honor-battery-profile.service
    /usr/lib/systemd/system-sleep/honor-battery-profile
)
if [[ -n "$desktop_user" ]]; then targets+=(/etc/sudoers.d/honor-battery-profile); fi
if "$dry_run"; then
    printf 'Install root-owned file: %s\n' "${targets[@]}"
    [[ -z "$desktop_user" ]] || printf 'Add specified desktop user to honor-charge; allow only three preset commands.\n'
    echo 'Enable boot service for next boot; do not change the active profile now.'
    exit 0
fi
(( EUID == 0 )) || { echo 'Run with sudo.' >&2; exit 1; }
[[ $(cat /sys/class/dmi/id/sys_vendor) == HONOR && $(cat /sys/class/dmi/id/product_name) == FMB-P ]] || {
    echo 'Only HONOR FMB-P is supported.' >&2; exit 1;
}
[[ -w /sys/devices/platform/huawei-wmi/charge_control_thresholds && -r /sys/class/power_supply/BAT0/charge_control_end_threshold ]] || {
    echo 'Required huawei-wmi / BAT0 interfaces are missing. Resolve kernel/firmware support first.' >&2; exit 1;
}
for tool in install flock systemctl; do command -v "$tool" >/dev/null; done
if [[ -n "$desktop_user" ]]; then
    [[ "$desktop_user" != root ]] && id "$desktop_user" >/dev/null || { echo 'Invalid desktop user.' >&2; exit 2; }
    for tool in visudo groupadd usermod getent; do command -v "$tool" >/dev/null; done
    visudo -cf "$SRC/sudoers/honor-battery-profile"
fi
for file in "${targets[@]}"; do
    [[ ! -e "$file" && ! -L "$file" ]] || { printf 'Refusing to replace existing file: %s\n' "$file" >&2; exit 1; }
done
install -o root -g root -m 0755 "$SRC/bin/honor-battery-profile" /usr/local/bin/honor-battery-profile
install -o root -g root -m 0755 "$SRC/bin/honor-battery-profile-menu" /usr/local/bin/honor-battery-profile-menu
install -D -o root -g root -m 0644 "$SRC/config/honor-battery-profile" /etc/default/honor-battery-profile
install -D -o root -g root -m 0644 "$SRC/systemd/honor-battery-profile.service" /etc/systemd/system/honor-battery-profile.service
install -D -o root -g root -m 0755 "$SRC/system-sleep/honor-battery-profile" /usr/lib/systemd/system-sleep/honor-battery-profile
if [[ -n "$desktop_user" ]]; then
    getent group honor-charge >/dev/null || groupadd --system honor-charge
    usermod -aG honor-charge "$desktop_user"
    install -D -o root -g root -m 0440 "$SRC/sudoers/honor-battery-profile" /etc/sudoers.d/honor-battery-profile
fi
systemctl daemon-reload
systemctl enable honor-battery-profile.service
echo 'Installed. Boot default is 40/70. Log out and in after adding desktop permissions. Current charge profile was not changed.'
