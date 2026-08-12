"""CLI entrypoints for python -m diligence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from diligence.prepare import prepare, write_committed_prepare_summary
from diligence.report import report_run_dir
from diligence.run import RunError, run
from diligence.verify import VerifyError, verify_run_dir
from diligence.schemas import SchemaError
from diligence.isolation import IsolationError
from diligence.privacy import PrivacyError
from diligence.constants import REPO_ROOT


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m diligence",
        description="Offline Catalyst/HALO diligence harness (Phase 1).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("prepare", help="Verify baseline and materialize offline fixtures")

    run_p = sub.add_parser("run", help="Run an experimental arm")
    run_p.add_argument("--arm", required=True)
    run_p.add_argument("--split", required=True, choices=["dev", "holdout"])
    run_p.add_argument("--repeats", type=int, default=1)

    verify_p = sub.add_parser("verify", help="Verify a run directory")
    verify_p.add_argument("--run-dir", required=True)

    report_p = sub.add_parser("report", help="Report on a verified run directory")
    report_p.add_argument("--run-dir", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare()
            summary_path = REPO_ROOT / "docs" / "catalyst-halo" / "prepare-summary.json"
            write_committed_prepare_summary(manifest, summary_path)
            print(json.dumps({"ok": True, "baseline_commit": manifest["baseline_commit"], "tasks": manifest["tasks"], "raw_root": manifest["raw_results"]["root"]}, indent=2))
            return 0
        if args.command == "run":
            run_dir = run(arm=args.arm, split=args.split, repeats=args.repeats)
            print(json.dumps({"ok": True, "run_dir": str(run_dir)}, indent=2))
            return 0
        if args.command == "verify":
            result = verify_run_dir(Path(args.run_dir))
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "report":
            result = report_run_dir(Path(args.run_dir))
            print(json.dumps(result, indent=2))
            return 0
        parser.error(f"unknown command {args.command}")
        return 2
    except (IsolationError, RunError, VerifyError, SchemaError, PrivacyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1
