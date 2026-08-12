"""run: orchestrate experimental arms (Phase 1: offline-fixture only succeeds)."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diligence import ALLOWED_ARMS, ALLOWED_SPLITS, BASELINE_COMMIT, PHASE2_ARMS, __version__
from diligence.constants import (
    PROMPTS_DIR,
    REPO_ROOT,
    TASKS_DIR,
    default_runs_root,
    default_workspace_root,
    raw_root,
)
from diligence.isolation import (
    IsolationError,
    assert_workspace_isolated,
    copy_public_task_materials,
    create_baseline_checkout,
    destroy_workspace,
    ensure_mode_0700,
    ensure_outside_git,
)
from diligence.privacy import load_canaries, scan_text_for_canaries, validate_privacy_matrix
from diligence.schemas import SchemaError, split_cli_to_manifest, validate_task_manifest
from diligence.scorers import run_scorer


class RunError(RuntimeError):
    """Raised when a run cannot proceed."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_split_tasks(split: str) -> list[dict[str, Any]]:
    manifest_split = split_cli_to_manifest(split)
    path = TASKS_DIR / ("development.json" if manifest_split == "development" else "holdout.json")
    tasks = json.loads(path.read_text(encoding="utf-8"))
    return validate_task_manifest(tasks, expected_split=manifest_split)


def phase2_not_configured_record(
    *,
    task: dict[str, Any],
    arm: str,
    split: str,
    repeat: int,
    started_at: str,
    duration_ms: int,
) -> dict[str, Any]:
    return {
        "task_id": task["id"],
        "arm": arm,
        "split": split,
        "repeat": repeat,
        "model": None,
        "codex_version": None,
        "adapter_version": __version__,
        "started_at": started_at,
        "duration_ms": duration_ms,
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "exit_status": 2,
        "tests_passed": False,
        "trace_complete": None,
        "privacy_checks_passed": True,
        "trace_id": None,
        "suggestion_ids": [],
        "notes": "Phase 2 not configured",
        "budget": {
            "timeout_seconds": task["timeout_seconds"],
            "max_tokens": task["max_tokens"],
            "max_cost_usd": task["max_cost_usd"],
            "enforced": True,
            "tokens_used": None,
            "cost_used_usd": None,
        },
    }


def _prompt_for(task: dict[str, Any]) -> str:
    prompt_file = task.get("prompt_file")
    if prompt_file:
        path = PROMPTS_DIR / prompt_file
        if path.exists():
            return path.read_text(encoding="utf-8")
    return task["prompt"]


def _fixture_files() -> dict[str, Path]:
    committed = Path(__file__).resolve().parent / "fixtures" / "data" / "bitcoin_rpc_mempool.json"
    # materialize may also write under raw; prefer committed deterministic copy.
    from diligence.fixtures import materialize_fixtures
    from diligence.constants import FIXTURES_DIR

    if not committed.exists():
        materialize_fixtures(FIXTURES_DIR)
    return {"bitcoin_rpc_mempool.json": FIXTURES_DIR / "bitcoin_rpc_mempool.json"}


def enforce_budgets(task: dict[str, Any], *, tokens_used: int | None, cost_used: float | None) -> dict[str, Any]:
    """Enforce timeout/token/cost fields even when offline cost is unused."""
    if task["timeout_seconds"] <= 0 or task["max_tokens"] <= 0 or task["max_cost_usd"] <= 0:
        raise RunError(f"task {task['id']} has non-positive budgets")
    status = {
        "timeout_seconds": task["timeout_seconds"],
        "max_tokens": task["max_tokens"],
        "max_cost_usd": task["max_cost_usd"],
        "enforced": True,
        "tokens_used": tokens_used,
        "cost_used_usd": cost_used,
        "within_budget": True,
    }
    if tokens_used is not None and tokens_used > task["max_tokens"]:
        status["within_budget"] = False
    if cost_used is not None and cost_used > task["max_cost_usd"]:
        status["within_budget"] = False
    return status


