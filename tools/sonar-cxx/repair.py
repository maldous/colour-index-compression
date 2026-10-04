#!/usr/bin/env python3
"""Pinned CXX/Cppcheck analysis of the current CIX native source.

prepare is read-only with respect to product sources. run requires the
authenticated benchmark stop/idle state and an exclusive WaveScheduler lease.
This is SonarOpenCommunity CXX, not SonarSource's licensed CFamily analyzer.
"""
from __future__ import annotations

import argparse
import ast
import collections
import dataclasses
import fcntl
import hashlib
import importlib.util
from itertools import chain
import json
import os
from pathlib import Path
import re
import resource
import selectors
import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HYGIENE = ROOT / "docs/research/2026-10-04-automatic-specialised-models/hygiene"
SOURCE = ROOT
TOOLS = ROOT.parent / "cix-sonar-cxx-tools"
SUMMARY = HYGIENE.parent / "qualification/silesia-confirmation-v1/summary.json"
STOP = SUMMARY.parent / "stop-20261004-user/stop.json"
STOP_COMMIT = "e9731f4bd"
STOP_PLAN_SHA256 = "6181ed5066495a12bc6fa09a41f5b14cb2442b4aaae0b16e0ddf015356432eaa"
STOP_SHA256 = "ed3c2aaf8ef104e2305c80defffcab8607c608525126b018ed9c85725feeed54"
STOP_VERIFIED = {
    "confirm-fast-dickens", "confirm-default-dickens", "confirm-best-dickens",
    "confirm-fast-mozilla", "confirm-default-mozilla",
}
STOP_INTERRUPTED = "confirm-best-mozilla"
SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
PAQ_NAMES = ("v215", "v216", "joint-discount", "store-state")
SCOPES = {
    "cix-native-core": ["rust/cix-native/include", "rust/cix-native/src", "rust/cix-native/codecs",
                        "rust/cix-native/examples", "rust/cix-native/experiments"],
    "cix-native-adapters": ["rust/cix-native/adapters", "rust/cix-native/bindings",
                            "rust/cix-native/packaging", "rust/cix-native/tests"],
    "native-vendor": ["rust/cix-native/vendor"],
    **{f"paq-{name}": [f"benchmark-work/references/{path}"]
       for name, path in {
           "v215": "paq8px-v215/paq8px-215",
           "v216": "paq8px-v216/paq8px-216",
           "joint-discount": "paq8px-cix-joint-discount/source",
           "store-state": "paq8px-cix-store-state/source",
       }.items()},
}
# These are completed CMake target receipts, not guessed settings.  A receipt
# contributes a command only while the current source still hashes identically
# to the source copy compiled by that job.
CMAKE_RECEIPTS = (
    ("rocksdb", "benchmark-work/native-rc-check-v1/rocksdb-host-v2/adapter/CMakeFiles/cix_rocksdb_compression_manager.dir",
     "benchmark-work/native-rc-check-v1/rocksdb-adapter-source-v2", "rust/cix-native/adapters/rocksdb",
     ("cix_compression_manager.cc",), "CXX"),
    ("sevenzip", "benchmark-work/native-rc-check-v1/codec-hosts-v7/sevenzip/CMakeFiles/cix_7zip_experimental_module.dir",
     "benchmark-work/native-rc-check-v1/codec-hosts-source-v7/adapters/sevenzip", "rust/cix-native/adapters/sevenzip",
     ("cix_7zip_module.cpp", "cix_7zip_coder.cpp"), "CXX"),
    ("wiredtiger", "benchmark-work/native-rc-check-v1/codec-hosts-v7/wiredtiger/CMakeFiles/cix_wt_compressor.dir",
     "benchmark-work/native-rc-check-v1/codec-hosts-source-v7/adapters/wiredtiger", "rust/cix-native/adapters/wiredtiger",
     ("src/cix_wt_compressor.c",), "C"),
    ("hdf5", "benchmark-work/native-rc-check-v1/host-adapters-v6/hdf5/CMakeFiles/H5Zcix.dir",
     "benchmark-work/native-rc-check-v1/host-adapters-source-v6/hdf5", "rust/cix-native/adapters/hdf5",
     ("src/cix_hdf5_filter.c",), "C"),
    ("blosc2", "benchmark-work/native-rc-check-v1/codec-hosts-v3/blosc2/CMakeFiles/cix_blosc2_adapter.dir",
     "benchmark-work/native-rc-check-v1/codec-hosts-source-v3/adapters/blosc2", "rust/cix-native/adapters/blosc2",
     ("src/cix_blosc2_adapter.c",), "C"),
    ("blosc2-contract", "benchmark-work/native-rc-check-v1/codec-hosts-v3/blosc2/CMakeFiles/cix_blosc2_contract.dir",
     "benchmark-work/native-rc-check-v1/codec-hosts-source-v3/adapters/blosc2", "rust/cix-native/adapters/blosc2",
     ("tests/blosc2_cix_contract.c",), "C"),
    ("gio", "benchmark-work/native-rc-check-v1/host-adapters-v4/gio/CMakeFiles/cix-gconverter.dir",
     "benchmark-work/native-rc-check-v1/host-adapters-source-v4/gio", "rust/cix-native/adapters/gio",
     ("cix-gconverter.c",), "C"),
    ("gio-contract", "benchmark-work/native-rc-check-v1/host-adapters-v4/gio/CMakeFiles/cix-gconverter-contract.dir",
     "benchmark-work/native-rc-check-v1/host-adapters-source-v4/gio", "rust/cix-native/adapters/gio",
     ("contract.c",), "C"),
    ("storage-example", "benchmark-work/native-rc-check-v1/stream-storage-hosts-v1/storage-build/CMakeFiles/cix-backup.dir",
     "benchmark-work/native-rc-check-v1/stream-storage-source-v1/storage-examples", "rust/cix-native/adapters/storage-examples",
     ("cix_backup.cpp",), "CXX"),
    ("gstreamer", "benchmark-work/native-rc-check-v1/gstreamer-host-v2/gst-build/CMakeFiles/gstcixstream.dir",
     "benchmark-work/native-rc-check-v1/gstreamer-source-v2", "rust/cix-native/adapters/gstreamer",
     ("src/gstcixstream.c",), "C"),
    ("gstreamer-contract", "benchmark-work/native-rc-check-v1/gstreamer-host-v2/gst-build/CMakeFiles/cix-gstream-contract.dir",
     "benchmark-work/native-rc-check-v1/gstreamer-source-v2", "rust/cix-native/adapters/gstreamer",
     ("tests/contract.c",), "C"),
    ("hdf5-contract", "benchmark-work/native-rc-check-v1/host-adapters-v6/hdf5/CMakeFiles/cix_hdf5_filter_contract.dir",
     "benchmark-work/native-rc-check-v1/host-adapters-source-v6/hdf5", "rust/cix-native/adapters/hdf5",
     ("tests/filter_contract.c",), "C"),
    ("rocksdb-contract", "benchmark-work/native-rc-check-v1/rocksdb-host-v2/adapter/CMakeFiles/cix_rocksdb_contract.dir",
     "benchmark-work/native-rc-check-v1/rocksdb-adapter-source-v2", "rust/cix-native/adapters/rocksdb",
     ("contract_test.cc",), "CXX"),
    ("wiredtiger-contract", "benchmark-work/native-rc-check-v1/codec-hosts-v7/wiredtiger/CMakeFiles/cix_wt_contract.dir",
     "benchmark-work/native-rc-check-v1/codec-hosts-source-v7/adapters/wiredtiger", "rust/cix-native/adapters/wiredtiger",
     ("tests/wiredtiger_contract.c",), "C"),
    ("node", "benchmark-work/native-rc-check-v1/node-binding-language-consumers-v2/CMakeFiles/cix_node.dir",
     "benchmark-work/native-rc-check-v1/execution-language-consumers-v2/bindings/node", "rust/cix-native/bindings/node",
     ("src/cix_node.c",), "C"),
    ("java", "benchmark-work/native-rc-check-v1/java-binding-language-consumers-v2/CMakeFiles/cix_jni.dir",
     "benchmark-work/native-rc-check-v1/execution-language-consumers-v2/bindings/java", "rust/cix-native/bindings/java",
     ("src/main/c/cix_jni.c",), "C"),
    ("paq-v215-bridge", "benchmark-work/native-rc-check-v1/paq-v215-qualification-v2-output/CMakeFiles/cix_paq_v215_bridge.dir",
     "benchmark-work/native-rc-check-v1/paq-v215-qualification-v2-bridge", "rust/cix-native/codecs/paq/v215",
     ("paq_v215_bridge.cpp",), "CXX"),
    ("paq-v216-bridge", "benchmark-work/native-rc-check-v1/paq-v216-qualification-v1-output/CMakeFiles/cix_paq_v216_bridge.dir",
     "benchmark-work/native-rc-check-v1/paq-v216-qualification-v1-bridge", "rust/cix-native/codecs/paq/v216",
     ("paq_v216_bridge.cpp",), "CXX"),
    ("paq-joint-discount-bridge", "benchmark-work/native-rc-check-v1/paq-joint-discount-qualification-v1-output/CMakeFiles/cix_paq_joint_discount_bridge.dir",
     "benchmark-work/native-rc-check-v1/paq-joint-discount-qualification-v1-bridge", "rust/cix-native/codecs/paq/joint_discount",
     ("paq_joint_discount_bridge.cpp",), "CXX"),
    ("paq-store-state-bridge", "benchmark-work/native-rc-check-v1/paq-store-state-qualification-v1-output/CMakeFiles/cix_paq_store_state_bridge.dir",
     "benchmark-work/native-rc-check-v1/paq-store-state-qualification-v1-bridge", "rust/cix-native/codecs/paq/store_state",
     ("paq_store_state_bridge.cpp",), "CXX"),
    ("sevenzip-module", "benchmark-work/native-rc-check-v1/consumer-hosts-v3/sevenzip-adapter/CMakeFiles/cix_7zip_experimental_module.dir",
     "benchmark-work/native-rc-check-v1/consumer-hosts-source-v3/adapters/sevenzip", "rust/cix-native/adapters/sevenzip",
     ("cix_7zip_module.cpp", "cix_7zip_coder.cpp"), "CXX"),
    ("sevenzip-contract", "benchmark-work/native-rc-check-v1/consumer-hosts-v3/sevenzip-adapter/CMakeFiles/cix_7zip_contract.dir",
     "benchmark-work/native-rc-check-v1/consumer-hosts-source-v3/adapters/sevenzip", "rust/cix-native/adapters/sevenzip",
     ("cix_7zip_contract.cpp",), "CXX"),
)
# These are successful, retained direct compiler invocations.  They are kept
# separate from CMake receipts because the job logged the actual argv rather
# than generating flags.make.  As with CMake, the source path is re-rooted
# only after an exact snapshot-to-current hash comparison.
DIRECT_COMMAND_RECEIPTS = (
    ("libarchive-contract",
     "docs/research/2026-10-04-execution/jobs/host-adapters-v3/raw/cix-rel01-execution-host-adapters-v3.stdout.log",
     "libarchive", "benchmark-work/native-rc-check-v1/host-adapters-source-v3/libarchive",
     "rust/cix-native/adapters/libarchive", "libarchive_program_filter.c", "C"),
    ("hdf5-netcdf-contract",
     "docs/research/2026-10-04-execution/jobs/host-adapters-v6/raw/cix-rel01-execution-host-adapters-v6.stdout.log",
     "hdf5", "benchmark-work/native-rc-check-v1/host-adapters-source-v6/hdf5",
     "rust/cix-native/adapters/hdf5", "examples/netcdf_filter.c", "C"),
    ("squash-package-contract",
     "docs/research/2026-10-04-execution/jobs/codec-hosts-v8/raw/cix-rel01-execution-codec-hosts-v8.stdout.log",
     "squash", "benchmark-work/native-rc-check-v1/codec-hosts-source-v8/packaging/squash",
     "rust/cix-native/packaging/squash", "contract.c", "C"),
)
DISTRIBUTION_COMPILER_RECEIPT = {
    "job": "docs/research/2026-10-04-execution/jobs/distribution-engineering-v4",
    "database": "compiler-invocations.jsonl",
    "source": "benchmark-work/native-rc-check-v1/distribution-engineering-v4/source-output/cix-0.1.0/rust/cix-native",
    "current": "rust/cix-native",
}
FILESYSTEM_COMMANDS_RECEIPT = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/filesystem-commands-v1.json"
BRIDGE_PORTABILITY_RECEIPT = ROOT / "benchmark-work/native-rc-check-v1/bridge-portability-v1/receipt.json"
SPATIAL_PORTABILITY_RECEIPT = ROOT / "benchmark-work/native-rc-check-v1/bridge-portability-v2/receipt.json"
CAPTURE_V1 = ROOT / "benchmark-work/native-rc-check-v1/compiler-capture-v1"
HOST_V3 = ROOT / "docs/research/2026-10-04-execution/jobs/compiler-capture-host-v3"
HOST_V3_RESOLUTION = ROOT / "docs/research/2026-10-04-execution/sonar-preparation/compiler-capture-host-v3-source-resolution.json"
C_API_CAPTURE_RECEIPT = ROOT / "docs/research/2026-10-04-execution/jobs/compiler-c-api-capture-v1/receipt.json"
# The pinned server image carries these built-in extensions in its immutable
# /opt/sonarqube/lib/extensions layer.  The CXX registration probe replaces
# that layer with an empty read-only bind mount, then mounts only the separately
# checksummed CXX plugin into the ordinary extensions/plugins volume.  This
# avoids deploying unrelated language plugins into the bounded probe runtime.
IMAGE_CORE_EXTENSION_INVENTORY = (
    ("sonar-cayc-plugin-2.6.0.3665.jar", 522422, None),
    ("sonar-csharp-plugin-10.33.0.1635.jar", 5758005, "csharp"),
    ("sonar-flex-plugin-2.18.0.6281.jar", 1348071, "flex"),
    ("sonar-go-plugin-1.43.0.7704.jar", 19422477, "go"),
    ("sonar-html-plugin-3.31.0.8334.jar", 1684132, "html"),
    ("sonar-iac-plugin-2.16.0.22905.jar", 21878926, "iac"),
    ("sonar-jacoco-plugin-1.6.0.5741.jar", 38975, None),
    ("sonar-java-plugin-8.41.0.47177.jar", 20626853, "java"),
    ("sonar-java-symbolic-execution-plugin-8.16.4.1912.jar", 1228080, "java"),
    ("sonar-javascript-plugin-13.8.0.44569-multi.jar", 125730006, "javascript"),
    ("sonar-kotlin-plugin-3.9.0.9809.jar", 54629576, "kotlin"),
    ("sonar-php-plugin-3.60.0.16641.jar", 2943650, "php"),
    ("sonar-python-plugin-5.31.0.36502.jar", 19671347, "python"),
    ("sonar-ruby-plugin-1.25.0.2597.jar", 15300331, "ruby"),
    ("sonar-rust-plugin-1.8.1.3395.jar", 8795777, "rust"),
    ("sonar-scala-plugin-1.24.0.2554.jar", 16044068, "scala"),
    ("sonar-text-plugin-2.49.0.12346.jar", 6960291, "text"),
    ("sonar-vbnet-plugin-10.33.0.1635.jar", 4880051, "vbnet"),
    ("sonar-xml-plugin-2.19.0.8138.jar", 2713112, "xml"),
)
# The probe is deliberately much smaller than a product analysis.  Its
# reservation includes the physical blocks already occupied by retained native
# job material, all probe tmpfs ceilings, and a bounded allowance for its new
# evidence.  Images, packaged tools and immutable source are not temporary
# work space and are therefore recorded separately, not charged here.
TEMPORARY_BUDGET_BYTES = 4_000_000_000
RETAINED_NATIVE_WORK = ROOT / "benchmark-work/native-rc-check-v1"
PROBE_SERVER_DATA_BYTES = 256 * 1024**2
PROBE_SERVER_LOG_BYTES = 16 * 1024**2
PROBE_SERVER_TEMP_BYTES = 64 * 1024**2
PROBE_SERVER_EXTENSIONS_BYTES = 16 * 1024**2
PROBE_SERVER_TMP_BYTES = 16 * 1024**2
SERVER_ENTRYPOINT = ("/opt/sonarqube/docker/entrypoint.sh",)
SERVER_IMAGE_VOLUMES = (
    "/opt/sonarqube/data",
    "/opt/sonarqube/extensions",
    "/opt/sonarqube/logs",
    "/opt/sonarqube/temp",
)
PROBE_SCANNER_TEMP_BYTES = 128 * 1024**2
SCANNER_LOG_BYTES = 8 * 1024**2
SCANNER_REPORT_TASK_BYTES = 64 * 1024
# The scanner itself never writes this host-bound file.  The bounded log sink
# and the shell's post-scan, size-checked metadata copy share it.
SCANNER_EVIDENCE_BYTES = SCANNER_LOG_BYTES + SCANNER_REPORT_TASK_BYTES + 4096
PROBE_EVIDENCE_RESERVE_BYTES = 96 * 1024**2
EVIDENCE_ALLOCATION_BYTES = 4096
FAILURE_RECEIPT_RESERVE_BYTES = 256 * 1024
FAILURE_LOG_BYTES = 64 * 1024
TERMINAL_RECEIPT_RESERVE_BYTES = 64 * 1024
CPPHECK_PROJECTED_TU_BYTES = 2 * 1024**2
CPPHECK_KERNEL_PROJECTED_TU_BYTES = 8 * 1024**2
# The decompressor exceeded the default cap in adapter-context-probe-v3.
# Give it and the companion Kbuild registration unit a bounded larger check;
# every other projection remains at 2 MiB.
CPPHECK_PROJECTED_RELATIVES = frozenset({
    "rust/cix-native/adapters/gio/cix-gconverter.c",
    "rust/cix-native/adapters/gio/contract.c",
    "rust/cix-native/adapters/sevenzip/cix_7zip_module.cpp",
    "rust/cix-native/adapters/sevenzip/cix_7zip_coder.cpp",
    "rust/cix-native/adapters/sevenzip/cix_7zip_contract.cpp",
})
# The adapter-context-v2 probe identifies only these additional raw commands.
# They are projected through their retained compilers; no Cppcheck macro is
# injected and no general adapter class is enabled.
CPPHECK_PROBE_V2_CONFIRMED_RELATIVES = frozenset({
    "rust/cix-native/adapters/blosc2/tests/blosc2_cix_contract.c",
    "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c",
    "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c",
})
CPPHECK_NEW_ANALYSIS_KERNEL_RELATIVES = frozenset({
    "rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c",
    "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c",
    "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_fs_register.c",
})
ANALYSIS_COVERAGE_CPPHECK_IDS = frozenset({
    "unknownMacro",
    "preprocessorErrorDirective",
})
PACKAGES = {
    "sonar-cxx-plugin-2.3.0.1496.jar": (
        "https://github.com/SonarOpenCommunity/sonar-cxx/releases/download/cxx-2.3.0/sonar-cxx-plugin-2.3.0.1496.jar",
        "95dd162a04d954a63713dd7cc6b4e14f1d361de6645dffdd8755069a12ea0197"),
    "cppcheck.deb": (
        "https://archive.ubuntu.com/ubuntu/pool/universe/c/cppcheck/cppcheck_2.13.0-2ubuntu3_amd64.deb",
        "c84251e17148b6b4ff3698bb71ceec0f445896d97888bedad8bba471c00aeadf"),
    "libtinyxml2.deb": (
        "https://archive.ubuntu.com/ubuntu/pool/universe/t/tinyxml2/libtinyxml2-10_10.0.0+dfsg-2_amd64.deb",
        "7444576728d0886cc58cee1749dc2ab5a680c1756f0a8b49c973fa0cfb180973"),
}
CPPHECK_RUNTIME_VERSION = "cppcheck-runtime-v2"
CPPHECK_BINARY_SHA256 = "2e2db3b85cc9d1795fee4fd0c90e04898bd6ad583c528cb3f381779b928cb93e"
CPPHECK_RUNTIME_DSOS = (
    ("libstdc++.so.6", "/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33",
     "1fd75fe70354a416d75aef22bcae68c47bd25d20e2d0568c30b1a9838cf62f11"),
    ("libm.so.6", "/usr/lib/x86_64-linux-gnu/libm.so.6",
     "fce00b6f25f459cf4ae0b7fae4257909a1a8a86f9149e7c029a5d617baf1ccd0"),
    ("libgcc_s.so.1", "/usr/lib/x86_64-linux-gnu/libgcc_s.so.1",
     "d93224d2b0dab4247598be683adca02f5cf00586f99c187579cd7e92058fb7cb"),
    ("libc.so.6", "/usr/lib/x86_64-linux-gnu/libc.so.6",
     "3a15d66867d83762c7f2f1e37359cb8f6c5743edb369c65285cb0b1c4f7498bf"),
    ("libtinyxml2.so.10", "cppcheck/usr/lib/x86_64-linux-gnu/libtinyxml2.so.10.0.0",
     "f9e01d87fb78af744a426af8c992e94abf8cd3810a256e117bcc94cd84d2be6d"),
)
CPPHECK_RUNTIME_LOADER = ("/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",
                          "c20a2dc8917c755f02b94049356320fe1f62ac7d9f8994731f807d9df39302da")


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class EvidenceLimitError(RuntimeError):
    """An analysis attempt tried to retain more evidence than its reservation."""


