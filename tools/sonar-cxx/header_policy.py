"""Validate declared CIX-owned file headers without touching vendor files."""
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'docs/research/2026-10-04-execution/reviews/cix-header-policy-v1.json'
KERNEL = 'rust/cix-native/adapters/squashfs/kernel/'
OWNED_PREFIXES = (
    'rust/cix-native/adapters/', 'rust/cix-native/bindings/java/src/main/c/',
    'rust/cix-native/bindings/node/src/', 'rust/cix-native/packaging/sdk/tests/',
    'rust/cix-native/packaging/squash/', 'rust/cix-native/tests/',
)


def header_matches(line, license_id):
    """Accept a complete first-line SPDX comment with exactly the expected ID."""
    identifier = re.escape(license_id)
    body = r'SPDX-License-Identifier:[ \t]*' + identifier
    pattern = r'(?://[ \t]*' + body + r'[ \t]*|/\*[ \t]*' + body + r'[ \t]*\*/[ \t]*)'
    return re.fullmatch(pattern, line) is not None


def licensed_paths(policy):
    """Reject duplicate, escaping, vendor or incorrectly classified entries."""
    result = {}
    for key, identifier in (('userspace_mit', 'MIT'), ('kernel_gpl_2_only', 'GPL-2.0-only')):
        for name in policy[key]:
            path = PurePosixPath(name)
            if (path.is_absolute() or '..' in path.parts or str(path) != name
                    or not name.startswith(OWNED_PREFIXES)
                    or any(part in {'vendor', 'third_party', 'upstream'} for part in path.parts)
                    or name in result
                    or name.startswith(KERNEL) != (identifier == 'GPL-2.0-only')):
                raise ValueError('invalid CIX policy path: ' + name)
            result[name] = identifier
    return result


def validate(policy_path=POLICY, root=ROOT):
    """Check the exact manifest; unlisted files remain unclassified."""
    policy = json.loads(Path(policy_path).read_text())
    bad = []
    for name, identifier in licensed_paths(policy).items():
        path = root / name
        if path.is_symlink() or not path.is_file():
            bad.append((name, 'missing direct regular file'))
            continue
        first = path.read_text(encoding='utf-8').splitlines()
        if not first or not header_matches(first[0], identifier):
            bad.append((name, identifier))
    return bad


if __name__ == '__main__':
    violations = validate()
    print(json.dumps({'ok': not violations, 'violations': violations}))
    raise SystemExit(bool(violations))
