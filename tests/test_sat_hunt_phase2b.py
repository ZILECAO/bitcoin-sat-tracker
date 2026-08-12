"""Additional deterministic tests for attribution, fixtures, tools, and scorers."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from diligence.sat_hunt.attribution import (  # noqa: E402
    EXPECTED_CSV_SHA256,
    EXPECTED_RECORDS,
    AttributionError,
    CurrentOutputIdentity,
    build_match_index,
    derived_set_hash,
    load_patoshi_csv,
    match_current_output,
    p2pk_script_hex,
    p2pkh_address_mainnet,
    verify_csv_bytes,
)
from diligence.sat_hunt.fixtures import build_fixture, build_oracle  # noqa: E402
from diligence.sat_hunt.scorers import (  # noqa: E402
    score_ordinal_fifo,
    score_public_satoshi_attribution,
)
from diligence.sat_hunt.agent.tools import ToolRegistry  # noqa: E402
from diligence.sat_hunt.tasks import prepare_task_workspace  # noqa: E402
from diligence.sat_hunt.score import ATTRIBUTION_PASS_CLAIM  # noqa: E402


CSV_PATH = Path(os.environ.get("DILIGENCE_RAW_DIR", str(Path.home() / "diligence-raw-phase2b"))) / "patoshi" / "patoshi_pubkeys_COMPLETE.csv"


@unittest.skipUnless(CSV_PATH.exists(), "Patoshi CSV not present in private raw dir")
class AttributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_patoshi_csv(CSV_PATH)
        cls.match_index = build_match_index(cls.records)

    def test_csv_hash_and_count(self):
        digest = verify_csv_bytes(CSV_PATH.read_bytes())
        self.assertEqual(digest, EXPECTED_CSV_SHA256)
        self.assertEqual(len(self.records), EXPECTED_RECORDS)

    def test_rejects_hash_mismatch(self):
        with self.assertRaises(AttributionError):
            verify_csv_bytes(b"not-the-csv")

    def test_pubkey_script_and_address_derivation(self):
        rec = self.records[0]
        self.assertEqual(p2pk_script_hex(rec.public_key_hex), rec.p2pk_script_hex)
        self.assertEqual(p2pkh_address_mainnet(rec.public_key_hex), rec.p2pkh_address)
        self.assertTrue(rec.p2pk_script_hex.startswith("41"))
        self.assertTrue(rec.p2pk_script_hex.endswith("ac"))
        self.assertTrue(rec.p2pkh_address.startswith("1"))

    def test_exact_match_and_nonmatch(self):
        rec = self.records[0]
        hit = match_current_output(
            CurrentOutputIdentity(public_key_hex=rec.public_key_hex),
            self.match_index,
        )
        self.assertTrue(hit["excluded"])
        miss = match_current_output(
            CurrentOutputIdentity(address="bcrt1qnotpatoshi"),
            self.match_index,
        )
        self.assertFalse(miss["excluded"])
        self.assertEqual(miss["claim"], ATTRIBUTION_PASS_CLAIM)

    def test_derived_set_hash_stable(self):
        self.assertEqual(derived_set_hash(self.records), derived_set_hash(self.records))


@unittest.skipUnless(CSV_PATH.exists(), "Patoshi CSV not present in private raw dir")
class FixtureOracleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = load_patoshi_csv(CSV_PATH)
        cls.match_index = build_match_index(cls.records)
        cls.fixture = build_fixture(attribution_records=cls.records)
        cls.oracle = build_oracle(cls.fixture, cls.match_index)

    def test_oracle_active_before_inscribed(self):
        active = self.oracle["earliest_active_sat"]["sat_number"]
        inscribed = self.oracle["earliest_active_inscribed_sat"]["sat_number"]
        self.assertLess(active, inscribed)

    def test_attributed_current_excluded_moved_not(self):
        tracked = self.fixture["tracked_sats"]
        attr = self.fixture["sat_index"][str(tracked["attributed_current"])]
        u = self.fixture["utxos"][attr["outpoint"]]
        self.assertTrue(
            match_current_output(
                CurrentOutputIdentity(
                    script_pubkey_hex=u["script_pubkey"],
                    address=u["address"],
                    public_key_hex=u["public_key"],
                ),
                self.match_index,
            )["excluded"]
        )
        moved = self.fixture["sat_index"][str(tracked["patoshi_origin_moved"])]
        u2 = self.fixture["utxos"][moved["outpoint"]]
        self.assertFalse(
            match_current_output(
                CurrentOutputIdentity(
                    script_pubkey_hex=u2["script_pubkey"],
                    address=u2["address"],
                ),
                self.match_index,
            )["excluded"]
        )

    def test_activity_window_and_transfers(self):
        sat = self.fixture["tracked_sats"]["earliest_active_uninscribed"]
        utxo = self.fixture["utxos"][self.fixture["sat_index"][str(sat)]["outpoint"]]
        window_start = self.fixture["activity_window"]["window_start_height"]
        self.assertGreaterEqual(utxo["height"], window_start)
        self.assertGreaterEqual(utxo["transfers_in_activity_window"], 3)
        self.assertTrue(utxo["spendable"])


@unittest.skipUnless(CSV_PATH.exists(), "Patoshi CSV not present in private raw dir")
class ToolAndScorerTests(unittest.TestCase):
    def test_tools_confinement_and_fifo_scorer(self):
        records = load_patoshi_csv(CSV_PATH)
        fixture = build_fixture(attribution_records=records)
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            prepare_task_workspace(ws, fixture=fixture, include_toolkit=True)
            tools = ToolRegistry(workspace=ws, fixture=fixture)
            listed = tools.call("list_files", {})
            self.assertTrue(listed.ok)
            self.assertIn("fixture.json", listed.result["files"])
            escape = tools.call("read_file", {"path": "../etc/passwd"})
            self.assertFalse(escape.ok)
            demo = tools.call("fixture_fee_demo", {})
            self.assertTrue(demo.ok)
            # write correct fifo answer
            from diligence.sat_hunt.ordinal import assign_ordinal_ranges

            out, fees = assign_ordinal_ranges(
                demo.result["input_ranges"], demo.result["output_values"]
            )
            (ws / "answers").mkdir(exist_ok=True)
            (ws / "answers" / "fifo.json").write_text(
                json.dumps({"output_ranges": out, "fee_ranges": fees})
            )
            (ws / "tests" / "test_fifo.py").write_text("def test_ok():\n    assert True\n")
            score = score_ordinal_fifo(ws, fixture)
            self.assertTrue(score.passed)

    def test_workspace_excludes_diligence(self):
        records = load_patoshi_csv(CSV_PATH)
        fixture = build_fixture(attribution_records=records)
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws2"
            prepare_task_workspace(ws, fixture=fixture)
            self.assertFalse((ws / "diligence").exists())
            self.assertFalse((ws / "AGENTS.md").exists())
            self.assertFalse((ws / "docs").exists())


if __name__ == "__main__":
    unittest.main()
