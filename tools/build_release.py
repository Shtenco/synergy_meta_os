#!/usr/bin/env python3
"""Build and verify a byte-reproducible v31 source/evidence ZIP."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
import zipfile
from pathlib import Path


PREFIX = "SYNERGY_META_OS_v31_SIGNED_DURABLE_SUPERVISOR_RC"
SKIP_PARTS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".venv", "__pycache__"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_files(root: Path) -> list[Path]:
    result = []
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_PARTS for part in relative.parts) or path.suffix == ".pyc":
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix())


def zip_info(name: str, executable: bool) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    mode = 0o100755 if executable else 0o100644
    info.external_attr = mode << 16
    info.flag_bits |= 0x800
    return info


def build(root: Path, output: Path) -> tuple[str, int]:
    payloads: list[tuple[str, bytes, bool]] = []
    for path in source_files(root):
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        executable = relative.startswith("tools/") and relative.endswith(".py")
        payloads.append((f"{PREFIX}/{relative}", data, executable))

    manifest = "".join(f"{digest(data)}  {name}\n" for name, data, _ in payloads).encode("utf-8")
    payloads.append((f"{PREFIX}/RELEASE_MANIFEST.sha256", manifest, False))

    output.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, data, executable in payloads:
                archive.writestr(zip_info(name, executable), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(temporary, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"ZIP CRC verification failed at {bad}")
            for name, data, _ in payloads:
                if archive.read(name) != data:
                    raise RuntimeError(f"ZIP read-back mismatch at {name}")
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return digest(output.read_bytes()), len(payloads)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent
    sha256, entries = build(root, args.output.resolve())
    print(f"SYNERGY_META_OS_V31_RELEASE_PASS entries={entries} sha256={sha256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
