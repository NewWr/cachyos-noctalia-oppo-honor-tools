# Packaging verification

[简体中文](VERIFICATION.md) · [README](../README.en.md)

Packaging date: 2026-10-08. This report separates checks executed now from historical hardware validation inherited from existing documentation.

## Checks executed

| Check | Result / scope |
| --- | --- |
| Local version inspection | CachyOS, Linux 7.2.9-1-cachyos, Noctalia 5.2.1; DMI HONOR / FMB-P / M1030; no serial numbers read |
| Enabled configuration | All three IDs and matching path sources found in existing settings; relevant structure inspected without copying personal settings |
| Python / TOML / JSON / Shell syntax | Upload copy passed; no repository Python caches generated |
| OPPO offline regression | All 51 tests passed; mock transport/players, no real earbuds contacted |
| Noctalia plugin lint | All three: 0 errors, 0 warnings |
| Kernel compilation | Both modules compiled in an isolated working directory against matching 7.2.9-1-cachyos headers with LLVM; no new modules installed/loaded |
| Installer previews | All three `--dry-run` modes passed; installation was not performed |
| Sudoers parsing | `visudo -cf` returned 0 and `parsed OK`; sandbox-mapped system sudo.conf ownership produced an environment warning and was not changed |
| Read-only charging status | Installed backend reported `home` / 40/70; thresholds were not changed |
| Public-content scan | No configured secret/device/local-file patterns found; six synthetic negative examples rejected |
| Documentation/file integrity | Local Markdown file links passed; a relative-path SHA-256 manifest is supplied |
| Archive | Per-file comparison and ZIP integrity checks passed; no `.git`, caches, runtime files or build products |

`systemd-analyze verify` was attempted separately, but the execution environment denied required socket operations and the command did not succeed. It is not recorded as passed. The unit was inherited from the installed system; activation, boot and resume behavior need target-machine checks.

## Historical results

Existing OPPO 1.1.2 notes describe Free4 standard edition/firmware 138 verification for noise modes, switches, EQ create/edit/delete, notifications and wear/playback integration. The code and protocol tests are retained. Historical notes do not substitute for a fresh real-earbud test here or establish full compatibility for other models.

HONOR sources use existing hwmon, three-level LED and huawei-wmi/BAT0 interfaces. This work checked source, interface existence, compilation and read-only state without clicking the UI to change backlight or thresholds.

## Not verified

- Desktop Noctalia IPC was unreachable from this execution environment. Loading the new source, UI layout and real click behavior were not confirmed.
- Privileged installation, boot/resume cycles, new module loading and Secure Boot signing were not performed.
- Other machines, distributions, BIOS versions and earbud models were not tested.
- Audible find-earbud behavior was not reverified and remains experimental.
- The privacy scanner is heuristic; review staged content again for new commits.

Packaging did not change installed plugins, desktop layout, current backlight or charging configuration. This report covers pre-upload checks; the public copy is subsequently published to the GitHub repository specified by the user.
