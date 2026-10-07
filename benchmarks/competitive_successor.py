"""Require the scored parent to match the encoder's actual parent policy."""
import argparse
import json
from pathlib import Path

from benchmarks import competitive_certified


def validate_parent(profile, path):
    report = json.loads((Path(path) / 'complete.json').read_text())
    if not report.get('complete') or report.get('members') != 12:
        raise ValueError('incomplete successor parent')
    if report.get('policy', {}).get('name') != profile.parent.NAME:
        raise ValueError('scored parent does not match the encoder parent')
    return report


def main(profile):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--parent', required=True)
    args, _ = parser.parse_known_args()
    validate_parent(profile, args.parent)
    competitive_certified.main(profile)
