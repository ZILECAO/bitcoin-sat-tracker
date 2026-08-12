"""Task manifests, prompts, and workspace preparation for sat-hunt."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from diligence.constants import BASELINE_COMMIT, REPO_ROOT
from diligence.isolation import create_baseline_checkout

TASKS_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = TASKS_DIR / "prompts"


DEVELOPMENT_TASKS: list[dict[str, Any]] = [
    {
        "id": "sat-dev-001",
        "family": "ordinal_fifo",
        "scorer_id": "ordinal_fifo",
        "prompt_file": "sat-dev-001.md",
        "answer_name": "answers/fifo.json",
    },
    {
        "id": "sat-dev-002",
        "family": "fees_and_coinbase",
        "scorer_id": "fees_and_coinbase",
        "prompt_file": "sat-dev-002.md",
        "answer_name": "answers/fees.json",
    },
    {
        "id": "sat-dev-003",
        "family": "satpoint_history",
        "scorer_id": "satpoint_history",
        "prompt_file": "sat-dev-003.md",
        "answer_name": "answers/satpoint.json",
    },
    {
        "id": "sat-dev-004",
        "family": "snapshot_utxo",
        "scorer_id": "snapshot_utxo",
        "prompt_file": "sat-dev-004.md",
        "answer_name": "answers/utxo.json",
    },
    {
        "id": "sat-dev-005",
        "family": "activity_proxy",
        "scorer_id": "activity_proxy",
        "prompt_file": "sat-dev-005.md",
        "answer_name": "answers/activity.json",
    },
    {
        "id": "sat-dev-006",
        "family": "inscription_attachment",
        "scorer_id": "inscription_attachment",
        "prompt_file": "sat-dev-006.md",
        "answer_name": "answers/inscriptions.json",
    },
    {
        "id": "sat-dev-007",
        "family": "minimum_certificate",
        "scorer_id": "minimum_certificate",
        "prompt_file": "sat-dev-007.md",
        "answer_name": "answers/minimum.json",
    },
    {
        "id": "sat-dev-008",
        "family": "checkpoint_resume",
        "scorer_id": "checkpoint_resume",
        "prompt_file": "sat-dev-008.md",
        "answer_name": "checkpoint.json",
    },
    {
        "id": "sat-dev-009",
        "family": "evidence_provenance",
        "scorer_id": "evidence_provenance",
        "prompt_file": "sat-dev-009.md",
        "answer_name": "answers/evidence.json",
    },
    {
        "id": "sat-dev-010",
        "family": "new_script",
        "scorer_id": "new_script",
        "prompt_file": "sat-dev-010.md",
        "answer_name": None,
    },
    {
        "id": "sat-dev-011",
        "family": "public_satoshi_attribution",
        "scorer_id": "public_satoshi_attribution",
        "prompt_file": "sat-dev-011.md",
        "answer_name": "answers/attribution.json",
    },
]

HELDOUT_TASKS: list[dict[str, Any]] = [
    {
        "id": "sat-hold-001",
        "family": "fifo_plus_fees",
        "scorer_id": "ordinal_fifo",
        "prompt_file": "sat-hold-001.md",
        "answer_name": "answers/fifo.json",
    },
    {
        "id": "sat-hold-002",
        "family": "activity_plus_utxo",
        "scorer_id": "activity_proxy",
        "prompt_file": "sat-hold-002.md",
        "answer_name": "answers/activity.json",
    },
    {
        "id": "sat-hold-003",
        "family": "inscription_plus_certificate",
        "scorer_id": "inscription_attachment",
        "prompt_file": "sat-hold-003.md",
        "answer_name": "answers/inscriptions.json",
    },
    {
        "id": "sat-hold-004",
        "family": "attribution_plus_evidence",
        "scorer_id": "public_satoshi_attribution",
        "prompt_file": "sat-hold-004.md",
        "answer_name": "answers/attribution.json",
    },
]


PROMPT_TEXT = {
    "sat-dev-001.md": """# Development: Ordinal FIFO

Using only the fixture fee demo tools, implement FIFO sat-range assignment.
Write `answers/fifo.json` with `output_ranges` and `fee_ranges`.
Also write a small unit test file proving your assignment helper.
""",
    "sat-dev-002.md": """# Development: Fees and Coinbase

Using the fixture fee demo, show how leftover fee ranges are reassigned through
the block coinbase. Write `answers/fees.json` with `coinbase_assigned_ranges`.
""",
    "sat-dev-003.md": """# Development: Satpoint History

Trace the earliest active uninscribed sat through the fixture transaction graph.
Write `answers/satpoint.json` with an ordered `hops` list and `final_outpoint`.
""",
    "sat-dev-004.md": """# Development: Snapshot UTXO

