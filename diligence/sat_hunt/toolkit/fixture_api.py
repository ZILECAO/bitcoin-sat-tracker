"""Reusable Bitcoin/ord fixture toolkit helpers for task workspaces.

This module is copied into disposable task workspaces when the toolkit arm is
enabled. It does not contain hidden oracle answers.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def load_fixture(path: str | Path = "fixture.json") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_json(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def evidence_item(*, evidence_id: str, source: str, request: dict[str, Any], response: Any) -> dict[str, Any]:
    return {
        "id": evidence_id,
        "source": source,
        "request": request,
        "response_sha256": sha256_json(response),
    }


def is_active_utxo(utxo: dict[str, Any], *, window_start: int, min_transfers: int = 3) -> bool:
    return bool(
        utxo.get("spendable")
        and not utxo.get("provably_unspendable")
        and int(utxo.get("height") or -1) >= window_start
        and int(utxo.get("transfers_in_activity_window") or 0) >= min_transfers
    )


def continuous_certificate(candidate_sat: int, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
    if candidate_sat < 0:
        raise ValueError("candidate_sat must be non-negative")
    if candidate_sat == 0:
        return {"candidate_sat": 0, "complete": True, "covered_intervals": []}
    return {
        "candidate_sat": candidate_sat,
        "complete": True,
        "covered_intervals": [
            {
                "start": 0,
                "end": candidate_sat,
                "reason": reason,
                "evidence_refs": evidence_refs,
            }
        ],
    }
