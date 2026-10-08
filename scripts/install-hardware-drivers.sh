#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ ${1:-} == --help ]]; then
    echo 'Usage: sudo bash scripts/install-hardware-drivers.sh [--dry-run]'
    exit 0
fi
[[ $# == 0 || ( $# == 1 && $1 == --dry-run ) ]] || exit 2
if [[ ${1:-} == --dry-run ]]; then
    echo 'Install/build honor-fmbp-hwmon 1.0 and honor-fmbp-kbdlight 1.1 using DKMS; enable module loading at boot.'
    echo 'Does not load modules now. Refuses existing sources or an existing keyboard LED interface.'
    exit 0
fi
(( EUID == 0 )) || { echo 'Run with sudo.' >&2; exit 1; }
[[ $(cat /sys/class/dmi/id/sys_vendor) == HONOR && $(cat /sys/class/dmi/id/product_name) == FMB-P ]] || {
    echo 'Only HONOR FMB-P is supported.' >&2; exit 1;
}
for tool in dkms make install; do command -v "$tool" >/dev/null; done
[[ -f /lib/modules/$(uname -r)/build/Makefile ]] || { echo 'Install matching kernel headers first.' >&2; exit 1; }
[[ ! -e /sys/class/leds/huawei::kbd_backlight ]] || { echo 'A keyboard LED provider already exists. Review drivers manually to avoid a duplicate provider.' >&2; exit 1; }
[[ ! -e /etc/modules-load.d/honor-device-toolkit.conf ]] || exit 1
for pair in honor-fmbp-hwmon:1.0 honor-fmbp-kbdlight:1.1; do
    name=${pair%:*}; version=${pair#*:}
    [[ ! -e /usr/src/$name-$version ]] || { echo 'Driver sources already exist; reuse the installed drivers.' >&2; exit 1; }
done
for pair in honor-fmbp-hwmon:1.0 honor-fmbp-kbdlight:1.1; do
    name=${pair%:*}; version=${pair#*:}
    install -d -o root -g root -m 0755 "/usr/src/$name-$version"
    for file in "$name.c" Makefile dkms.conf; do
        install -o root -g root -m 0644 "$ROOT/backends/honor-hardware/$name-$version/$file" "/usr/src/$name-$version/$file"
    done
    dkms add -m "$name" -v "$version"
    dkms build -m "$name" -v "$version"
    dkms install -m "$name" -v "$version"
done
install -D -o root -g root -m 0644 "$ROOT/backends/honor-hardware/modules-load.conf" /etc/modules-load.d/honor-device-toolkit.conf
echo 'Drivers installed for next boot. Reboot to activate, or load each module manually after reviewing compatibility.'
