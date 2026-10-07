#!/usr/bin/env python3
"""Focused contract for public PAQ identities in the exported provenance."""

from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
NATIVE_ROOT = HERE.parents[1]
PROVENANCE = NATIVE_ROOT / "packaging/notices/provider-provenance-v3.json"
SPEC = importlib.util.spec_from_file_location("export_source", HERE / "export_source.py")
assert SPEC is not None and SPEC.loader is not None
EXPORT_SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT_SOURCE)


class ProviderProvenanceSanitizerTest(unittest.TestCase):
    def test_paq_canonical_identity_survives_without_private_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            exported_root = Path(temporary)
            destination = exported_root / "rust/cix-native/packaging/notices"
            destination.mkdir(parents=True)
            shutil.copyfile(PROVENANCE, destination / PROVENANCE.name)

            digests: dict[str, str] = {}
            EXPORT_SOURCE.sanitize_exported_provider_notice_manifest(exported_root, digests)
            EXPORT_SOURCE.reject_private_references(exported_root)

            document = json.loads((destination / PROVENANCE.name).read_text(encoding="utf-8"))
            identities = document["source_identities"]
            self.assertEqual(
                identities["paq_v215"]["archive_sha256"],
                "e3a86a08961f90bab73b01cb3db27327471a701b6ac2dde0c972e5b6f78c0737",
            )
            self.assertEqual(
                identities["paq_v216"]["commit"],
                "bf7b658fdcfc045a892920d01e830e6c6a790c21",
            )
            providers = document["providers"]
            self.assertEqual(
                providers["CIX_RUNTIME_PAQ_JOINT_DISCOUNT_BRIDGE"]["source"]["source_identity"],
                "paq_v215",
            )
            self.assertEqual(
                providers["CIX_RUNTIME_PAQ_STORE_STATE_BRIDGE"]["source"]["source_identity"],
                "paq_v216",
            )
            for provider in providers.values():
                source = provider.get("source") if isinstance(provider, dict) else None
                if isinstance(source, dict):
                    self.assertNotIn("local_root", source)
                    self.assertNotIn("receipt", source)


if __name__ == "__main__":
    unittest.main()
