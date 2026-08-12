"""prepare: verify baseline, materialize fixtures, create raw dirs and manifest."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diligence import BASELINE_COMMIT, __version__
from diligence.constants import (
    MANIFEST_NAME,
    NETWORK_CONTRACT_NAME,
    REPO_ROOT,
    TASKS_DIR,
    default_runs_root,
    default_workspace_root,
    raw_root,
    state_dir,
)
from diligence.fixtures import materialize_fixtures
from diligence.isolation import (
    IsolationError,
    ensure_mode_0700,
    ensure_outside_git,
    verify_baseline_scripts_unchanged,
    verify_repository,
)
from diligence.privacy import load_canaries, validate_privacy_matrix
from diligence.schemas import validate_task_manifest


def _load_tasks() -> dict[str, list[dict[str, Any]]]:
    dev = json.loads((TASKS_DIR / "development.json").read_text(encoding="utf-8"))
    hold = json.loads((TASKS_DIR / "holdout.json").read_text(encoding="utf-8"))
    return {
        "development": validate_task_manifest(dev, expected_split="development"),
        "holdout": validate_task_manifest(hold, expected_split="holdout"),
    }


def prepare(*, repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    repo_info = verify_repository(root)
    script_hashes = verify_baseline_scripts_unchanged(root)

    raw = raw_root()
    ensure_outside_git(raw, root)
    ensure_mode_0700(raw)
    workspaces = default_workspace_root()
    runs = default_runs_root()
    ensure_mode_0700(workspaces)
    ensure_mode_0700(runs)
    fixture_dir = raw / "fixtures"
    ensure_mode_0700(fixture_dir)
    fixture_paths = materialize_fixtures(fixture_dir)

    # Outside-workspace canary file (never inside task checkouts).
    outside_canary = raw / "privacy-canary-outside.txt"
    canaries = load_canaries()
    outside_canary.write_text(
        canaries["canaries"]["outside_workspace_file"]["value"] + "\n",
        encoding="utf-8",
    )
    validate_privacy_matrix(canaries)

    tasks = _load_tasks()
    families = sorted(
        {
            t["family"]
            for split_tasks in tasks.values()
            for t in split_tasks
        }
    )
    if len(families) < 8:
        raise IsolationError(f"need at least 8 task families, found {len(families)}")

    # Sample isolated checkout to prove exclusion of diligence materials.
    sample = workspaces / "_prepare_sample_checkout"
    if sample.exists():
        import shutil

        shutil.rmtree(sample)
    from diligence.isolation import create_baseline_checkout, destroy_workspace

    create_baseline_checkout(sample, repo_root=root)
    sample_files = sorted(p.name for p in sample.iterdir())
    for banned in ("AGENTS.md", "diligence", "docs", "tests"):
        if banned in sample_files or (sample / banned).exists():
            raise IsolationError(f"sample checkout contains {banned}")
    destroy_workspace(sample)

    state = state_dir(root)
    state.mkdir(parents=True, exist_ok=True)
    # Keep state gitignored; do not place secrets there.
    network_contract = {
        "network": "disabled",
        "enforcement": "Task workspaces receive network-policy.json and must not be launched with network access in future model-backed phases.",
        "file": NETWORK_CONTRACT_NAME,
    }

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "diligence_version": __version__,
        "baseline_commit": BASELINE_COMMIT,
        "repository": repo_info,
        "baseline_script_sha256": script_hashes,
        "evaluator": {
            "package": "diligence",
            "commands": [
                "python -m diligence prepare",
                "python -m diligence run --arm <arm> --split <dev|holdout> --repeats <n>",
                "python -m diligence verify --run-dir <path>",
                "python -m diligence report --run-dir <path>",
            ],
        },
        "tasks": {
            "development_count": len(tasks["development"]),
            "holdout_count": len(tasks["holdout"]),
            "families": families,
            "development_ids": [t["id"] for t in tasks["development"]],
            "holdout_ids": [t["id"] for t in tasks["holdout"]],
        },
        "fixtures": fixture_paths,
        "raw_results": {
            "root": str(raw),
            "mode": "0700",
            "workspaces": str(workspaces),
            "runs": str(runs),
        },
        "network_contract": network_contract,
        "privacy_canaries": {
            "path": "diligence/privacy/canaries.json",
            "outside_workspace_file": str(outside_canary),
            "count": len(canaries["canaries"]),
        },
        "future_model_versions": {
            "codex_cli": "0.146.1",
            "codex_model": None,
            "halo_engine": None,
            "catalyst_tracing": None,
            "small_base_model": None,
            "note": "Model-backed versions remain unset until Phase 2 approval.",
        },
        "platform": {
            "python": sys.version.split()[0],
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "phase": 1,
        "phase2_configured": False,
    }

    manifest_path = state / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    # Also write a committed scrubbed copy under docs for reproduction (no secrets).
    return manifest


def write_committed_prepare_summary(manifest: dict[str, Any], dest: Path) -> None:
    scrubbed = {
        "baseline_commit": manifest["baseline_commit"],
        "diligence_version": manifest["diligence_version"],
        "tasks": manifest["tasks"],
        "phase": manifest["phase"],
        "phase2_configured": manifest["phase2_configured"],
        "evaluator_commands": manifest["evaluator"]["commands"],
        "raw_results_mode": manifest["raw_results"]["mode"],
        "network": manifest["network_contract"]["network"],
        "created_at": manifest["created_at"],
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(scrubbed, indent=2) + "\n", encoding="utf-8")
