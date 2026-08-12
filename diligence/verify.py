"""verify: validate run records, isolation, privacy, and commit safety."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from diligence import ALLOWED_ARMS, BASELINE_COMMIT
from diligence.constants import PROHIBITED_COMMIT_PATTERNS, REPO_ROOT, SCRUBBED_REQUIRED_FIELDS
from diligence.privacy import (
    PrivacyError,
    compare_secret_in_memory,
    load_canaries,
    reject_prohibited_artifacts,
    scan_text_for_canaries,
    scan_text_for_secrets,
    validate_privacy_matrix,
)
from diligence.run import load_split_tasks
from diligence.schemas import SchemaError, validate_scrubbed_record


class VerifyError(RuntimeError):
    """Raised when verification fails."""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_run_dir(run_dir: Path, *, repo_root: Path | None = None) -> dict[str, Any]:
    root = (repo_root or REPO_ROOT).resolve()
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        raise VerifyError(f"run dir missing: {run_dir}")

    meta_path = run_dir / "run-meta.json"
    index_path = run_dir / "index.json"
    if not meta_path.exists() or not index_path.exists():
        raise VerifyError("run-meta.json and index.json are required")

    meta = _load_json(meta_path)
    index = _load_json(index_path)

    if meta.get("baseline_commit") != BASELINE_COMMIT:
        raise VerifyError(f"baseline mismatch: {meta.get('baseline_commit')}")
    if index.get("baseline_commit") != BASELINE_COMMIT:
        raise VerifyError("index baseline mismatch")
    if meta.get("network") != "disabled":
        raise VerifyError("network policy must be disabled")

    arm = meta.get("arm")
    split = meta.get("split")
    if arm not in ALLOWED_ARMS:
        raise VerifyError(f"unknown arm in meta: {arm}")

    expected_tasks = load_split_tasks(split)
    expected_ids = {t["id"] for t in expected_tasks}
    repeats = int(meta.get("repeats", 1))

    scrubbed_dir = run_dir / "scrubbed"
    if not scrubbed_dir.is_dir():
        raise VerifyError("scrubbed/ directory missing")

    records: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for rel in index.get("records", []):
        path = run_dir / rel
        if not path.exists():
            raise VerifyError(f"missing scrubbed record: {rel}")
        record = validate_scrubbed_record(_load_json(path))
        if record["arm"] != arm or record["split"] != split:
            raise VerifyError(f"record arm/split mismatch in {rel}")
        if record["task_id"] not in expected_ids:
            raise VerifyError(f"unexpected task_id: {record['task_id']}")
        key = (record["task_id"], record["repeat"])
        if key in seen:
            raise VerifyError(f"duplicate record for {key}")
        seen.add(key)

        # Scorer result expected for offline-fixture.
        if arm == "offline-fixture":
            detail = record.get("scorer_detail")
            if not isinstance(detail, dict) or "scorer_id" not in detail:
                raise VerifyError(f"missing scorer_detail for {rel}")

        text = path.read_text(encoding="utf-8")
        if scan_text_for_secrets(text):
            raise VerifyError(f"secret-like material in {rel}")
        if scan_text_for_canaries(text):
            raise VerifyError(f"privacy canary present in scrubbed record {rel}")
        if not record.get("privacy_checks_passed", False):
            raise VerifyError(f"privacy_checks_passed is false in {rel}")

        # Reject raw bodies / env references in scrubbed records.
        lowered = text.lower()
        for banned in ("raw_prompt", "trace_body", "provider_response", "model_output"):
            # Allow explicit null-absent notes in schemas/tests only; scrubbed task
            # records should not embed these payloads.
            if f'"{banned}"' in lowered:
                raise VerifyError(f"prohibited raw field {banned} in {rel}")
        if ".env" in text:
            raise VerifyError(f".env reference in scrubbed record {rel}")
        if re.search(r"/(home|Users|var|tmp)/[^\"]+", text) and "budget" not in rel:
            # Absolute paths in scrubbed committed output are rejected except
            # ephemeral run dirs which remain outside git; still flag workspace leaks.
            if "diligence-raw" in text or str(root) in text:
                raise VerifyError(f"unexpected absolute path in {rel}")

        records.append(record)

    # Every expected task/repeat must exist.
    for task in expected_tasks:
        for repeat in range(1, repeats + 1):
            if (task["id"], repeat) not in seen:
                raise VerifyError(f"missing result for {task['id']} repeat {repeat}")

    # Privacy canary matrix must validate.
    try:
        validate_privacy_matrix(load_canaries())
    except PrivacyError as exc:
        raise VerifyError(str(exc)) from exc

    # In-memory secret compare API: only pass/fail, never log secrets.
    # Use clearly fake values for Phase 1 self-check.
    memory_ok = compare_secret_in_memory("FAKE_COMPARE_A", "FAKE_COMPARE_A")
    memory_bad = compare_secret_in_memory("FAKE_COMPARE_A", "FAKE_COMPARE_B")
    if not memory_ok or memory_bad:
        raise VerifyError("in-memory secret compare self-check failed")

    # Commit-safety scan of the run directory artifacts proposed for commit.
    # Raw subdirectory must not be staged; verify it exists but is outside git.
    raw_dir = run_dir / "raw"
    if arm == "offline-fixture" and not raw_dir.exists():
        raise VerifyError("raw/ directory missing for offline-fixture run")

    # Reject prohibited artifacts if someone copied them into scrubbed/.
    reject_prohibited_artifacts(list(scrubbed_dir.glob("*")))

    result = {
        "verified": True,
        "run_dir": str(run_dir),
        "arm": arm,
        "split": split,
        "baseline_commit": BASELINE_COMMIT,
        "network": "disabled",
        "record_count": len(records),
        "privacy_matrix_ok": True,
        "memory_secret_compare_ok": True,
    }
    (run_dir / "verify-result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result
