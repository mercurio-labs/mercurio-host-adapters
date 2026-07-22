#!/usr/bin/env python3
"""Generate the checksum and target manifest consumed by Mercurio VS Code."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def target_for_wheel(filename: str) -> str:
    lowered = filename.lower()
    if "win_amd64" in lowered:
        return "win32-x64"
    if "win_arm64" in lowered:
        return "win32-arm64"
    if "macosx" in lowered and "arm64" in lowered:
        return "darwin-arm64"
    if "macosx" in lowered and "x86_64" in lowered:
        return "darwin-x64"
    if ("manylinux" in lowered or "musllinux" in lowered) and "aarch64" in lowered:
        return "linux-arm64"
    if ("manylinux" in lowered or "musllinux" in lowered) and "x86_64" in lowered:
        return "linux-x64"
    raise ValueError(f"unsupported wheel platform: {filename}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    wheels = sorted(args.dist.glob("*.whl"))
    if not wheels:
        raise SystemExit("no wheel artifacts found")
    artifacts = []
    targets = set()
    for wheel in wheels:
        target = target_for_wheel(wheel.name)
        if target in targets:
            raise SystemExit(f"multiple wheels map to target {target}")
        targets.add(target)
        artifacts.append(
            {
                "filename": wheel.name,
                "sha256": sha256(wheel),
                "targets": [target],
                "url": f"{args.base_url.rstrip('/')}/{wheel.name}",
            }
        )

    manifest = {
        "schemaVersion": 1,
        "package": "mercurio-sysml",
        "version": args.version,
        "requiresPython": ">=3.10",
        "artifacts": artifacts,
    }
    args.output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
