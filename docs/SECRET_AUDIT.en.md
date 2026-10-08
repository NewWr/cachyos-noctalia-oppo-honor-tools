# API key and personal-data audit

[简体中文](SECRET_AUDIT.md) · [Project README](../README.en.md)

Audit date: 2026-10-08. Repository: [NewWr/cachyos-noctalia-oppo-honor-tools](https://github.com/NewWr/cachyos-noctalia-oppo-honor-tools).

Audit baseline: `main` commit `533e4dc`. Inspected all 83 files at that revision, both accessible published commits (`f7297e9`, `533e4dc`), their 81 distinct file objects, and commit author/committer emails. After fetching remote branches and tags, only `main` was present; no other accessible branches or tags were found.

**Result: no API keys, access tokens, private keys or personal contact information found.** No real Bluetooth addresses, personal absolute paths, user settings, device serial numbers or OEM product keys were found. Both published commits use GitHub noreply author/committer emails.

Checks covered private-key markers, GitHub/OpenAI/Anthropic/Slack/cloud credentials, Google API keys, GitLab tokens, JWT/Bearer shapes, credential assignments in source/JSON/YAML, HTTP credentials, email addresses, MACs, firmware/runtime files and image metadata. Credential-related source was also reviewed manually. Reports never print suspected credential values.

The original OPPO image downloader's hardcoded signing credential was removed from the upload copy before publication and is absent from both published commits. Test MACs are fictional. Preserved `osp54`, `dc` and `MagicBook Linux project` identify public code attribution. Product IDs, protocol UUIDs and generic system paths are functional information, not authentication secrets.

This update strengthens the scanner patterns and checks the added documentation. Static/heuristic checks do not guarantee recognition of every encoded or transformed secret, and do not cover inaccessible deleted refs or GitHub-side environment variables. No local private keys or API credentials were read.

Before later commits:

```bash
python3 scripts/check-public-content.py
git diff --cached
```

If a credential is confirmed public later, revoke/rotate it before cleaning files/history. Deleting it only from the latest revision does not remove older disclosures.
