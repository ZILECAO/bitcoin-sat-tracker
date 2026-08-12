"""Deterministic sat-hunt chain fixture generator.

Creates a self-contained snapshot universe with enough structure to exercise
every development family and the final-exam predicates without a live node.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from diligence.sat_hunt.attribution import (
    SOURCE_ID as ATTRIBUTION_SOURCE_ID,
    CurrentOutputIdentity,
    AttributionRecord,
    match_current_output,
    p2pk_script_hex,
    p2pkh_address_mainnet,
)
from diligence.sat_hunt.ordinal import assign_ordinal_ranges, first_sat_of_block, locate_sat
from diligence.sat_hunt.score import ATTRIBUTION_PASS_CLAIM, ATTRIBUTION_POLICY_ID

BENCHMARK_VERSION = "sat-hunt-v2"
ACTIVITY_LOOKBACK = 4320
MIN_TRANSFERS = 3


def _txid(label: str) -> str:
    return hashlib.sha256(f"sat-hunt-fixture:{label}".encode()).hexdigest()


def _block_hash(height: int) -> str:
    return hashlib.sha256(f"sat-hunt-block:{height}".encode()).hexdigest()


def build_fixture(*, attribution_records: list[AttributionRecord] | None = None) -> dict[str, Any]:
    """Build the frozen deterministic fixture and embedded public views."""
    snapshot_height = 10_000
    window_start = snapshot_height - ACTIVITY_LOOKBACK  # 5680
    # Use tiny synthetic sat ranges for clarity; treat them as ordinal numbers.
    # Patoshi-origin sat later moves to a non-matching output.
    sat_uninscribed_active = 100
    sat_inscribed_active = 250
    sat_inactive = 50
    sat_attributed_current = 400
    sat_patoshi_origin_moved = 500
    sat_unspendable = 600
    sat_low_misleading_inactive = 10
    sat_low_misleading_attributed = 20

    # Attribution sample: first real Patoshi record if available, else synthetic.
    if attribution_records:
        attr = attribution_records[0]
        attr_pubkey = attr.public_key_hex
        attr_script = attr.p2pk_script_hex
        attr_address = attr.p2pkh_address
    else:
        # Deterministic synthetic uncompressed key-shaped hex (not a real curve point).
        # For fixture-only matching we still use the same derivation helpers.
        attr_pubkey = "04" + ("11" * 64)
        try:
            attr_script = p2pk_script_hex(attr_pubkey)
            attr_address = p2pkh_address_mainnet(attr_pubkey)
        except Exception:
            attr_script = "51"
            attr_address = "attr-synthetic"

    # Transaction graph (heights inside/outside window)
    # Coinbase-like creation of ranges at early heights, then transfers.
    txs: dict[str, Any] = {}
    utxos: dict[str, Any] = {}
    inscriptions: dict[str, list[str]] = {}
    sat_index: dict[str, Any] = {}

    def add_tx(label: str, height: int, vin: list[dict], vout: list[dict], coinbase: bool = False):
        txid = _txid(label)
        txs[txid] = {
            "txid": txid,
            "height": height,
            "coinbase": coinbase,
            "vin": vin,
            "vout": vout,
            "block_hash": _block_hash(height),
        }
        return txid

    # Genesis-like creations (coinbase) outside window
    t_c1 = add_tx(
        "cb-early-1",
        100,
        [],
        [
            {"value": 100, "script_type": "op_return", "script_pubkey": "6a0100", "ranges": [[sat_unspendable, sat_unspendable + 100]], "provably_unspendable": True},
            {"value": 50, "script_type": "p2wpkh", "script_pubkey": "0014" + "aa" * 20, "ranges": [[sat_inactive, sat_inactive + 50]], "address": "bcrt1qinactive0000000000000000000000000"},
        ],
        coinbase=True,
    )
    t_c2 = add_tx(
        "cb-early-2",
        200,
        [],
        [
            {"value": 200, "script_type": "p2wpkh", "script_pubkey": "0014" + "bb" * 20, "ranges": [[sat_uninscribed_active, sat_uninscribed_active + 100]], "address": "bcrt1qactivebase000000000000000000000"},
            {"value": 100, "script_type": "p2wpkh", "script_pubkey": "0014" + "cc" * 20, "ranges": [[sat_inscribed_active, sat_inscribed_active + 100]], "address": "bcrt1qinscribebase0000000000000000000"},
            {"value": 50, "script_type": "p2pk", "script_pubkey": attr_script, "ranges": [[sat_attributed_current, sat_attributed_current + 50]], "address": attr_address, "public_key": attr_pubkey},
            {"value": 50, "script_type": "p2pk", "script_pubkey": attr_script, "ranges": [[sat_patoshi_origin_moved, sat_patoshi_origin_moved + 50]], "address": attr_address, "public_key": attr_pubkey},
            {"value": 20, "script_type": "p2wpkh", "script_pubkey": "0014" + "dd" * 20, "ranges": [[sat_low_misleading_inactive, sat_low_misleading_inactive + 20]], "address": "bcrt1qmisleadinginactive000000000000"},
            {"value": 20, "script_type": "p2pk", "script_pubkey": attr_script, "ranges": [[sat_low_misleading_attributed, sat_low_misleading_attributed + 20]], "address": attr_address, "public_key": attr_pubkey},
        ],
        coinbase=True,
    )

    # Move active uninscribed sat through >=3 non-coinbase transfers inside window
    # Also create current output inside window.
    prev = {"txid": t_c2, "vout": 0}
    heights = [window_start + 10, window_start + 20, window_start + 30, window_start + 40]
    labels = ["xfer-u1", "xfer-u2", "xfer-u3", "xfer-u4"]
    for i, (h, lab) in enumerate(zip(heights, labels)):
        txid = add_tx(
            lab,
            h,
            [{"txid": prev["txid"], "vout": prev["vout"]}],
            [
                {
                    "value": 100,
                    "script_type": "p2wpkh",
                    "script_pubkey": "0014" + f"{i+1:02x}" * 20,
                    "ranges": [[sat_uninscribed_active, sat_uninscribed_active + 100]],
                    "address": f"bcrt1qactive{i}",
                }
            ],
        )
        prev = {"txid": txid, "vout": 0}
    active_uninscribed_outpoint = f"{prev['txid']}:{prev['vout']}"
    active_uninscribed_height = heights[-1]

    # Move inscribed active sat similarly, attach inscription on final output
    prev = {"txid": t_c2, "vout": 1}
    heights_i = [window_start + 11, window_start + 21, window_start + 31, window_start + 41]
    for i, (h, lab) in enumerate(zip(heights_i, ["xfer-i1", "xfer-i2", "xfer-i3", "xfer-i4"])):
        txid = add_tx(
            lab,
            h,
            [{"txid": prev["txid"], "vout": prev["vout"]}],
            [
                {
                    "value": 100,
                    "script_type": "p2tr",
                    "script_pubkey": "5120" + f"{i+1:02x}" * 32,
                    "ranges": [[sat_inscribed_active, sat_inscribed_active + 100]],
                    "address": f"bcrt1pinscribed{i}",
                }
            ],
        )
        prev = {"txid": txid, "vout": 0}
    active_inscribed_outpoint = f"{prev['txid']}:{prev['vout']}"
    active_inscribed_height = heights_i[-1]
    inscription_id = f"{prev['txid']}i0"
    inscriptions[str(sat_inscribed_active)] = [inscription_id]
    # reinscription pointer example
    inscriptions[str(sat_inscribed_active)].append(f"{prev['txid']}i1")

    # Patoshi-origin sat moves to NON-matching current output inside window with enough transfers
    prev = {"txid": t_c2, "vout": 3}
    heights_p = [window_start + 12, window_start + 22, window_start + 32, window_start + 42]
    for i, (h, lab) in enumerate(zip(heights_p, ["xfer-p1", "xfer-p2", "xfer-p3", "xfer-p4"])):
        txid = add_tx(
            lab,
            h,
            [{"txid": prev["txid"], "vout": prev["vout"]}],
            [
                {
                    "value": 50,
                    "script_type": "p2wpkh",
                    "script_pubkey": "0014" + "ee" * 20,
                    "ranges": [[sat_patoshi_origin_moved, sat_patoshi_origin_moved + 50]],
                    "address": "bcrt1qmovednonmatch000000000000000000",
                }
            ],
        )
        prev = {"txid": txid, "vout": 0}
    moved_outpoint = f"{prev['txid']}:{prev['vout']}"

    # Attributed current output: never moved (still exact match) — created early, outside activity
    attributed_outpoint = f"{t_c2}:2"
    inactive_outpoint = f"{t_c1}:1"
    unspendable_outpoint = f"{t_c1}:0"
    misleading_inactive_outpoint = f"{t_c2}:4"
    misleading_attr_outpoint = f"{t_c2}:5"

    # UTXO set at snapshot
    def utxo(outpoint: str, sat: int, height: int, script_type: str, script: str, address: str | None, pubkey: str | None, spendable: bool, transfers: int, ranges: list):
        txid, vout_s = outpoint.split(":")
        utxos[outpoint] = {
            "outpoint": outpoint,
            "txid": txid,
            "vout": int(vout_s),
            "height": height,
            "script_type": script_type,
            "script_pubkey": script,
            "address": address,
            "public_key": pubkey,
            "spendable": spendable,
            "provably_unspendable": not spendable and script_type == "op_return",
            "value": sum(e - s for s, e in ranges),
            "ranges": ranges,
            "transfers_in_activity_window": transfers,
        }
        for start, end in ranges:
            for sat_n in range(start, min(start + 1, end)):  # index first sat of each range for lookup
                sat_index[str(sat_n)] = {
                    "sat": sat_n,
                    "outpoint": outpoint,
                    "offset": locate_sat(ranges, sat_n),
                    "inscription_ids": inscriptions.get(str(sat_n), []),
                }
        # Also index the specific tracked sats
        if locate_sat(ranges, sat) is not None:
            sat_index[str(sat)] = {
                "sat": sat,
                "outpoint": outpoint,
                "offset": locate_sat(ranges, sat),
                "inscription_ids": inscriptions.get(str(sat), []),
            }

    utxo(active_uninscribed_outpoint, sat_uninscribed_active, active_uninscribed_height, "p2wpkh", "0014" + "04" * 20, "bcrt1qactive3", None, True, 4, [[sat_uninscribed_active, sat_uninscribed_active + 100]])
    utxo(active_inscribed_outpoint, sat_inscribed_active, active_inscribed_height, "p2tr", "5120" + "04" * 32, "bcrt1pinscribed3", None, True, 4, [[sat_inscribed_active, sat_inscribed_active + 100]])
    utxo(moved_outpoint, sat_patoshi_origin_moved, heights_p[-1], "p2wpkh", "0014" + "ee" * 20, "bcrt1qmovednonmatch000000000000000000", None, True, 4, [[sat_patoshi_origin_moved, sat_patoshi_origin_moved + 50]])
    utxo(attributed_outpoint, sat_attributed_current, 200, "p2pk", attr_script, attr_address, attr_pubkey, True, 0, [[sat_attributed_current, sat_attributed_current + 50]])
    utxo(inactive_outpoint, sat_inactive, 100, "p2wpkh", "0014" + "aa" * 20, "bcrt1qinactive0000000000000000000000000", None, True, 0, [[sat_inactive, sat_inactive + 50]])
    utxo(unspendable_outpoint, sat_unspendable, 100, "op_return", "6a0100", None, None, False, 0, [[sat_unspendable, sat_unspendable + 100]])
    utxo(misleading_inactive_outpoint, sat_low_misleading_inactive, 200, "p2wpkh", "0014" + "dd" * 20, "bcrt1qmisleadinginactive000000000000", None, True, 0, [[sat_low_misleading_inactive, sat_low_misleading_inactive + 20]])
    utxo(misleading_attr_outpoint, sat_low_misleading_attributed, 200, "p2pk", attr_script, attr_address, attr_pubkey, True, 0, [[sat_low_misleading_attributed, sat_low_misleading_attributed + 20]])

    # Fee example: split/merge demo transaction for development tasks
    fee_demo_inputs = [[0, 10], [20, 30]]
    fee_outputs, fee_ranges = assign_ordinal_ranges(fee_demo_inputs, [5, 8])
    fee_demo = {
        "input_ranges": fee_demo_inputs,
        "output_values": [5, 8],
        "output_ranges": fee_outputs,
        "fee_ranges": fee_ranges,
        "coinbase_fee_reassignment": {
            "coinbase_height": snapshot_height,
            "assigned_ranges": fee_ranges,
            "note": "Fees are reassigned through the block coinbase in order.",
        },
    }

    fixture = {
        "benchmark_version": BENCHMARK_VERSION,
        "fixture_id": "sat-hunt-deterministic-v1",
        "snapshot": {
            "height": snapshot_height,
            "block_hash": _block_hash(snapshot_height),
            "confirmations": 6,
        },
        "activity_window": {
            "lookback_blocks": ACTIVITY_LOOKBACK,
            "window_start_height": window_start,
            "minimum_confirmed_non_coinbase_transfers": MIN_TRANSFERS,
        },
        "transactions": txs,
        "utxos": utxos,
        "sat_index": sat_index,
        "inscriptions": inscriptions,
        "fee_demo": fee_demo,
        "tracked_sats": {
            "earliest_active_uninscribed": sat_uninscribed_active,
            "earliest_active_inscribed": sat_inscribed_active,
            "inactive": sat_inactive,
            "attributed_current": sat_attributed_current,
            "patoshi_origin_moved": sat_patoshi_origin_moved,
            "unspendable": sat_unspendable,
            "misleading_inactive": sat_low_misleading_inactive,
            "misleading_attributed": sat_low_misleading_attributed,
        },
        "public_views": {
            "list_utxos": sorted(utxos),
            "list_sats": sorted(int(k) for k in sat_index),
        },
    }
    return fixture


def fixture_sha256(fixture: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(fixture, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_public_fixture(fixture: dict[str, Any], dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
    return fixture_sha256(fixture)


def build_oracle(fixture: dict[str, Any], match_index: dict[str, list[str]]) -> dict[str, Any]:
    """Hidden oracle for the deterministic final exam."""
    tracked = fixture["tracked_sats"]
    utxos = fixture["utxos"]
    sat_index = fixture["sat_index"]

    def candidate(sat: int) -> dict[str, Any]:
        info = sat_index[str(sat)]
        utxo = utxos[info["outpoint"]]
        identity = CurrentOutputIdentity(
            outpoint=info["outpoint"],
            script_pubkey_hex=utxo.get("script_pubkey"),
            address=utxo.get("address"),
            public_key_hex=utxo.get("public_key"),
        )
        attribution = match_current_output(identity, match_index)
        # Passing candidates must not be excluded
        assert attribution["excluded"] is False
        return {
            "sat_number": sat,
            "outpoint": info["outpoint"],
            "offset": info["offset"],
            "script_type": utxo["script_type"],
            "current_output_height": utxo["height"],
            "transfers_in_activity_window": utxo["transfers_in_activity_window"],
            "inscription_ids": list(info["inscription_ids"]),
            "satoshi_attribution": {
                "policy_id": ATTRIBUTION_POLICY_ID,
                "excluded": False,
                "match_source_ids": [],
                "sources_checked": [ATTRIBUTION_SOURCE_ID],
                "claim": ATTRIBUTION_PASS_CLAIM,
            },
            "evidence_refs": ["ev-fixture-snapshot"],
        }

    active_sat = tracked["earliest_active_uninscribed"]
    inscribed_sat = tracked["earliest_active_inscribed"]
    oracle = {
        "benchmark_version": BENCHMARK_VERSION,
        "snapshot": fixture["snapshot"],
        "earliest_active_sat": candidate(active_sat),
        "earliest_active_inscribed_sat": candidate(inscribed_sat),
        "notes": {
            "misleading_lower_inactive": tracked["misleading_inactive"],
            "misleading_lower_attributed": tracked["misleading_attributed"],
            "patoshi_origin_moved_still_qualifies_if_active": tracked["patoshi_origin_moved"],
        },
    }
    return oracle
