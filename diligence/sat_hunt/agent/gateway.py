"""OpenAI-compatible Catalyst Gateway client with browser-like User-Agent."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any


class GatewayError(RuntimeError):
    pass


class GatewayClient:
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://api.inference.net/v1",
        task_id: str | None = None,
        environment: str = "sat-hunt-phase2b",
        raw_dir: Path | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("INFERENCE_API_KEY") or ""
        if not self.api_key:
            raise GatewayError("INFERENCE_API_KEY missing")
        self.base_url = base_url.rstrip("/")
        self.task_id = task_id or "unspecified"
        self.environment = environment
        self.raw_dir = raw_dir
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.calls = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | None = "auto",
        temperature: float = 0,
        max_tokens: int = 1200,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice

        headers_path, body_path, out_path = self._temp_files(body)
        ua = (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        cmd = [
            "curl",
            "-sS",
            "-o",
            str(out_path),
            "-w",
            "%{http_code} %{time_total}",
            "-A",
            ua,
            "-H",
            f"@{headers_path}",
            "-H",
            f"x-inference-task-id: {self.task_id}",
            "-H",
            f"x-inference-environment: {self.environment}",
            "-X",
            "POST",
            f"{self.base_url}/chat/completions",
            "--data-binary",
            f"@{body_path}",
        ]
        started = time.monotonic()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        latency = time.monotonic() - started
        meta = proc.stdout.strip().split()
        http_code = int(meta[0]) if meta else 0
        text = out_path.read_text(errors="replace")
        text = text.replace(self.api_key, "<REDACTED>")
        out_path.write_text(text)
        if self.raw_dir:
            stamp = uuid.uuid4().hex[:10]
            (self.raw_dir / f"gw-{stamp}.json").write_text(text)
        if http_code != 200:
            raise GatewayError(f"gateway HTTP {http_code}: {text[:300]}")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GatewayError(f"invalid JSON response: {exc}") from exc
        usage = data.get("usage") or {}
        in_tok = int(usage.get("prompt_tokens") or 0)
        out_tok = int(usage.get("completion_tokens") or 0)
        # deepseek-v4-flash approx pricing used for local accounting; platform cost tracked separately
        cost = in_tok / 1e6 * 0.14 + out_tok / 1e6 * 0.28
        self.total_input_tokens += in_tok
        self.total_output_tokens += out_tok
        self.total_cost_usd += cost
        self.calls += 1
        data["_diligence"] = {
            "latency_s": latency,
            "http_code": http_code,
            "cost_usd_est": cost,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
        }
        return data

    def _temp_files(self, body: dict[str, Any]) -> tuple[Path, Path, Path]:
        raw = self.raw_dir or Path(tempfile.mkdtemp(prefix="sat-hunt-gw-"))
        raw.mkdir(parents=True, exist_ok=True)
        headers = raw / "curl-headers.txt"
        if not headers.exists():
            headers.write_text(
                f"Authorization: Bearer {self.api_key}\n"
                "Content-Type: application/json\n"
                "Accept: application/json\n"
            )
            headers.chmod(0o600)
        body_path = raw / f"req-{uuid.uuid4().hex}.json"
        out_path = raw / f"resp-{uuid.uuid4().hex}.json"
        body_path.write_text(json.dumps(body))
        body_path.chmod(0o600)
        return headers, body_path, out_path
