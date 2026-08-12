"""Shared constants for the diligence harness."""

from __future__ import annotations

import os
from pathlib import Path

from diligence import BASELINE_COMMIT

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_ROOT.parent
TASKS_DIR = PACKAGE_ROOT / "tasks"
FIXTURES_DIR = PACKAGE_ROOT / "fixtures" / "data"
PROMPTS_DIR = TASKS_DIR / "prompts"
CANARIES_PATH = PACKAGE_ROOT / "privacy" / "canaries.json"

DEFAULT_RAW_ROOT = Path.home() / "diligence-raw"
RAW_ROOT_ENV = "DILIGENCE_RAW_DIR"
STATE_DIR_NAME = ".diligence-state"
MANIFEST_NAME = "prepare-manifest.json"
NETWORK_CONTRACT_NAME = "network-policy.json"

# Paths / names that must never appear inside a task workspace.
FORBIDDEN_WORKSPACE_NAMES = frozenset(
    {
        "AGENTS.md",
        "diligence",
        "docs",
        ".diligence-state",
        "tests",
        "holdout.json",
        "development.json",
        "canaries.json",
        ".env",
        ".env.local",
        ".env.example",
    }
)

FORBIDDEN_WORKSPACE_SUBSTRINGS = (
    "catalyst-halo",
    "held-out",
    "holdout",
    "scorer",
    "expected_answer",
    "answers.json",
)

PROHIBITED_COMMIT_PATTERNS = (
    r"(?i)api[_-]?key\s*[:=]\s*['\"]?[a-z0-9_\-]{16,}",
    r"(?i)secret\s*[:=]\s*['\"]?[a-z0-9_\-]{16,}",
    r"(?i)authorization:\s*bearer\s+[a-z0-9\-._~+/]+=*",
    r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"(?i)aws_secret_access_key",
    r"(?i)INFERENCE_API_KEY\s*=\s*\S+",
    r"(?i)OPENAI_API_KEY\s*=\s*\S+",
    r"(?i)CATALYST_OTLP_TOKEN\s*=\s*\S+",
)

SCRUBBED_REQUIRED_FIELDS = (
    "task_id",
    "arm",
    "split",
    "repeat",
    "model",
    "codex_version",
    "adapter_version",
    "started_at",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "exit_status",
    "tests_passed",
    "trace_complete",
    "privacy_checks_passed",
    "trace_id",
    "suggestion_ids",
)


def raw_root() -> Path:
    """Return the mode-0700 raw-results root outside the Git checkout."""
    override = os.environ.get(RAW_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_RAW_ROOT.resolve()


def state_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or REPO_ROOT
    return root / STATE_DIR_NAME


def default_workspace_root() -> Path:
    return raw_root() / "workspaces"


def default_runs_root() -> Path:
    return raw_root() / "runs"


__all__ = [
    "BASELINE_COMMIT",
    "PACKAGE_ROOT",
    "REPO_ROOT",
    "TASKS_DIR",
    "FIXTURES_DIR",
    "PROMPTS_DIR",
    "CANARIES_PATH",
    "DEFAULT_RAW_ROOT",
    "RAW_ROOT_ENV",
    "STATE_DIR_NAME",
    "MANIFEST_NAME",
    "NETWORK_CONTRACT_NAME",
    "FORBIDDEN_WORKSPACE_NAMES",
    "FORBIDDEN_WORKSPACE_SUBSTRINGS",
    "PROHIBITED_COMMIT_PATTERNS",
    "SCRUBBED_REQUIRED_FIELDS",
    "raw_root",
    "state_dir",
    "default_workspace_root",
    "default_runs_root",
]
