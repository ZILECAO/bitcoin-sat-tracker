"""Strict schema validation for tasks and run records."""

from __future__ import annotations

import re
from typing import Any

from diligence import ALLOWED_ARMS, ALLOWED_SPLITS, BASELINE_COMMIT

TASK_REQUIRED = (
    "id",
    "prompt",
    "baseline_commit",
    "fixture_id",
    "scorer_id",
    "timeout_seconds",
    "network",
    "max_tokens",
    "max_cost_usd",
    "family",
    "split",
)

SCRUBBED_REQUIRED = (
    "task_id",
    "arm",
    "split",
    "repeat",
    "model",
    "codex_version",
    "adapter_version",
    "started_at",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "exit_status",
    "tests_passed",
    "trace_complete",
    "privacy_checks_passed",
    "trace_id",
    "suggestion_ids",
)

_TASK_ID_RE = re.compile(r"^btc-(dev|hold)-\d{3}$")
_RFC3339_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


class SchemaError(ValueError):
    """Raised when a task or run record fails schema validation."""


def _require_keys(obj: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise SchemaError(f"{label} missing required fields: {missing}")


def validate_task(task: dict[str, Any], *, expected_split: str | None = None) -> dict[str, Any]:
    if not isinstance(task, dict):
        raise SchemaError("task must be an object")
    _require_keys(task, TASK_REQUIRED, "task")
    unknown = sorted(set(task) - set(TASK_REQUIRED) - {"prompt_file", "target_files", "notes"})
    if unknown:
        raise SchemaError(f"task has unknown fields: {unknown}")

    task_id = task["id"]
    if not isinstance(task_id, str) or not _TASK_ID_RE.match(task_id):
        raise SchemaError(f"invalid task id: {task_id!r}")

    split = task["split"]
    if split not in ("development", "holdout"):
        raise SchemaError(f"invalid task split: {split!r}")
    if expected_split is not None and split != expected_split:
        raise SchemaError(f"task {task_id} split {split!r} != manifest {expected_split!r}")

    if task["baseline_commit"] != BASELINE_COMMIT:
        raise SchemaError(
            f"task {task_id} baseline_commit must be {BASELINE_COMMIT}, got {task['baseline_commit']!r}"
        )
    if task["network"] != "disabled":
        raise SchemaError(f"task {task_id} network must be 'disabled'")
    for field in ("timeout_seconds", "max_tokens"):
        value = task[field]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SchemaError(f"task {task_id} {field} must be a positive integer")
    cost = task["max_cost_usd"]
    if not isinstance(cost, (int, float)) or isinstance(cost, bool) or cost <= 0:
        raise SchemaError(f"task {task_id} max_cost_usd must be a positive number")
    for field in ("prompt", "fixture_id", "scorer_id", "family"):
        if not isinstance(task[field], str) or not task[field].strip():
            raise SchemaError(f"task {task_id} {field} must be a non-empty string")
    return task


def validate_task_manifest(tasks: list[Any], *, expected_split: str) -> list[dict[str, Any]]:
    if not isinstance(tasks, list) or not tasks:
        raise SchemaError("task manifest must be a non-empty list")
    seen: set[str] = set()
    validated: list[dict[str, Any]] = []
    for item in tasks:
        task = validate_task(item, expected_split=expected_split)
        if task["id"] in seen:
            raise SchemaError(f"duplicated task id: {task['id']}")
        seen.add(task["id"])
        validated.append(task)
    return validated


def validate_scrubbed_record(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise SchemaError("scrubbed record must be an object")
    _require_keys(record, SCRUBBED_REQUIRED, "scrubbed record")
    unknown = sorted(set(record) - set(SCRUBBED_REQUIRED) - {"budget", "scorer_detail", "notes"})
    if unknown:
        raise SchemaError(f"scrubbed record has unknown fields: {unknown}")

    if record["arm"] not in ALLOWED_ARMS:
        raise SchemaError(f"unknown arm: {record['arm']!r}")
    if record["split"] not in ALLOWED_SPLITS:
        raise SchemaError(f"unknown split: {record['split']!r}")
    if not isinstance(record["repeat"], int) or record["repeat"] < 1:
        raise SchemaError("repeat must be an integer >= 1")
    if not isinstance(record["started_at"], str) or not _RFC3339_RE.match(record["started_at"]):
        raise SchemaError("started_at must be RFC 3339")
    if not isinstance(record["duration_ms"], int) or record["duration_ms"] < 0:
        raise SchemaError("duration_ms must be a non-negative integer")
    if not isinstance(record["exit_status"], int):
        raise SchemaError("exit_status must be an integer")
    for flag in ("tests_passed", "privacy_checks_passed"):
        if not isinstance(record[flag], bool):
            raise SchemaError(f"{flag} must be a boolean")
    if record["trace_complete"] is not None and not isinstance(record["trace_complete"], bool):
        raise SchemaError("trace_complete must be bool or null")
    for metric in ("input_tokens", "output_tokens", "cost_usd", "trace_id"):
        value = record[metric]
        if value is None:
            continue
        if metric == "trace_id":
            if not isinstance(value, str):
                raise SchemaError("trace_id must be string or null")
        elif metric == "cost_usd":
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                raise SchemaError("cost_usd must be null or a non-negative number")
        else:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise SchemaError(f"{metric} must be null or a non-negative integer")
    if not isinstance(record["suggestion_ids"], list):
        raise SchemaError("suggestion_ids must be a list")
    return record


def split_cli_to_manifest(split: str) -> str:
    if split == "dev":
        return "development"
    if split == "holdout":
        return "holdout"
    raise SchemaError(f"split must be one of {ALLOWED_SPLITS}, got {split!r}")