def run_offline_fixture_task(
    *,
    task: dict[str, Any],
    split: str,
    repeat: int,
    run_dir: Path,
    workspace_root: Path,
    repo_root: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    started_at = _utc_now()
    workspace = workspace_root / f"{task['id']}-r{repeat}-{uuid.uuid4().hex[:8]}"
    raw_task_dir = run_dir / "raw" / f"{task['id']}-r{repeat}"
    raw_task_dir.mkdir(parents=True, exist_ok=True)

    create_baseline_checkout(workspace, repo_root=repo_root)
    prompt = _prompt_for(task)
    copy_public_task_materials(workspace, prompt_text=prompt, fixture_files=_fixture_files())
    assert_workspace_isolated(workspace)

    # Privacy: ensure canaries are not already leaking into scrubbed outputs.
    canaries = load_canaries()
    validate_privacy_matrix(canaries)

    score = run_scorer(task["scorer_id"], workspace)
    duration_ms = int((time.monotonic() - started) * 1000)
    if duration_ms > task["timeout_seconds"] * 1000:
        # Extremely unlikely for static scoring; still enforce the contract.
        within_timeout = False
    else:
        within_timeout = True

    budget = enforce_budgets(task, tokens_used=None, cost_used=None)
    # Offline fixture does not incur tokens/cost; leave metrics null (not zero).
    record = {
        "task_id": task["id"],
        "arm": "offline-fixture",
        "split": split,
        "repeat": repeat,
        "model": "offline-fixture",
        "codex_version": None,
        "adapter_version": __version__,
        "started_at": started_at,
        "duration_ms": duration_ms,
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "exit_status": 0 if within_timeout else 124,
        "tests_passed": bool(score.passed) and within_timeout and budget["within_budget"],
        "trace_complete": None,
        "privacy_checks_passed": True,
        "trace_id": None,
        "suggestion_ids": [],
        "budget": budget,
        "scorer_detail": score.as_dict(),
        "notes": (
            "Offline fixture scored the immutable baseline without a model call. "
            "Baseline tasks are expected to fail most scorers until a future agent patch."
        ),
    }

    # Raw private record (may include more detail) stays outside git.
    raw_payload = {
        "scrubbed": record,
        "workspace_files": sorted(
            str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()
        ),
        "baseline_commit": BASELINE_COMMIT,
        "network": "disabled",
        "raw_note": "Phase 1 offline-fixture raw record. No model prompt/output/trace bodies exist.",
    }
    (raw_task_dir / "raw-record.json").write_text(
        json.dumps(raw_payload, indent=2) + "\n", encoding="utf-8"
    )

    # Confirm scrubbed JSON does not embed canary values.
    scrubbed_text = json.dumps(record)
    hits = scan_text_for_canaries(scrubbed_text)
    if hits:
        record["privacy_checks_passed"] = False
        raise RunError("privacy canary leaked into scrubbed record")

    destroy_workspace(workspace)
    return record


def run(
    *,
    arm: str,
    split: str,
    repeats: int,
    repo_root: Path | None = None,
    run_id: str | None = None,
) -> Path:
    if arm not in ALLOWED_ARMS:
        raise RunError(f"unknown arm: {arm}. allowed={ALLOWED_ARMS}")
    if split not in ALLOWED_SPLITS:
        raise RunError(f"unknown split: {split}. allowed={ALLOWED_SPLITS}")
    if not isinstance(repeats, int) or repeats < 1:
        raise RunError("repeats must be an integer >= 1")

    root = (repo_root or REPO_ROOT).resolve()
    raw = raw_root()
    ensure_outside_git(raw, root)
    ensure_mode_0700(raw)
    runs_root = default_runs_root()
    ensure_mode_0700(runs_root)
    workspace_root = default_workspace_root()
    ensure_mode_0700(workspace_root)

    tasks = load_split_tasks(split)
    rid = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    run_dir = runs_root / f"{arm}-{split}-{rid}"
    run_dir.mkdir(parents=False, exist_ok=False)
    ensure_mode_0700(run_dir)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    (run_dir / "scrubbed").mkdir(parents=True, exist_ok=True)

    meta = {
        "run_id": rid,
        "arm": arm,
        "split": split,
        "repeats": repeats,
        "baseline_commit": BASELINE_COMMIT,
        "created_at": _utc_now(),
        "phase2_configured": False,
        "network": "disabled",
        "task_ids": [t["id"] for t in tasks],
    }
    (run_dir / "run-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    records: list[dict[str, Any]] = []
    if arm in PHASE2_ARMS:
        for task in tasks:
            for repeat in range(1, repeats + 1):
                started_at = _utc_now()
                record = phase2_not_configured_record(
                    task=task,
                    arm=arm,
                    split=split,
                    repeat=repeat,
                    started_at=started_at,
                    duration_ms=0,
                )
                records.append(record)
                out = run_dir / "scrubbed" / f"{task['id']}-r{repeat}.json"
                out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    elif arm == "offline-fixture":
        for task in tasks:
            for repeat in range(1, repeats + 1):
                record = run_offline_fixture_task(
                    task=task,
                    split=split,
                    repeat=repeat,
                    run_dir=run_dir,
                    workspace_root=workspace_root,
                    repo_root=root,
                )
                records.append(record)
                out = run_dir / "scrubbed" / f"{task['id']}-r{repeat}.json"
                out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    else:
        raise RunError(f"unhandled arm: {arm}")

    index = {
        "run_id": rid,
        "arm": arm,
        "split": split,
        "repeats": repeats,
        "baseline_commit": BASELINE_COMMIT,
        "records": [f"scrubbed/{r['task_id']}-r{r['repeat']}.json" for r in records],
        "count": len(records),
    }
    (run_dir / "index.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    return run_dir
