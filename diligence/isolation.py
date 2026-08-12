"""Repository and task-workspace isolation helpers."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable

from diligence import BASELINE_COMMIT, EXPECTED_REPO_SUFFIXES
from diligence.constants import (
    FORBIDDEN_WORKSPACE_NAMES,
    FORBIDDEN_WORKSPACE_SUBSTRINGS,
    NETWORK_CONTRACT_NAME,
    REPO_ROOT,
)


class IsolationError(RuntimeError):
    """Raised when repository or workspace isolation checks fail."""


def git_output(args: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd or REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise IsolationError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def verify_repository(repo_root: Path | None = None) -> dict[str, str]:
    root = (repo_root or REPO_ROOT).resolve()
    if not (root / ".git").exists():
        raise IsolationError(f"not a git repository: {root}")

    top = git_output(["rev-parse", "--show-toplevel"], cwd=root)
    if Path(top).resolve() != root:
        raise IsolationError(f"unexpected git toplevel {top!r}, expected {str(root)!r}")

    remote = git_output(["remote", "get-url", "origin"], cwd=root)
    if not any(remote.rstrip("/").endswith(suffix) or f"/{suffix}." in remote for suffix in EXPECTED_REPO_SUFFIXES):
        # Accept both https://github.com/ZILECAO/bitcoin-sat-tracker and SSH forms.
        if "bitcoin-sat-tracker" not in remote:
            raise IsolationError(f"unexpected repository remote: {remote}")

    head = git_output(["rev-parse", "HEAD"], cwd=root)
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_COMMIT, "HEAD"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if ancestor.returncode != 0:
        raise IsolationError(
            f"immutable baseline {BASELINE_COMMIT} is not an ancestor of HEAD ({head})"
        )

    baseline_tree = git_output(["rev-parse", f"{BASELINE_COMMIT}^{{tree}}"], cwd=root)
    return {
        "repo_root": str(root),
        "remote": remote,
        "head": head,
        "baseline_commit": BASELINE_COMMIT,
        "baseline_tree": baseline_tree,
    }


def verify_baseline_scripts_unchanged(repo_root: Path | None = None) -> dict[str, str]:
    root = (repo_root or REPO_ROOT).resolve()
    hashes: dict[str, str] = {}
    for name in ("track-forwards.py", "watch-wallet.py"):
        current = (root / name).read_bytes()
        expected = subprocess.run(
            ["git", "show", f"{BASELINE_COMMIT}:{name}"],
            cwd=str(root),
            check=True,
            capture_output=True,
        ).stdout
        if current != expected:
            raise IsolationError(f"baseline script changed: {name}")
        import hashlib

        hashes[name] = hashlib.sha256(current).hexdigest()
    return hashes


def ensure_mode_0700(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o700:
        raise IsolationError(f"expected mode 0700 for {path}, got {oct(mode)}")


def _is_forbidden_path(rel: Path) -> bool:
    parts = rel.parts
    if not parts:
        return False
    if parts[0] in FORBIDDEN_WORKSPACE_NAMES:
        return True
    text = str(rel).lower()
    return any(token in text for token in FORBIDDEN_WORKSPACE_SUBSTRINGS)


def create_baseline_checkout(dest: Path, *, repo_root: Path | None = None) -> Path:
    """Create an isolated checkout of the immutable baseline into dest."""
    root = (repo_root or REPO_ROOT).resolve()
    if dest.exists():
        raise IsolationError(f"checkout destination already exists: {dest}")
    dest.mkdir(parents=True, exist_ok=False)

    archive = subprocess.run(
        ["git", "archive", "--format=tar", BASELINE_COMMIT],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp:
        tmp.write(archive.stdout)
        tmp_path = Path(tmp.name)
    try:
        with tarfile.open(tmp_path, "r:") as tf:
            for member in tf.getmembers():
                name = Path(member.name)
                if name.is_absolute() or ".." in name.parts:
                    raise IsolationError(f"unsafe archive member: {member.name}")
                if _is_forbidden_path(name):
                    raise IsolationError(
                        f"baseline archive unexpectedly contains diligence material: {member.name}"
                    )
            # filter='data' avoids Python 3.14 default-extraction warnings and
            # rejects unusual members without executing anything.
            try:
                tf.extractall(dest, filter="data")
            except TypeError:
                tf.extractall(dest)
    finally:
        tmp_path.unlink(missing_ok=True)

    # Refuse credential leakage into task checkouts.
    for env_name in (".env", ".env.local", ".env.production"):
        if (dest / env_name).exists():
            raise IsolationError(f"refusing to leave {env_name} in task checkout")

    assert_workspace_isolated(dest)
    write_network_contract(dest)
    return dest


def write_network_contract(workspace: Path) -> Path:
    contract = {
        "network": "disabled",
        "policy": "Task workspaces must not access the network. "
        "Future agent launches must enforce this before execution.",
        "blocked": [
            "model provider APIs",
            "git fetch of non-baseline refs",
            "held-out branch retrieval",
            "Catalyst/HALO hosted endpoints",
            "mempool.space and other live Bitcoin HTTP APIs",
        ],
    }
    path = workspace / NETWORK_CONTRACT_NAME
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return path


def assert_workspace_isolated(workspace: Path) -> None:
    if not workspace.is_dir():
        raise IsolationError(f"workspace missing: {workspace}")
    for path in workspace.rglob("*"):
        rel = path.relative_to(workspace)
        if path.name in FORBIDDEN_WORKSPACE_NAMES or _is_forbidden_path(rel):
            # network-policy.json is intentionally present and allowed.
            if path.name == NETWORK_CONTRACT_NAME:
                continue
            raise IsolationError(f"forbidden path in task workspace: {rel}")
        lower = path.name.lower()
        if lower.endswith(".env") or lower.startswith(".env"):
            raise IsolationError(f".env material in task workspace: {rel}")

    # Held-out answers / scorers must not be visible.
    for banned in ("scorers", "answers", "holdout", "development.json", "canaries.json"):
        if (workspace / banned).exists():
            raise IsolationError(f"banned material present: {banned}")


def copy_public_task_materials(
    workspace: Path,
    *,
    prompt_text: str,
    fixture_files: dict[str, Path] | None = None,
) -> None:
    """Copy only public task instructions and synthetic fixtures into workspace."""
    task_dir = workspace / "TASK"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / "PROMPT.md").write_text(prompt_text, encoding="utf-8")
    if fixture_files:
        fixtures_dir = task_dir / "fixtures"
        fixtures_dir.mkdir(parents=True, exist_ok=True)
        for name, src in fixture_files.items():
            if ".." in Path(name).parts or Path(name).is_absolute():
                raise IsolationError(f"unsafe fixture name: {name}")
            target = fixtures_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
    assert_workspace_isolated(workspace)


def list_files(workspace: Path) -> list[str]:
    return sorted(
        str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()
    )


def destroy_workspace(workspace: Path) -> None:
    if workspace.exists():
        shutil.rmtree(workspace)


def ensure_outside_git(path: Path, repo_root: Path | None = None) -> None:
    root = (repo_root or REPO_ROOT).resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return
    raise IsolationError(f"path must live outside the Git checkout: {resolved}")
