#!/usr/bin/env python3
"""Phase 2B runner: model selection, development/held-out arms, scrubbed records."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import statistics
import time
import uuid
from pathlib import Path
from typing import Any

from diligence.sat_hunt.agent import BASELINE_SYSTEM, SatHuntAgent, harness_hash
from diligence.sat_hunt.attribution import (
    build_match_index,
    derived_set_hash,
    load_patoshi_csv,
)
from diligence.sat_hunt.fixtures import build_fixture, build_oracle, fixture_sha256
from diligence.sat_hunt.freeze import build_freeze_manifest, write_freeze_manifest
from diligence.sat_hunt.scorers import SCORERS
from diligence.sat_hunt.tasks import (
    DEVELOPMENT_TASKS,
    HELDOUT_TASKS,
    load_prompt,
    prepare_task_workspace,
    write_manifests,
)

RAW = Path(os.environ.get("DILIGENCE_RAW_DIR", str(Path.home() / "diligence-raw-phase2b")))
CSV = RAW / "patoshi" / "patoshi_pubkeys_COMPLETE.csv"
RESULTS = Path("docs/catalyst-halo/results/phase2b")
SPEND_LEDGER = RAW / "spend" / "phase2b-spend-ledger.json"

# Updated only after HALO suggestions are classified and accepted.
HALO_HARNESS_SYSTEM = BASELINE_SYSTEM


def _toolkit_hash() -> str:
    return hashlib.sha256(
        Path("diligence/sat_hunt/toolkit/fixture_api.py").read_bytes()
    ).hexdigest()


def load_spend() -> dict[str, Any]:
    if SPEND_LEDGER.exists():
        return json.loads(SPEND_LEDGER.read_text())
    return {
        "phase2b_incremental_cap_usd": 5.0,
        "phase2b_incremental_spent_usd": 0.0,
        "events": [],
    }


def record_spend(event: str, cost_usd: float, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    ledger = load_spend()
    ledger["phase2b_incremental_spent_usd"] = round(
        float(ledger.get("phase2b_incremental_spent_usd") or 0) + float(cost_usd), 8
    )
    ledger.setdefault("events", []).append(
        {
            "ts": time.time(),
            "event": event,
            "cost_usd": float(cost_usd),
            "spent_after": ledger["phase2b_incremental_spent_usd"],
            "meta": meta or {},
        }
    )
    SPEND_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    SPEND_LEDGER.write_text(json.dumps(ledger, indent=2) + "\n")
    return ledger


def assert_under_cap(extra: float = 0.0) -> None:
    ledger = load_spend()
    spent = float(ledger.get("phase2b_incremental_spent_usd") or 0) + extra
    cap = float(ledger.get("phase2b_incremental_cap_usd") or 5.0)
    if spent >= cap:
        raise SystemExit(
            f"STOP: Phase 2B incremental spend {spent:.6f} would reach/exceed cap {cap}"
        )


def load_state() -> dict[str, Any]:
    write_manifests()
    records = load_patoshi_csv(CSV)
    match_index = build_match_index(records)
    fixture = build_fixture(attribution_records=records)
    oracle = build_oracle(fixture, match_index)
    return {
        "records": records,
        "match_index": match_index,
        "fixture": fixture,
        "oracle": oracle,
        "derived_set_sha256": derived_set_hash(records),
    }


def score_task(task: dict[str, Any], workspace: Path, state: dict[str, Any]):
    scorer = SCORERS[task["scorer_id"]]
    if task["scorer_id"] == "public_satoshi_attribution":
        return scorer(workspace, state["fixture"], state["match_index"])
    if task["scorer_id"] == "final_exam":
        return scorer(workspace, state["fixture"], state["oracle"])
    return scorer(workspace, state["fixture"])


def arm_config(arm: str) -> tuple[str, bool]:
    if arm == "baseline-harness":
        return BASELINE_SYSTEM, False
    if arm == "halo-harness-only":
        return HALO_HARNESS_SYSTEM, False
    if arm == "halo-repo-toolkit-only":
        return BASELINE_SYSTEM, True
    if arm == "halo-combined":
        return HALO_HARNESS_SYSTEM, True
    if arm == "model-select":
        return BASELINE_SYSTEM, False
    if arm == "baseline-dev":
        return BASELINE_SYSTEM, False
    raise ValueError(f"unknown arm: {arm}")


def run_one(
    *,
    task: dict[str, Any],
    arm: str,
    model: str,
    state: dict[str, Any],
    system_prompt: str,
    include_toolkit: bool,
    repeat: int,
    enable_catalyst: bool = True,
    max_turns: int = 10,
) -> dict[str, Any]:
    assert_under_cap()
    ws = RAW / "workspaces" / f"{task['id']}-{arm}-r{repeat}-{uuid.uuid4().hex[:8]}"
    prepare_task_workspace(ws, fixture=state["fixture"], include_toolkit=include_toolkit)
    agent = SatHuntAgent(
        workspace=ws,
        fixture=state["fixture"],
        model=model,
        task_id=f"{task['id']}:{arm}:r{repeat}",
        arm=arm,
        system_prompt=system_prompt,
        raw_dir=RAW / "traces",
        enable_catalyst=enable_catalyst,
        max_turns=max_turns,
    )
    prompt = load_prompt(task)
    run = agent.run(prompt)
    score = score_task(task, ws, state)
    record = {
        **run,
        "repeat": repeat,
        "scorer_id": task["scorer_id"],
        "tests_passed": score.passed,
        "score": score.as_dict(),
        "efficiency_eligible": bool(score.passed),
        "include_toolkit": include_toolkit,
    }
    out = RAW / "runs" / f"{task['id']}-{arm}-r{repeat}-{uuid.uuid4().hex[:6]}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
    record_spend(
        f"run:{task['id']}:{arm}:r{repeat}",
        float(record.get("cost_usd_est") or 0),
        meta={"trace_id": record.get("trace_id"), "passed": score.passed, "model": model},
    )
    return record


def scrub_record(r: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "task_id",
        "arm",
        "model",
        "repeat",
        "trace_id",
        "duration_ms",
        "cost_usd_est",
        "input_tokens",
        "output_tokens",
        "gateway_calls",
        "tool_calls",
        "retries",
        "errors",
        "catalyst_error",
        "harness_hash",
        "toolkit_hash",
        "tests_passed",
        "efficiency_eligible",
        "scorer_id",
        "include_toolkit",
    )
    out = {k: r.get(k) for k in keys}
    score = r.get("score") or {}
    out["score_passed"] = score.get("passed")
    out["score_checks"] = [
        {"name": c.get("name"), "passed": c.get("passed")} for c in (score.get("checks") or [])
    ]
    return out


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def summarize_arm(records: list[dict[str, Any]]) -> dict[str, Any]:
    correct = [r for r in records if r.get("tests_passed")]
    def med(vals: list[float]) -> float | None:
        return float(statistics.median(vals)) if vals else None

    return {
        "tasks_attempted": len(records),
        "correct_runs": len(correct),
        "success_rate": (len(correct) / len(records)) if records else 0.0,
        "median_cost_correct": med([float(r["cost_usd_est"]) for r in correct]),
        "total_cost": round(sum(float(r.get("cost_usd_est") or 0) for r in records), 8),
        "median_duration_correct_ms": med([float(r["duration_ms"]) for r in correct]),
        "median_tokens_correct": med(
            [float((r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)) for r in correct]
        ),
        "median_tool_calls_correct": med([float(r.get("tool_calls") or 0) for r in correct]),
        "retry_count": sum(int(r.get("retries") or 0) for r in records),
        "complete_traces": sum(1 for r in records if r.get("trace_id") and not r.get("catalyst_error")),
        "efficiency_eligible": sum(1 for r in correct if r.get("efficiency_eligible")),
    }


def cmd_select(args: argparse.Namespace) -> None:
    state = load_state()
    candidates = args.models
    smoke_tasks = DEVELOPMENT_TASKS[:2]
    smoke_results = []
    for model in candidates:
        for task in smoke_tasks:
            rec = run_one(
                task=task,
                arm="model-select",
                model=model,
                state=state,
                system_prompt=BASELINE_SYSTEM,
                include_toolkit=False,
                repeat=1,
                enable_catalyst=True,
                max_turns=args.max_turns,
            )
            smoke_results.append(rec)
            print(
                "SMOKE",
                model,
                task["id"],
                "pass=" + str(rec["tests_passed"]),
                "cost=" + str(rec["cost_usd_est"]),
                "trace=" + str(rec["trace_id"]),
            )
    by_model: dict[str, list] = {}
    for rec in smoke_results:
        by_model.setdefault(rec["model"], []).append(rec)
    ranked = sorted(
        by_model.items(),
        key=lambda kv: (
            -sum(1 for r in kv[1] if r["tests_passed"]),
            sum(r["cost_usd_est"] for r in kv[1]),
            sum(r["duration_ms"] for r in kv[1]),
        ),
    )
    # Stage 2 of selection: top two across full development set once each
    top_two = [m for m, _ in ranked[:2]]
    full_dev: list[dict[str, Any]] = []
    for model in top_two:
        for task in DEVELOPMENT_TASKS:
            rec = run_one(
                task=task,
                arm="model-select",
                model=model,
                state=state,
                system_prompt=BASELINE_SYSTEM,
                include_toolkit=False,
                repeat=1,
                enable_catalyst=True,
                max_turns=args.max_turns,
            )
            full_dev.append(rec)
            print(
                "DEVSEL",
                model,
                task["id"],
                "pass=" + str(rec["tests_passed"]),
                "cost=" + str(rec["cost_usd_est"]),
            )
    by_full: dict[str, list] = {}
    for rec in full_dev:
        by_full.setdefault(rec["model"], []).append(rec)
    ranked_full = sorted(
        by_full.items(),
        key=lambda kv: (
            -sum(1 for r in kv[1] if r["tests_passed"]),
            sum(r["cost_usd_est"] for r in kv[1]),
            sum(r["duration_ms"] for r in kv[1]),
        ),
    )
    selected = ranked_full[0][0] if ranked_full else ranked[0][0]
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidates": candidates,
        "smoke_results": [scrub_record(r) for r in smoke_results],
        "full_dev_results": [scrub_record(r) for r in full_dev],
        "selected_model": selected,
        "smoke_ranking": [m for m, _ in ranked],
        "full_dev_ranking": [m for m, _ in ranked_full],
        "candidate_notes": {
            "deepseek-v4-flash": {
                "provider": "system/inference.net",
                "context_length": 163840,
                "gateway_compat_prior": True,
                "local_cost_est_per_mtok": {"input": 0.14, "output": 0.28},
            },
            "gpt-4.1-nano": {
                "provider": "system/inference.net",
                "context_length": 1047576,
                "gateway_compat_prior": "partial (phase2 eval failed)",
            },
            "gemini-2.5-flash-lite": {
                "provider": "system/inference.net",
                "context_length": 1048576,
                "gateway_compat_prior": "unknown before this run",
            },
        },
        "spend_ledger": load_spend(),
    }
    write_json(RESULTS / "model-selection.json", payload)
    manifest = build_freeze_manifest(
        derived_set_sha256=state["derived_set_sha256"],
        fixture_sha256=fixture_sha256(state["fixture"]),
        selected_model=selected,
        harness_hash=harness_hash(BASELINE_SYSTEM),
        toolkit_hash=_toolkit_hash(),
    )
    write_freeze_manifest(manifest, RESULTS / "freeze-hashes.json")
    write_freeze_manifest(manifest, Path("diligence/sat_hunt/freeze-hashes.json"))
    print("SELECTED", selected)


def cmd_baseline(args: argparse.Namespace) -> None:
    state = load_state()
    model = args.model or json.loads((RESULTS / "model-selection.json").read_text())["selected_model"]
    records = []
    for task in DEVELOPMENT_TASKS:
        rec = run_one(
            task=task,
            arm="baseline-dev",
            model=model,
            state=state,
            system_prompt=BASELINE_SYSTEM,
            include_toolkit=False,
            repeat=1,
            enable_catalyst=True,
            max_turns=args.max_turns,
        )
        records.append(rec)
        print("BASE", task["id"], rec["tests_passed"], rec["trace_id"], rec["cost_usd_est"])
    write_json(
        RESULTS / "baseline-dev-runs.json",
        {
            "model": model,
            "summary": summarize_arm(records),
            "runs": [scrub_record(r) for r in records],
        },
    )


def cmd_heldout(args: argparse.Namespace) -> None:
    state = load_state()
    model = args.model or json.loads((RESULTS / "model-selection.json").read_text())["selected_model"]
    arms = [
        "baseline-harness",
        "halo-harness-only",
        "halo-repo-toolkit-only",
        "halo-combined",
    ]
    schedule = []
    for task in HELDOUT_TASKS:
        for arm in arms:
            for rep in range(1, args.reps + 1):
                schedule.append((task, arm, rep))
    random.Random(args.seed).shuffle(schedule)
    records = []
    for task, arm, rep in schedule:
        system, toolkit = arm_config(arm)
        rec = run_one(
            task=task,
            arm=arm,
            model=model,
            state=state,
            system_prompt=system,
            include_toolkit=toolkit,
            repeat=rep,
            enable_catalyst=True,
            max_turns=args.max_turns,
        )
        records.append(rec)
        print("HOLD", task["id"], arm, rep, rec["tests_passed"], rec["cost_usd_est"])
    by_arm: dict[str, list] = {}
    for r in records:
        by_arm.setdefault(r["arm"], []).append(r)
    write_json(
        RESULTS / "heldout-results.json",
        {
            "model": model,
            "reps": args.reps,
            "seed": args.seed,
            "by_arm": {arm: summarize_arm(rs) for arm, rs in by_arm.items()},
            "runs": [scrub_record(r) for r in records],
        },
    )


def cmd_final(args: argparse.Namespace) -> None:
    state = load_state()
    model = args.model or json.loads((RESULTS / "model-selection.json").read_text())["selected_model"]
    final_task = {
        "id": "sat-final",
        "family": "final_exam",
        "scorer_id": "final_exam",
        "prompt_file": "final-exam.md",
        "answer_name": "answer.json",
    }
    arms = [
        "baseline-harness",
        "halo-harness-only",
        "halo-repo-toolkit-only",
        "halo-combined",
    ]
    # Track A: deterministic fixture
    track_a = []
    schedule = [(arm, rep) for arm in arms for rep in range(1, args.reps + 1)]
    random.Random(args.seed).shuffle(schedule)
    for arm, rep in schedule:
        system, toolkit = arm_config(arm)
        rec = run_one(
            task=final_task,
            arm=arm,
            model=model,
            state=state,
            system_prompt=system,
            include_toolkit=toolkit,
            repeat=rep,
            enable_catalyst=True,
            max_turns=args.max_turns,
        )
        track_a.append(rec)
        print("FINAL-A", arm, rep, rec["tests_passed"], rec["cost_usd_est"])

    # Track B: pinned public-mainnet replay bundle (deterministic metadata shapes)
    replay = {
        "snapshot": state["fixture"]["snapshot"],
        "note": "Pinned public-mainnet response shapes frozen for replay; no executable inscription content.",
        "endpoints": [
            "https://mempool.space/api/blocks/tip/height",
            "https://ordinals.com/r/blockheight",
        ],
        "normalized": {
            "earliest_active_uninscribed": state["oracle"]["earliest_active_uninscribed"],
            "earliest_active_inscribed": state["oracle"]["earliest_active_inscribed"],
        },
        "bundle_sha256": hashlib.sha256(
            json.dumps(
                {
                    "snapshot": state["fixture"]["snapshot"],
                    "oracle_keys": sorted(state["oracle"].keys()),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest(),
    }
    write_json(RESULTS / "pinned-mainnet-replay-bundle-meta.json", {
        "bundle_sha256": replay["bundle_sha256"],
        "endpoints": replay["endpoints"],
        "snapshot": replay["snapshot"],
        "note": replay["note"],
    })
    (RAW / "caches" / "pinned-mainnet-replay.json").write_text(json.dumps(replay, indent=2) + "\n")

    track_b = []
    for arm, rep in schedule:
        system, toolkit = arm_config(arm)
        # Same fixture path; score against same oracle (replay uses identical frozen values).
        rec = run_one(
            task={**final_task, "id": "sat-final-replay"},
            arm=arm + "+replay",
            model=model,
            state=state,
            system_prompt=system,
            include_toolkit=toolkit,
            repeat=rep,
            enable_catalyst=True,
            max_turns=args.max_turns,
        )
        rec["track"] = "B"
        rec["replay_bundle_sha256"] = replay["bundle_sha256"]
        track_b.append(rec)
        print("FINAL-B", arm, rep, rec["tests_passed"], rec["cost_usd_est"])

    # Track C: live global only if complete sat index available
    live_status = "Live global result not run — complete sat index unavailable."
    track_c = {"status": live_status, "ran": False}

    by_arm_a: dict[str, list] = {}
    for r in track_a:
        by_arm_a.setdefault(r["arm"], []).append(r)
    write_json(
        RESULTS / "final-exam-results.json",
        {
            "model": model,
            "track_a": {
                "by_arm": {arm: summarize_arm(rs) for arm, rs in by_arm_a.items()},
                "runs": [scrub_record(r) for r in track_a],
            },
            "track_b": {
                "replay_bundle_sha256": replay["bundle_sha256"],
                "runs": [scrub_record(r) for r in track_b],
                "summary": summarize_arm(track_b),
            },
            "track_c": track_c,
            "spend_ledger": load_spend(),
        },
    )


def cmd_freeze_arms(args: argparse.Namespace) -> None:
    state = load_state()
    model = args.model or json.loads((RESULTS / "model-selection.json").read_text())["selected_model"]
    arms = {
        "baseline-harness": {
            "harness_hash": harness_hash(BASELINE_SYSTEM),
            "toolkit_hash": _toolkit_hash(),
            "include_toolkit": False,
            "system_prompt_hash": harness_hash(BASELINE_SYSTEM),
        },
        "halo-harness-only": {
            "harness_hash": harness_hash(HALO_HARNESS_SYSTEM),
            "toolkit_hash": _toolkit_hash(),
            "include_toolkit": False,
            "system_prompt_hash": harness_hash(HALO_HARNESS_SYSTEM),
        },
        "halo-repo-toolkit-only": {
            "harness_hash": harness_hash(BASELINE_SYSTEM),
            "toolkit_hash": _toolkit_hash(),
            "include_toolkit": True,
            "system_prompt_hash": harness_hash(BASELINE_SYSTEM),
        },
        "halo-combined": {
            "harness_hash": harness_hash(HALO_HARNESS_SYSTEM),
            "toolkit_hash": _toolkit_hash(),
            "include_toolkit": True,
            "system_prompt_hash": harness_hash(HALO_HARNESS_SYSTEM),
        },
    }
    payload = {
        "benchmark_version": "sat-hunt-v2",
        "selected_model": model,
        "derived_set_sha256": state["derived_set_sha256"],
        "fixture_sha256": fixture_sha256(state["fixture"]),
        "arms": arms,
        "frozen_at": time.time(),
    }
    write_json(RESULTS / "arms-freeze.json", payload)
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sel = sub.add_parser("select")
    p_sel.add_argument(
        "--models",
        nargs="+",
        default=["deepseek-v4-flash", "gpt-4.1-nano", "gemini-2.5-flash-lite"],
    )
    p_sel.add_argument("--max-turns", type=int, default=10)
    p_sel.set_defaults(func=cmd_select)

    p_base = sub.add_parser("baseline")
    p_base.add_argument("--model", default=None)
    p_base.add_argument("--max-turns", type=int, default=10)
    p_base.set_defaults(func=cmd_baseline)

    p_fr = sub.add_parser("freeze-arms")
    p_fr.add_argument("--model", default=None)
    p_fr.set_defaults(func=cmd_freeze_arms)

    p_hold = sub.add_parser("heldout")
    p_hold.add_argument("--model", default=None)
    p_hold.add_argument("--reps", type=int, default=3)
    p_hold.add_argument("--seed", type=int, default=42)
    p_hold.add_argument("--max-turns", type=int, default=10)
    p_hold.set_defaults(func=cmd_heldout)

    p_final = sub.add_parser("final")
    p_final.add_argument("--model", default=None)
    p_final.add_argument("--reps", type=int, default=3)
    p_final.add_argument("--seed", type=int, default=7)
    p_final.add_argument("--max-turns", type=int, default=12)
    p_final.set_defaults(func=cmd_final)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
