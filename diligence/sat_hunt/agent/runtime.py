"""Instrumented sat-hunt coding agent with Catalyst tracing."""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from diligence.sat_hunt.agent.gateway import GatewayClient, GatewayError
from diligence.sat_hunt.agent.tools import ToolRegistry

SERVICE_NAME = "bitcoin-sat-tracker-sat-hunt"
BASELINE_SYSTEM = """You are a specialized Bitcoin/ordinal research coding agent.
You must write Python scripts and tests in the workspace, use only the provided tools,
and produce machine-checkable answer artifacts. Never claim certainty about wallet ownership.
Use the fixture_* tools for deterministic data. Prefer small scripts and explicit evidence.
Workspace includes fixture.json, benchmark.json, and attribution-sources.json (metadata only).
When finished, call submit_answer with name set to the required answer path
(for example answers/fifo.json) and answer set to the JSON object.
"""


def harness_hash(system_prompt: str) -> str:
    return hashlib.sha256(system_prompt.encode()).hexdigest()


class SatHuntAgent:
    def __init__(
        self,
        *,
        workspace: Path,
        fixture: dict[str, Any],
        model: str,
        task_id: str,
        arm: str,
        system_prompt: str | None = None,
        max_turns: int = 12,
        raw_dir: Path | None = None,
        enable_catalyst: bool = True,
    ) -> None:
        self.workspace = workspace
        self.fixture = fixture
        self.model = model
        self.task_id = task_id
        self.arm = arm
        self.system_prompt = system_prompt or BASELINE_SYSTEM
        self.max_turns = max_turns
        self.raw_dir = raw_dir
        self.enable_catalyst = enable_catalyst
        self.tools = ToolRegistry(workspace=workspace, fixture=fixture)
        self.gateway = GatewayClient(
            model=model,
            task_id=task_id,
            raw_dir=raw_dir,
            environment=f"sat-hunt-{arm}",
        )
        self.harness_revision = harness_hash(self.system_prompt)
        self.toolkit_revision = hashlib.sha256(
            Path(__file__).read_bytes() + Path(__file__).with_name("tools.py").read_bytes()
        ).hexdigest()

    def run(self, user_prompt: str) -> dict[str, Any]:
        started = time.monotonic()
        trace_id = None
        catalyst = None
        root_ctx = None
        if self.enable_catalyst:
            try:
                from catalyst_tracing import agent_span, setup
                from opentelemetry import trace

                catalyst = setup(
                    endpoint=os.environ.get("CATALYST_OTLP_ENDPOINT", "https://telemetry.inference.net"),
                    service_name=os.environ.get("CATALYST_SERVICE_NAME", SERVICE_NAME),
                    service_version="0.2.0",
                    batching="simple",
                )
                tracer = catalyst.tracer
                root_cm = agent_span(
                    tracer,
                    agent_id="sat-hunt-agent",
                    agent_name="sat-hunt-agent",
                    span_name=f"sat-hunt.{self.task_id}",
                    system="inference.net",
                    metadata={
                        "inference.task_id": self.task_id,
                        "sat_hunt.arm": self.arm,
                        "sat_hunt.benchmark": "sat-hunt-v2",
                        "sat_hunt.harness_hash": self.harness_revision,
                        "sat_hunt.toolkit_hash": self.toolkit_revision,
                    },
                )
                root_ctx = root_cm.__enter__()
                root_ctx.set_input(user_prompt[:2000])
                span = trace.get_current_span()
                span.set_attribute("inference.task_id", self.task_id)
                span.set_attribute("sat_hunt.arm", self.arm)
                trace_id = format(span.get_span_context().trace_id, "032x")
            except Exception as exc:  # noqa: BLE001
                catalyst = None
                root_ctx = None
                trace_id = uuid.uuid4().hex
                catalyst_error = f"{type(exc).__name__}: {exc}"
            else:
                catalyst_error = None
        else:
            trace_id = uuid.uuid4().hex
            catalyst_error = "disabled"

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        tool_events: list[dict[str, Any]] = []
        errors: list[str] = []
        retries = 0
        final_text = ""

        try:
            for turn in range(self.max_turns):
                try:
                    if catalyst is not None:
                        from catalyst_tracing import SpanKindValues, manual_span

                        with manual_span(
                            catalyst.tracer,
                            name=f"llm.{self.model}",
                            span_kind=SpanKindValues.LLM,
                            model=self.model,
                            input={"messages": len(messages)},
                        ) as llm_ctx:
                            response = self.gateway.chat(
                                messages,
                                tools=self.tools.schemas(),
                                max_tokens=1200,
                            )
                            llm_ctx.record_tokens(
                                prompt=response.get("_diligence", {}).get("input_tokens", 0),
                                completion=response.get("_diligence", {}).get("output_tokens", 0),
                            )
                    else:
                        response = self.gateway.chat(
                            messages,
                            tools=self.tools.schemas(),
                            max_tokens=1200,
                        )
                except GatewayError as exc:
                    errors.append(str(exc))
                    retries += 1
                    if retries >= 3:
                        break
                    time.sleep(min(2 ** retries, 8))
                    continue

                choice = (response.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                tool_calls = message.get("tool_calls") or []
                content = message.get("content") or ""
                if content:
                    final_text = content
                messages.append(
                    {
                        "role": "assistant",
                        "content": content,
                        "tool_calls": tool_calls or None,
                    }
                )

                if not tool_calls:
                    break

                for call in tool_calls:
                    fn = call.get("function") or {}
                    name = fn.get("name") or ""
                    arguments = fn.get("arguments") or "{}"
                    result = None
                    if catalyst is not None:
                        try:
                            from catalyst_tracing import SpanKindValues, manual_span

                            with manual_span(
                                catalyst.tracer,
                                name=f"tool.{name}",
                                span_kind=SpanKindValues.TOOL,
                                tool_name=name,
                                input=str(arguments)[:1500],
                            ) as tool_ctx:
                                result = self.tools.call(name, arguments)
                                tool_ctx.set_output(json.dumps(result.as_dict())[:1500])
                        except Exception:  # noqa: BLE001
                            result = self.tools.call(name, arguments)
                    else:
                        result = self.tools.call(name, arguments)
                    tool_events.append(result.as_dict())
                    if not result.ok and result.retryable:
                        retries += 1
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.get("id") or name,
                            "content": json.dumps(result.as_dict())[:8000],
                        }
                    )
        finally:
            if catalyst is not None and root_ctx is not None:
                try:
                    root_ctx.set_output((final_text or json.dumps({"tool_events": len(tool_events)}))[:2000])
                    root_ctx.record_tokens(
                        prompt=self.gateway.total_input_tokens,
                        completion=self.gateway.total_output_tokens,
                    )
                    root_cm.__exit__(None, None, None)
                    catalyst.shutdown()
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"catalyst_shutdown: {type(exc).__name__}")

        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "task_id": self.task_id,
            "arm": self.arm,
            "model": self.model,
            "trace_id": trace_id,
            "duration_ms": duration_ms,
            "cost_usd_est": round(self.gateway.total_cost_usd, 8),
            "input_tokens": self.gateway.total_input_tokens,
            "output_tokens": self.gateway.total_output_tokens,
            "gateway_calls": self.gateway.calls,
            "tool_calls": self.tools.calls,
            "retries": retries,
            "errors": errors,
            "catalyst_error": catalyst_error,
            "harness_hash": self.harness_revision,
            "toolkit_hash": self.toolkit_revision,
            "final_text_excerpt": (final_text or "")[:1000],
            "tool_events": tool_events,
            "workspace": str(self.workspace),
        }
