"""Freeze sat-hunt benchmark input hashes before model-backed runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def build_freeze_manifest(
    *,
    derived_set_sha256: str,
    fixture_sha256: str,
    selected_model: str | None = None,
    harness_hash: str | None = None,
    toolkit_hash: str | None = None,
) -> dict[str, Any]:
    files = {
        "benchmark.json": ROOT / "benchmark.json",
        "attribution-sources.json": ROOT / "attribution-sources.json",
        "attribution-derived-meta.json": ROOT / "attribution-derived-meta.json",
        "development.json": ROOT / "development.json",
        "development_tasks.json": ROOT / "development_tasks.json",
        "heldout.json": ROOT / "heldout.json",
        "ordinal.py": ROOT / "ordinal.py",
        "score.py": ROOT / "score.py",
        "attribution.py": ROOT / "attribution.py",
        "fixtures.py": ROOT / "fixtures.py",
        "scorers.py": ROOT / "scorers.py",
        "tasks.py": ROOT / "tasks.py",
        "fixture_deterministic_v1": ROOT / "fixtures" / "deterministic_v1.json",
        "final_exam_prompt": ROOT / "prompts" / "final-exam.md",
        "agent_runtime": ROOT / "agent" / "runtime.py",
        "agent_tools": ROOT / "agent" / "tools.py",
        "agent_gateway": ROOT / "agent" / "gateway.py",
        "toolkit_fixture_api": ROOT / "toolkit" / "fixture_api.py",
    }
    file_hashes = {}
    for key, path in files.items():
        if path.exists():
            file_hashes[key] = _sha_file(path)
    return {
        "benchmark_version": "sat-hunt-v2",
        "patoshi_csv_sha256": "f649579e286085325a881bec1168e88bbb6f5d67e10b7ef8cb5c65e916a34a2e",
        "derived_attribution_set_sha256": derived_set_sha256,
        "fixture_sha256": fixture_sha256,
        "selected_model": selected_model,
        "harness_hash": harness_hash,
        "toolkit_hash": toolkit_hash,
        "files": file_hashes,
    }


def write_freeze_manifest(manifest: dict[str, Any], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return dest
