"""Privacy canaries and secret-pattern checks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from diligence.constants import CANARIES_PATH, PROHIBITED_COMMIT_PATTERNS


class PrivacyError(RuntimeError):
    """Raised when privacy or secret checks fail."""


def load_canaries(path: Path | None = None) -> dict[str, Any]:
    canary_path = path or CANARIES_PATH
    data = json.loads(canary_path.read_text(encoding="utf-8"))
    required_locations = {
        "user_prompt",
        "model_response",
        "tool_name",
        "tool_arguments",
        "tool_result",
        "repository_file",
        "outside_workspace_file",
        "synthetic_environment_variable",
        "fake_api_key_shaped_value",
        "url_query_and_header_shaped_value",
    }
    missing = required_locations - set(data.get("canaries", {}))
    if missing:
        raise PrivacyError(f"canary matrix missing locations: {sorted(missing)}")
    for key, entry in data["canaries"].items():
        value = entry.get("value", "")
        if not isinstance(value, str) or "FAKE" not in value.upper() and "CANARY" not in value.upper():
            # Allow structured values that still declare fake/canary in the id.
            if "FAKE" not in key.upper() and "CANARY" not in str(entry.get("id", "")).upper():
                raise PrivacyError(f"canary {key} is not clearly labeled fake")
        if re.search(r"sk-live-|sk-proj-[A-Za-z0-9]{20,}", value):
            raise PrivacyError("canary resembles a real provider credential")
    return data


def canary_values(path: Path | None = None) -> list[str]:
    data = load_canaries(path)
    values = []
    for entry in data["canaries"].values():
        values.append(entry["value"])
        values.append(entry.get("id", ""))
    return [v for v in values if v]


def scan_text_for_canaries(text: str, *, path: Path | None = None) -> list[str]:
    hits = []
    for value in canary_values(path):
        if value and value in text:
            hits.append(value)
    return hits


def scan_text_for_secrets(text: str) -> list[str]:
    hits = []
    for pattern in PROHIBITED_COMMIT_PATTERNS:
        match = re.search(pattern, text)
        if match:
            hits.append(match.group(0)[:80])
    return hits


def compare_secret_in_memory(candidate: str, expected: str) -> bool:
    """Compare a future real secret only in memory; return pass/fail only."""
    if not candidate or not expected:
        return False
    # Constant-time-ish compare for future use; no secret is logged.
    if len(candidate) != len(expected):
        return False
    result = 0
    for a, b in zip(candidate.encode("utf-8"), expected.encode("utf-8")):
        result |= a ^ b
    return result == 0


def validate_privacy_matrix(matrix: dict[str, Any] | None = None) -> dict[str, Any]:
    data = matrix or load_canaries()
    channels = data.get("channels")
    if not isinstance(channels, list) or not channels:
        raise PrivacyError("privacy matrix requires channels list")
    expected_channels = {
        "codex_jsonl",
        "local_halo_storage",
        "hosted_catalyst_trace_tree",
        "raw_catalyst_span_json",
        "downloaded_traces",
        "cli_output",
        "evaluator_output",
        "scrubbed_committed_reports",
    }
    if set(channels) != expected_channels:
        raise PrivacyError(f"unexpected privacy channels: {sorted(set(channels))}")
    allowed_states = {"present", "redacted", "hashed", "truncated", "absent", "not_yet_measured"}
    for key, entry in data["canaries"].items():
        states = entry.get("states")
        if not isinstance(states, dict):
            raise PrivacyError(f"canary {key} missing states map")
        if set(states) != expected_channels:
            raise PrivacyError(f"canary {key} incomplete channel coverage")
        for channel, state in states.items():
            if state not in allowed_states:
                raise PrivacyError(f"canary {key} invalid state for {channel}: {state}")
    return data


def reject_prohibited_artifacts(paths: list[Path]) -> None:
    for path in paths:
        name = path.name.lower()
        if name == ".env" or name.startswith(".env.") or name.endswith(".env"):
            raise PrivacyError(f"prohibited artifact: {path}")
        if name.endswith((".tgz", ".tar", ".tar.gz", ".zip")) and "vendor" in str(path).lower():
            raise PrivacyError(f"vendor archive must not be staged: {path}")
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise PrivacyError(f"cannot read {path}: {exc}") from exc
            secrets = scan_text_for_secrets(text)
            if secrets:
                raise PrivacyError(f"secret-like material in {path}")
            # Raw prompt/trace bodies should not be committed.
            if '"raw_prompt"' in text or '"provider_response"' in text or '"trace_body"' in text:
                if "schema" not in name and "test" not in str(path):
                    # Allow schema docs / tests that mention field names.
                    if path.suffix == ".json" and "scrubbed" not in name:
                        raise PrivacyError(f"raw payload fields in {path}")
