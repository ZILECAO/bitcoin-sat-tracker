"""Phase 2 offline helpers: synthetic Bitcoin agent traces and export attempts.

These helpers never load held-out answers or scorers. They emit only public
synthetic canaries and deterministic tool results for Catalyst/HALO demos.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from diligence.privacy import load_canaries


SERVICE_NAME = "bitcoin-sat-tracker-diligence"
DEV_TASK_IDS = [
    "btc-dev-001",
    "btc-dev-002",
    "btc-dev-003",
    "btc-dev-004",
    "btc-dev-005",
    "btc-dev-006",
]


def _utc_ns(ts: float | None = None) -> str:
    t = ts if ts is not None else time.time()
    # HALO fixtures use 9 fractional digits.
    whole = int(t)
    frac = int((t - whole) * 1_000_000_000)
    dt = datetime.fromtimestamp(whole, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{frac:09d}Z"


def _hex_id(nbytes: int = 8) -> str:
    return uuid.uuid4().hex[: nbytes * 2]


def deterministic_bitcoin_tools() -> dict[str, Any]:
    """Fake Bitcoin tools — no network, no wallet, synthetic only."""
    return {
        "block_reward": {
            "args": {"height": 210000},
            "result": {"sats": 2500000000},
        },
        "parse_satpoint": {
            "args": {"satpoint": "abcd" * 16 + ":0:0"},
            "result": {"txid": "abcd" * 16, "vout": 0, "offset": 0, "valid": True},
        },
        "mempool_outspend_lookup": {
            "args": {"txid": "deadbeef" * 8, "vout": 0},
            "result": {"spent": False, "txid": None},
        },
    }


def build_development_trace_spans(*, task_id: str, repeat: int = 1) -> list[dict[str, Any]]:
    """Build nested AGENT / LLM / TOOL spans for one development task."""
    canaries = load_canaries()["canaries"]
    tools = deterministic_bitcoin_tools()
    trace_id = hashlib.sha256(f"{task_id}-r{repeat}".encode()).hexdigest()[:32]
    root_id = _hex_id()
    llm_id = _hex_id()
    tool_id = _hex_id()
    t0 = time.time()
    resource = {
        "attributes": {
            "service.name": SERVICE_NAME,
            "service.version": "0.1.0",
            "deployment.environment": "diligence-phase2",
        }
    }
    scope = {"name": "diligence.phase2.synthetic", "version": "0.1.0"}
    prompt_canary = canaries["user_prompt"]["value"]
    response_canary = canaries["model_response"]["value"]
    tool_name_canary = canaries["tool_name"]["value"]
    tool_args_canary = canaries["tool_arguments"]["value"]
    tool_result_canary = canaries["tool_result"]["value"]

    root = {
        "trace_id": trace_id,
        "span_id": root_id,
        "parent_span_id": "",
        "trace_state": "",
        "name": f"synthetic-agent.{task_id}",
        "kind": "SPAN_KIND_INTERNAL",
        "start_time": _utc_ns(t0),
        "end_time": _utc_ns(t0 + 1.2),
        "status": {"code": "STATUS_CODE_OK", "message": ""},
        "resource": resource,
        "scope": scope,
        "attributes": {
            "openinference.span.kind": "AGENT",
            "inference.export.schema_version": 1,
            "inference.observation_kind": "AGENT",
            "inference.agent_name": "synthetic-bitcoin-agent",
            "inference.task_id": task_id,
            "agent.name": "synthetic-bitcoin-agent",
            "input.value": f"Public synthetic task {task_id}. Canary={prompt_canary}",
            "output.value": f"Completed synthetic steps. Canary={response_canary}",
        },
    }
    llm = {
        "trace_id": trace_id,
        "span_id": llm_id,
        "parent_span_id": root_id,
        "trace_state": "",
        "name": "chat.completions.create",
        "kind": "SPAN_KIND_CLIENT",
        "start_time": _utc_ns(t0 + 0.05),
        "end_time": _utc_ns(t0 + 0.55),
        "status": {"code": "STATUS_CODE_OK", "message": ""},
        "resource": resource,
        "scope": scope,
        "attributes": {
            "openinference.span.kind": "LLM",
            "llm.provider": "inference.net",
            "llm.model_name": "unconfigured-pending-egress",
            "llm.token_count.prompt": 128,
            "llm.token_count.completion": 64,
            "llm.token_count.total": 192,
            "input.value": f"Plan tool calls for {task_id}. {prompt_canary}",
            "output.value": f"Call block_reward then parse_satpoint. {response_canary}",
            "inference.task_id": task_id,
        },
    }
    tool = {
        "trace_id": trace_id,
        "span_id": tool_id,
        "parent_span_id": root_id,
        "trace_state": "",
        "name": tool_name_canary,
        "kind": "SPAN_KIND_INTERNAL",
        "start_time": _utc_ns(t0 + 0.6),
        "end_time": _utc_ns(t0 + 0.9),
        "status": {"code": "STATUS_CODE_OK", "message": ""},
        "resource": resource,
        "scope": scope,
        "attributes": {
            "openinference.span.kind": "TOOL",
            "tool.name": "block_reward",
            "tool.parameters": json.dumps(
                {**tools["block_reward"]["args"], "canary": tool_args_canary}
            ),
            "output.value": json.dumps(
                {**tools["block_reward"]["result"], "canary": tool_result_canary}
            ),
            "inference.task_id": task_id,
        },
    }
    return [root, llm, tool]


def write_development_jsonl(dest: Path) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    spans: list[dict[str, Any]] = []
    for task_id in DEV_TASK_IDS:
        spans.extend(build_development_trace_spans(task_id=task_id))
    with dest.open("w", encoding="utf-8") as fh:
        for span in spans:
            fh.write(json.dumps(span, separators=(",", ":")) + "\n")
    digest = hashlib.sha256(dest.read_bytes()).hexdigest()
    return {
        "path": str(dest),
        "span_count": len(spans),
        "task_ids": list(DEV_TASK_IDS),
        "sha256": digest,
        "bytes": dest.stat().st_size,
        "held_out_included": False,
    }


def attempt_otlp_export_python(spans_meta: dict[str, Any]) -> dict[str, Any]:
    """Attempt Catalyst OTLP export via pinned catalyst-tracing. Never logs secrets."""
    result: dict[str, Any] = {
        "sdk": "catalyst-tracing==0.1.8",
        "endpoint_configured": os.environ.get("CATALYST_OTLP_ENDPOINT"),
        "service_name": os.environ.get("CATALYST_SERVICE_NAME", SERVICE_NAME),
        "token_present": bool(os.environ.get("CATALYST_OTLP_TOKEN")),
        "ok": False,
        "error": None,
        "note": None,
    }
    try:
        # Import from isolated venv path if available.
        from catalyst_tracing import agent_span, setup  # type: ignore
    except Exception as exc:  # pragma: no cover - environment specific
        result["error"] = f"{type(exc).__name__}: import_failed"
        result["note"] = "Import catalyst_tracing from vendor venv before calling."
        return result

    try:
        tracing = setup(
            endpoint=os.environ.get("CATALYST_OTLP_ENDPOINT", "https://telemetry.inference.net"),
            service_name=result["service_name"],
            # token resolved from CATALYST_OTLP_TOKEN in env by SDK
        )
        canaries = load_canaries()["canaries"]
        with agent_span(
            tracing.tracer,
            agent_id="synthetic-bitcoin-agent",
            agent_name="synthetic-bitcoin-agent",
            span_name="synthetic.otlp.probe",
            system="inference.net",
        ) as span:
            span.set_input(f"OTLP probe {canaries['user_prompt']['value']}")
            span.set_output(f"local-only until egress allows {canaries['model_response']['value']}")
            span.record_tokens(prompt=12, completion=8)
        tracing.shutdown()
        result["ok"] = True
        result["note"] = "setup/shutdown completed; delivery depends on egress"
        result["spans_meta"] = spans_meta
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        # Never include env values.
        msg = str(exc)
        token = os.environ.get("CATALYST_OTLP_TOKEN") or ""
        if token and token in msg:
            result["error"] = f"{type(exc).__name__}: <redacted>"
    return result


def build_training_splits(dest_dir: Path) -> dict[str, Any]:
    """Create non-overlapping synthetic train/val/holdout JSONL hashes."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    # Train/val use only development families; holdout uses holdout task IDs as
    # metadata labels without embedding scorer answers.
    splits = {
        "train": DEV_TASK_IDS[:4],
        "validation": DEV_TASK_IDS[4:],
        "holdout": [
            "btc-hold-001",
            "btc-hold-002",
            "btc-hold-003",
            "btc-hold-004",
            "btc-hold-005",
            "btc-hold-006",
            "btc-hold-007",
            "btc-hold-008",
        ],
    }
    overlap = set(splits["train"]) & set(splits["validation"])
    if overlap:
        raise RuntimeError(f"train/val overlap: {overlap}")
    if set(splits["train"] + splits["validation"]) & set(splits["holdout"]):
        raise RuntimeError("dev/holdout overlap")

    out: dict[str, Any] = {"splits": {}, "overlap_check": "passed"}
    for name, ids in splits.items():
        rows = []
        for task_id in ids:
            rows.append(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Synthetic public coding task id={task_id}",
                        },
                        {
                            "role": "assistant",
                            "content": (
                                "Apply a generic harness improvement without encoding "
                                "hidden answers."
                            ),
                        },
                    ],
                    "task_id": task_id,
                    "split": name,
                }
            )
        path = dest_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")
        out["splits"][name] = {
            "path": str(path),
            "count": len(rows),
            "task_ids": ids,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return out
