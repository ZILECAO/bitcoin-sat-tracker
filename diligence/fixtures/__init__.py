"""Deterministic synthetic Bitcoin RPC and mempool fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from diligence.constants import FIXTURES_DIR

GENESIS_TXID = "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
SAMPLE_TXID = "5435a6f76793a55e20626fb3fda796e93462f62ccb0f244c382127043f495451"
SAMPLE_SPEND_TXID = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SAMPLE_BLOCKHASH = "0000000000000000000fakeblockhash000000000000000000000000000001"


def block_reward_sats(height: int) -> int:
    halvings = height // 210000
    reward = 5000000000
    while halvings > 0:
        reward //= 2
        halvings -= 1
    return reward


def sample_transaction(*, txid: str = SAMPLE_TXID, confirmed: bool = True) -> dict[str, Any]:
    tx: dict[str, Any] = {
        "txid": txid,
        "vin": [
            {
                "txid": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                "vout": 0,
            }
        ],
        "vout": [
            {
                "value": 0.5,
                "n": 0,
                "scriptPubKey": {
                    "address": "bc1qfakeaddress0000000000000000000000001",
                    "type": "witness_v0_keyhash",
                },
            },
            {
                "value": 0.49,
                "n": 1,
                "scriptPubKey": {
                    "address": "bc1qfakeaddress0000000000000000000000002",
                    "type": "witness_v0_keyhash",
                },
            },
        ],
    }
    if confirmed:
        tx["blockhash"] = SAMPLE_BLOCKHASH
    return tx


def sample_block(*, height: int = 800000) -> dict[str, Any]:
    return {
        "hash": SAMPLE_BLOCKHASH,
        "height": height,
        "time": 1700000000,
        "tx": [
            "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            SAMPLE_SPEND_TXID,
        ],
    }


def mempool_outspend(*, spent: bool = True) -> dict[str, Any]:
    if spent:
        return {"spent": True, "txid": SAMPLE_SPEND_TXID, "vin": 0}
    return {"spent": False}


def rpc_fixture_bundle() -> dict[str, Any]:
    return {
        "bitcoin_rpc": {
            "url": "http://127.0.0.1:18443",
            "user": "regtest-fake-user",
            "password": "regtest-fake-pass-NOT-A-SECRET",
            "responses": {
                f"getrawtransaction:{SAMPLE_TXID}:True": sample_transaction(),
                f"getrawtransaction:{SAMPLE_SPEND_TXID}:True": sample_transaction(
                    txid=SAMPLE_SPEND_TXID
                ),
                f"getblock:{SAMPLE_BLOCKHASH}": sample_block(),
                "getblockchaininfo": {"chain": "regtest", "blocks": 101},
            },
            "errors": {
                f"getrawtransaction:{GENESIS_TXID}:True": {
                    "code": -5,
                    "message": "The genesis block coinbase is not considered an ordinary transaction",
                }
            },
        },
        "mempool": {
            "base_url": "https://example.invalid/mempool-fake",
            "outspends": {
                f"{SAMPLE_TXID}:0": mempool_outspend(spent=True),
                f"{SAMPLE_TXID}:1": mempool_outspend(spent=False),
            },
        },
        "block_rewards": {
            str(h): block_reward_sats(h) for h in (0, 209999, 210000, 420000, 1260000)
        },
        "edge_cases": {
            "unconfirmed_tx": sample_transaction(txid="dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd", confirmed=False),
            "out_of_range_vout": {"txid": SAMPLE_TXID, "vout": 99},
            "satpoint_valid": f"{SAMPLE_TXID}:0:0",
            "satpoint_invalid": f"{SAMPLE_TXID}:0:-1",
        },
    }


def materialize_fixtures(dest: Path) -> dict[str, str]:
    dest.mkdir(parents=True, exist_ok=True)
    bundle = rpc_fixture_bundle()
    written: dict[str, str] = {}
    path = dest / "bitcoin_rpc_mempool.json"
    path.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written["bitcoin_rpc_mempool"] = str(path)

    # Also keep a package-local copy for committed deterministic fixtures.
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    committed = FIXTURES_DIR / "bitcoin_rpc_mempool.json"
    committed.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written["committed_bitcoin_rpc_mempool"] = str(committed)
    return written


def load_committed_fixtures() -> dict[str, Any]:
    path = FIXTURES_DIR / "bitcoin_rpc_mempool.json"
    return json.loads(path.read_text(encoding="utf-8"))