Prove one spendable UTXO at the frozen fixture snapshot. Write `answers/utxo.json`
including snapshot_height, snapshot_block_hash, outpoint, spendable=true, and
used_mempool=false.
""",
    "sat-dev-005.md": """# Development: Activity Proxy

Compute transfers_in_activity_window for an active UTXO. Write `answers/activity.json`
with transfers_in_activity_window (>=3), activity_is_proxy=true, and a claim that
does not assert wallet ownership.
""",
    "sat-dev-006.md": """# Development: Inscription Attachment

Find inscriptions for the earliest active inscribed sat. Write
`answers/inscriptions.json` with inscription_ids (include reinscriptions).
""",
    "sat-dev-007.md": """# Development: Minimum Certificate

Produce continuous coverage for [0, earliest_active_uninscribed_sat).
Write `answers/minimum.json` with candidate_sat, complete=true, covered_intervals.
""",
    "sat-dev-008.md": """# Development: Checkpoint Resume

Create a content-addressed cache entry and save checkpoint.json containing
completed_queries and content_hashes so a later run can resume.
""",
    "sat-dev-009.md": """# Development: Evidence Provenance

Write `answers/evidence.json` as a list of evidence objects with id, source,
request, and response_sha256 for at least one fixture query.
""",
    "sat-dev-010.md": """# Development: New Research Script

Write a new Python CLI script and tests that can read fixture snapshot metadata
and print the snapshot height/hash. Do not hard-code the final exam answer.
""",
    "sat-dev-011.md": """# Development: Public Satoshi Attribution

Using fixture UTXOs, determine which current outputs exact-match the frozen
public attribution heuristic concept. Write `answers/attribution.json` with:
csv_sha256 for the pinned Patoshi CSV, record_count 21953,
attributed_current_excluded, moved_nonmatch_excluded, and the required
uncertainty claim language. Do not claim ownership certainty.
""",
    "sat-hold-001.md": """# Held-out: FIFO + fee leftover

Solve the fixture FIFO assignment and include fee ranges in answers/fifo.json.
Write a test.
""",
    "sat-hold-002.md": """# Held-out: Activity + snapshot discipline

Produce answers/activity.json for an active circulating UTXO with proxy language.
""",
    "sat-hold-003.md": """# Held-out: Inscription set

Write answers/inscriptions.json for the fixture's earliest active inscribed sat.
""",
    "sat-hold-004.md": """# Held-out: Attribution matching

Write answers/attribution.json distinguishing exact current-output matches from
Patoshi-origin-but-moved non-matches, with uncertainty language.
""",
}


def ensure_prompts() -> None:
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in PROMPT_TEXT.items():
        path = PROMPTS_DIR / name
        if not path.exists():
            path.write_text(text.strip() + "\n", encoding="utf-8")
    # final exam already exists


def write_manifests() -> None:
    ensure_prompts()
    (TASKS_DIR / "heldout.json").write_text(json.dumps(HELDOUT_TASKS, indent=2) + "\n")
    # keep development.json family list; write expanded runtime manifest
    (TASKS_DIR / "development_tasks.json").write_text(
        json.dumps(DEVELOPMENT_TASKS, indent=2) + "\n"
    )


def prepare_task_workspace(
    dest: Path,
    *,
    fixture: dict[str, Any],
    include_toolkit: bool = False,
    repo_root: Path | None = None,
) -> Path:
    """Create an isolated baseline checkout and copy public fixture materials."""
    create_baseline_checkout(dest, repo_root=repo_root or REPO_ROOT)
    (dest / "answers").mkdir(exist_ok=True)
    (dest / "tests").mkdir(exist_ok=True)
    (dest / "fixture.json").write_text(json.dumps(fixture, indent=2) + "\n")
    # Copy public benchmark definition only
    shutil.copy2(TASKS_DIR / "benchmark.json", dest / "benchmark.json")
    if include_toolkit:
        toolkit_src = TASKS_DIR / "toolkit" / "fixture_api.py"
        pkg = dest / "sat_hunt_toolkit"
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text("from .fixture_api import *\n")
        shutil.copy2(toolkit_src, pkg / "fixture_api.py")
    # Ensure no diligence evaluator leakage
    for banned in ("AGENTS.md", "docs", "diligence"):
        path = dest / banned
        if path.exists():
            raise RuntimeError(f"task workspace contains banned path: {banned}")
    return dest


def load_prompt(task: dict[str, Any]) -> str:
    ensure_prompts()
    return (PROMPTS_DIR / task["prompt_file"]).read_text(encoding="utf-8")
