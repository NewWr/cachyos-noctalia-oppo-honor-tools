# Public contents and local privacy

[简体中文](PRIVACY.md) · [README](../README.en.md)

## Changes applied to this package

- Copy only the three enabled plugin sources and explicit backend dependencies, not user configuration directories.
- Remove the hardcoded signing credential and network code from the original OPPO image downloader; retain control protocols, icons and local-cache reads.
- Replace a real Bluetooth address in tests with a fictional locally administered sample. Protocol fixtures contain only handshake/features and anonymous EQ data.
- Exclude pairing data, private keys, tokens, personal emails, serial numbers, playback logs, plugin settings, runtime sockets/locks, backups and build products.
- Exclude `.aml`, `.dsl`, `.dat` and raw ACPI dumps, which can include Windows OEM product keys.
- Preserve public authorship (`osp54`, namespace `dc`), model IDs and fixed protocol UUIDs. These are not machine authentication secrets.
- Include no previous Git history that might inherit local information from older commits.

## Data generated during use

| Tool | Local location | Possible data |
| --- | --- | --- |
| OPPO | `oppo_pods_*` files/socket under `$XDG_RUNTIME_DIR`; original fallback is `/tmp` | Bluetooth address, state and saved-device list |
| OPPO | `$XDG_CACHE_HOME/noctalia/oppo-pods` | User-supplied device artwork; upload version does not download it |
| HONOR Battery | `/var/lib/honor-battery-profile/profile` | Saved preset |
| Noctalia | User settings/config files | Custom addresses, paths and other plugins' credentials |

None of these locations belong in the repository. Check device addresses, account names and unrelated application data separately before sharing logs, screenshots or complete configurations.

## Scan and limitations

```bash
python3 scripts/check-public-content.py
```

The scanner checks common private-key markers, GitHub/cloud credentials, literal credential assignments, HTTP credentials, personal paths, OEM-key shapes, non-fictional MAC addresses, excluded runtime/firmware files and unreviewed binaries. Retained WebP icons are checked for metadata chunks and printable content. Reports identify locations/categories without echoing suspicious values.

This is an offline heuristic check, not a guarantee against every encoded or transformed secret. Copied source was also inspected manually; new files still require review. `.gitignore` helps prevent mistakes but cannot remove already published history.

The battery sudoers template contains no username. It grants a group only three exact commands. Actual group membership is local system state; do not export complete sudoers files, user lists or security configuration into the repository.
