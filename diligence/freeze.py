"""Freeze SHA-256 hashes for prompts, fixtures, manifests, and scorers."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diligence import BASELINE_COMMIT, __version__
from diligence.constants import (
    CANARIES_PATH,
    FIXTURES_DIR,
    PACKAGE_ROOT,
    PROMPTS_DIR,
    REPO_ROOT,
    TASKS_DIR,
)


def _sha256_file(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def collect_freeze_entries() -> list[dict[str, Any]]:
    paths: list[Path] = [
        TASKS_DIR / "development.json",
        TASKS_DIR / "holdout.json",
        PACKAGE_ROOT / "scorers" / "__init__.py",
        FIXTURES_DIR / "bitcoin_rpc_mempool.json",
        CANARIES_PATH,
    ]
    paths.extend(sorted(PROMPTS_DIR.glob("btc-*.md")))
    return [_sha256_file(p) for p in paths]


def build_freeze_manifest() -> dict[str, Any]:
    entries = collect_freeze_entries()
    return {
        "frozen_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "baseline_commit": BASELINE_COMMIT,
        "diligence_version": __version__,
        "purpose": (
            "Immutable pre-model freeze of prompts, fixtures, task manifests, "
            "and scorers for Phase 2 overnight runs."
        ),
        "entry_count": len(entries),
        "entries": entries,
        "aggregate_sha256": hashlib.sha256(
            "\n".join(f"{e['path']}:{e['sha256']}" for e in entries).encode("utf-8")
        ).hexdigest(),
    }


def write_freeze_manifest(dest: Path | None = None) -> dict[str, Any]:
    manifest = build_freeze_manifest()
    out = dest or (REPO_ROOT / "docs" / "catalyst-halo" / "freeze-hashes.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
