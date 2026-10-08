#!/usr/bin/env python3
"""Offline release check. Report locations/types only, never suspected values."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'GitHub credential': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})\b'),
    'cloud access key': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'service credential': re.compile(r'\b(?:sk-[A-Za-z0-9_-]{24,}|xox[baprs]-[A-Za-z0-9-]{20,})\b'),
    'Google API key': re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'),
    'GitLab credential': re.compile(r'\bglpat-[0-9A-Za-z_-]{20,}\b'),
    'JWT-like credential': re.compile(r'\beyJ[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}\b'),
    'Bearer credential': re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_./+-]{20,}'),
    'embedded HTTP credentials': re.compile(r'https?://[^\s/]+:[^\s/]+@'),
    'personal absolute path': re.compile(r'(?:/home/|/Users/)[A-Za-z0-9_.-]+/'),
    'Windows OEM key': re.compile(r'\b[A-Z0-9]{5}(?:-[A-Z0-9]{5}){4}\b'),
    'literal credential assignment': re.compile(r'''(?i)\b(?:[a-z][a-z0-9]*[_-])*(?:secret(?:_[a-z0-9]+)*|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)\s*["']?\s*[:=]\s*["'][^"'\n]{8,}["']'''),
}
MAC = re.compile(r'\b[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}\b')
TEST_ADDRESSES = {'00:00:00:00:00:00', 'AA:BB:CC:DD:EE:FF', 'AA:BB:CC:DD:EE:00', '02:00:00:00:00:0A'}
BLOCKED_DIRS = {'.git', '.ssh', '.aws', '.gnupg', '__pycache__', '.venv', 'acpi-dumps', 'work', 'dist'}
BLOCKED_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.pyc', '.aml', '.dsl', '.dat', '.ko', '.o', '.log', '.zip', '.sock', '.lock'}
BLOCKED_NAMES = {'settings.toml', 'credentials.json', 'secrets.json', 'oppo_pods_state.json', 'oppo_pods_channel.txt', 'profile'}
ALLOWED_BINARY = {'.webp'}


def scan(root):
    findings = []
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        # Repository metadata is not part of an upload diff. A nested .git is rejected.
        if rel.parts[0] == '.git':
            continue
        if path.is_symlink():
            findings.append((str(rel), 0, 'symlink'))
            continue
        if not path.is_file():
            continue
        if set(rel.parts) & BLOCKED_DIRS or path.suffix.lower() in BLOCKED_SUFFIXES or path.name in BLOCKED_NAMES or path.name.startswith('.env') or '.bak' in path.name:
            findings.append((str(rel), 0, 'excluded local/generated file'))
            continue
        data = path.read_bytes()
        try:
            source = data.decode('utf-8')
        except UnicodeDecodeError:
            if path.suffix.lower() not in ALLOWED_BINARY:
                findings.append((str(rel), 0, 'unreviewed binary'))
                continue
            # Reject metadata chunks; scan printable byte sequences as text too.
            if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
                findings.append((str(rel), 0, 'invalid image type'))
                continue
            offset = 12
            while offset + 8 <= len(data):
                chunk = data[offset:offset + 4]
                length = int.from_bytes(data[offset + 4:offset + 8], 'little')
                if chunk in {b'EXIF', b'XMP ', b'ICCP'}:
                    findings.append((str(rel), 0, 'image metadata requires review'))
                offset += 8 + length + length % 2
            source = '\n'.join(x.decode('ascii') for x in re.findall(rb'[\x20-\x7e]{8,}', data))
        for line_no, line in enumerate(source.splitlines(), 1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append((str(rel), line_no, label))
            for match in MAC.finditer(line):
                allowed = ('tests' in rel.parts or rel.as_posix() == 'scripts/check-public-content.py') and match.group().upper() in TEST_ADDRESSES
                if not allowed:
                    findings.append((str(rel), line_no, 'device address'))
    return findings


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
    findings = scan(root)
    for path, line, label in findings:
        print(f'{path}:{line}: {label}')
    if findings:
        print(f'FAIL: {len(findings)} potential disclosure(s); inspect locally before upload.')
        return 1
    print('PASS: no configured credential/device/local-file patterns found. Heuristic scan, not a guarantee.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
