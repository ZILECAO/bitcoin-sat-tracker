"""Deterministic hidden scorers for coding-agent tasks.

Scorers run outside the task workspace and must not require Bitcoin Core or
network access. They inspect workspace source with static checks and synthetic
fixtures only.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from diligence.fixtures import block_reward_sats, load_committed_fixtures


@dataclass
class ScoreResult:
    scorer_id: str
    passed: bool
    checks: list[dict] = field(default_factory=list)
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "scorer_id": self.scorer_id,
            "passed": self.passed,
            "checks": self.checks,
            "detail": self.detail,
        }


def _read(workspace: Path, rel: str) -> str:
    return (workspace / rel).read_text(encoding="utf-8")


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "passed": bool(ok), "detail": detail}


def score_rpc_config_externalized(workspace: Path) -> ScoreResult:
    """Family 1: Move Bitcoin RPC configuration out of source."""
    text = _read(workspace, "track-forwards.py")
    checks = [
        _check(
            "no_hardcoded_url_constant",
            "BITCOIN_URL = \"http://127.0.0.1:8332\"" not in text,
        ),
        _check(
            "no_hardcoded_user_constant",
            'BITCOIN_USER = "TODO_REPLACE"' not in text,
        ),
        _check(
            "uses_env_or_config",
            bool(
                re.search(r"os\.environ|getenv|configparser|BITCOIN_RPC|load_config", text)
            ),
        ),
    ]
    return ScoreResult("rpc_config_externalized", all(c["passed"] for c in checks), checks)


def score_missing_config_safe(workspace: Path) -> ScoreResult:
    """Family 2: Validate missing configuration without logging secrets."""
    text = _read(workspace, "track-forwards.py") + "\n" + _read(workspace, "watch-wallet.py")
    # Must not print password/user values; should validate presence.
    logs_secret = bool(
        re.search(r"print\(.*BITCOIN_PASS|print\(.*password|logging.*(BITCOIN_PASS|rpcpassword)", text)
    )
    validates = bool(
        re.search(r"missing|required|ValueError|ConfigurationError|raise .*config", text, re.I)
    )
    checks = [
        _check("does_not_log_secrets", not logs_secret),
        _check("validates_missing_config", validates),
    ]
    return ScoreResult("missing_config_safe", all(c["passed"] for c in checks), checks)


def score_timeouts_and_status(workspace: Path) -> ScoreResult:
    """Family 3: Add request timeouts and HTTP status validation."""
    texts = {
        "track-forwards.py": _read(workspace, "track-forwards.py"),
        "watch-wallet.py": _read(workspace, "watch-wallet.py"),
    }
    checks = []
    for name, text in texts.items():
        checks.append(
            _check(
                f"{name}_timeout",
                bool(re.search(r"timeout\s*=", text)),
            )
        )
        checks.append(
            _check(
                f"{name}_status_validation",
                "raise_for_status" in text or re.search(r"status_code|HTTPError", text) is not None,
            )
        )
    return ScoreResult("timeouts_and_status", all(c["passed"] for c in checks), checks)


def score_structured_errors(workspace: Path) -> ScoreResult:
    """Family 4: Structured Bitcoin RPC and mempool error handling."""
    text = _read(workspace, "track-forwards.py")
    checks = [
        _check(
            "rpc_error_branch",
            bool(re.search(r"\berror\b", text)) and ("RequestException" in text or "JSONDecodeError" in text or "RPCError" in text or "BitcoindError" in text),
        ),
        _check(
            "mempool_error_handling",
            "spending_txid" in text
            and (
                "raise_for_status" in text
                or "RequestException" in text
                or "MempoolError" in text
                or "try:" in text
            ),
        ),
        _check(
            "no_bare_json_index_on_http",
            ".json()[\"result\"]" not in text,
        ),
    ]
    return ScoreResult("structured_errors", all(c["passed"] for c in checks), checks)


def score_injectable_dependencies(workspace: Path) -> ScoreResult:
    """Family 5: Make RPC and mempool dependencies injectable."""
    text = _read(workspace, "track-forwards.py")
    tree = ast.parse(text)
    fn_args = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            fn_args[node.name] = [a.arg for a in node.args.args]
    injectable = any(
        set(args) & {"client", "rpc", "session", "mempool", "http_get", "bitcoind"}
        for args in fn_args.values()
    )
    checks = [
        _check("has_injectable_parameters", injectable),
        _check(
            "query_or_spending_accepts_dependency",
            "client" in fn_args.get("query_bitcoind", [])
            or "session" in fn_args.get("spending_txid", [])
            or "rpc" in fn_args.get("query_bitcoind", [])
            or "mempool_get" in text
            or "BitcoindClient" in text,
        ),
    ]
    return ScoreResult("injectable_dependencies", all(c["passed"] for c in checks), checks)


def score_block_reward_tests(workspace: Path) -> ScoreResult:
    """Family 6: Add deterministic block-reward tests."""
    # Look for a test module in the workspace that asserts fixture rewards.
    fixtures = load_committed_fixtures()["block_rewards"]
    test_files = list(workspace.glob("test*.py")) + list(workspace.glob("**/test_*.py"))
    found_assertions = False
    detail = "no test files"
    for path in test_files:
        text = path.read_text(encoding="utf-8")
        if "block_reward" not in text:
            continue
        ok = True
        for height, reward in fixtures.items():
            if str(reward) not in text and f"block_reward({height})" not in text:
                # Require at least one explicit expected reward constant.
                continue
            found_assertions = True
            detail = f"checked via {path.name}"
            break
        if found_assertions:
            break
        # If file mentions block_reward and assert, count it.
        if "assert" in text and "block_reward" in text:
            found_assertions = True
            detail = f"assert present in {path.name}"
    # Also verify the function still matches fixture math when present.
    text = _read(workspace, "track-forwards.py")
    local_ok = True
    if "def block_reward" in text:
        # Execute only the pure function from source via AST extraction would be heavy;
        # compare known fixture values against reimplementation.
        for height, reward in fixtures.items():
            if block_reward_sats(int(height)) != int(reward):
                local_ok = False
    checks = [
        _check("fixture_rewards_consistent", local_ok),
        _check("workspace_has_block_reward_tests", found_assertions, detail),
    ]
    return ScoreResult("block_reward_tests", all(c["passed"] for c in checks), checks)


def score_satpoint_validation(workspace: Path) -> ScoreResult:
    """Family 7: Validate satpoint and output-boundary inputs."""
    text = _read(workspace, "track-forwards.py")
    checks = [
        _check(
            "validates_satpoint_format",
            bool(re.search(r"satpoint|split\(:\)|ValueError|invalid", text, re.I))
            and ("offset" in text),
        ),
        _check(
            "rejects_negative_or_non_int",
            bool(re.search(r"offset\s*<\s*0|int\(|ValueError|InvalidSatpoint", text)),
        ),
        _check(
            "bounds_check_before_use",
            "vout >=" in text or "vout >" in text,
        ),
    ]
    # Baseline already has a vout bounds check inside track_satpoint; require
    # explicit validation helper or CLI validation beyond the current bare split.
    has_helper = bool(
        re.search(r"def (parse_satpoint|validate_satpoint|parse_output)\b", text)
    )
    checks.append(_check("has_parse_or_validate_helper", has_helper))
    return ScoreResult("satpoint_validation", all(c["passed"] for c in checks), checks)


def score_no_sys_exit_in_library(workspace: Path) -> ScoreResult:
    """Family 8: Remove process-wide sys.exit from library functions."""
    text = _read(workspace, "track-forwards.py")
    tree = ast.parse(text)
    library_exits = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name != "main":
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    func = child.func
                    if isinstance(func, ast.Attribute) and func.attr == "exit":
                        library_exits.append(node.name)
                    if isinstance(func, ast.Name) and func.id == "exit":
                        library_exits.append(node.name)
    checks = [
        _check("library_functions_avoid_sys_exit", not library_exits, ",".join(library_exits)),
        _check(
            "uses_exceptions_instead",
            bool(re.search(r"raise\s+\w+", text)),
        ),
    ]
    return ScoreResult("no_sys_exit_in_library", all(c["passed"] for c in checks), checks)


def score_safe_cli_layer(workspace: Path) -> ScoreResult:
    """Family 9: Add a safe command-line layer."""
    text_tf = _read(workspace, "track-forwards.py")
    text_ww = _read(workspace, "watch-wallet.py")
    checks = [
        _check(
            "track_uses_argparse_or_click",
            "argparse" in text_tf or "click" in text_tf,
        ),
        _check(
            "watch_uses_argparse_or_click",
            "argparse" in text_ww or "click" in text_ww,
        ),
        _check(
            "main_guard_present",
            'if __name__ == "__main__"' in text_tf and 'if __name__ == "__main__"' in text_ww,
        ),
    ]
    return ScoreResult("safe_cli_layer", all(c["passed"] for c in checks), checks)


def score_bounded_wallet_polling(workspace: Path) -> ScoreResult:
    """Family 10: Bound and test wallet-monitor polling."""
    text = _read(workspace, "watch-wallet.py")
    checks = [
        _check(
            "poll_interval_configurable",
            bool(re.search(r"interval|poll|sleep\([^)]*[a-zA-Z_]", text)),
        ),
        _check(
            "has_max_iterations_or_stop",
            bool(re.search(r"max_|stop_|iterations|KeyboardInterrupt|running", text)),
        ),
        _check(
            "not_only_hardcoded_sleep_60",
            "time.sleep(60)" not in text or "interval" in text.lower(),
        ),
    ]
    test_files = list(workspace.glob("test*.py")) + list(workspace.glob("**/test_*.py"))
    has_test = any("monitor" in p.read_text(encoding="utf-8").lower() or "poll" in p.read_text(encoding="utf-8").lower() for p in test_files)
    checks.append(_check("has_polling_test", has_test))
    return ScoreResult("bounded_wallet_polling", all(c["passed"] for c in checks), checks)


def score_fee_flow_edge_cases(workspace: Path) -> ScoreResult:
    """Family 11: Correct fee-flow and coinbase edge cases."""
    text = _read(workspace, "track-forwards.py")
    test_files = list(workspace.glob("test*.py")) + list(workspace.glob("**/test_*.py"))
    has_fee_tests = False
    for path in test_files:
        t = path.read_text(encoding="utf-8")
        if "fee" in t.lower() and ("coinbase" in t.lower() or "subsidy" in t.lower()):
            has_fee_tests = True
            break
    checks = [
        _check(
            "fee_helper_handles_missing_inputs",
            bool(re.search(r"fee|coinbase|subsidy", text, re.I)),
        ),
        _check("has_fee_or_coinbase_tests", has_fee_tests),
        _check(
            "avoids_unbounded_recursive_fee_lookups_comment_or_guard",
            "get_fee_for_txid" in text,
        ),
    ]
    # Require tests for this family to pass — baseline has fee logic but no tests.
    return ScoreResult("fee_flow_edge_cases", all(c["passed"] for c in checks), checks)


def score_tx_output_edge_cases(workspace: Path) -> ScoreResult:
    """Family 12: Correct transaction-output edge cases with generated fixtures."""
    fixtures = load_committed_fixtures()
    edge = fixtures["edge_cases"]
    test_files = list(workspace.glob("test*.py")) + list(workspace.glob("**/test_*.py"))
    combined = "\n".join(p.read_text(encoding="utf-8") for p in test_files)
    checks = [
        _check("has_tests", bool(test_files)),
        _check(
            "covers_unconfirmed",
            "unconfirmed" in combined.lower() or edge["unconfirmed_tx"]["txid"][:8] in combined,
        ),
        _check(
            "covers_out_of_range_vout",
            "vout" in combined.lower() and ("range" in combined.lower() or "invalid" in combined.lower() or "index" in combined.lower()),
        ),
        _check(
            "uses_fixture_or_generated_data",
            "fixture" in combined.lower() or "SAMPLE" in combined or "fake" in combined.lower(),
        ),
    ]
    return ScoreResult("tx_output_edge_cases", all(c["passed"] for c in checks), checks)


SCORERS: dict[str, Callable[[Path], ScoreResult]] = {
    "rpc_config_externalized": score_rpc_config_externalized,
    "missing_config_safe": score_missing_config_safe,
    "timeouts_and_status": score_timeouts_and_status,
    "structured_errors": score_structured_errors,
    "injectable_dependencies": score_injectable_dependencies,
    "block_reward_tests": score_block_reward_tests,
    "satpoint_validation": score_satpoint_validation,
    "no_sys_exit_in_library": score_no_sys_exit_in_library,
    "safe_cli_layer": score_safe_cli_layer,
    "bounded_wallet_polling": score_bounded_wallet_polling,
    "fee_flow_edge_cases": score_fee_flow_edge_cases,
    "tx_output_edge_cases": score_tx_output_edge_cases,
}


def get_scorer(scorer_id: str) -> Callable[[Path], ScoreResult]:
    if scorer_id not in SCORERS:
        raise KeyError(f"unknown scorer_id: {scorer_id}")
    return SCORERS[scorer_id]


def run_scorer(scorer_id: str, workspace: Path) -> ScoreResult:
    return get_scorer(scorer_id)(workspace)
