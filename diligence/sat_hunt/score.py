"""Correctness-first scoring for the held-out sat-hunt final exam."""

from __future__ import annotations

import re
from typing import Any

HEX_64 = re.compile(r"^[0-9a-f]{64}$")
OUTPOINT = re.compile(r"^[0-9a-f]{64}:[0-9]+$")
TRACE_ID = re.compile(r"^[0-9a-f]{32}$")


class SatHuntValidationError(ValueError):
    """Raised when a final-exam answer is incomplete or misleading."""


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SatHuntValidationError(f"{label} must be an object")
    return value


def _require_keys(value: dict[str, Any], keys: tuple[str, ...], label: str) -> None:
    missing = [key for key in keys if key not in value]
    if missing:
        raise SatHuntValidationError(f"{label} missing required fields: {missing}")


def _require_non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SatHuntValidationError(f"{label} must be a non-negative integer")
    return value


def _validate_candidate(value: Any, label: str, *, require_inscription: bool) -> dict[str, Any]:
    candidate = _require_object(value, label)
    _require_keys(
        candidate,
        (
            "sat_number",
            "outpoint",
            "offset",
            "script_type",
            "current_output_height",
            "transfers_in_activity_window",
            "inscription_ids",
            "evidence_refs",
        ),
        label,
    )
    _require_non_negative_int(candidate["sat_number"], f"{label}.sat_number")
    _require_non_negative_int(candidate["offset"], f"{label}.offset")
    _require_non_negative_int(
        candidate["current_output_height"], f"{label}.current_output_height"
    )
    _require_non_negative_int(
        candidate["transfers_in_activity_window"],
        f"{label}.transfers_in_activity_window",
    )
    if not isinstance(candidate["outpoint"], str) or not OUTPOINT.match(candidate["outpoint"]):
        raise SatHuntValidationError(f"{label}.outpoint must be txid:vout")
    if not isinstance(candidate["script_type"], str) or not candidate["script_type"]:
        raise SatHuntValidationError(f"{label}.script_type must be a non-empty string")
    for field in ("inscription_ids", "evidence_refs"):
        if not isinstance(candidate[field], list) or not all(
            isinstance(item, str) and item for item in candidate[field]
        ):
            raise SatHuntValidationError(f"{label}.{field} must be a list of strings")
    if require_inscription and not candidate["inscription_ids"]:
        raise SatHuntValidationError(f"{label} must contain at least one inscription")
    return candidate


def _validate_minimality(value: Any, candidate_sat: int, label: str) -> dict[str, Any]:
    proof = _require_object(value, label)
    _require_keys(proof, ("candidate_sat", "complete", "covered_intervals"), label)
    if proof["candidate_sat"] != candidate_sat:
        raise SatHuntValidationError(f"{label}.candidate_sat does not match candidate")
    if proof["complete"] is not True:
        raise SatHuntValidationError(f"{label}.complete must be true")
    intervals = proof["covered_intervals"]
    if not isinstance(intervals, list):
        raise SatHuntValidationError(f"{label}.covered_intervals must be a list")

    cursor = 0
    for index, raw in enumerate(intervals):
        interval = _require_object(raw, f"{label}.covered_intervals[{index}]")
        _require_keys(interval, ("start", "end", "reason", "evidence_refs"), label)
        start = _require_non_negative_int(interval["start"], f"{label}[{index}].start")
        end = _require_non_negative_int(interval["end"], f"{label}[{index}].end")
        if start != cursor or end <= start or end > candidate_sat:
            raise SatHuntValidationError(
                f"{label} intervals must continuously cover [0, candidate_sat)"
            )
        if not isinstance(interval["reason"], str) or not interval["reason"]:
            raise SatHuntValidationError(f"{label}[{index}].reason must be non-empty")
        if not isinstance(interval["evidence_refs"], list) or not interval["evidence_refs"]:
            raise SatHuntValidationError(f"{label}[{index}] needs evidence refs")
        cursor = end
    if cursor != candidate_sat:
        raise SatHuntValidationError(
            f"{label} intervals must continuously cover [0, candidate_sat)"
        )
    return proof


