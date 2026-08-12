"""Offline unit and integration tests for the diligence harness."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from diligence import BASELINE_COMMIT, PHASE2_ARMS  # noqa: E402
from diligence.constants import raw_root  # noqa: E402
from diligence.isolation import (  # noqa: E402
    IsolationError,
    assert_workspace_isolated,
    create_baseline_checkout,
    verify_baseline_scripts_unchanged,
    verify_repository,
)
from diligence.prepare import prepare  # noqa: E402
from diligence.privacy import (  # noqa: E402
    PrivacyError,
    compare_secret_in_memory,
    load_canaries,
    reject_prohibited_artifacts,
    scan_text_for_secrets,
    validate_privacy_matrix,
)
from diligence.report import report_run_dir  # noqa: E402
from diligence.run import run  # noqa: E402
from diligence.schemas import SchemaError, validate_task, validate_task_manifest  # noqa: E402
from diligence.verify import VerifyError, verify_run_dir  # noqa: E402


class BaselineTests(unittest.TestCase):
    def test_repository_and_baseline(self):
        info = verify_repository(REPO_ROOT)
        self.assertEqual(info["baseline_commit"], BASELINE_COMMIT)
        hashes = verify_baseline_scripts_unchanged(REPO_ROOT)
        self.assertIn("track-forwards.py", hashes)
        self.assertIn("watch-wallet.py", hashes)

    def test_refuse_unexpected_baseline(self):
        task = {
            "id": "btc-dev-001",
            "prompt": "x",
            "baseline_commit": "0" * 40,
            "fixture_id": "bitcoin_rpc_mempool",
            "scorer_id": "rpc_config_externalized",
            "timeout_seconds": 900,
            "network": "disabled",
            "max_tokens": 50000,
            "max_cost_usd": 10,
            "family": "rpc_config_externalized",
            "split": "development",
        }
        with self.assertRaises(SchemaError):
            validate_task(task, expected_split="development")


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        os.environ["DILIGENCE_RAW_DIR"] = str(self.tmp / "raw")

    def tearDown(self):
        self._tmpdir.cleanup()
        os.environ.pop("DILIGENCE_RAW_DIR", None)

    def test_task_workspace_excludes_diligence_materials(self):
        dest = self.tmp / "ws"
        create_baseline_checkout(dest, repo_root=REPO_ROOT)
        names = {p.name for p in dest.iterdir()}
        self.assertIn("track-forwards.py", names)
        self.assertIn("watch-wallet.py", names)
        self.assertNotIn("AGENTS.md", names)
        self.assertNotIn("diligence", names)
        self.assertNotIn("docs", names)
        self.assertFalse((dest / "diligence").exists())
        self.assertFalse((dest / "docs" / "catalyst-halo").exists())
        assert_workspace_isolated(dest)

    def test_held_out_answers_not_in_workspace(self):
        dest = self.tmp / "ws2"
        create_baseline_checkout(dest, repo_root=REPO_ROOT)
        for path in dest.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace").lower()
                self.assertNotIn("scorer_id", text)
                self.assertNotIn("holdout", text)
                self.assertNotIn("btc-hold-", text)

    def test_raw_results_mode_0700(self):
        manifest = prepare(repo_root=REPO_ROOT)
        raw = Path(manifest["raw_results"]["root"])
        mode = stat.S_IMODE(raw.stat().st_mode)
        self.assertEqual(mode, 0o700)
        self.assertTrue(raw.resolve().is_relative_to(Path(os.environ["DILIGENCE_RAW_DIR"]).resolve()) or raw == Path(os.environ["DILIGENCE_RAW_DIR"]).resolve())

    def test_no_network_contract(self):
        dest = self.tmp / "ws3"
        create_baseline_checkout(dest, repo_root=REPO_ROOT)
        contract = json.loads((dest / "network-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["network"], "disabled")


class ArmTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        os.environ["DILIGENCE_RAW_DIR"] = str(self.tmp / "raw")
        prepare(repo_root=REPO_ROOT)

    def tearDown(self):
        self._tmpdir.cleanup()
        os.environ.pop("DILIGENCE_RAW_DIR", None)

    def test_model_backed_arms_fail_closed(self):
        for arm in PHASE2_ARMS[:3]:  # sample; all share same path
            run_dir = run(arm=arm, split="dev", repeats=1, repo_root=REPO_ROOT)
            index = json.loads((run_dir / "index.json").read_text(encoding="utf-8"))
            self.assertGreater(index["count"], 0)
            record = json.loads((run_dir / index["records"][0]).read_text(encoding="utf-8"))
            self.assertEqual(record["exit_status"], 2)
            self.assertIn("Phase 2 not configured", record.get("notes", ""))
            self.assertIsNone(record["input_tokens"])
            self.assertIsNone(record["cost_usd"])

    def test_offline_fixture_end_to_end(self):
        run_dir = run(arm="offline-fixture", split="dev", repeats=1, repo_root=REPO_ROOT)
        result = verify_run_dir(run_dir, repo_root=REPO_ROOT)
        self.assertTrue(result["verified"])
        report = report_run_dir(run_dir)
        self.assertEqual(report["arm"], "offline-fixture")
        self.assertEqual(report["input_tokens"]["status"], "unavailable")
        self.assertEqual(report["cost_usd"]["status"], "unavailable")
        self.assertIsNone(report["input_tokens"]["value"])
        # Baseline is expected to fail most tasks; success rate may be zero — that is observed.
        self.assertEqual(report["task_success"]["status"], "observed")


class PrivacyAndSchemaTests(unittest.TestCase):
    def test_privacy_canary_matrix(self):
        data = validate_privacy_matrix(load_canaries())
        self.assertEqual(len(data["canaries"]), 10)

    def test_secret_pattern_rejection(self):
        hits = scan_text_for_secrets('OPENAI_API_KEY=sk-thisisafakevalue123456')
        self.assertTrue(hits)
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / ".env"
            bad.write_text("OPENAI_API_KEY=sk-thisisafakevalue123456\n", encoding="utf-8")
            with self.assertRaises(PrivacyError):
                reject_prohibited_artifacts([bad])

    def test_memory_secret_compare_returns_only_bool(self):
        self.assertTrue(compare_secret_in_memory("abc", "abc"))
        self.assertFalse(compare_secret_in_memory("abc", "xyz"))

    def test_missing_versus_zero_metrics_in_report(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["DILIGENCE_RAW_DIR"] = td
            try:
                prepare(repo_root=REPO_ROOT)
                run_dir = run(arm="offline-fixture", split="dev", repeats=1, repo_root=REPO_ROOT)
                verify_run_dir(run_dir, repo_root=REPO_ROOT)
                report = report_run_dir(run_dir)
                # Unavailable metrics must not become zero.
                self.assertNotEqual(report["input_tokens"]["status"], "observed")
                self.assertIsNone(report["input_tokens"].get("value", None) if report["input_tokens"]["status"] == "unavailable" else "x")
                self.assertEqual(report["retries"]["status"], "unavailable")
                self.assertIsNone(report["retries"]["value"])
            finally:
                os.environ.pop("DILIGENCE_RAW_DIR", None)

    def test_duplicate_task_id_rejected(self):
        tasks = json.loads((REPO_ROOT / "diligence" / "tasks" / "development.json").read_text())
        tasks = tasks + [tasks[0]]
        with self.assertRaises(SchemaError):
            validate_task_manifest(tasks, expected_split="development")

    def test_network_must_be_disabled(self):
        task = json.loads((REPO_ROOT / "diligence" / "tasks" / "development.json").read_text())[0]
        task["network"] = "enabled"
        with self.assertRaises(SchemaError):
            validate_task(task, expected_split="development")


class DeterministicReportTests(unittest.TestCase):
    def test_report_stable_keys(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["DILIGENCE_RAW_DIR"] = td
            try:
                prepare(repo_root=REPO_ROOT)
                run_dir = run(arm="offline-fixture", split="holdout", repeats=1, repo_root=REPO_ROOT)
                verify_run_dir(run_dir, repo_root=REPO_ROOT)
                a = report_run_dir(run_dir)
                b = json.loads((run_dir / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(a["arm"], b["arm"])
                self.assertEqual(a["task_success"], b["task_success"])
                self.assertNotIn("raw_prompt", json.dumps(a))
            finally:
                os.environ.pop("DILIGENCE_RAW_DIR", None)


class CliSmokeTests(unittest.TestCase):
    def test_module_help(self):
        proc = subprocess.run(
            [sys.executable, "-m", "diligence", "--help"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("prepare", proc.stdout)


if __name__ == "__main__":
    unittest.main()
