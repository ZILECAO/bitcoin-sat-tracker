"""Bounded tools for the sat-hunt coding agent.

Tools are confined to a disposable task workspace and never expose evaluator
paths, host secrets, or unrestricted shells.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

MAX_READ_BYTES = 200_000
MAX_WRITE_BYTES = 500_000
MAX_CMD_OUTPUT = 50_000
DEFAULT_TIMEOUT_S = 30


@dataclass
class ToolResult:
    ok: bool
    name: str
    result: Any = None
    error: str | None = None
    retryable: bool = False
    duration_ms: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "name": self.name,
            "result": self.result,
            "error": self.error,
            "retryable": self.retryable,
            "duration_ms": self.duration_ms,
        }


class ToolError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def _safe_path(workspace: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
        raise ToolError("path must be a relative workspace path without ..")
    path = (workspace / rel).resolve()
    root = workspace.resolve()
    if root != path and root not in path.parents:
        raise ToolError("path escapes workspace")
    return path


class ToolRegistry:
    def __init__(
        self,
        *,
        workspace: Path,
        fixture: dict[str, Any],
        cache_dir: Path | None = None,
    ) -> None:
        self.workspace = workspace
        self.fixture = fixture
        # Scorers expect a content-addressed `cache/` directory at workspace root.
        self.cache_dir = cache_dir or (workspace / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.calls = 0
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_python": self.run_python,
            "run_tests": self.run_tests,
            "fixture_get_snapshot": self.fixture_get_snapshot,
            "fixture_get_utxo": self.fixture_get_utxo,
            "fixture_get_sat": self.fixture_get_sat,
            "fixture_get_tx": self.fixture_get_tx,
            "fixture_list_utxos": self.fixture_list_utxos,
            "fixture_fee_demo": self.fixture_fee_demo,
            "cache_put": self.cache_put,
            "cache_get": self.cache_get,
            "checkpoint_save": self.checkpoint_save,
            "checkpoint_load": self.checkpoint_load,
            "submit_answer": self.submit_answer,
        }

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": handler.__doc__ or name,
                    "parameters": {"type": "object", "additionalProperties": True},
                },
            }
            for name, handler in self.handlers.items()
        ]

    def call(self, name: str, arguments: dict[str, Any] | str) -> ToolResult:
        started = time.monotonic()
        self.calls += 1
        try:
            if name not in self.handlers:
                raise ToolError(f"unknown tool: {name}", retryable=False)
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments else {}
                except json.JSONDecodeError as exc:
                    raise ToolError(f"invalid tool arguments JSON: {exc}", retryable=True) from exc
            if not isinstance(arguments, dict):
                raise ToolError("tool arguments must be an object")
            result = self.handlers[name](arguments)
            return ToolResult(
                ok=True,
                name=name,
                result=result,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except ToolError as exc:
            return ToolResult(
                ok=False,
                name=name,
                error=str(exc),
                retryable=exc.retryable,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                ok=False,
                name=name,
                error=f"{type(exc).__name__}: {exc}",
                retryable=True,
                duration_ms=int((time.monotonic() - started) * 1000),
            )

    def list_files(self, args: dict[str, Any]) -> Any:
        """List files under an optional relative directory."""
        rel = args.get("path") or "."
        root = _safe_path(self.workspace, rel) if rel != "." else self.workspace.resolve()
        if not root.exists():
            raise ToolError("path not found")
        files = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append(str(path.relative_to(self.workspace)))
        return {"files": files[:500]}

    def read_file(self, args: dict[str, Any]) -> Any:
        """Read a UTF-8 text file from the workspace."""
        path = _safe_path(self.workspace, args.get("path", ""))
        if not path.exists() or not path.is_file():
            raise ToolError("file not found")
        data = path.read_bytes()
        if len(data) > MAX_READ_BYTES:
            raise ToolError("file too large")
        return {"path": args["path"], "content": data.decode("utf-8", errors="replace")}

    def write_file(self, args: dict[str, Any]) -> Any:
        """Write a UTF-8 text file inside the workspace."""
        path = _safe_path(self.workspace, args.get("path", ""))
        content = args.get("content")
        if not isinstance(content, str):
            raise ToolError("content must be a string")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_WRITE_BYTES:
            raise ToolError("content too large")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"path": args["path"], "bytes": len(encoded)}

    def run_python(self, args: dict[str, Any]) -> Any:
        """Run an allowlisted python3 command inside the workspace."""
        script = args.get("script")
        if not isinstance(script, str) or not script.endswith(".py"):
            raise ToolError("script must be a .py path in the workspace")
        path = _safe_path(self.workspace, script)
        if not path.exists():
            raise ToolError("script not found")
        return self._run(["python3", str(path)], timeout=int(args.get("timeout_s") or DEFAULT_TIMEOUT_S))

    def run_tests(self, args: dict[str, Any]) -> Any:
        """Run python3 -m unittest for an allowlisted module or discover path."""
        target = args.get("target") or "discover"
        timeout = int(args.get("timeout_s") or DEFAULT_TIMEOUT_S)
        if target == "discover":
            cmd = ["python3", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py"]
        else:
            if not isinstance(target, str) or any(x in target for x in [";", "|", "&", "`", "$"]):
                raise ToolError("invalid test target")
            cmd = ["python3", "-m", "unittest", target]
        return self._run(cmd, timeout=timeout)

    def _run(self, cmd: list[str], *, timeout: int) -> dict[str, Any]:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=timeout,
                env={"PATH": os.environ.get("PATH", ""), "HOME": str(self.workspace / ".home"), "PYTHONDONTWRITEBYTECODE": "1"},
            )
        except subprocess.TimeoutExpired as exc:
            raise ToolError("command timed out", retryable=True) from exc
        out = (proc.stdout or "")[-MAX_CMD_OUTPUT:]
        err = (proc.stderr or "")[-MAX_CMD_OUTPUT:]
        return {
            "exit_code": proc.returncode,
            "stdout": out,
            "stderr": err,
            "ok": proc.returncode == 0,
        }

    def fixture_get_snapshot(self, args: dict[str, Any]) -> Any:
        """Return the frozen fixture snapshot metadata."""
        return self.fixture["snapshot"]

    def fixture_get_utxo(self, args: dict[str, Any]) -> Any:
        """Return one UTXO by outpoint from the fixture."""
        outpoint = args.get("outpoint")
        if outpoint not in self.fixture["utxos"]:
            raise ToolError("utxo not found")
        return self.fixture["utxos"][outpoint]

    def fixture_get_sat(self, args: dict[str, Any]) -> Any:
        """Return sat index metadata for one sat number."""
        sat = str(args.get("sat"))
        if sat not in self.fixture["sat_index"]:
            raise ToolError("sat not found in fixture index")
        return self.fixture["sat_index"][sat]

    def fixture_get_tx(self, args: dict[str, Any]) -> Any:
        """Return one transaction by txid from the fixture."""
        txid = args.get("txid")
        if txid not in self.fixture["transactions"]:
            raise ToolError("tx not found")
        return self.fixture["transactions"][txid]

    def fixture_list_utxos(self, args: dict[str, Any]) -> Any:
        """List fixture UTXO outpoints."""
        return {"outpoints": sorted(self.fixture["utxos"])}

    def fixture_fee_demo(self, args: dict[str, Any]) -> Any:
        """Return the fixture fee/FIFO demo vectors."""
        return self.fixture["fee_demo"]

    def cache_put(self, args: dict[str, Any]) -> Any:
        """Store a content-addressed cache entry."""
        key = args.get("key")
        value = args.get("value")
        if not isinstance(key, str) or not key:
            raise ToolError("key required")
        blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        digest = hashlib.sha256(blob).hexdigest()
        path = self.cache_dir / f"{digest}.json"
        path.write_bytes(blob)
        index = self.cache_dir / "index.json"
        mapping = json.loads(index.read_text()) if index.exists() else {}
        mapping[key] = digest
        index.write_text(json.dumps(mapping, indent=2) + "\n")
        return {"key": key, "sha256": digest}

    def cache_get(self, args: dict[str, Any]) -> Any:
        """Load a content-addressed cache entry by key."""
        key = args.get("key")
        index = self.cache_dir / "index.json"
        if not index.exists():
            raise ToolError("cache empty")
        mapping = json.loads(index.read_text())
        digest = mapping.get(key)
        if not digest:
            raise ToolError("cache miss", retryable=False)
        path = self.cache_dir / f"{digest}.json"
        return {"key": key, "sha256": digest, "value": json.loads(path.read_text())}

    def checkpoint_save(self, args: dict[str, Any]) -> Any:
        """Save a checkpoint.json with completed query markers."""
        payload = {
            "completed_queries": args.get("completed_queries") or [],
            "content_hashes": args.get("content_hashes") or {},
            "cursor": args.get("cursor"),
        }
        path = self.workspace / "checkpoint.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return {"path": "checkpoint.json"}

    def checkpoint_load(self, args: dict[str, Any]) -> Any:
        """Load checkpoint.json if present."""
        path = self.workspace / "checkpoint.json"
        if not path.exists():
            return {"exists": False}
        return {"exists": True, "checkpoint": json.loads(path.read_text())}

    def submit_answer(self, args: dict[str, Any]) -> Any:
        """Write answer.json or a named answers/*.json artifact."""
        name = args.get("name") or "answer.json"
        if name != "answer.json" and not name.startswith("answers/"):
            raise ToolError("answer path must be answer.json or answers/...")
        path = _safe_path(self.workspace, name)
        payload = args.get("answer")
        if payload is None:
            raise ToolError("answer required")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return {"path": name}