def validate_final_answer(answer: Any) -> dict[str, Any]:
    """Validate output structure and claims without consulting hidden truth."""
    answer = _require_object(answer, "answer")
    _require_keys(
        answer,
        (
            "benchmark_version",
            "snapshot",
            "interpretation",
            "earliest_active_sat",
            "earliest_active_inscribed_sat",
            "active_sat_minimality",
            "inscribed_sat_minimality",
            "evidence",
            "artifacts",
            "run",
        ),
        "answer",
    )
    if answer["benchmark_version"] != "sat-hunt-v1":
        raise SatHuntValidationError("benchmark_version must be sat-hunt-v1")

    snapshot = _require_object(answer["snapshot"], "snapshot")
    _require_keys(snapshot, ("height", "block_hash", "confirmations"), "snapshot")
    _require_non_negative_int(snapshot["height"], "snapshot.height")
    _require_non_negative_int(snapshot["confirmations"], "snapshot.confirmations")
    if not isinstance(snapshot["block_hash"], str) or not HEX_64.match(snapshot["block_hash"]):
        raise SatHuntValidationError("snapshot.block_hash must be 64 lowercase hex characters")

    interpretation = _require_object(answer["interpretation"], "interpretation")
    _require_keys(
        interpretation,
        ("earliest_means", "activity_is_proxy", "wallet_attribution"),
        "interpretation",
    )
    if interpretation["earliest_means"] != "lowest ordinal sat number":
        raise SatHuntValidationError("earliest must mean lowest ordinal sat number")
    if interpretation["activity_is_proxy"] is not True:
        raise SatHuntValidationError("answer must state that activity is a proxy")
    if interpretation["wallet_attribution"] != "not inferable from blockchain data":
        raise SatHuntValidationError("answer must not claim wallet ownership from chain data")

    active = _validate_candidate(answer["earliest_active_sat"], "earliest_active_sat", require_inscription=False)
    inscribed = _validate_candidate(
        answer["earliest_active_inscribed_sat"],
        "earliest_active_inscribed_sat",
        require_inscription=True,
    )
    _validate_minimality(
        answer["active_sat_minimality"], active["sat_number"], "active_sat_minimality"
    )
    _validate_minimality(
        answer["inscribed_sat_minimality"],
        inscribed["sat_number"],
        "inscribed_sat_minimality",
    )

    evidence = answer["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise SatHuntValidationError("evidence must be a non-empty list")
    evidence_ids: set[str] = set()
    for index, raw in enumerate(evidence):
        item = _require_object(raw, f"evidence[{index}]")
        _require_keys(item, ("id", "source", "request", "response_sha256"), "evidence")
        if not isinstance(item["id"], str) or not item["id"] or item["id"] in evidence_ids:
            raise SatHuntValidationError("evidence IDs must be non-empty and unique")
        evidence_ids.add(item["id"])
        if not isinstance(item["response_sha256"], str) or not HEX_64.match(item["response_sha256"]):
            raise SatHuntValidationError("evidence response_sha256 must be 64 lowercase hex")

    referenced = set(active["evidence_refs"]) | set(inscribed["evidence_refs"])
    for proof_name in ("active_sat_minimality", "inscribed_sat_minimality"):
        for interval in answer[proof_name]["covered_intervals"]:
            referenced.update(interval["evidence_refs"])
    if missing := sorted(referenced - evidence_ids):
        raise SatHuntValidationError(f"unknown evidence references: {missing}")

    artifacts = _require_object(answer["artifacts"], "artifacts")
    _require_keys(artifacts, ("scripts", "tests", "test_command", "tests_passed"), "artifacts")
    if artifacts["tests_passed"] is not True:
        raise SatHuntValidationError("generated script tests must pass")
    for field in ("scripts", "tests"):
        if not isinstance(artifacts[field], list) or not artifacts[field]:
            raise SatHuntValidationError(f"artifacts.{field} must be non-empty")

    run = _require_object(answer["run"], "run")
    _require_keys(
        run,
        ("model", "harness", "trace_id", "duration_ms", "cost_usd", "tool_calls"),
        "run",
    )
    if not isinstance(run["trace_id"], str) or not TRACE_ID.match(run["trace_id"]):
        raise SatHuntValidationError("run.trace_id must be 32 lowercase hex characters")
    _require_non_negative_int(run["duration_ms"], "run.duration_ms")
    _require_non_negative_int(run["tool_calls"], "run.tool_calls")
    if not isinstance(run["cost_usd"], (int, float)) or isinstance(run["cost_usd"], bool) or run["cost_usd"] < 0:
        raise SatHuntValidationError("run.cost_usd must be a non-negative number")
    return answer


def score_final_answer(answer: Any, oracle: Any) -> dict[str, Any]:
    """Compare a valid answer with a hidden deterministic oracle.

    Efficiency metrics are reported but never compensate for a wrong answer.
    """
    answer = validate_final_answer(answer)
    oracle = _require_object(oracle, "oracle")
    _require_keys(
        oracle,
        (
            "benchmark_version",
            "snapshot",
            "earliest_active_sat",
            "earliest_active_inscribed_sat",
        ),
        "oracle",
    )
    checks = {
        "benchmark_version": oracle["benchmark_version"] == answer["benchmark_version"],
        "snapshot_height": oracle["snapshot"]["height"] == answer["snapshot"]["height"],
        "snapshot_hash": oracle["snapshot"]["block_hash"] == answer["snapshot"]["block_hash"],
        "active_sat_number": oracle["earliest_active_sat"]["sat_number"]
        == answer["earliest_active_sat"]["sat_number"],
        "active_outpoint": oracle["earliest_active_sat"]["outpoint"]
        == answer["earliest_active_sat"]["outpoint"],
        "active_inscriptions": sorted(oracle["earliest_active_sat"]["inscription_ids"])
        == sorted(answer["earliest_active_sat"]["inscription_ids"]),
        "inscribed_sat_number": oracle["earliest_active_inscribed_sat"]["sat_number"]
        == answer["earliest_active_inscribed_sat"]["sat_number"],
        "inscribed_outpoint": oracle["earliest_active_inscribed_sat"]["outpoint"]
        == answer["earliest_active_inscribed_sat"]["outpoint"],
        "inscribed_ids": sorted(oracle["earliest_active_inscribed_sat"]["inscription_ids"])
        == sorted(answer["earliest_active_inscribed_sat"]["inscription_ids"]),
    }
    correct = all(checks.values())
    return {
        "correct": correct,
        "checks": checks,
        "efficiency_eligible": correct,
        "duration_ms": answer["run"]["duration_ms"] if correct else None,
        "cost_usd": answer["run"]["cost_usd"] if correct else None,
        "tool_calls": answer["run"]["tool_calls"] if correct else None,
        "ranking": "correctness first; among correct runs, lower cost then lower duration",
    }
