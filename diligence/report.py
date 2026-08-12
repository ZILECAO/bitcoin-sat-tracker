"""report: aggregate verified scrubbed run records without raw payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diligence.verify import VerifyError, verify_run_dir


def _unavailable() -> dict[str, Any]:
    return {"status": "unavailable", "value": None}


def _observed(value: Any) -> dict[str, Any]:
    return {"status": "observed", "value": value}


def report_run_dir(run_dir: Path, *, require_verified: bool = True) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    verify_path = run_dir / "verify-result.json"
    if require_verified:
        if not verify_path.exists():
            # Run verification first.
            verify_run_dir(run_dir)
        else:
            existing = json.loads(verify_path.read_text(encoding="utf-8"))
            if not existing.get("verified"):
                raise VerifyError("run directory is not verified")
            # Re-verify to refuse stale/failed privacy state.
            verify_run_dir(run_dir)

    meta = json.loads((run_dir / "run-meta.json").read_text(encoding="utf-8"))
    index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))

    records = []
    for rel in index["records"]:
        records.append(json.loads((run_dir / rel).read_text(encoding="utf-8")))

    successes = [r for r in records if r.get("tests_passed") is True]
    durations = [r["duration_ms"] for r in records if isinstance(r.get("duration_ms"), int)]

    def metric_series(field: str) -> dict[str, Any]:
        values = []
        any_null = False
        for r in records:
            if field not in r:
                any_null = True
                continue
            if r[field] is None:
                any_null = True
            else:
                values.append(r[field])
        if not values and any_null:
            return _unavailable()
        if not values:
            return _unavailable()
        # Never invent zeros for uncollected metrics. If some records observed
        # values, report those only and mark partial.
        agg = {
            "status": "observed" if not any_null else "partial",
            "count_observed": len(values),
            "count_unavailable": sum(1 for r in records if r.get(field) is None),
            "sum": sum(values) if values and all(isinstance(v, (int, float)) for v in values) else None,
            "mean": (
                (sum(values) / len(values))
                if values and all(isinstance(v, (int, float)) for v in values)
                else None
            ),
            "values": values,
        }
        return agg

    privacy_pass = all(r.get("privacy_checks_passed") is True for r in records)
    tool_errors = _unavailable()  # not collected in Phase 1 offline arm
    retries = _unavailable()

    report = {
        "arm": meta["arm"],
        "split": meta["split"],
        "baseline_commit": meta["baseline_commit"],
        "run_id": meta["run_id"],
        "task_success": _observed(
            {
                "passed": len(successes),
                "total": len(records),
                "rate": (len(successes) / len(records)) if records else None,
                "passed_task_ids": sorted({r["task_id"] for r in successes}),
                "failed_task_ids": sorted(
                    {r["task_id"] for r in records if not r.get("tests_passed")}
                ),
            }
        ),
        "duration_ms": _observed(
            {
                "count": len(durations),
                "sum": sum(durations) if durations else 0,
                "mean": (sum(durations) / len(durations)) if durations else None,
            }
        ),
        "input_tokens": metric_series("input_tokens"),
        "output_tokens": metric_series("output_tokens"),
        "cost_usd": metric_series("cost_usd"),
        "retries": retries,
        "tool_errors": tool_errors,
        "trace_completeness": metric_series("trace_complete"),
        "privacy_checks": _observed({"all_passed": privacy_pass, "record_count": len(records)}),
        "notes": [
            "Report consumes verified scrubbed records only.",
            "Raw prompts, outputs, tool results, trace bodies, and provider responses are excluded.",
            "Metrics with status 'unavailable' were not collected; zeros are not invented.",
        ],
        "evidence_class": "observed" if meta["arm"] == "offline-fixture" else "phase2_blocked",
    }

    # Integrity: ensure report text has no raw payload keys with content.
    blob = json.dumps(report)
    for banned in ("raw_prompt", "provider_response", "trace_body", "model_output"):
        if f'"{banned}"' in blob:
            raise VerifyError(f"report unexpectedly contains {banned}")

    out = run_dir / "report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
