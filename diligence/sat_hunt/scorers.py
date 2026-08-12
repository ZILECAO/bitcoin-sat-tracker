"""Hidden scorers for sat-hunt development and held-out tasks.

Scorers stay outside task-agent workspaces. They inspect generated scripts,
tests, and answer artifacts using the deterministic fixture and oracle.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from diligence.sat_hunt.attribution import (
    EXPECTED_CSV_SHA256,
    EXPECTED_RECORDS,
    CurrentOutputIdentity,
    match_current_output,
    p2pk_script_hex,
    p2pkh_address_mainnet,
    verify_csv_bytes,
)
from diligence.sat_hunt.ordinal import assign_ordinal_ranges, locate_sat
from diligence.sat_hunt.score import (
    ATTRIBUTION_PASS_CLAIM,
    score_final_answer,
    validate_final_answer,
)


@dataclass
class ScoreResult:
    scorer_id: str
    passed: bool
    checks: list[dict[str, Any]] = field(default_factory=list)
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "scorer_id": self.scorer_id,
            "passed": self.passed,
            "checks": self.checks,
            "detail": self.detail,
        }


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "passed": bool(ok), "detail": detail}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_object(data: Any) -> dict[str, Any] | None:
    return data if isinstance(data, dict) else None


def score_ordinal_fifo(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    demo = fixture["fee_demo"]
    answer_path = workspace / "answers" / "fifo.json"
    checks = [_check("answer_exists", answer_path.exists())]
    if not answer_path.exists():
        return ScoreResult("ordinal_fifo", False, checks, "missing answers/fifo.json")
    data = _read_json(answer_path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("ordinal_fifo", False, checks, "answer not object")
    expected_out, expected_fee = assign_ordinal_ranges(demo["input_ranges"], demo["output_values"])
    checks.append(_check("output_ranges", data.get("output_ranges") == expected_out))
    checks.append(_check("fee_ranges", data.get("fee_ranges") == expected_fee))
    tests = list(workspace.glob("tests/test_*.py")) + list(workspace.glob("test_*.py"))
    checks.append(_check("has_tests", bool(tests)))
    return ScoreResult("ordinal_fifo", all(c["passed"] for c in checks), checks)


def score_fees_and_coinbase(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "fees.json"
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("fees_and_coinbase", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("fees_and_coinbase", False, checks)
    expected = fixture["fee_demo"]["coinbase_fee_reassignment"]["assigned_ranges"]
    checks.append(_check("coinbase_ranges", data.get("coinbase_assigned_ranges") == expected))
    checks.append(_check("mentions_coinbase", "coinbase" in json.dumps(data).lower()))
    return ScoreResult("fees_and_coinbase", all(c["passed"] for c in checks), checks)


def score_satpoint_history(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "satpoint.json"
    sat = fixture["tracked_sats"]["earliest_active_uninscribed"]
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("satpoint_history", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("satpoint_history", False, checks)
    hops = data.get("hops") or data.get("history") or []
    checks.append(_check("has_hops", isinstance(hops, list) and len(hops) >= 4))
    final = fixture["sat_index"][str(sat)]["outpoint"]
    checks.append(
        _check(
            "ends_at_current",
            any(final in json.dumps(h) for h in hops) or data.get("final_outpoint") == final,
        )
    )
    return ScoreResult("satpoint_history", all(c["passed"] for c in checks), checks)


def score_snapshot_utxo(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "utxo.json"
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("snapshot_utxo", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("snapshot_utxo", False, checks)
    checks.append(_check("height", data.get("snapshot_height") == fixture["snapshot"]["height"]))
    checks.append(
        _check("block_hash", data.get("snapshot_block_hash") == fixture["snapshot"]["block_hash"])
    )
    checks.append(_check("spendable", data.get("spendable") is True))
    checks.append(_check("no_mempool", data.get("used_mempool") is not True))
    return ScoreResult("snapshot_utxo", all(c["passed"] for c in checks), checks)


def score_activity_proxy(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "activity.json"
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("activity_proxy", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("activity_proxy", False, checks)
    checks.append(
        _check(
            "transfers",
            isinstance(data.get("transfers_in_activity_window"), int)
            and data["transfers_in_activity_window"] >= 3,
        )
    )
    checks.append(_check("proxy_language", data.get("activity_is_proxy") is True))
    claim = str(data.get("claim") or "")
    checks.append(_check("no_ownership_claim", "definitely" not in claim.lower()))
    return ScoreResult("activity_proxy", all(c["passed"] for c in checks), checks)


def score_inscription_attachment(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "inscriptions.json"
    sat = fixture["tracked_sats"]["earliest_active_inscribed"]
    expected = fixture["sat_index"][str(sat)]["inscription_ids"]
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("inscription_attachment", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("inscription_attachment", False, checks)
    got = data.get("inscription_ids") or []
    checks.append(_check("ids_match", sorted(got) == sorted(expected)))
    checks.append(_check("reinscription_count", len(got) >= 2))
    return ScoreResult("inscription_attachment", all(c["passed"] for c in checks), checks)


def score_minimum_certificate(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "minimum.json"
    sat = fixture["tracked_sats"]["earliest_active_uninscribed"]
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("minimum_certificate", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("minimum_certificate", False, checks)
    intervals = data.get("covered_intervals") or []
    checks.append(_check("complete", data.get("complete") is True))
    checks.append(_check("candidate", data.get("candidate_sat") == sat))
    cursor = 0
    continuous = True
    for interval in intervals:
        if interval.get("start") != cursor or interval.get("end", 0) <= cursor:
            continuous = False
            break
        cursor = interval["end"]
    checks.append(_check("continuous", continuous and cursor == sat))
    return ScoreResult("minimum_certificate", all(c["passed"] for c in checks), checks)


def score_checkpoint_resume(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    cache = workspace / "cache"
    checkpoint = workspace / "checkpoint.json"
    checks = [
        _check("cache_dir", cache.exists()),
        _check("checkpoint", checkpoint.exists()),
    ]
    if checkpoint.exists():
        data = _read_json(checkpoint)
        if not isinstance(data, dict):
            checks.append(_check("checkpoint_object", False))
        else:
            checks.append(_check("has_entries", bool(data.get("completed_queries"))))
            checks.append(_check("content_addressed", bool(data.get("content_hashes"))))
    return ScoreResult("checkpoint_resume", all(c["passed"] for c in checks), checks)


def score_evidence_provenance(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    path = workspace / "answers" / "evidence.json"
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("evidence_provenance", False, checks)
    data = _read_json(path)
    items = data if isinstance(data, list) else data.get("evidence") or []
    checks.append(_check("non_empty", bool(items)))
    ok = True
    for item in items:
        if not all(k in item for k in ("id", "source", "request", "response_sha256")):
            ok = False
        sha = item.get("response_sha256", "")
        if not isinstance(sha, str) or len(sha) != 64:
            ok = False
    checks.append(_check("shape", ok))
    return ScoreResult("evidence_provenance", all(c["passed"] for c in checks), checks)


def score_new_script(workspace: Path, fixture: dict[str, Any]) -> ScoreResult:
    scripts = list(workspace.glob("**/*.py"))
    scripts = [p for p in scripts if "test" not in p.name.lower()]
    tests = list(workspace.glob("**/test_*.py"))
    checks = [
        _check("has_script", bool(scripts)),
        _check("has_tests", bool(tests)),
    ]
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in scripts[:10])
    checks.append(_check("mentions_rpc_or_ord", bool(re.search(r"rpc|ord|bitcoin|sat", text, re.I))))
    return ScoreResult("new_script", all(c["passed"] for c in checks), checks)


def score_public_satoshi_attribution(
    workspace: Path, fixture: dict[str, Any], match_index: dict[str, list[str]]
) -> ScoreResult:
    path = workspace / "answers" / "attribution.json"
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("public_satoshi_attribution", False, checks)
    data = _read_json(path)
    if not isinstance(data, dict):
        checks.append(_check("answer_object", False, "expected JSON object"))
        return ScoreResult("public_satoshi_attribution", False, checks)
    checks.append(_check("csv_sha", data.get("csv_sha256") == EXPECTED_CSV_SHA256))
    checks.append(_check("records", data.get("record_count") == EXPECTED_RECORDS))
    tracked = fixture["tracked_sats"]
    # Must exclude attributed current and accept moved non-match
    attr_info = fixture["sat_index"][str(tracked["attributed_current"])]
    moved_info = fixture["sat_index"][str(tracked["patoshi_origin_moved"])]
    checks.append(
        _check(
            "excludes_current_match",
            data.get("attributed_current_excluded") is True
            or data.get("results", {}).get(str(tracked["attributed_current"]), {}).get("excluded")
            is True,
        )
    )
    checks.append(
        _check(
            "allows_moved_nonmatch",
            data.get("moved_nonmatch_excluded") is False
            or data.get("results", {}).get(str(tracked["patoshi_origin_moved"]), {}).get("excluded")
            is False,
        )
    )
    claim = str(data.get("claim") or data.get("uncertainty") or "")
    checks.append(
        _check(
            "uncertainty_language",
            ATTRIBUTION_PASS_CLAIM in claim
            or "does not prove who controls the output" in claim,
        )
    )
    # Independent verification using match index
    u = fixture["utxos"][attr_info["outpoint"]]
    res = match_current_output(
        CurrentOutputIdentity(
            outpoint=attr_info["outpoint"],
            script_pubkey_hex=u.get("script_pubkey"),
            address=u.get("address"),
            public_key_hex=u.get("public_key"),
        ),
        match_index,
    )
    checks.append(_check("fixture_attr_really_matches", res["excluded"] is True))
    return ScoreResult("public_satoshi_attribution", all(c["passed"] for c in checks), checks)


def score_final_exam(
    workspace: Path, fixture: dict[str, Any], oracle: dict[str, Any]
) -> ScoreResult:
    path = workspace / "answer.json"
    checks = [_check("answer_exists", path.exists())]
    if not path.exists():
        return ScoreResult("final_exam", False, checks)
    try:
        answer = validate_final_answer(_read_json(path))
        result = score_final_answer(answer, oracle)
    except Exception as exc:
        return ScoreResult("final_exam", False, [_check("valid", False, str(exc))])
    checks.append(_check("correct", result["correct"]))
    for name, ok in result["checks"].items():
        checks.append(_check(name, ok))
    scripts = answer["artifacts"]["scripts"]
    checks.append(
        _check(
            "scripts_exist",
            all((workspace / rel).exists() for rel in scripts),
        )
    )
    return ScoreResult("final_exam", all(c["passed"] for c in checks), checks, detail=json.dumps(result))


SCORERS: dict[str, Callable[..., ScoreResult]] = {
    "ordinal_fifo": score_ordinal_fifo,
    "fees_and_coinbase": score_fees_and_coinbase,
    "satpoint_history": score_satpoint_history,
    "snapshot_utxo": score_snapshot_utxo,
    "activity_proxy": score_activity_proxy,
    "inscription_attachment": score_inscription_attachment,
    "minimum_certificate": score_minimum_certificate,
    "checkpoint_resume": score_checkpoint_resume,
    "evidence_provenance": score_evidence_provenance,
    "new_script": score_new_script,
    "public_satoshi_attribution": score_public_satoshi_attribution,
    "final_exam": score_final_exam,
}
