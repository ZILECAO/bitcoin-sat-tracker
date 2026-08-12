"""Tests for the heavier sat-hunt benchmark contract and ordinal primitives."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from diligence.sat_hunt.ordinal import (  # noqa: E402
    OrdinalRangeError,
    assign_ordinal_ranges,
    block_subsidy_sats,
    first_sat_of_block,
    locate_sat,
    range_size,
)
from diligence.sat_hunt.score import (  # noqa: E402
    SatHuntValidationError,
    score_final_answer,
    validate_final_answer,
)


def _answer() -> dict:
    block_hash = "ab" * 32
    txid = "cd" * 32
    evidence_hash = "ef" * 32
    trace_id = "12" * 16
    evidence = [
        {
            "id": "ev-all",
            "source": "fixture",
            "request": {"method": "snapshot"},
            "response_sha256": evidence_hash,
        }
    ]
    return {
        "benchmark_version": "sat-hunt-v1",
        "snapshot": {"height": 100, "block_hash": block_hash, "confirmations": 6},
        "interpretation": {
            "earliest_means": "lowest ordinal sat number",
            "activity_is_proxy": True,
            "wallet_attribution": "not inferable from blockchain data",
        },
        "earliest_active_sat": {
            "sat_number": 12,
            "outpoint": f"{txid}:0",
            "offset": 2,
            "script_type": "witness_v1_taproot",
            "current_output_height": 99,
            "transfers_in_activity_window": 3,
            "inscription_ids": [],
            "evidence_refs": ["ev-all"],
        },
        "earliest_active_inscribed_sat": {
            "sat_number": 20,
            "outpoint": f"{txid}:1",
            "offset": 0,
            "script_type": "witness_v1_taproot",
            "current_output_height": 98,
            "transfers_in_activity_window": 4,
            "inscription_ids": [f"{txid}i0"],
            "evidence_refs": ["ev-all"],
        },
        "active_sat_minimality": {
            "candidate_sat": 12,
            "complete": True,
            "covered_intervals": [
                {"start": 0, "end": 12, "reason": "inactive", "evidence_refs": ["ev-all"]}
            ],
        },
        "inscribed_sat_minimality": {
            "candidate_sat": 20,
            "complete": True,
            "covered_intervals": [
                {
                    "start": 0,
                    "end": 20,
                    "reason": "not active and inscribed",
                    "evidence_refs": ["ev-all"],
                }
            ],
        },
        "evidence": evidence,
        "artifacts": {
            "scripts": ["sat_hunt/cli.py"],
            "tests": ["tests/test_sat_hunt_agent.py"],
            "test_command": "python3 -m unittest",
            "tests_passed": True,
        },
        "run": {
            "model": "example-model",
            "harness": "baseline-harness",
            "trace_id": trace_id,
            "duration_ms": 1000,
            "cost_usd": 0.01,
            "tool_calls": 5,
        },
    }


class OrdinalPrimitiveTests(unittest.TestCase):
    def test_subsidy_and_first_sat_boundaries(self):
        self.assertEqual(block_subsidy_sats(0), 5_000_000_000)
        self.assertEqual(block_subsidy_sats(209_999), 5_000_000_000)
        self.assertEqual(block_subsidy_sats(210_000), 2_500_000_000)
        self.assertEqual(first_sat_of_block(0), 0)
        self.assertEqual(first_sat_of_block(1), 5_000_000_000)
        self.assertEqual(first_sat_of_block(210_000), 1_050_000_000_000_000)

    def test_fifo_assignment_and_fee_ranges(self):
        outputs, fees = assign_ordinal_ranges([[0, 5], [10, 15]], [3, 4])
        self.assertEqual(outputs, [[[0, 3]], [[3, 5], [10, 12]]])
        self.assertEqual(fees, [[12, 15]])
        self.assertEqual(range_size(outputs[1]), 4)
        self.assertEqual(locate_sat(outputs[1], 11), 3)
        self.assertIsNone(locate_sat(outputs[1], 9))

    def test_rejects_output_inflation(self):
        with self.assertRaises(OrdinalRangeError):
            assign_ordinal_ranges([[0, 2]], [3])


class SatHuntContractTests(unittest.TestCase):
    def test_committed_benchmark_is_training_free(self):
        benchmark = json.loads(
            (REPO_ROOT / "diligence" / "sat_hunt" / "benchmark.json").read_text()
        )
        self.assertEqual(benchmark["benchmark_version"], "sat-hunt-v1")
        self.assertEqual(benchmark["training"], "out_of_scope")
        self.assertEqual(len(benchmark["arms"]), 4)
        self.assertEqual(benchmark["definitions"]["activity_proxy"]["lookback_blocks"], 4320)

    def test_valid_answer_and_oracle_score(self):
        answer = _answer()
        validated = validate_final_answer(answer)
        oracle = {
            "benchmark_version": "sat-hunt-v1",
            "snapshot": answer["snapshot"],
            "earliest_active_sat": answer["earliest_active_sat"],
            "earliest_active_inscribed_sat": answer["earliest_active_inscribed_sat"],
        }
        result = score_final_answer(validated, oracle)
        self.assertTrue(result["correct"])
        self.assertTrue(result["efficiency_eligible"])
        self.assertEqual(result["cost_usd"], 0.01)

    def test_wrong_answer_cannot_win_on_cost(self):
        answer = _answer()
        oracle = {
            "benchmark_version": "sat-hunt-v1",
            "snapshot": answer["snapshot"],
            "earliest_active_sat": {**answer["earliest_active_sat"], "sat_number": 11},
            "earliest_active_inscribed_sat": answer["earliest_active_inscribed_sat"],
        }
        result = score_final_answer(answer, oracle)
        self.assertFalse(result["correct"])
        self.assertFalse(result["efficiency_eligible"])
        self.assertIsNone(result["cost_usd"])

    def test_rejects_wallet_attribution_claim(self):
        answer = _answer()
        answer["interpretation"]["wallet_attribution"] = "not Satoshi"
        with self.assertRaises(SatHuntValidationError):
            validate_final_answer(answer)

    def test_rejects_gap_in_minimum_certificate(self):
        answer = copy.deepcopy(_answer())
        answer["active_sat_minimality"]["covered_intervals"] = [
            {"start": 1, "end": 12, "reason": "inactive", "evidence_refs": ["ev-all"]}
        ]
        with self.assertRaises(SatHuntValidationError):
            validate_final_answer(answer)


if __name__ == "__main__":
    unittest.main()
