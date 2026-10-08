# Licenses, origins and attribution

[简体中文](THIRD_PARTY.md)

| Component | Origin/declaration | License treatment |
| --- | --- | --- |
| OPPO Pods | Enabled local `osp54/oppo-pods` 1.1.2; `Copyright (c) 2026 osp54` | Preserve full `plugins/oppo-pods/LICENSE`, author and ID; MIT |
| HONOR UI | Enabled local `dc/honor-fan` 1.1.4 and `dc/honor-battery-profile` 1.0.0; manifests declare MIT | Preserve namespace/author and add separate MIT texts |
| HONOR battery backend | Locally installed helper/service/config/resume hook | Distributed with the local tools under MIT; no personal authorization files copied |
| HONOR hwmon / kbdlight | Installed source versions 1.0 / 1.1; `SPDX-License-Identifier: GPL-2.0`, `MODULE_AUTHOR("MagicBook Linux project")` | Preserve headers/authorship; GPL-2.0-only with full text in `LICENSES/GPL-2.0-only.txt` |
| Packaging scripts, scanner and docs | Added during this collection work | MIT, explicitly distinguished from kernel-module GPL scope |

Bundled original plugin icons/illustrations are retained with the MIT plugin. Brand names identify compatibility targets without implying trademark authorization or official certification. No manufacturer download caches are packaged.

References inherited from existing code/docs; this packaging work did not fetch or verify new website contents:

- [Noctalia community OPPO plugin](https://noctalia.dev/plugins/community/oppo-pods)
- [OPPO Android reference](https://github.com/1812z/OppoPods)
- [OPPO protocol reference](https://github.com/Zhaoyi-ya/OppoPodsManager)
- [HONOR MagicBook Linux project](https://github.com/drphilth/honor-magicbook-pro-14-ubuntu)

Packaging changes: remove remote-image signing credential/downloader, anonymize test addresses, exclude undeclared legacy widget/preview/runtime data, add guides/install/check tooling and a non-personal permission template. The battery helper gains an FMB-P write guard, exact argument count, noninteractive sudo and a lock in the root-owned state directory. Installed runtime files were left intact; changes apply to the upload copy only.
