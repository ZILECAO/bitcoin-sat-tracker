#!/usr/bin/env python3
"""Phase 2B runner: model selection, development/held-out arms, scrubbed records."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
import uuid
from pathlib import Path
from typing import Any

from diligence.sat_hunt.agent import BASELINE_SYSTEM, SatHuntAgent
from diligence.sat_hunt.attribution import (
    build_match_index,
    derived_set_hash,
    load_patoshi_csv,
)
from diligence.sat_hunt.fixtures import build_fixture, build_oracle
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
) -> dict[str, Any]:
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
        max_turns=10,
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
    }
    out = RAW / "runs" / f"{task['id']}-{arm}-r{repeat}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2) + "\n")
    return record


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
    # rank models by correctness then cost
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
    selected = ranked[0][0]
    RESULTS.mkdir(parents=True, exist_ok=True)
    payload = {
        "candidates": candidates,
        "smoke_results": [
            {
                k: r[k]
                for k in (
                    "task_id",
                    "model",
                    "tests_passed",
                    "cost_usd_est",
                    "duration_ms",
                    "trace_id",
                    "errors",
                )
            }
            for r in smoke_results
        ],
        "selected_model": selected,
        "ranking": [m for m, _ in ranked],
    }
    (RESULTS / "model-selection.json").write_text(json.dumps(payload, indent=2) + "\n")
    # update freeze with selected model
    from diligence.sat_hunt.agent import harness_hash
    import hashlib
    from diligence.sat_hunt.fixtures import fixture_sha256

    manifest = build_freeze_manifest(
        derived_set_sha256=state["derived_set_sha256"],
        fixture_sha256=fixture_sha256(state["fixture"]),
        selected_model=selected,
        harness_hash=harness_hash(BASELINE_SYSTEM),
        toolkit_hash=hashlib.sha256(
            Path("diligence/sat_hunt/toolkit/fixture_api.py").read_bytes()
        ).hexdigest(),
    )
    write_freeze_manifest(manifest, RESULTS / "freeze-hashes.json")
    write_freeze_manifest(manifest, Path("diligence/sat_hunt/freeze-hashes.json"))
    print("SELECTED", selected)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_sel = sub.add_parser("select")
    p_sel.add_argument(
        "--models",
        nargs="+",
        default=["deepseek-v4-flash", "gpt-4.1-nano", "gemini-2.5-flash-lite"],
    )
    p_sel.set_defaults(func=cmd_select)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
