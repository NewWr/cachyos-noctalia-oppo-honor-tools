#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
export PYTHONDONTWRITEBYTECODE=1
python3 "$ROOT/scripts/check-public-content.py"
python3 - "$ROOT" <<'PY'
import ast
import json
import sys
import tomllib
from pathlib import Path
root = Path(sys.argv[1])
for path in root.rglob('*.py'):
    ast.parse(path.read_text(), filename=str(path.relative_to(root)))
for path in root.rglob('*.toml'):
    tomllib.loads(path.read_text())
for path in root.rglob('*.json'):
    json.loads(path.read_text())
print('PASS: Python, TOML and JSON syntax')
PY
for script in "$ROOT"/scripts/*.sh "$ROOT"/backends/honor-battery/bin/*; do
    bash -n "$script"
done
sh -n "$ROOT/backends/honor-battery/system-sleep/honor-battery-profile"
python3 -m unittest discover -s "$ROOT/plugins/oppo-pods/tests" -v
if command -v noctalia >/dev/null; then
    for plugin in "$ROOT"/plugins/*; do noctalia plugins lint "$plugin"; done
else
    echo 'SKIP: Noctalia lint (Noctalia not installed).'
fi
