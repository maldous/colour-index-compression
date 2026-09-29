#!/usr/bin/env python3
"""Remove only verified redundant decoder outputs and leave an audit receipt."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/home/user/src/colour-index-compression')
RESULT = ROOT / 'results/leaderboard/paq-store-state-qualified/complete.json'
RECEIPT = ROOT / 'results/leaderboard/paq-store-state-qualified/restored-copy-deletion-receipt.json'


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def write_receipt(receipt: dict) -> None:
    temporary = RECEIPT.with_suffix('.json.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(RECEIPT)


def main() -> None:
    report = json.loads(RESULT.read_text(encoding='utf-8'))
    if not report.get('complete') or not report.get('all_originals_restored'):
        raise ValueError('store-state result is not a complete restoration proof')
    targets = []
    for row in report['rows']:
        name = row['file']
        restored = ROOT / 'results/leaderboard/paq-store-state-qualified' / name / 'restored.bin'
        canonical = ROOT / 'benchmark-work/silesia' / name
        if not restored.is_file() or restored.is_symlink() or not canonical.is_file():
            raise ValueError(f'unsafe or missing target for {name}')
        expected = row['restored_sha256']
        restored_hash = sha256(restored)
        source_hash = sha256(canonical)
        if restored_hash != expected or source_hash != expected:
            raise ValueError(f'hash mismatch for {name}')
        if restored.stat().st_size != canonical.stat().st_size or restored.stat().st_size != row['original']:
            raise ValueError(f'length mismatch for {name}')
        targets.append({
            'member': name,
            'path': str(restored),
            'bytes': restored.stat().st_size,
            'sha256': restored_hash,
            'recovery_source': str(canonical),
            'recovery_source_sha256': source_hash,
            'archive_path_retained': row['archive_path'],
            'archive_sha256_retained': row['archive_sha256'],
            'verified_before_deletion': True,
        })
    receipt = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'purpose': 'Remove redundant restored original-byte copies after SHA-256 comparison with canonical Silesia inputs.',
        'result_proof_retained': str(RESULT),
        'targets': targets,
        'total_bytes': sum(target['bytes'] for target in targets),
        'removal_complete': False,
    }
    write_receipt(receipt)
    for target in targets:
        path = Path(target['path'])
        path.unlink()
        if path.exists():
            raise ValueError(f'failed to remove {path}')
    receipt['removed_at'] = datetime.now(timezone.utc).isoformat()
    receipt['removal_complete'] = True
    write_receipt(receipt)
    print(json.dumps({'removed_targets': len(targets), 'removed_bytes': receipt['total_bytes'], 'receipt': str(RECEIPT)}))


if __name__ == '__main__':
    main()
