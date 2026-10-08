# Upload to one GitHub repository

[简体中文](GITHUB_UPLOAD.md) · [README](../README.en.md)

Target repository: [NewWr/cachyos-noctalia-oppo-honor-tools](https://github.com/NewWr/cachyos-noctalia-oppo-honor-tools). This folder is the repository root, with all three plugins under `plugins/`. Do not upload the computer's complete Noctalia configuration directory.

## Option 1: Git CLI

1. Create an empty GitHub repository. Choose Public for sharing or Private for initial review. Do not auto-generate README/license/ignore files; this package already contains them.
2. Enter this folder locally, run checks and initialize fresh history:

```bash
bash scripts/check.sh
git init -b main
# Choose the identity you want to publish; a GitHub noreply email is an option.
git config --local user.name "YOUR_PUBLIC_NAME"
git config --local user.email "YOUR_GITHUB_NOREPLY_EMAIL"
git add .
git status --short
git diff --cached --stat
git diff --cached
```

3. Review staged content, ensuring it contains only package sources, documentation and licenses. Replace `YOUR_ACCOUNT`; never put a token in the remote URL:

```bash
git commit -m "Add OPPO Pods and HONOR Noctalia tools"
git remote add origin https://github.com/NewWr/cachyos-noctalia-oppo-honor-tools.git
git push -u origin main
```

Authenticate through a credential manager or existing GitHub CLI/SSH setup. No key file belongs in this repository. Commit author names/emails become public history, so choose your intended public identity first. Start with this clean package instead of importing old working-directory history, logs or `.git/config`.

## Option 2: GitHub browser upload

Use Upload files and put the **contents of this folder** at the repository root. Preserve the three plugin directories, `backends/`, `scripts/`, `docs/`, licenses and hidden `.gitignore` / `.gitattributes`. A ZIP is useful for extraction or a Release attachment; uploading only the ZIP does not produce a browsable source repository.

If hidden files are omitted by the file picker, create them manually. Run the scan before browser upload too: the browser does not automatically filter dragged personal files using the local `.gitignore`.

## Repository landing page and optional release

- `README.md` is Chinese; `README.en.md` is English. Each plugin has both languages too.
- This collection has mixed licenses: MIT UI/scripts and GPL-2.0-only kernel modules. Do not replace their notices with an auto-generated blanket license.
- Optional description: `OPPO Pods and HONOR FMB-P hardware / battery tools for Noctalia`.
- Optional topics: `noctalia`, `linux`, `honor`, `oppo`, `bluetooth`, `battery`.
- Check the file tree and documentation links after uploading. The same clean ZIP can be attached to a Release.

## Subsequent changes

Run `bash scripts/check.sh` and review staged differences before each commit. `.gitignore` does not exclude files already tracked. If credentials were committed, revoke/rotate them and clean the history; deleting the current file does not remove its contents from older commits.

This repository uses the address above. For later updates, commit and push from the existing clone instead of reinitializing it or adding the same remote again.