class EvidenceBudget:
    """Pre-write physical-allocation admission control for one scan attempt."""

    def __init__(self, root: Path, *, limit: int = PROBE_EVIDENCE_RESERVE_BYTES,
                 failure_reserve: int = FAILURE_RECEIPT_RESERVE_BYTES):
        self.root = root.resolve()
        self.limit = limit
        self.failure_reserve = failure_reserve
        self.reservations: dict[str, int] = {}
        if limit < failure_reserve:
            raise ValueError("evidence limit is smaller than the failure receipt reserve")

    @staticmethod
    def rounded(size: int) -> int:
        if size < 0:
            raise ValueError("negative evidence size")
        return ((size + EVIDENCE_ALLOCATION_BYTES - 1) // EVIDENCE_ALLOCATION_BYTES) * EVIDENCE_ALLOCATION_BYTES

    def _path(self, path: Path) -> Path:
        resolved = path.resolve(strict=False)
        if resolved != self.root and not resolved.is_relative_to(self.root):
            raise EvidenceLimitError("evidence write escapes its attempt root: " + str(path))
        return resolved

    def _missing_directory_bytes(self, path: Path) -> int:
        """Reserve 4 KiB for each not-yet-created directory before mkdir()."""
        missing = 0
        current = path
        while not current.exists():
            missing += 1
            if current == self.root:
                break
            current = current.parent
        if current != self.root and not current.is_relative_to(self.root):
            raise EvidenceLimitError("evidence directory escapes its attempt root: " + str(path))
        # A new directory consumes its own block and may grow its parent entry
        # table.  Charge both before creation rather than relying on a later
        # physical-allocation check.
        return missing * 2 * EVIDENCE_ALLOCATION_BYTES

    def used(self) -> int:
        return evidence_allocated_bytes(self.root) if self.root.exists() else 0

    @staticmethod
    def _target_allocation(path: Path) -> int:
        if not path.exists() or path.is_symlink() or not path.is_file():
            return 0
        return path.stat().st_blocks * 512

    def _allowance(self, *, failure: bool, terminal: bool = False) -> int:
        reserve = 0 if terminal else (TERMINAL_RECEIPT_RESERVE_BYTES if failure else self.failure_reserve)
        return self.limit - sum(self.reservations.values()) - reserve

    def admit(self, path: Path, size: int, *, failure: bool = False, terminal: bool = False) -> None:
        path = self._path(path)
        directory_bytes = self._missing_directory_bytes(path.parent)
        entry_bytes = 0 if path.exists() or path.is_symlink() else EVIDENCE_ALLOCATION_BYTES
        projected = self.used() - self._target_allocation(path) + directory_bytes + entry_bytes + self.rounded(size)
        allowance = self._allowance(failure=failure, terminal=terminal)
        if projected > allowance:
            raise EvidenceLimitError(
                f"evidence write exceeds reserved allocation: {projected}>{allowance} bytes ({path})")
        path.parent.mkdir(parents=True, exist_ok=True)

    def reserve(self, name: str, size: int) -> None:
        if name in self.reservations:
            raise EvidenceLimitError("duplicate evidence reservation: " + name)
        rounded = self.rounded(size)
        projected = self.used() + sum(self.reservations.values()) + rounded
        if projected > self.limit - self.failure_reserve:
            raise EvidenceLimitError(
                f"evidence reservation exceeds available allocation: {projected}>{self.limit - self.failure_reserve}")
        self.reservations[name] = rounded

    def release(self, name: str) -> None:
        self.reservations.pop(name, None)

    def remaining(self, *, failure: bool = False) -> int:
        return max(0, self._allowance(failure=failure) - self.used())

    def mkdir(self, path: Path, *, failure: bool = False) -> None:
        path = self._path(path)
        projected = self.used() + self._missing_directory_bytes(path)
        allowance = self._allowance(failure=failure)
        if projected > allowance:
            raise EvidenceLimitError(
                f"evidence directory exceeds reserved allocation: {projected}>{allowance} bytes ({path})")
        path.mkdir(parents=True, exist_ok=True)

    def write_bytes(self, path: Path, body: bytes, *, failure: bool = False, terminal: bool = False) -> None:
        self.admit(path, len(body), failure=failure, terminal=terminal)
        path.write_bytes(body)
        if self.used() > self._allowance(failure=failure, terminal=terminal):
            raise EvidenceLimitError("evidence allocation exceeded its admission after write: " + str(path))

    def write_text(self, path: Path, text: str, *, failure: bool = False, terminal: bool = False) -> None:
        self.write_bytes(path, text.encode(), failure=failure, terminal=terminal)

    def symlink(self, path: Path, target: Path | str) -> None:
        target_text = str(target)
        self.admit(path, len(target_text.encode()))
        path.symlink_to(target_text)

    def save(self, path: Path, value, *, failure: bool = False, terminal: bool = False) -> None:
        self.write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n", failure=failure, terminal=terminal)

    def commit_external(self, name: str, path: Path, maximum: int) -> None:
        """Account for an externally written bounded file before retaining it."""
        path = self._path(path)
        if not path.is_file() or path.is_symlink():
            raise EvidenceLimitError("external evidence file is absent or unsafe: " + str(path))
        if path.stat().st_size > maximum or self._target_allocation(path) > self.rounded(maximum):
            raise EvidenceLimitError("external evidence file exceeded its declared bound: " + str(path))
        self.release(name)
        if self.used() > self.limit - self.failure_reserve:
            raise EvidenceLimitError("external evidence exhausted the failure receipt reserve")


def save(path: Path, value, budget: EvidenceBudget | None = None, *, failure: bool = False,
         terminal: bool = False) -> None:
    body = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if budget is None:
        path.write_text(body)
    else:
        budget.write_text(path, body, failure=failure, terminal=terminal)


def save_terminal_result(path: Path, value: dict, budget: EvidenceBudget) -> None:
    """Persist a bounded final status even when optional diagnostics filled their allowance."""
    body = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if len(body.encode()) > TERMINAL_RECEIPT_RESERVE_BYTES:
        body = json.dumps({"status": value.get("status", "FAILED"),
                           "error": str(value.get("error", "terminal result truncated"))[:2048],
                           "terminal_receipt": "compact; optional evidence exceeded its retained allowance"},
                          indent=2, sort_keys=True) + "\n"
    budget.write_text(path, body, failure=True, terminal=True)


def allocated_bytes(path: Path) -> int:
    """Return physical allocation, not apparent file length, without mutating it."""
    if not path.is_dir():
        raise RuntimeError("retained native work tree is absent: " + str(path))
    total, seen = 0, set()
    for item in chain((path,), path.rglob("*")):
        stat = item.lstat()
        identity = (stat.st_dev, stat.st_ino)
        if identity not in seen:
            seen.add(identity)
            total += stat.st_blocks * 512
    return total


def evidence_allocated_bytes(path: Path) -> int:
    """Count evidence symlinks conservatively as retained metadata as well."""
    if not path.is_dir():
        raise RuntimeError("evidence root is absent: " + str(path))
    total, seen = 0, set()
    for item in chain((path,), path.rglob("*")):
        stat = item.lstat()
        identity = (stat.st_dev, stat.st_ino)
        if identity in seen:
            continue
        seen.add(identity)
        if item.is_symlink():
            total += max(stat.st_blocks * 512, EVIDENCE_ALLOCATION_BYTES)
        else:
            total += stat.st_blocks * 512
    return total


def enforce_evidence_budget(out: Path) -> int:
    """Fail closed before a later analysis stage can extend an oversized receipt."""
    used = evidence_allocated_bytes(out) if out.exists() else 0
    if used > PROBE_EVIDENCE_RESERVE_BYTES:
        raise RuntimeError(f"analysis evidence exceeds its reserved bound: {used}>{PROBE_EVIDENCE_RESERVE_BYTES}")
    return used


def probe_temporary_accounting() -> dict:
    retained = allocated_bytes(RETAINED_NATIVE_WORK)
    tmpfs = (PROBE_SERVER_DATA_BYTES + PROBE_SERVER_LOG_BYTES + PROBE_SERVER_TEMP_BYTES
             + PROBE_SERVER_EXTENSIONS_BYTES + PROBE_SERVER_TMP_BYTES + PROBE_SCANNER_TEMP_BYTES)
    total = retained + tmpfs + PROBE_EVIDENCE_RESERVE_BYTES
    receipt = {
        "policy_temp_budget_bytes": TEMPORARY_BUDGET_BYTES,
        "retained_native_work_path": str(RETAINED_NATIVE_WORK),
        "retained_native_work_allocated_bytes": retained,
        "probe_tmpfs_ceiling_bytes": tmpfs,
        "server_tmpfs": {"data": PROBE_SERVER_DATA_BYTES, "logs": PROBE_SERVER_LOG_BYTES,
                           "temp": PROBE_SERVER_TEMP_BYTES, "extensions": PROBE_SERVER_EXTENSIONS_BYTES,
                           "tmp": PROBE_SERVER_TMP_BYTES},
        "probe_evidence_reserve_bytes": PROBE_EVIDENCE_RESERVE_BYTES,
        "aggregate_reserved_bytes": total,
        "remaining_bytes": TEMPORARY_BUDGET_BYTES - total,
        "images_and_tool_packages": "recorded provenance; not temporary workspace",
    }
    if total > TEMPORARY_BUDGET_BYTES:
        raise RuntimeError("probe temporary reservation exceeds the shared 4 GB policy: " + json.dumps(receipt, sort_keys=True))
    return receipt


def scanner_writable_contract() -> dict:
    return {
        "container_root_filesystem": "read-only (--read-only)",
        "source_mount": "/usr/src:ro",
        "report_mount": "/out:ro; the only writable evidence paths are two pre-created, size-bounded file binds",
        "writable_tmpfs": {"path": "/tmp", "bytes": PROBE_SCANNER_TEMP_BYTES,
                            "includes": ["HOME", "XDG_CONFIG_HOME", "SONAR_USER_HOME", "SCANNER_WORKDIR_PATH"]},
        "scanner_evidence": {"host_path": "<attempt>/scanner.log", "container_path": "/scanner-log",
                             "bytes": SCANNER_EVIDENCE_BYTES, "precreated_file_bind": True,
                             "writer": "8 MiB RLIMIT log-sink, then shell metadata copy after a 65537-byte check"},
        "scanner_report_task": {"path": "/tmp/report-task.txt", "bytes": SCANNER_REPORT_TASK_BYTES,
                                "container_only_until_bounded_copy": True},
        "docker_log_driver": "none; scanner stdout/stderr flows through the bounded log-sink",
        "jre": "image Java 21; scanner JRE provisioning disabled with -Dsonar.scanner.skipJreProvisioning=true",
    }


def server_start_contract(entrypoint: tuple[str, ...] | list[str] = SERVER_ENTRYPOINT) -> tuple[list[str], list[str], dict]:
    """Return the read-only server mounts and wrapper for a recorded image argv.

    The caller must supply the inspected immutable image entrypoint and command;
    this helper deliberately does not infer a startup path from the host.
    """
    if not entrypoint or not all(isinstance(value, str) and value for value in entrypoint):
        raise RuntimeError("recorded Sonar server entrypoint argv is required")
    startup_log = "/opt/sonarqube/logs/cix-startup.log"
    exit_marker = "/opt/sonarqube/logs/cix-startup-exit"
    wrapper = (
        "set -o pipefail; "
        "( \"$@\" 2>&1 | { head -c 65536 > " + startup_log + "; cat > /dev/null; }; "
        "status=${PIPESTATUS[0]}; printf '%s\\n' \"$status\" > " + exit_marker + "; "
        "while :; do sleep 3600; done )"
    )
    mounts = ["--read-only", "--log-driver", "none",
              "--tmpfs", f"/opt/sonarqube/data:rw,uid=1000,gid=0,size={PROBE_SERVER_DATA_BYTES}",
              "--tmpfs", f"/opt/sonarqube/logs:rw,uid=1000,gid=0,size={PROBE_SERVER_LOG_BYTES}",
              "--tmpfs", f"/opt/sonarqube/temp:rw,uid=1000,gid=0,size={PROBE_SERVER_TEMP_BYTES}",
              "--tmpfs", f"/opt/sonarqube/extensions:rw,uid=1000,gid=0,size={PROBE_SERVER_EXTENSIONS_BYTES}",
              "--tmpfs", f"/tmp:rw,exec,size={PROBE_SERVER_TMP_BYTES}",
              "--entrypoint", "bash"]
    receipt = {"image_entrypoint": entrypoint, "wrapper": wrapper, "startup_log": startup_log,
               "exit_marker": exit_marker, "startup_log_bytes": FAILURE_LOG_BYTES,
               "image_volumes": list(SERVER_IMAGE_VOLUMES), "image_volumes_bounded": list(SERVER_IMAGE_VOLUMES),
               "tmpfs": {"data": PROBE_SERVER_DATA_BYTES, "logs": PROBE_SERVER_LOG_BYTES,
                         "temp": PROBE_SERVER_TEMP_BYTES, "extensions": PROBE_SERVER_EXTENSIONS_BYTES,
                         "tmp": PROBE_SERVER_TMP_BYTES}}
    return mounts, ["-c", wrapper, "cix-sonar-server", *entrypoint], receipt


def rebase_include_commands(commands: list, source: Path) -> tuple[list, list[tuple[Path, str]], list[dict]]:
    """Map only recorded include operands, retaining their resolution evidence."""
    context = load_module("cix_include_context", Path(__file__).with_name("include_context.py"))
    return context.rebase_include_context(commands, source)


def external_include_mounts(commands: list, source: Path) -> list[Path]:
    """Return the canonical roots explicitly named by the recorded commands."""
    _, mounts, _ = rebase_include_commands(commands, source)
    return [root for root, _ in mounts]


def containerize_commands(commands: list, source: Path) -> tuple[list, list[tuple[Path, str]]]:
    mapped, mounts, _ = rebase_include_commands(commands, source)
    return mapped, mounts


def prepare_cxx_only_extensions(raw: Path, server_image: str, budget: EvidenceBudget | None = None) -> Path:
    """Record the fixed image inventory and create the read-only empty overlay."""
    empty = raw / "empty-core-extensions"
    if budget is None:
        empty.mkdir()
    else:
        budget.mkdir(empty)
    empty.chmod(0o555)
    entries = [{"jar": jar, "bytes": size, "language": language}
               for jar, size, language in IMAGE_CORE_EXTENSION_INVENTORY]
    omitted = sorted({language for _, _, language in IMAGE_CORE_EXTENSION_INVENTORY if language})
    save(raw / "image-core-extension-inventory.json", {
        "image": server_image,
        "image_path": "/opt/sonarqube/lib/extensions",
        "entries": entries,
        "inventory_method": "read-only container-layer listing before probe-v3 configuration",
    }, budget)
    save(raw / "omitted-core-extensions.json", {
        "mount": f"{empty}:/opt/sonarqube/lib/extensions:ro",
        "omitted_languages": omitted,
        "omitted_non_language_extensions": [jar for jar, _, language in IMAGE_CORE_EXTENSION_INVENTORY if not language],
        "included_extension": "separately checksummed SonarOpenCommunity CXX plugin mounted at /opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar",
        "scope": "CXX registration and Cppcheck null-pointer fixture only",
        "limitation": "This probe provides no product-language coverage; each omitted language needs its own later coverage configuration.",
        "image_unchanged": True,
    }, budget)
    return empty


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    # Dataclass and similar decorators resolve their defining module through
    # sys.modules while it is being executed.
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _runtime_inventory(root: Path) -> list[dict]:
    return [{"path": str(path.relative_to(root)), "sha256": digest(path)}
            for path in sorted(root.rglob("*")) if path.is_file()]


def stage_private_cppcheck_runtime() -> Path:
    """Stage the exact loader closure below the existing architecture lib mountpoint."""
    runtime = TOOLS / CPPHECK_RUNTIME_VERSION
    manifest = runtime / "manifest.json"
    if runtime.exists():
        if not manifest.is_file():
            raise RuntimeError("private Cppcheck runtime is incomplete; refuse to overwrite it")
        return runtime
    source_cfg = TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu/cppcheck/cfg"
    if not source_cfg.is_dir():
        raise RuntimeError("private Cppcheck configuration is absent")
    temporary = Path(tempfile.mkdtemp(prefix=CPPHECK_RUNTIME_VERSION + ".", dir=TOOLS))
    try:
        lib = temporary / "usr/lib/x86_64-linux-gnu"
        lib.mkdir(parents=True)
        binary_source = TOOLS / "cppcheck/usr/bin/cppcheck"
        if not binary_source.is_file() or digest(binary_source) != CPPHECK_BINARY_SHA256:
            raise RuntimeError("private Cppcheck binary does not match its pinned hash")
        binary_target = temporary / "usr/bin/cppcheck"
        binary_target.parent.mkdir(parents=True)
        shutil.copy2(binary_source, binary_target)
        shutil.copytree(source_cfg, lib / "cppcheck/cfg")
        rows = []
        for name, source, expected in CPPHECK_RUNTIME_DSOS:
            source_path = TOOLS / source if not source.startswith("/") else Path(source)
            if not source_path.is_file() or digest(source_path) != expected:
                raise RuntimeError("Cppcheck runtime dependency does not match its pinned hash: " + str(source_path))
            copied = lib / source_path.name
            shutil.copy2(source_path, copied)
            target = lib / name
            if target != copied:
                target.symlink_to(copied.name)
            rows.append({"soname": name, "source": str(source_path), "sha256": expected,
                         "staged": str(copied.relative_to(temporary))})
        loader_source, loader_expected = CPPHECK_RUNTIME_LOADER
        loader = Path(loader_source)
        if not loader.is_file() or digest(loader) != loader_expected:
            raise RuntimeError("Cppcheck ELF loader does not match its pinned hash")
        loader_target = temporary / "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
        loader_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(loader, loader_target)
        save(temporary / "manifest.json", {
            "schema": 1,
            "purpose": "private Bubblewrap Cppcheck FILESDIR and ELF dependency overlay",
            "architecture_library_mount": "/usr/lib/x86_64-linux-gnu",
            "elf_loader_mount": "/usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2",
            "binary": {"source": str(binary_source), "sha256": CPPHECK_BINARY_SHA256,
                       "staged": str(binary_target.relative_to(temporary)), "mount": "/usr/bin/cppcheck"},
            "dependencies": rows,
            "elf_loader": {"source": loader_source, "sha256": loader_expected,
                           "staged": str(loader_target.relative_to(temporary))},
            "cfg_source": str(source_cfg), "cfg_inventory": _runtime_inventory(lib / "cppcheck/cfg"),
        })
        os.replace(temporary, runtime)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return runtime


def provision() -> None:
    """Download only checksummed tooling, without installing system packages."""
    TOOLS.mkdir(exist_ok=True)
    for name, (url, expected) in PACKAGES.items():
        path = TOOLS / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                body = response.read()
            if hashlib.sha256(body).hexdigest() != expected:
                raise RuntimeError(f"download checksum mismatch: {name}")
            path.write_bytes(body)
        if digest(path) != expected:
            raise RuntimeError(f"tool checksum mismatch: {name}")
        if name.endswith(".deb"):
            subprocess.run(["dpkg-deb", "-x", str(path), str(TOOLS / "cppcheck")], check=True)
    cppcheck_cfg = TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu/cppcheck/cfg"
    if not shutil.which("bwrap"):
        raise RuntimeError("private Cppcheck needs bubblewrap to bind its compiled FILESDIR without modifying host files")
    for name in ("std.cfg", "posix.cfg"):
        if not (cppcheck_cfg / name).is_file():
            raise RuntimeError("private Cppcheck configuration is incomplete: " + name)
    stage_private_cppcheck_runtime()
    save(TOOLS / "provenance.json", {
        "packages": {name: {"url": url, "sha256": sha}
                     for name, (url, sha) in PACKAGES.items()},
        "cppcheck": "Ubuntu noble 2.13.0-2ubuntu3; private extraction, no system mutation; "
                    "bubblewrap privately binds its compiled FILESDIR at execution",
        "plugin": "CXX 2.3.0.1496; requires Java >=21; live server compatibility must be verified",
    })


def inventory(source: Path) -> dict:
    result = {}
    for name, roots in SCOPES.items():
        files = []
        for prefix in roots:
            directory = source / prefix
            if not directory.is_dir():
                raise RuntimeError(f"missing source scope: {directory}")
            for path in sorted(directory.rglob("*")):
                if path.is_file() and path.suffix.lower() in SUFFIXES:
                    if path.is_symlink():
                        raise RuntimeError(f"symlink in source scope: {path}")
                    files.append({"path": str(path.relative_to(source)), "sha256": digest(path)})
        if not files:
            raise RuntimeError(f"empty source scope: {name}")
        result[name] = {"roots": roots, "files": files}
    return result


def _make_assignments(path: Path, language: str) -> tuple[str, list[str]]:
    text = path.read_text()
    compiler = re.search(rf"# compile {language} with (.+)", text)
    if not compiler:
        raise RuntimeError(f"missing compiler identity in completed CMake receipt: {path}")
    values = []
    for key in (f"{language}_DEFINES", f"{language}_INCLUDES", f"{language}_FLAGS"):
        match = re.search(rf"^{key} = (.*)$", text, re.M)
        values.extend(shlex.split(match.group(1)) if match and match.group(1) else [])
    return compiler.group(1), values


def _completed_cmake_commands(source: Path) -> tuple[list, dict]:
    commands, provenance = [], {}
    for name, receipt, snapshot, current, paths, language in CMAKE_RECEIPTS:
        receipt_dir, snapshot_root, current_root = ROOT / receipt, ROOT / snapshot, source / current
        flags_path = receipt_dir / "flags.make"
        row = {"flags_make": str(flags_path), "status": "unavailable"}
        if not flags_path.is_file():
            row["reason"] = "completed CMake flags receipt is absent"
            provenance[name] = row
            continue
        compiler, flags = _make_assignments(flags_path, language)
        mismatches = []
        for relative in paths:
            old_file, new_file = snapshot_root / relative, current_root / relative
            if not old_file.is_file() or not new_file.is_file() or digest(old_file) != digest(new_file):
                mismatches.append(relative)
                continue
            mapped = [item.replace(str(snapshot_root), str(current_root)) for item in flags]
            commands.append({"file": str(new_file), "directory": str(current_root),
                             "arguments": [compiler, *mapped, "-c", str(new_file)]})
        row.update({"sha256": digest(flags_path), "status": "completed CMake flags reused" if not mismatches else "stale_source",
                    "source_hash_mismatches": mismatches, "translation_units": len(paths) - len(mismatches)})
        provenance[name] = row
    return commands, provenance


def _completed_direct_commands(source: Path) -> tuple[list, dict]:
    """Reuse a logged successful compiler argv only when its source is current."""
    commands, provenance = [], {}
    for name, log, label, snapshot, current, relative, language in DIRECT_COMMAND_RECEIPTS:
        log_path, snapshot_root, current_root = ROOT / log, ROOT / snapshot, source / current
        old_file, new_file = snapshot_root / relative, current_root / relative
        row = {"stdout_log": str(log_path), "status": "unavailable"}
        if not log_path.is_file():
            row["reason"] = "completed job stdout receipt is absent"
        elif not old_file.is_file() or not new_file.is_file() or digest(old_file) != digest(new_file):
            row.update({"status": "stale_source", "source": relative})
        else:
            # Job logs use Python's list rendering.  PosixPath appears only
            # for output arguments, so normalize it before literal parsing;
            # the logged compiler argv itself remains otherwise unchanged.
            rendered = re.findall(rf"^{re.escape(label)} (\[.*\]) 0$", log_path.read_text(), re.M)
            parsed = [ast.literal_eval(re.sub(r"PosixPath\('([^']*)'\)", r"'\1'", item)) for item in rendered]
            old_argument = str(old_file)
            matches = [arguments for arguments in parsed if all(isinstance(arg, str) for arg in arguments)
                       and arguments.count(old_argument) == 1]
            if len(matches) != 1:
                row["reason"] = "expected exactly one successful compiler argv for the frozen translation unit in completed job stdout"
            else:
                commands.append({"file": str(new_file), "directory": str(current_root),
                                 "arguments": [str(new_file) if arg == old_argument else arg for arg in matches[0]]})
                row.update({"sha256": digest(log_path), "status": "completed direct compiler argv reused",
                            "translation_units": 1, "language": language})
        provenance[name] = row
    return commands, provenance


def _distribution_compiler_commands(source: Path) -> tuple[list, dict]:
    """Reuse only frozen-export commands whose translation-unit bytes are current."""
    receipt = DISTRIBUTION_COMPILER_RECEIPT
    job = ROOT / receipt["job"]
    database_path, frozen_root, current_root = job / receipt["database"], ROOT / receipt["source"], source / receipt["current"]
    row = {"compiler_invocations": str(database_path), "status": "unavailable"}
    if not database_path.is_file() or not frozen_root.is_dir():
        row["reason"] = "completed distribution compiler receipt or frozen export is absent"
        return [], row
    scheduler = json.loads((job / "scheduler-output.json").read_text()) if (job / "scheduler-output.json").is_file() else {}
    if scheduler.get("exit_code") != 0 or scheduler.get("child_status", {}).get("child_exit_code") != 0:
        row["reason"] = "distribution compiler receipt did not complete successfully"
        return [], row
    commands, stale, ignored = [], [], 0
    for raw in database_path.read_text().splitlines():
        item = json.loads(raw)
        arguments = item.get("arguments", [])
        if "-c" not in arguments:
            ignored += 1
            continue
        position = arguments.index("-c") + 1
        if position >= len(arguments):
            ignored += 1
            continue
        old_file = Path(arguments[position])
        if not old_file.is_absolute():
            old_file = Path(item["directory"]) / old_file
        old_file = old_file.resolve()
        if not old_file.is_relative_to(frozen_root):
            ignored += 1
            continue
        relative = old_file.relative_to(frozen_root)
        new_file = current_root / relative
        if not new_file.is_file() or digest(old_file) != digest(new_file):
            stale.append(str(relative))
            continue
        mapped = [str(new_file) if value == arguments[position] else value for value in arguments]
        commands.append({"file": str(new_file), "directory": str(current_root), "arguments": mapped})
    row.update({"sha256": digest(database_path), "status": "completed distribution compiler argv reused" if not stale else "partially_stale_source",
                "translation_units": len(commands), "source_hash_mismatches": stale, "ignored_non_tu_records": ignored,
                "frozen_export": str(frozen_root)})
    return commands, row


def _filesystem_commands(source: Path) -> tuple[list, dict]:
    """Use only per-TU, passed filesystem argv recorded by the read-only ledger."""
    row = {"path": str(FILESYSTEM_COMMANDS_RECEIPT), "status": "unavailable"}
    if not FILESYSTEM_COMMANDS_RECEIPT.is_file():
        row["reason"] = "filesystem command ledger is absent"
        return [], row
    ledger = json.loads(FILESYSTEM_COMMANDS_RECEIPT.read_text())
    if ledger.get("schema") != "cix.sonar.filesystem-commands.v1" or ledger.get("status") != "READ_ONLY_EVIDENCE_ONLY":
        row["reason"] = "filesystem command ledger has an unexpected schema or status"
        return [], row
    records = list(ledger.get("kernel_module_v4", {}).get("records", []))
    records.extend(ledger.get("userspace_reader_v7", {}).get("records", []))
    commands, rejected = [], []
    for record in records:
        relative = record.get("translation_unit")
        current = source / relative if relative else None
        arguments = record.get("argv")
        expected = record.get("current_sha256")
        if not current or not current.is_file() or not isinstance(arguments, list) or "-c" not in arguments:
            rejected.append({"path": relative, "reason": "not a per-TU compile argv"})
            continue
        qualified_name = record.get("qualified_stage_source") or record.get("qualified_staged_source")
        if not qualified_name or digest(current) != expected:
            rejected.append({"path": relative, "reason": "current source does not match qualified digest"})
            continue
        qualified = (ROOT / qualified_name).resolve()
        position = next((index for index, value in enumerate(arguments)
                         if value.startswith("/") and Path(value).resolve() == qualified), None)
        if position is None:
            rejected.append({"path": relative, "reason": "qualified argv does not name its recorded source"})
            continue
        if not qualified.is_file() or digest(qualified) != expected:
            rejected.append({"path": relative, "reason": "qualified argv source is absent or digest differs"})
            continue
        mapped = list(arguments)
        mapped[position] = str(current)
        commands.append({"file": str(current), "directory": record["working_directory"], "arguments": mapped})
    row.update({"sha256": digest(FILESYSTEM_COMMANDS_RECEIPT), "status": "completed per-TU argv reused",
                "translation_units": len(commands), "rejected": rejected,
                "excluded_profile_shared_compile": "profile_library_v2 has a combined non--c test argv; retained as evidence, not converted into synthetic per-TU commands"})
    return commands, row


def _bridge_portability_commands(source: Path) -> tuple[list, dict]:
    row = {"path": str(BRIDGE_PORTABILITY_RECEIPT), "status": "unavailable"}
    if not BRIDGE_PORTABILITY_RECEIPT.is_file():
        return [], row
    receipt = json.loads(BRIDGE_PORTABILITY_RECEIPT.read_text())
    passed = {item["label"].removesuffix("-build") for item in receipt.get("commands", [])
              if item.get("label", "").endswith("-build") and item.get("returncode") == 0}
    commands, stale = [], []
    for name, item in receipt.get("compile_commands", {}).items():
        database = Path(item["path"])
        if name not in passed or not database.is_file() or digest(database) != item.get("sha256"):
            continue
        for command in json.loads(database.read_text()):
            old = Path(command["file"]).resolve()
            if not old.is_relative_to(source):
                continue
            relative = str(old.relative_to(source)); current = source / relative
            expected = receipt.get("source_hashes", {}).get(relative)
            if expected is None:
                continue
            if expected != digest(current):
                stale.append(relative); continue
            args = command.get("arguments") or shlex.split(command["command"])
            commands.append({"file": str(current), "directory": command["directory"], "arguments": args})
    row.update({"status": "partial receipt: five successful builds reused; enclosing spatial configure failure retained",
                "enclosing_status": receipt.get("status"), "successful_builds": sorted(passed),
                "translation_units": len(commands), "source_hash_mismatches": stale})
    return commands, row


def _spatial_portability_commands(source: Path) -> tuple[list, dict]:
    row = {"path": str(SPATIAL_PORTABILITY_RECEIPT), "status": "unavailable"}
    if not SPATIAL_PORTABILITY_RECEIPT.is_file(): return [], row
    receipt = json.loads(SPATIAL_PORTABILITY_RECEIPT.read_text())
    database = ROOT / "benchmark-work/native-rc-check-v1/bridge-portability-v2/compile_commands.json"
    spatial = source / "rust/cix-native/codecs/spatial/cix_spatial_bridge.cpp"
    if not database.is_file() or digest(database) != receipt.get("spatial", {}).get("compile_commands_sha256") or digest(spatial) != receipt.get("spatial", {}).get("source_cpp_sha256"):
        row["reason"] = "passed spatial database or current source digest mismatch"; return [], row
    if not all(item.get("returncode") == 0 for item in receipt.get("commands", [])):
        row["reason"] = "spatial receipt command failed"; return [], row
    records = json.loads(database.read_text())
    commands = [{"file": str(spatial), "directory": item["directory"],
                 "arguments": item.get("arguments") or shlex.split(item["command"])}
                for item in records if Path(item["file"]).resolve() == spatial.resolve()]
    row.update({"status": "passed spatial v2 argv reused", "translation_units": len(commands),
                "receipt_status": receipt.get("status")})
    return commands, row


def _new_capture_commands(source: Path) -> tuple[list, dict]:
    receipt = CAPTURE_V1 / "receipt.json"; row={"status":"unavailable","path":str(receipt)}
    if not receipt.is_file(): return [], row
    value=json.loads(receipt.read_text())
    if value.get("kind") != "NEW_ANALYSIS_CONFIGURATION" or any(x.get("returncode") not in (0,None) for x in value.get("commands",[])): return [], row
    if any(not Path(path).is_file() or digest(Path(path)) != expected for path, expected in value.get("header_hashes", {}).items()):
        row["reason"]="captured header identity mismatch"; return [], row
    commands=[]
    for db in CAPTURE_V1.glob("*-compile_commands.json"):
        for item in json.loads(db.read_text()):
            file=Path(item["file"]).resolve()
            if file.is_relative_to(source) and value["source_hashes"].get(str(file.relative_to(source))) == digest(file):
                commands.append({"file":str(file),"directory":item["directory"],"arguments":item.get("arguments") or shlex.split(item["command"])})
    # The documented direct generator command is retained in the successful receipt.
    for item in value["commands"]:
        if item.get("label") == "stream-source-generator":
            file=source/"rust/cix-native/experiments/stream-qualification-v2/source-generator.c"
            if value["source_hashes"].get(str(file.relative_to(source))) == digest(file): commands.append({"file":str(file),"directory":item["cwd"],"arguments":item["argv"]})
    row.update({"status":"completed new analysis configuration", "translation_units":len(commands), "header_hashes":value.get("header_hashes",{})})
    return commands,row


def _host_capture_v3_commands(source: Path) -> tuple[list, dict]:
    log=HOST_V3/"compiler-invocations.jsonl"; row={"status":"unavailable","path":str(log)}
    if not log.is_file() or not HOST_V3_RESOLUTION.is_file(): return [],row
    receipt_path=ROOT/"benchmark-work/native-rc-check-v1/compiler-capture-host-v3/receipt.json"
    job_receipt=HOST_V3/"receipt.json"
    if not receipt_path.is_file() or not job_receipt.is_file() or digest(receipt_path)!=digest(job_receipt):
        row["reason"]="host receipt mirror mismatch"; return [],row
    receipt=json.loads(receipt_path.read_text())
    if receipt.get("schema")!="cix.compiler-capture-host.v3" or receipt.get("kind")!="NEW_ANALYSIS_CONFIGURATION" or any(x.get("returncode") not in (0,None) for x in receipt.get("commands",[])):
        row["reason"]="host build step failed"; return [],row
    resolution=json.loads(HOST_V3_RESOLUTION.read_text())
    capture=resolution.get("capture_receipt", {})
    if capture.get("sha256") != digest(receipt_path):
        row["reason"]="resolution capture receipt digest mismatch"; return [],row
    # The v3 final selector failure is preserved; each compiler command itself passed.
    resolved={x["translation_unit"] for x in resolution["records"]}
    records=[json.loads(line) for line in log.read_text().splitlines()]
    if records != receipt.get("compiler_invocations"):
        row["reason"]="host JSONL differs from receipt compiler invocations"; return [],row
    for identity in receipt.get("source_identity",{}).values():
        current=Path(identity["current"]); snapshot=Path(identity["snapshot"])
        if not current.is_file() or not snapshot.is_file() or digest(current)!=identity["sha256"] or digest(snapshot)!=identity["sha256"]:
            row["reason"]="host source identity mismatch"; return [],row
    for binding in resolution.get("records", []):
        index=binding.get("compiler_invocation_index")
        if not isinstance(index,int) or index >= len(records) or records[index].get("cwd") != str(ROOT / binding["working_directory"]) or binding["recorded_source_operand"] not in records[index].get("argv",[]) or digest(source / binding["resolved_source"]) != binding["sha256"] or digest(ROOT / binding["passed_snapshot"]) != binding["passed_snapshot_sha256"]:
            row["reason"]="resolution binding mismatch"; return [],row
    commands=[]
    for path in sorted({str(p.relative_to(source)) for p in (source/"rust/cix-native").rglob("*") if p.suffix in (".c",".cc",".cpp")}):
        current=source/path; match=None
        # Only accept host source operands with an exact captured identity.
        # Other helper commands are provided by their own qualified receipts.
        if str(current) not in {item["current"] for item in receipt["source_identity"].values()}:
            continue
        for item in records:
            for arg in item["argv"]:
                if arg.startswith("/") and Path(arg).resolve()==current.resolve(): match=item; break
            if match: break
        if match:
            # v3's CC wrapper delegates to shutil.which('cc'), recorded in its run.py.
            commands.append({"file":str(current),"directory":match["cwd"],"arguments":["/usr/bin/cc",*match["argv"]]})
    row.update({"status":"actual commands reused; enclosing receipt selector failure preserved","translation_units":len(commands),"resolution_sha256":digest(HOST_V3_RESOLUTION),"resolved_double_slash_translation_units":sorted(resolved)})
    return commands,row


def _c_api_capture_command(source: Path) -> tuple[list, dict]:
    row={"path":str(C_API_CAPTURE_RECEIPT),"status":"unavailable"}
    if not C_API_CAPTURE_RECEIPT.is_file(): return [],row
    value=json.loads(C_API_CAPTURE_RECEIPT.read_text()); file=source/"rust/cix-native/tests/c_api_consumer.c"
    headers=value.get("headers",{})
    if value.get("kind")!="NEW_ANALYSIS_CONFIGURATION" or value.get("returncode")!=0 or value.get("source")!=str(file) or value.get("source_sha256")!=digest(file) or any(not Path(p).is_file() or digest(Path(p))!=h for p,h in headers.items()):
        row["reason"]="capture source/header identity or exit mismatch"; return [],row
    row.update({"status":"completed new C API capture","header_hashes":headers})
    return [{"file":str(file),"directory":value["cwd"],"arguments":value["argv"]}],row


def compilation_metadata(source: Path, scopes: dict) -> tuple[list, dict, list[str]]:
    """Use retained PAQ databases and completed CMake flags without inventing commands."""
    database, provenance = [], {}
    registry = json.loads((ROOT / "runtime/backend-sources.json").read_text())["base"]
    for name in PAQ_NAMES:
        original = ROOT / registry[name]["source"]
        path = original.parent / "build-local/compile_commands.json"
        if not original.is_dir() or not path.is_file():
            provenance[name] = {"status": "unavailable", "source": str(original), "database": str(path),
                                "reason": "retained unchanged PAQ source or compilation database is absent"}
            continue
        records = json.loads(path.read_text())
        for record in records:
            old_file = Path(record["file"])
            if not old_file.is_file() or not old_file.is_relative_to(source):
                raise RuntimeError(f"PAQ compile database escapes current source closure: {old_file}")
            args = record.get("arguments") or shlex.split(record["command"])
            database.append({"file": str(old_file), "directory": record.get("directory", str(original)), "arguments": args})
        provenance[name] = {"database": str(path), "sha256": digest(path), "entries": len(records),
                            "status": "retained compile database for unchanged PAQ vendor source"}
    cmake_commands, cmake_provenance = _completed_cmake_commands(source)
    database.extend(cmake_commands)
    provenance["completed_cmake"] = cmake_provenance
    direct_commands, direct_provenance = _completed_direct_commands(source)
    database.extend(direct_commands)
    provenance["completed_direct"] = direct_provenance
    distribution_commands, distribution_provenance = _distribution_compiler_commands(source)
    database.extend(distribution_commands)
    provenance["distribution_engineering_v4"] = distribution_provenance
    filesystem_commands, filesystem_provenance = _filesystem_commands(source)
    database.extend(filesystem_commands)
    provenance["filesystem_commands_v1"] = filesystem_provenance
    bridge_commands, bridge_provenance = _bridge_portability_commands(source)
    database.extend(bridge_commands)
    provenance["bridge_portability_v1"] = bridge_provenance
    spatial_commands, spatial_provenance = _spatial_portability_commands(source)
    database.extend(spatial_commands)
    provenance["bridge_portability_v2"] = spatial_provenance
    capture_commands, capture_provenance = _new_capture_commands(source)
    database.extend(capture_commands)
    provenance["compiler_capture_v1"] = capture_provenance
    host_commands, host_provenance = _host_capture_v3_commands(source)
    database.extend(host_commands)
    provenance["compiler_capture_host_v3"] = host_provenance
    c_api_commands, c_api_provenance = _c_api_capture_command(source)
    database.extend(c_api_commands)
    provenance["compiler_c_api_capture_v1"] = c_api_provenance
    refresh = load_module("cix_sonar_compiler_refresh", Path(__file__).with_name("compiler_refresh.py"))
    refreshed_commands, refreshed_provenance = refresh.completed_boundary_commands(source)
    database.extend(refreshed_commands)
    provenance["compiler_refresh"] = refreshed_provenance
    configured = {Path(row["file"]).resolve() for row in database}
    translation_units = {source / row["path"] for scope in scopes.values() for row in scope["files"]
                         if Path(row["path"]).suffix.lower() in {".c", ".cc", ".cpp", ".cxx"}}
    unconfigured = sorted(str(path.relative_to(source)) for path in translation_units if path.resolve() not in configured)
    return database, provenance, unconfigured


def prepare(source: Path, out: Path) -> None:
    if out.exists():
        raise RuntimeError("refusing to overwrite prepared evidence")
    scopes = inventory(source)
    commands, provenance, unconfigured = compilation_metadata(source, scopes)
    out.mkdir(parents=True)
    excluded = [{"path": str(p.relative_to(source)), "reason": "CUDA header; CUDA/OpenMP disabled in rust/cix-native/build.rs"}
                for p in sorted((source / "rust/cix-native/vendor").rglob("*.cuh"))]
    save(out / "plan.json", {"source": str(source), "scopes": scopes, "analyzer": "SonarOpenCommunity CXX + Cppcheck",
        "commercial_cfamily": False, "excluded": excluded, "confirmation_summary": str(SUMMARY),
        "tools": {name: sha for name, (_, sha) in PACKAGES.items()},
        "status": "PREPARED_BLOCKED_COMPILER_CLOSURE" if unconfigured else "PREPARED_NOT_SCANNED",
        "compilation_metadata": provenance, "unconfigured_translation_units": unconfigured,
        "dependency_closure": {"paq_vendor": "included from retained unchanged source roots",
                               "paq_bridges": "included under cix-native-core",
                               "host_adapter_headers": "must have a matching completed compiler receipt before execution"}})
    save(out / "compile_commands.host.json", commands)
    save(out / "compile_commands.container.json", json.loads(json.dumps(commands).replace(str(source), "/usr/src")))
    print(json.dumps({"prepared": str(out), "files": {k: len(v["files"]) for k, v in scopes.items()},
                      "compile_commands": len(commands), "excluded_cuda": len(excluded),
                      "unconfigured_translation_units": len(unconfigured)}))


def require_confirmation(summary: Path) -> None:
    value = json.loads(summary.read_text())
    plan_path = summary.with_name("plan.json")
    plan = json.loads(plan_path.read_text())
    expected = {row["id"]: row for row in plan["cells"]}
    rows = value.get("rows", [])
    if (len(expected) != 36 or len(rows) != 36
            or {row["cell"] for row in rows} != set(expected)
            or value.get("plan_sha256") != digest(plan_path)
            or any(row.get("status") != "VERIFIED" for row in rows)):
        raise RuntimeError("full 36-cell confirmation is not yet VERIFIED; do not compete with the frozen run")
    for row in rows:
        cell = expected[row["cell"]]
        if row["source"] != cell["source"] or row["profile"] != cell["profile"]:
            raise RuntimeError("confirmation identities differ from the frozen plan")


def _committed_stop_bytes(stop: Path) -> bytes:
    """Read the stop receipt from its pinned commit, never trusting a worktree copy."""
    relative = stop.relative_to(ROOT).as_posix()
    result = subprocess.run(["git", "show", f"{STOP_COMMIT}:{relative}"], cwd=ROOT,
                            check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError("pinned benchmark-stop receipt is absent from its authenticated checkpoint")
    return result.stdout


def require_stopped_confirmation(summary: Path, stop: Path = STOP, *,
                                 committed_reader=_committed_stop_bytes, root: Path = ROOT) -> None:
    """Authorize non-benchmark hygiene only for the exact user-stopped run.

    This is deliberately narrower than accepting a status string: both the
    receipt and its commit copy must hash-match, and every planned cell must be
    classified exactly once as verified, interrupted, or unstarted.
    """
    plan_path = summary.with_name("plan.json")
    if digest(plan_path) != STOP_PLAN_SHA256:
        raise RuntimeError("stopped-run authorization has a different frozen plan")
    if not stop.is_file() or digest(stop) != STOP_SHA256 or committed_reader(stop) != stop.read_bytes():
        raise RuntimeError("stopped-run receipt is not the pinned committed receipt")
    receipt, value, plan = json.loads(stop.read_text()), json.loads(summary.read_text()), json.loads(plan_path.read_text())
    if receipt.get("status") != "STOPPED_BY_USER" or receipt.get("plan_sha256") != STOP_PLAN_SHA256:
        raise RuntimeError("stopped-run receipt is not an authorized user stop")
    if receipt.get("automatic_restart_allowed") is not False:
        raise RuntimeError("stopped-run receipt permits restart")
    expected = {row["id"] for row in plan.get("cells", [])}
    verified = set(receipt.get("verified_cells", []))
    interrupted = receipt.get("interrupted_cells", [])
    unstarted = set(receipt.get("not_started_cells", []))
    if (len(expected) != 36 or verified != STOP_VERIFIED or len(interrupted) != 1
            or interrupted[0] != {"cell": STOP_INTERRUPTED, "phase": "encode", "status": "INTERRUPTED_UNQUALIFIED", "decode_started": False}
            or len(unstarted) != 30 or expected != verified | {STOP_INTERRUPTED} | unstarted
            or len(verified | {STOP_INTERRUPTED} | unstarted) != 36):
        raise RuntimeError("stopped-run receipt has invalid cell classification")
    rows = value.get("rows", [])
    if (value.get("plan_sha256") != STOP_PLAN_SHA256 or value.get("stop_receipt") != str(stop.relative_to(root))
            or {row.get("cell") for row in rows} != verified or any(row.get("status") != "VERIFIED" for row in rows)):
        raise RuntimeError("summary does not match the pinned stopped-run receipt")


def assert_benchmark_idle(*, runner=subprocess.run, cgroup_root: Path = Path("/sys/fs/cgroup")) -> None:
    """Fail closed if the stopped confirmation could have resumed on this host."""
    listing = runner(["ps", "-eo", "pid=,args="], check=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout
    markers = (str(SUMMARY.parent), "finish-frozen-cix-silesia-confirmation",
               "complete-cix-0-1-release-qualification")
    if any(marker in line for line in listing.splitlines() for marker in markers):
        raise RuntimeError("a stopped benchmark process is active")
    for unit in ("finish-frozen-cix-silesia-confirmation.service", "complete-cix-0-1-release-qualification.service"):
        state = runner(["systemctl", "show", unit, "--property=ActiveState", "--value"],
                               check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout.strip()
        if state != "inactive":
            raise RuntimeError("a stopped benchmark unit is active or unknown")
    if cgroup_root.exists():
        matches = list(cgroup_root.rglob("*silesia-confirmation*"))
        if any(path.is_dir() and any(path.iterdir()) for path in matches):
            raise RuntimeError("a stopped benchmark cgroup is active or unknown")


def validate_indexed(files: list[str], components: list[dict], log: str) -> set[str]:
    indexed = {row["path"] for row in components if row.get("language") == "cxx"}
    missing = sorted(set(files) - indexed)
    if missing or "Sensor CXX [cxx]" not in log:
        raise RuntimeError(f"CXX source analysis incomplete: missing={missing}")
    return indexed


def private_cppcheck_runtime() -> tuple[Path, Path, Path, Path]:
    """Return the staged private FILESDIR and exact ELF dependency overlay."""
    runtime = TOOLS / CPPHECK_RUNTIME_VERSION
    executable = runtime / "usr/bin/cppcheck"
    cfg = runtime / "usr/lib/x86_64-linux-gnu/cppcheck/cfg"
    loader = runtime / "usr/lib/x86_64-linux-gnu/ld-linux-x86-64.so.2"
    bubblewrap = shutil.which("bwrap")
    manifest = runtime / "manifest.json"
    if not executable.is_file() or not bubblewrap or not manifest.is_file() or not loader.is_file():
        raise RuntimeError("private Cppcheck runtime or bubblewrap is unavailable")
    for name in ("std.cfg", "posix.cfg"):
        if not (cfg / name).is_file():
            raise RuntimeError("private Cppcheck configuration is incomplete: " + name)
    value = json.loads(manifest.read_text())
    if value.get("schema") != 1 or value.get("architecture_library_mount") != "/usr/lib/x86_64-linux-gnu":
        raise RuntimeError("private Cppcheck runtime manifest is invalid")
    if digest(executable) != value.get("binary", {}).get("sha256"):
        raise RuntimeError("staged Cppcheck binary changed")
    for row in value.get("dependencies", []):
        staged = runtime / row["staged"]
        if not staged.is_file() or digest(staged) != row.get("sha256"):
            raise RuntimeError("staged Cppcheck runtime dependency changed: " + str(staged))
    if digest(loader) != value.get("elf_loader", {}).get("sha256"):
        raise RuntimeError("staged Cppcheck ELF loader changed")
    return Path(bubblewrap), executable, runtime, cfg


def _kill_process_group(process: subprocess.Popen) -> None:
    """Stop a capture producer before an over-limit pipe can be persisted."""
    try:
        # The session leader can have exited while a descendant still owns a
        # pipe.  Signal the process group regardless of leader state.
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def collect_bounded_pipes(process: subprocess.Popen, budget: EvidenceBudget,
                          *, timeout: float, maximum: int | None = None,
                          failure: bool = False) -> tuple[bytes, bytes]:
    """Drain both pipes fairly, killing the isolated producer before excess is written."""
    selector = selectors.DefaultSelector()
    stdout_stream, stderr_stream = process.stdout, process.stderr
    if stdout_stream is None or stderr_stream is None:
        selector.close()
        raise RuntimeError("bounded capture requires both subprocess pipes")
    streams = {stdout_stream: bytearray(), stderr_stream: bytearray()}
    for stream in streams:
        os.set_blocking(stream.fileno(), False)
        selector.register(stream, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    exceeded = False
    try:
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _kill_process_group(process)
                raise TimeoutError("bounded subprocess capture timed out")
            for key, _ in selector.select(min(remaining, 1.0)):
                chunk = os.read(key.fileobj.fileno(), 64 * 1024)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                available = budget.remaining(failure=failure)
                limit = min(available, maximum) if maximum is not None else available
                if sum(len(value) for value in streams.values()) + len(chunk) > limit:
                    exceeded = True
                    _kill_process_group(process)
                    continue
                streams[key.fileobj].extend(chunk)
        process.wait(timeout=10)
    finally:
        selector.close()
        _kill_process_group(process)
        if process.poll() is None:
            process.wait(timeout=10)
        for stream in streams:
            stream.close()
    if exceeded:
        raise EvidenceLimitError("subprocess output exceeded the remaining aggregate evidence allocation")
    return bytes(streams[stdout_stream]), bytes(streams[stderr_stream])


def _projected_command(row: dict, destination: Path, extra_arguments: tuple[str, ...] = ()) -> list[str]:
    """Replay one recorded compiler command as a bounded preprocess-only action."""
    arguments = list(row["arguments"])
    source = row["file"]
    source_operands = [value for value in arguments[1:] if not value.startswith("-")
                       and (Path(row["directory"]) / value).resolve() == Path(source).resolve()]
    if len(source_operands) != 1 or arguments.count("-c") != 1:
        raise RuntimeError("compiler receipt lacks one explicit source and -c operand: " + source)
    context = load_module("cix_projection_command", Path(__file__).with_name("translation_context.py"))
    argv = list(context.preprocess_command(row, destination).argv)
    return [argv[0], *extra_arguments, *argv[1:]]


def _kernel_stage_quote_arguments(relative: str, stage: Path) -> tuple[str, ...]:
    """Restore only the build-stage quoted-include directory required by decompressor."""
    if relative == "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c":
        return ("-iquote", str(stage))
    return ()


def _kernel_stage_analysis_inputs(source: Path, relative: str) -> tuple[dict[str, str], dict]:
    """Bind current stage headers for new analysis; never present them as build proof."""
    stage = source / "benchmark-work/native-rc-check-v1/kernel-module-v4/stage"
    job = source / "docs/research/2026-10-04-execution/jobs/kernel-module-v4"
    receipt_path, inputs_path = job / "receipt.json", job / "input-hashes.json"
    receipt, inputs = json.loads(receipt_path.read_text()), json.loads(inputs_path.read_text())
    if receipt.get("prepare_returncode") != 0 or receipt.get("build_returncode") != 0 or Path(receipt.get("stage", "")).resolve() != stage.resolve():
        raise RuntimeError("kernel stage lacks its successful retained build receipt")
    manifest_path = Path(receipt.get("source_manifest", ""))
    if not manifest_path.is_file() or digest(manifest_path) != receipt.get("source_manifest_sha256"):
        raise RuntimeError("kernel stage source manifest differs from its build receipt")
    manifest = json.loads(manifest_path.read_text()).get("files")
    if not isinstance(manifest, dict):
        raise RuntimeError("kernel stage manifest has no file identities")
    current_source = source / relative
    expected_source = inputs.get(relative)
    if not isinstance(expected_source, str) or digest(current_source) != expected_source:
        raise RuntimeError("current kernel CIX source differs from the retained stage build input")
    selected = [stage / "include" / name for name in ("cix_squashfs_kernel.h", "cix_squashfs_prefix.h", "cix_squashfs_register.h")]
    selected += [stage / "profile/include/cix_squashfs_profile.h", stage / "profile/src/cix_squashfs_profile.c"]
    if relative.endswith("cix_squashfs_decompressor.c"):
        selected += sorted((stage / "upstream").glob("*.h"))
    bound: dict[str, str] = {}
    for path in selected:
        if not path.is_file():
            raise RuntimeError("required retained kernel stage input is absent: " + str(path))
        resolved = path.resolve()
        upstream_key = "fs/squashfs/" + path.name
        expected = manifest.get(upstream_key) if path.parent.name == "upstream" else None
        if expected is None:
            # Stage copies are CIX-owned inputs and must equal the recorded source bytes.
            candidates = [name for name in inputs if name.endswith("/" + path.name)]
            if len(candidates) != 1 or digest(path) != inputs[candidates[0]]:
                raise RuntimeError("stage-local input lacks a matching retained CIX source identity: " + str(path))
        elif digest(resolved) != expected:
            raise RuntimeError("stage upstream header differs from its retained manifest: " + str(path))
        bound[str(path)] = digest(path)
    return bound, {"kind": "NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF", "stage": str(stage),
                   "build_receipt_sha256": digest(receipt_path), "source_manifest_sha256": digest(manifest_path),
                   "current_cix_source_sha256": expected_source, "local_header_sha256": bound,
                   "quoted_include_arguments": list(_kernel_stage_quote_arguments(relative, stage))}


def _projection_size_limit(relative: str) -> int:
    """Return the reviewed cap for one projected translation unit."""
    if relative in CPPHECK_PROBE_V2_CONFIRMED_RELATIVES - {
            "rust/cix-native/adapters/blosc2/tests/blosc2_cix_contract.c"}:
        return CPPHECK_KERNEL_PROJECTED_TU_BYTES
    return CPPHECK_PROJECTED_TU_BYTES


def _projected_file_limit(limit: int = CPPHECK_PROJECTED_TU_BYTES) -> None:
    resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))


def _normalise_preprocessor_projection(body: bytes, *, kernel_gnu_typeof: bool = False) -> tuple[bytes, int, int, int]:
    """Preserve lexical content while normalising only known compiler-output syntax."""
    text = body.decode("utf-8")
    extensions = pragmas = typeofs = 0
    output: list[str] = []
    outside: list[str] = []

    def normalise_fragment(fragment: str) -> str:
        nonlocal extensions, pragmas, typeofs
        rendered: list[str] = []
        for line in fragment.splitlines(keepends=True):
            # Directives retain their complete lexical spelling: quoted operands
            # (including a filename containing `typeof`) are never token-rewritten.
            if line.lstrip().startswith("#"):
                line = re.sub(r'^# (\d+) ("[^"\n]*")[^\n]*$', r'#line \1 \2', line)
                line, omitted = re.subn(r"^#pragma GCC diagnostic[^\n]*", "", line)
                pragmas += omitted
                rendered.append(line)
                continue
            def remove_extension(match: re.Match) -> str:
                return " " * len(match.group())
            line, count = re.subn(r"(?<![A-Za-z0-9_])__extension__(?![A-Za-z0-9_])", remove_extension, line)
            extensions += count
            if kernel_gnu_typeof:
                line, count = re.subn(r"(?<![A-Za-z0-9_])typeof(?![A-Za-z0-9_])", "__typeof__", line)
                typeofs += count
            rendered.append(line)
        return "".join(rendered)

    def flush_outside() -> None:
        if outside:
            output.append(normalise_fragment("".join(outside)))
            outside.clear()

    index = 0
    while index < len(text):
        # Raw literals must precede ordinary quote handling.
        if text.startswith('R"', index):
            delimiter_end = text.find("(", index + 2, index + 19)
            if delimiter_end != -1:
                delimiter = text[index + 2:delimiter_end]
                end = text.find(")" + delimiter + '"', delimiter_end + 1)
                if end != -1:
                    end += len(delimiter) + 2
                    flush_outside(); output.append(text[index:end]); index = end; continue
        # Comments are opaque: directives and token rewrites cannot cross them.
        if text.startswith("//", index):
            end = text.find("\n", index)
            # A backslash-newline continues a line comment; retain every continued
            # line as opaque lexical content.
            while end != -1:
                # Translation phase 2 splices the last backslash even when
                # another backslash precedes it; this is not string escaping.
                if end == index or text[end - 1] != "\\":
                    break
                end = text.find("\n", end + 1)
            end = len(text) if end == -1 else end
            flush_outside(); output.append(text[index:end]); index = end; continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            end = len(text) if end == -1 else end + 2
            flush_outside(); output.append(text[index:end]); index = end; continue
        if text[index] in "\"'":
            quote, end = text[index], index + 1
            while end < len(text):
                if text[end] == "\\": end += 2
                elif text[end] == quote: end += 1; break
                else: end += 1
            # Keep directive strings with the directive, so #line conversion is whole-line.
            current_line = "".join(outside).rsplit("\n", 1)[-1]
            if current_line.lstrip().startswith("#"):
                outside.append(text[index:end])
            else:
                flush_outside(); output.append(text[index:end])
            index = end; continue
        outside.append(text[index]); index += 1
    flush_outside()
    return "".join(output).encode(), pragmas, extensions, typeofs

def project_cppcheck_translation_units(source: Path, selected: list[dict], out: Path,
                                      budget: EvidenceBudget) -> tuple[list[dict], list[dict]]:
    """Project the reviewed compiler-incompatible TUs with recorded build options."""
    context = load_module("cix_projection_context", Path(__file__).with_name("translation_context.py"))
    eligible = (CPPHECK_PROJECTED_RELATIVES | set(context.PROJECTABLE_RELATIVES)
                | CPPHECK_PROBE_V2_CONFIRMED_RELATIVES)
    candidates = [row for row in selected
                  if Path(row["file"]).resolve().relative_to(source).as_posix() in eligible]
    if not candidates:
        return selected, []
    projected_root = out / "cppcheck-projected"
    budget.mkdir(projected_root)
    projected_rows, receipts = [], []
    for index, row in enumerate(candidates):
        relative = Path(row["file"]).resolve().relative_to(source).as_posix()
        bound_inputs, context_evidence = {}, None
        if relative in context.PROJECTABLE_RELATIVES:
            recorded = context.load_recorded_inputs(source, row)
            bound_inputs = dict(recorded.qualified_inputs)
            context_evidence = dataclasses.asdict(recorded)
            if recorded.gaps:
                if relative != "rust/cix-native/adapters/squashfs/kernel/cix_profile_portable.c":
                    raise RuntimeError("recorded projection input gap: " + repr(recorded.gaps))
                # The old kernel build did not bind these individual headers.
                # Freeze their current identities for this NEW analysis action;
                # never describe them as evidence of the historical build.
                operands = context._forced_includes(row["arguments"])
                operands += context._macro_values(row["arguments"], "CIX_PORTABLE_PROFILE_SOURCE")
                bound_inputs = {str((Path(row["directory"]) / value).resolve()):
                                digest((Path(row["directory"]) / value).resolve()) for value in operands}
                context_evidence = {"kind": "NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF",
                                    "historical_gaps": list(recorded.gaps), "sha256": bound_inputs,
                                    "recorded_compiler": row}
                save(out / "kernel-analysis-inputs.json", context_evidence, budget)
            context.validate_translation_context(row, source, bound_inputs)
        if relative in CPPHECK_NEW_ANALYSIS_KERNEL_RELATIVES and context_evidence is None:
            # These raw Kbuild commands were selected by the context probe,
            # but the historical module build did not retain per-header
            # identities.  Bind the current forced headers only for this new,
            # isolated analysis action; do not present them as old-build proof.
            operands = context._forced_includes(row["arguments"])
            bound_inputs = {}
            for value in operands:
                input_path = (Path(row["directory"]) / value).resolve()
                if not input_path.is_file():
                    raise RuntimeError("kernel projection forced input is absent: " + str(input_path))
                bound_inputs[str(input_path)] = digest(input_path)
            context_evidence = {
                "kind": "NEW_ANALYSIS_INPUT_FREEZE_NOT_HISTORICAL_BUILD_PROOF",
                "historical_gaps": ["raw kernel forced-header identities were not retained by the module build"],
                "sha256": bound_inputs,
                "recorded_compiler": row,
            }
        stage_arguments = ()
        if relative in CPPHECK_NEW_ANALYSIS_KERNEL_RELATIVES:
            stage_inputs, stage_evidence = _kernel_stage_analysis_inputs(source, relative)
            bound_inputs.update(stage_inputs)
            context_evidence = {**(context_evidence or {}), "stage_context": stage_evidence}
            stage_arguments = _kernel_stage_quote_arguments(relative, source / "benchmark-work/native-rc-check-v1/kernel-module-v4/stage")
        projection_limit = _projection_size_limit(relative)
        reservation = f"cppcheck-projected-{index}"
        suffix = Path(row["file"]).suffix
        destination = projected_root / f"{index}{suffix}"
        # The compiler creates this file externally.  Admit its directory entry
        # before launch, then reserve the bounded payload it may replace it with.
        budget.write_bytes(destination, b"")
        budget.reserve(reservation, projection_limit)
        try:
            argv = _projected_command(row, destination, stage_arguments)
            removed_outputs = context.preprocess_command(row, destination).removed_dependency_outputs
            sandbox_argv = ["bwrap", "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/",
                            "--bind", str(projected_root), str(projected_root), "--", *argv]
            process = subprocess.Popen(sandbox_argv, cwd=row["directory"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       start_new_session=True, preexec_fn=lambda: _projected_file_limit(projection_limit))
            stdout, stderr = collect_bounded_pipes(process, budget, timeout=60, maximum=FAILURE_LOG_BYTES)
            if process.returncode:
                raise RuntimeError("compiler preprocessing failed for " + row["file"] + ": " + stderr.decode(errors="replace"))
            if stdout:
                raise RuntimeError("compiler preprocessing unexpectedly wrote stdout for " + row["file"])
            if not destination.is_file() or destination.stat().st_size > projection_limit:
                raise EvidenceLimitError("preprocessed translation unit exceeded its declared bound")
            if any(digest(Path(name)) != expected for name, expected in bound_inputs.items()):
                raise RuntimeError("projection input changed during compiler preprocessing")
            original = destination.read_bytes()
            normalised, pragmas, extensions, typeofs = _normalise_preprocessor_projection(
                original, kernel_gnu_typeof=relative == "rust/cix-native/adapters/squashfs/kernel/cix_squashfs_decompressor.c")
            budget.commit_external(reservation, destination, projection_limit)
            budget.write_bytes(destination, normalised)
            mapped = {**row, "file": str(destination),
                      "arguments": [str(destination) if not value.startswith("-") and
                                    (Path(row["directory"]) / value).resolve() == Path(row["file"]).resolve()
                                    else value for value in row["arguments"]
                                    if value not in removed_outputs]}
            projected_rows.append(mapped)
            receipts.append({"source": row["file"], "source_sha256": digest(Path(row["file"])),
                             "compiler_argv": argv, "directory": row["directory"], "projected": str(destination),
                             "sandbox_argv": sandbox_argv, "input_context": context_evidence,
                             "removed_dependency_outputs": list(removed_outputs),
                             "gcc_preprocessed_sha256": hashlib.sha256(original).hexdigest(),
                             "projected_sha256": digest(destination), "bytes": destination.stat().st_size,
                             "size_limit_bytes": projection_limit,
                             "line_markers": "GNU markers normalised to standard #line",
                             "gcc_diagnostic_pragmas_omitted": pragmas,
                             "gcc_extension_markers_omitted": extensions,
                             "gnu_typeof_spellings_normalised": typeofs})
        finally:
            budget.release(reservation)
    return _replace_projected_rows(selected, projected_rows, receipts), receipts


def _replace_projected_rows(selected: list[dict], projected: list[dict], receipts: list[dict]) -> list[dict]:
    replacements = {receipt["source"]: row for row, receipt in zip(projected, receipts)}
    return [replacements.get(row["file"], row) for row in selected]


def _overlay_expected_children(children: list[Path]) -> set[str]:
    return {child.name for child in children} | {"cppcheck"}


def cppcheck_header_overlay(out: Path, runtime: Path, budget: EvidenceBudget) -> tuple[Path, list[str], dict]:
    """Expose the packaged cfg leaf without hiding the host architecture headers."""
    architecture = Path("/usr/lib/x86_64-linux-gnu")
    alias = Path("/mnt")
    if not architecture.is_dir() or not alias.is_dir():
        raise RuntimeError("Cppcheck host-header bootstrap paths are unavailable")
    children = sorted(architecture.iterdir(), key=lambda path: path.name)
    overlay = budget.root / "cppcheck-arch-overlay"
    if not overlay.exists():
        budget.mkdir(overlay)
        reservation = "cppcheck-header-overlay"
        budget.reserve(reservation, (len(children) + 1) * EVIDENCE_ALLOCATION_BYTES)
        try:
            for child in children:
                if child.name != "cppcheck":
                    budget.symlink(overlay / child.name, alias / child.name)
            budget.symlink(overlay / "cppcheck", runtime / "usr/lib/x86_64-linux-gnu/cppcheck")
        finally:
            budget.release(reservation)
    expected = _overlay_expected_children(children)
    actual = {child.name for child in overlay.iterdir()}
    if actual != expected or not (overlay / "cppcheck").is_symlink():
        raise RuntimeError("Cppcheck host-header overlay is incomplete")
    mounts = ["--ro-bind", str(architecture), str(alias), "--ro-bind", str(overlay), str(architecture)]
    return overlay, mounts, {"host_architecture_alias": str(alias), "overlay": str(overlay),
                             "host_children": len(children), "only_added_leaf": "cppcheck",
                             "all_mounts_readonly": True}


def cppcheck(source: Path, files: list[str], out: Path, commands: list, budget: EvidenceBudget) -> None:
    enforce_evidence_budget(out)
    bubblewrap, executable, runtime, cfg = private_cppcheck_runtime()
    libdir = runtime / "usr/lib/x86_64-linux-gnu"
    filesdir = libdir / "cppcheck"
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(libdir)
    selected = [row for row in commands if Path(row["file"]).relative_to(source).as_posix() in files]
    selected, projections = project_cppcheck_translation_units(source, selected, out, budget)
    database = out / "compile_commands.cppcheck.json"
    save(database, selected, budget)
    if projections:
        save(out / "cppcheck-preprocessing.json", projections, budget)
    cppcheck_arguments = [str(executable), "--xml", "--xml-version=2", "--enable=warning,style,performance,portability,information",
                          "--platform=unix64", "--max-configs=12", "-j", "2", "--library=" + str(filesdir / "cfg/std.cfg"),
                          "--library=" + str(filesdir / "cfg/posix.cfg")]
    if selected:
        cppcheck_arguments.append("--project=" + str(database))
    else:
        cppcheck_arguments.extend(str(source / file) for file in files if Path(file).suffix in {".c", ".cpp", ".cc", ".cxx"})
    overlay, header_mounts, header_receipt = cppcheck_header_overlay(out, runtime, budget)
    # The host root and the header overlay are read-only.  The overlay preserves
    # every host architecture child through short /mnt aliases and contributes
    # only the staged Cppcheck configuration leaf.
    loader = libdir / "ld-linux-x86-64.so.2"
    arguments = [str(bubblewrap), "--die-with-parent", "--ro-bind", "/", "/", *header_mounts, "--",
                 str(loader), "--library-path", str(libdir), str(executable), *cppcheck_arguments[1:]]
    process = subprocess.Popen(arguments, cwd=source, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    stdout, stderr = collect_bounded_pipes(process, budget, timeout=3600)
    budget.write_bytes(out / "cppcheck.stdout", stdout)
    budget.write_bytes(out / "cppcheck.host.xml", stderr)
    save(out / "cppcheck-execution.json", {"argv": arguments, "cppcheck_argv": cppcheck_arguments,
         "private_runtime_overlay": {"source": str(runtime), "binary_destination": str(executable), "library_destination": str(libdir),
                                     "loader_destination": str(loader), "host_mutation": False, "header_overlay": header_receipt},
         "exit": process.returncode, "checked_translation_units": len(selected), "configuration_limit": 12}, budget)
    if process.returncode:
        raise RuntimeError("Cppcheck did not complete")
    report = ET.parse(out / "cppcheck.host.xml")
    for location in report.iter("location"):
        for key in ("file", "file0"):
            if key in location.attrib:
                file = Path(location.attrib[key])
                if file.is_absolute() and file.is_relative_to(source):
                    location.attrib[key] = "/usr/src/" + str(file.relative_to(source))
    rendered = ET.tostring(report.getroot(), encoding="utf-8", xml_declaration=True)
    budget.write_bytes(out / "cppcheck.xml", rendered)
    enforce_evidence_budget(out)


def request(h, base: str, password: str, endpoint: str, fields=None):
    payload = urllib.parse.urlencode(fields).encode() if fields is not None else None
    return h.api(base, endpoint, "admin", password, payload)


def profile(h, base: str, password: str, raw: Path, budget: EvidenceBudget) -> None:
    repositories = request(h, base, password, "/api/rules/repositories?language=cxx")
    save(raw / "rule-repositories.json", repositories, budget)
    selected = [row["key"] for row in repositories["repositories"]
                if row["key"] == "cxx" or "cppcheck" in row["key"].lower()]
    if not any("cppcheck" in key for key in selected) or "cxx" not in selected:
        raise RuntimeError("CXX native/Cppcheck rule repositories are missing")
    created = request(h, base, password, "/api/qualityprofiles/create", {"language": "cxx", "name": "CIX CXX and Cppcheck"})
    key = created["profile"]["key"]
    activated = request(h, base, password, "/api/qualityprofiles/activate_rules", {"targetKey": key, "repositories": ",".join(selected)})
    request(h, base, password, "/api/qualityprofiles/set_default", {"language": "cxx", "qualityProfile": "CIX CXX and Cppcheck"})
    active = request(h, base, password, "/api/rules/search?activation=true&qprofile=" + urllib.parse.quote(key) + "&ps=1")
    if active.get("total", active.get("paging", {}).get("total", 0)) < 1:
        raise RuntimeError("CXX profile has no active rules")
    save(raw / "profile.json", {"created": created, "activated": activated, "active_rules": active}, budget)


def collect(h, base: str, key: str, task: str, password: str, out: Path, budget: EvidenceBudget) -> None:
    """Bounded local replacement for the general scan helper's unbounded collector."""
    for _ in range(90):
        receipt = request(h, base, password, f"/api/ce/task?id={urllib.parse.quote(task)}")
        status = receipt.get("task", {}).get("status")
        if status in {"SUCCESS", "FAILED", "CANCELED"}:
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"compute engine did not finish for {key}")
    save(out / "ce-task.json", receipt, budget)
    if status != "SUCCESS":
        raise RuntimeError(f"compute engine failed for {key}: {status}")
    issues = request(h, base, password, f"/api/issues/search?componentKeys={urllib.parse.quote(key)}&resolved=false&ps=500")
    total = issues["paging"]["total"]
    for page in range(2, (total + 499) // 500 + 1):
        issues["issues"].extend(request(
            h, base, password,
            f"/api/issues/search?componentKeys={urllib.parse.quote(key)}&resolved=false&ps=500&p={page}")["issues"])
    gate = request(h, base, password, f"/api/qualitygates/project_status?projectKey={urllib.parse.quote(key)}")
    save(out / "issues.json", issues, budget)
    save(out / "quality-gate.json", gate, budget)


def analysis_coverage_gaps(issues: list[dict], scanner_log: str,
                           cppcheck_diagnostics: dict[str, int]) -> dict:
    """Return parser/preprocessor findings which prevent a clean analysis claim.

    The result deliberately preserves the source of each finding.  In
    particular, a vendor project's findings are not folded into first-party
    projects or silently ignored merely because the source is third-party.
    """
    sonar_recovery = sum(
        row.get("rule") == "cxx:ParsingErrorRecovery" for row in issues
    )
    scanner_syntax = sum(
        int(match.group(1))
        for match in re.finditer(r"\b(\d+)\s+syntax error\(s\)\s+detected\b",
                                 scanner_log, re.IGNORECASE)
    )
    cppcheck = {
        diagnostic: max(
            int(cppcheck_diagnostics.get(diagnostic, 0)),
            sum(row.get("rule") == "cppcheck:" + diagnostic for row in issues),
        )
        for diagnostic in sorted(ANALYSIS_COVERAGE_CPPHECK_IDS)
    }
    return {
        "cxx_parsing_error_recovery": sonar_recovery,
        "scanner_syntax_errors": scanner_syntax,
        "cppcheck_configuration_errors": {
            diagnostic: count for diagnostic, count in cppcheck.items() if count
        },
    }


def has_analysis_coverage_gaps(gaps: dict) -> bool:
    """Keep the release gate explicit rather than relying on truthy containers."""
    return bool(gaps["cxx_parsing_error_recovery"]
                or gaps["scanner_syntax_errors"]
                or gaps["cppcheck_configuration_errors"])


def bounded_scanner(h, base: str, password: str, token: str, envfile: Path, parent: str,
                    name: str, source: Path, out: Path, budget: EvidenceBudget, include_mounts=None) -> str:
    """Run the scanner without a writable Docker layer or unbounded cache paths."""
    scanner = "cix-hygiene-scanner-" + name
    log_path = out / "scanner.log"
    report_task_path = out / "report-task.txt"
    # Docker removes tmpfs contents with the stopped container.  Bind one
    # pre-created evidence file.  The scanner writes neither it nor a report
    # directory: a capped log sink writes the log, then the shell copies the
    # tmpfs metadata only after a one-byte-over-limit check.
    budget.reserve("scanner-" + name, SCANNER_EVIDENCE_BYTES)
    budget.write_bytes(log_path, b"")
    command = ("set -o pipefail; sonar-scanner -Dsonar.scanner.skipJreProvisioning=true "
               "-Dsonar.projectBaseDir=/usr/src -Dproject.settings=/out/properties "
               "-Dsonar.scanner.metadataFilePath=/tmp/report-task.txt 2>&1 "
               "| (ulimit -f 8192; cat > /scanner-log); statuses=(${PIPESTATUS[@]}); "
               "metadata_bytes=0; metadata_over_limit=0; if test -f /tmp/report-task.txt; then "
               "metadata_bytes=$(head -c 65537 /tmp/report-task.txt | wc -c); "
               "test \"$metadata_bytes\" -le 65536 || metadata_over_limit=1; fi; "
               "printf '\\n--CIX-SCANNER-STATUS--\\nscanner=%s\\nsink=%s\\nmetadata_bytes=%s\\nmetadata_over_limit=%s\\n--CIX-SCANNER-REPORT-TASK--\\n' "
               "\"${statuses[0]}\" \"${statuses[1]}\" \"$metadata_bytes\" \"$metadata_over_limit\" >> /scanner-log; "
               "test \"$metadata_bytes\" -eq 0 || head -c 65537 /tmp/report-task.txt >> /scanner-log; "
               "exit \"${statuses[0]}\"")
    execution = {"contract": scanner_writable_contract(), "argv": command,
                 "log_path": str(log_path), "report_task_path": str(report_task_path),
                 "docker_cp": {"used": False, "status": "not_attempted",
                               "reason": "stopped-container tmpfs was unrecoverable in probe-v6; bounded file binds retain both artifacts before exit"}}
    try:
        mounts = []
        for root, destination in include_mounts or []:
            mounts.extend(["-v", f"{root}:{destination}:ro"])
        h.docker_run(scanner, h.SCANNER_IMAGE, h.SCANNER_MEMORY, parent, [
            "--network", "host", "--read-only", "--log-driver", "none",
            "--tmpfs", f"/tmp:rw,exec,size={PROBE_SCANNER_TEMP_BYTES}",
            "--env", "HOME=/tmp", "--env", "XDG_CONFIG_HOME=/tmp",
            "--env", "SONAR_USER_HOME=/tmp/.sonar", "--env", "SCANNER_WORKDIR_PATH=/tmp/.scannerwork",
            "--env-file", str(envfile), "-v", f"{source}:/usr/src:ro", "-v", f"{out}:/out:ro",
            "-v", f"{log_path}:/scanner-log:rw",
            *mounts, "-w", "/usr/src", "--entrypoint", "bash"], ["-c", command])
        waited = subprocess.run(["docker", "wait", scanner], check=False, text=True, capture_output=True, timeout=900)
        execution["docker_wait"] = {"exit": waited.returncode, "stdout": waited.stdout, "stderr": waited.stderr}
        if waited.returncode:
            save(out / "scanner-execution.json", execution, budget, failure=True)
            raise RuntimeError("docker wait failed while preserving bounded scanner evidence")
        code = waited.stdout.strip()
        execution["exit"] = code
        execution["log_bytes"] = log_path.stat().st_size
        if execution["log_bytes"] > SCANNER_EVIDENCE_BYTES:
            save(out / "scanner-execution.json", execution, budget, failure=True)
            raise RuntimeError("scanner evidence file exceeded its declared bound")
        evidence = log_path.read_text(errors="replace")
        marker = "\n--CIX-SCANNER-STATUS--\n"
        if marker not in evidence:
            save(out / "scanner-execution.json", execution, budget, failure=True)
            raise RuntimeError("bounded scanner evidence lacks sink/scanner status")
        scanner_log, status = evidence.rsplit(marker, 1)
        status, delimiter, report_task = status.partition("--CIX-SCANNER-REPORT-TASK--\n")
        fields = dict(line.split("=", 1) for line in status.splitlines() if "=" in line)
        execution["pipeline_status"] = fields
        if not delimiter or fields.get("metadata_over_limit") != "0" or fields.get("sink") != "0":
            save(out / "scanner-execution.json", execution, budget, failure=True)
            raise RuntimeError("scanner log-sink or report metadata did not satisfy its declared bound")
        budget.commit_external("scanner-" + name, log_path, SCANNER_EVIDENCE_BYTES)
        budget.write_text(log_path, h.scrub(scanner_log, [password, token]))
        budget.write_text(report_task_path, h.scrub(report_task, [password, token]))
        budget.write_text(out / "scanner-exit.txt", code + "\n")
        save(out / "scanner-execution.json", execution, budget)
        if code != "0":
            raise RuntimeError("Sonar scanner failed for " + name)
        task = re.search(r"ceTaskId=([^\s]+)", report_task_path.read_text())
        if not task:
            task = re.search(r"api/ce/task\?id=([^\s]+)", log_path.read_text())
        if not task:
            raise RuntimeError("Sonar scanner did not report a compute task for " + name)
        return task.group(1)
    finally:
        h.stop(scanner)


def bounded_server_log(server: str, budget: EvidenceBudget, h, secrets_to_scrub: list[str | None]) -> str:
    """Retain at most one small tail from the server's bounded tmpfs logs."""
    command = ["docker", "exec", server, "sh", "-c",
               "find /opt/sonarqube/logs -type f -exec tail -c 65536 {} + 2>/dev/null | head -c 65536"]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    stdout, stderr = collect_bounded_pipes(process, budget, timeout=30, maximum=FAILURE_LOG_BYTES, failure=True)
    if process.returncode:
        return h.scrub("server log tail unavailable: " + stderr.decode(errors="replace"), secrets_to_scrub)
    return h.scrub(stdout.decode(errors="replace"), secrets_to_scrub)


def scan(h, base: str, password: str, token: str, envfile: Path, parent: str,
         name: str, source: Path, files: list[str], commands: list, out: Path,
         budget: EvidenceBudget) -> dict:
    budget.mkdir(out)
    key = "cix-cxx-" + name
    cppcheck(source, files, out, commands, budget)
    mapped, external_mounts, include_evidence = rebase_include_commands(commands, source)
    save(out / "include-operand-mappings.json", include_evidence, budget)
    save(out / "compile_commands.json", mapped, budget)
    budget.write_text(out / "properties", "\n".join([
        f"sonar.projectKey={key}", "sonar.sources=" + ",".join(files), "sonar.sourceEncoding=UTF-8",
        "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true", "sonar.working.directory=/tmp/.scannerwork",
        "sonar.cxx.file.suffixes=" + ",".join(sorted(SUFFIXES)), "sonar.cxx.cppcheck.reportPaths=/out/cppcheck.xml",
        "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json",
        "sonar.cxx.jsonCompilationDatabase.analyzeOnlyContainedFiles=false", ""]))
    task = bounded_scanner(h, base, password, token, envfile, parent, "cxx-" + name, source, out,
                           budget, external_mounts)
    collect(h, base, key, task, password, out, budget)
    components, page = [], 1
    while True:
        result = request(h, base, password, f"/api/components/tree?component={key}&qualifiers=FIL&ps=500&p={page}")
        components.extend(result["components"])
        if len(components) >= result["paging"]["total"]:
            break
        page += 1
    save(out / "indexed-files.json", components, budget)
    log = (out / "scanner.log").read_text()
    indexed = validate_indexed(files, components, log)
    issues = json.loads((out / "issues.json").read_text())["issues"]
    if name == "probe" and not any("nullpointer" in row["rule"].lower() for row in issues):
        raise RuntimeError("known null-pointer canary was not imported as a Sonar issue")
    diagnostics = [line for line in log.splitlines()
                   if re.search(r"parse error|parsing error|unable to parse|cannot parse|syntax error\(s\)", line, re.I)]
    errors = [row.attrib for row in ET.parse(out / "cppcheck.xml").iter("error")]
    cppcheck_diagnostics = dict(collections.Counter(row["id"] for row in errors))
    coverage_gaps = analysis_coverage_gaps(issues, log, cppcheck_diagnostics)
    return {"status": "SCANNED", "expected_files": len(files), "indexed_cxx_files": len(indexed),
            "issues": len(issues), "rules": dict(collections.Counter(row["rule"] for row in issues)),
            "parser_diagnostics": diagnostics, "cppcheck_diagnostics": cppcheck_diagnostics,
            "analysis_coverage_gaps": coverage_gaps,
            "quality_gate": json.loads((out / "quality-gate.json").read_text())}


def wait_server_or_exit(h, base: str, password: str, server: str) -> None:
    """Wait for readiness, but preserve a simple startup exit without a long poll."""
    for _ in range(90):
        state = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", server],
                               check=False, capture_output=True, text=True, timeout=10)
        if state.returncode or state.stdout.strip() != "true":
            raise RuntimeError("Sonar server exited before becoming ready")
        marker = subprocess.run(["docker", "exec", server, "sh", "-c",
                                 "test ! -f /opt/sonarqube/logs/cix-startup-exit || cat /opt/sonarqube/logs/cix-startup-exit"],
                                check=False, text=True, capture_output=True, timeout=10)
        if marker.returncode == 0 and marker.stdout.strip():
            raise RuntimeError("Sonar server startup exited before readiness: " + marker.stdout.strip())
        try:
            if h.api(base, "/api/system/status", "admin", "admin").get("status") == "UP":
                h.api(base, "/api/users/change_password", "admin", "admin", urllib.parse.urlencode({
                    "login": "admin", "previousPassword": "admin", "password": password,
                }).encode())
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("Sonar server did not become ready")


def execute(prepared: Path, out: Path, source: Path, parent: str) -> None:
    h = load_module("cix_sonar_runtime", HYGIENE / "run_scan.py")
    plan = json.loads((prepared / "plan.json").read_text())
    if inventory(source) != plan["scopes"]:
        raise RuntimeError("source no longer matches prepared manifest")
    missing = plan.get("unconfigured_translation_units", [])
    if missing:
        raise RuntimeError("CXX scan blocked: current source has translation units without an exact compiler receipt: " +
                           ", ".join(missing))
    for name, (_, expected) in PACKAGES.items():
        if digest(TOOLS / name) != expected:
            raise RuntimeError("tool package changed: " + name)
    bubblewrap, _, runtime, _ = private_cppcheck_runtime()
    budget = EvidenceBudget(out)
    budget.mkdir(out)
    raw = out / "raw"; budget.mkdir(raw)
    save(raw / "scanner-writable-contract.json", scanner_writable_contract(), budget)
    save(raw / "tool-identities.json", {str(p): digest(p) for p in (
        Path(__file__), Path(__file__).with_name("include_context.py"),
        Path(__file__).with_name("translation_context.py"),
        HYGIENE / "run_scan.py", HYGIENE / "schedule_scan.py",
        bubblewrap, runtime / "manifest.json", runtime / "usr/bin/cppcheck",
        TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu/libtinyxml2.so.10.0.0")}, budget)
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        budget.write_text(raw / (kind + "-image-inspect.json"), h.image_receipt(image))
    save(raw / "temporary-accounting.json", probe_temporary_accounting(), budget)
    empty_core_extensions = prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)
    base, server = "http://127.0.0.1:9017", "cix-cxx-sonarqube"
    password = "Aa1!" + secrets.token_urlsafe(32)
    token = None
    envfile = raw / ".scanner-env"
    results = {"status": "STARTED", "analyzer": "SonarOpenCommunity CXX 2.3.0.1496 + Cppcheck 2.13.0",
               "plan_sha256": digest(prepared / "plan.json"), "projects": {}}
    server_options, server_command, server_receipt = server_start_contract()
    save(raw / "server-start-contract.json", server_receipt, budget)
    try:
        h.docker_run(server, h.SERVER_IMAGE, h.SERVER_MEMORY, parent, [
            "-p", "127.0.0.1:9017:9000", *server_options,
            "-v", f"{empty_core_extensions}:/opt/sonarqube/lib/extensions:ro",
            "-v", f"{TOOLS / 'sonar-cxx-plugin-2.3.0.1496.jar'}:/opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar:ro"],
                     server_command)
        wait_server_or_exit(h, base, password, server)
        languages = request(h, base, password, "/api/languages/list")
        save(raw / "languages.json", languages, budget)
        save(raw / "plugins.json", request(h, base, password, "/api/plugins/installed"), budget)
        if "cxx" not in {row["key"] for row in languages["languages"]}:
            raise RuntimeError("installed plugin did not register CXX")
        profile(h, base, password, raw, budget)
        token = request(h, base, password, "/api/user_tokens/generate", {"name": "cix-cxx-repair"})["token"]
        credentials = f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"
        budget.admit(envfile, len(credentials.encode()))
        fd = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(credentials)
        probe = out / "probe-source"; budget.mkdir(probe)
        budget.write_text(probe / "probe.cpp", "int main() { int *p = nullptr; return *p; }\n")
        results["probe"] = scan(h, base, password, token, envfile, parent, "probe", probe, ["probe.cpp"], [], out / "probe", budget)
        commands = json.loads((prepared / "compile_commands.host.json").read_text())
        for name, scope in plan["scopes"].items():
            results["projects"][name] = scan(h, base, password, token, envfile, parent, name, source,
                [row["path"] for row in scope["files"]], commands, out / name, budget)
            save(out / "result.json", results, budget)
        if inventory(source) != plan["scopes"]:
            raise RuntimeError("source changed during scan")
        gaps = {name: result["analysis_coverage_gaps"]
                for name, result in results["projects"].items()
                if has_analysis_coverage_gaps(result["analysis_coverage_gaps"])}
        results["status"] = "ANALYSIS_GAPS" if gaps else "SCANNED_WITH_RECORDED_FINDINGS"
        results["analysis_gaps"] = gaps
        if gaps:
            raise RuntimeError("analysis coverage gaps require correction: " + ", ".join(gaps))
    except Exception as error:
        results["status"] = "FAILED"
        results["error"] = h.scrub(str(error), [password, token])
        raise
    finally:
        try:
            if token:
                try:
                    request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-cxx-repair"})
                except Exception:
                    results["token_revocation"] = "failed; ephemeral server removed"
            if envfile.exists():
                envfile.unlink()
            budget.write_text(raw / "server.log", bounded_server_log(server, budget, h, [password, token]), failure=True)
        finally:
            try:
                h.stop(server)
            finally:
                save_terminal_result(out / "result.json", results, budget)


def scan_probe(h, base: str, password: str, token: str, envfile: Path, parent: str, out: Path,
               budget: EvidenceBudget) -> dict:
    """Run the fixture with the probe-only scanner tmpfs cap."""
    budget.mkdir(out)
    source = out / "probe-source"
    budget.mkdir(source)
    budget.write_text(source / "probe.cpp", "int main() { int *p = nullptr; return *p; }\n")
    cppcheck(source, ["probe.cpp"], out, [], budget)
    save(out / "compile_commands.json", [], budget)
    key = "cix-cxx-probe"
    budget.write_text(out / "properties", "\n".join([
        f"sonar.projectKey={key}", "sonar.sources=probe.cpp", "sonar.sourceEncoding=UTF-8",
        "sonar.scm.disabled=true", "sonar.scm.exclusions.disabled=true", "sonar.working.directory=/tmp/.scannerwork",
        "sonar.cxx.file.suffixes=" + ",".join(sorted(SUFFIXES)), "sonar.cxx.cppcheck.reportPaths=/out/cppcheck.xml",
        "sonar.cxx.jsonCompilationDatabase=/out/compile_commands.json", ""]))
    task = bounded_scanner(h, base, password, token, envfile, parent, "cxx-probe", source, out, budget)
    collect(h, base, key, task, password, out, budget)
    components = request(h, base, password, f"/api/components/tree?component={key}&qualifiers=FIL&ps=500&p=1")["components"]
    save(out / "indexed-files.json", components, budget)
    indexed = validate_indexed(["probe.cpp"], components, (out / "scanner.log").read_text())
    issues = json.loads((out / "issues.json").read_text())["issues"]
    if not any("nullpointer" in row["rule"].lower() for row in issues):
        raise RuntimeError("known null-pointer canary was not imported as a Sonar issue")
    errors = [row.attrib for row in ET.parse(out / "cppcheck.xml").iter("error")]
    return {"status": "SCANNED", "expected_files": 1, "indexed_cxx_files": len(indexed),
            "issues": len(issues), "rules": dict(collections.Counter(row["rule"] for row in issues)),
            "cppcheck_diagnostics": dict(collections.Counter(row["id"] for row in errors)),
            "quality_gate": json.loads((out / "quality-gate.json").read_text())}


def execute_probe(out: Path, parent: str) -> None:
    """Exercise the installed CXX plugin without accepting any product coverage."""
    h = load_module("cix_sonar_runtime", HYGIENE / "run_scan.py")
    for name, (_, expected) in PACKAGES.items():
        if digest(TOOLS / name) != expected:
            raise RuntimeError("tool package changed: " + name)
    bubblewrap, _, runtime, _ = private_cppcheck_runtime()
    budget = EvidenceBudget(out)
    budget.mkdir(out)
    raw = out / "raw"; budget.mkdir(raw)
    save(raw / "temporary-accounting.json", probe_temporary_accounting(), budget)
    save(raw / "scanner-writable-contract.json", scanner_writable_contract(), budget)
    save(raw / "tool-identities.json", {str(p): digest(p) for p in (
        Path(__file__), HYGIENE / "run_scan.py", TOOLS / "sonar-cxx-plugin-2.3.0.1496.jar", bubblewrap,
        runtime / "manifest.json", runtime / "usr/bin/cppcheck",
        TOOLS / "cppcheck/usr/lib/x86_64-linux-gnu/libtinyxml2.so.10.0.0")}, budget)
    for kind, image in (("server", h.SERVER_IMAGE), ("scanner", h.SCANNER_IMAGE)):
        budget.write_text(raw / (kind + "-image-inspect.json"), h.image_receipt(image))
    empty_core_extensions = prepare_cxx_only_extensions(raw, h.SERVER_IMAGE, budget)
    base, server = "http://127.0.0.1:9017", "cix-cxx-sonarqube-probe"
    password = "Aa1!" + secrets.token_urlsafe(32)
    token = None
    envfile = raw / ".scanner-env"
    results = {"status": "STARTED", "kind": "CXX_REGISTRATION_AND_NULL_POINTER_PROBE",
               "analyzer": "SonarOpenCommunity CXX 2.3.0.1496 + Cppcheck 2.13.0",
               "plugin_scope": "CXX only; immutable built-in language extensions omitted by recorded read-only overlay"}
    server_options, server_command, server_receipt = server_start_contract()
    save(raw / "server-start-contract.json", server_receipt, budget)
    try:
        h.docker_run(server, h.SERVER_IMAGE, h.SERVER_MEMORY, parent, [
            "-p", "127.0.0.1:9017:9000", *server_options,
            "-v", f"{empty_core_extensions}:/opt/sonarqube/lib/extensions:ro",
            "-v", f"{TOOLS / 'sonar-cxx-plugin-2.3.0.1496.jar'}:/opt/sonarqube/extensions/plugins/sonar-cxx-plugin.jar:ro"],
                     server_command)
        wait_server_or_exit(h, base, password, server)
        languages = request(h, base, password, "/api/languages/list")
        save(raw / "languages.json", languages, budget)
        save(raw / "plugins.json", request(h, base, password, "/api/plugins/installed"), budget)
        if "cxx" not in {row["key"] for row in languages["languages"]}:
            raise RuntimeError("installed plugin did not register CXX")
        profile(h, base, password, raw, budget)
        token = request(h, base, password, "/api/user_tokens/generate", {"name": "cix-cxx-probe"})["token"]
        credentials = f"SONAR_HOST_URL={base}\nSONAR_TOKEN={token}\n"
        budget.admit(envfile, len(credentials.encode()))
        fd = os.open(envfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(credentials)
        results["probe"] = scan_probe(h, base, password, token, envfile, parent, out / "probe", budget)
        results["status"] = "PROBE_PASSED_NOT_PRODUCT_SCAN"
    except Exception as error:
        results["status"] = "FAILED"
        results["error"] = h.scrub(str(error), [password, token])
        raise
    finally:
        try:
            if token:
                try:
                    request(h, base, password, "/api/user_tokens/revoke", {"name": "cix-cxx-probe"})
                except Exception:
                    results["token_revocation"] = "failed; ephemeral server removed"
            if envfile.exists():
                envfile.unlink()
            budget.write_text(raw / "server.log", bounded_server_log(server, budget, h, [password, token]), failure=True)
        finally:
            try:
                h.stop(server)
            finally:
                save_terminal_result(out / "result.json", results, budget)


def run(prepared: Path, out: Path) -> None:
    require_stopped_confirmation(SUMMARY)
    if out.exists():
        raise RuntimeError("refusing to overwrite a scan attempt; use a new output directory")
    s = load_module("cix_sonar_scheduler", HYGIENE / "schedule_scan.py")
    scheduler = s.WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=s.AGGREGATE_MEMORY, max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True)
    parent, anchor = "cix-cxx-hygiene.slice", "cix-cxx-hygiene-anchor"
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        leases = scheduler._lease_cores([{"physical_core": [s._core(cpu) for cpu in s.CPUS]}])
        try:
            assert_benchmark_idle()
            s._make_slice(parent, anchor)
            receipt = s._slice_receipt(parent); s._verify_slice(receipt)
            # Put this process (including Cppcheck) in the same aggregate slice.
            command = ["sudo", "-n", "systemd-run", "--uid", str(os.getuid()), "--gid", str(os.getgid()),
                       "--wait", "--pipe", "--collect", "--slice", parent, sys.executable, str(Path(__file__).resolve()),
                       "worker", "--prepared", str(prepared), "--out", str(out)]
            result = subprocess.run(command, timeout=21600)
            if out.exists():
                EvidenceBudget(out).write_text(out / "slice-receipt.txt", receipt)
            if result.returncode:
                raise RuntimeError("CXX scan failed; retain evidence and fix before claiming completion")
        finally:
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True)
            for lease in leases:
                lease.close()


def probe(out: Path) -> None:
    """Run only the deliberate CXX fixture under the ordinary hygiene guard."""
    require_stopped_confirmation(SUMMARY)
    if out.exists():
        raise RuntimeError("refusing to overwrite a probe attempt; use a new output directory")
    probe_temporary_accounting()
    s = load_module("cix_sonar_scheduler", HYGIENE / "schedule_scan.py")
    scheduler = s.WaveScheduler(ROOT, max_jobs=1, max_memory_bytes=s.AGGREGATE_MEMORY, max_temp_bytes=4_000_000_000)
    scheduler.state.mkdir(exist_ok=True)
    parent, anchor = "cix-cxx-hygiene.slice", "cix-cxx-hygiene-anchor"
    with scheduler._wave_lock_path().open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        leases = scheduler._lease_cores([{"physical_core": [s._core(cpu) for cpu in s.CPUS]}])
        try:
            assert_benchmark_idle()
            s._make_slice(parent, anchor)
            receipt = s._slice_receipt(parent); s._verify_slice(receipt)
            command = ["sudo", "-n", "systemd-run", "--uid", str(os.getuid()), "--gid", str(os.getgid()),
                       "--wait", "--pipe", "--collect", "--slice", parent, sys.executable, str(Path(__file__).resolve()),
                       "probe-worker", "--out", str(out)]
            result = subprocess.run(command, timeout=21600)
            if out.exists():
                EvidenceBudget(out).write_text(out / "slice-receipt.txt", receipt)
            if result.returncode:
                raise RuntimeError("CXX registration probe failed; retain evidence and fix before a product scan")
        finally:
            subprocess.run(["sudo", "-n", "systemctl", "stop", anchor], check=False, capture_output=True)
            for lease in leases:
                lease.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "prepare", "run", "worker", "probe", "probe-worker"))
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.action == "provision":
        provision()
    elif args.action == "prepare":
        prepare(args.source.resolve(), args.out.resolve())
    elif args.action == "run":
        run(args.prepared.resolve(), args.out.resolve())
    elif args.action == "probe":
        probe(args.out.resolve())
    elif args.action == "probe-worker":
        parent = "cix-cxx-hygiene.slice"
        if parent not in Path('/proc/self/cgroup').read_text():
            raise RuntimeError("probe worker is outside the reserved aggregate slice")
        require_stopped_confirmation(SUMMARY)
        execute_probe(args.out.resolve(), parent)
    else:
        # Worker may only be entered through the parent holding the global lease.
        parent = "cix-cxx-hygiene.slice"
        if parent not in Path('/proc/self/cgroup').read_text():
            raise RuntimeError("worker is outside the reserved aggregate slice")
        require_stopped_confirmation(SUMMARY)
        plan = json.loads((args.prepared / "plan.json").read_text())
        execute(args.prepared.resolve(), args.out.resolve(), Path(plan["source"]), parent)


if __name__ == "__main__":
    main()
