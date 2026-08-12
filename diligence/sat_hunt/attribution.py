"""Public Satoshi/Patoshi attribution normalization (exact-match only).

Downloads stay outside Git. This module derives deterministic identifiers from
the pinned CSV and never claims ownership certainty.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from diligence.sat_hunt.score import ATTRIBUTION_PASS_CLAIM, ATTRIBUTION_POLICY_ID, ATTRIBUTION_SOURCE_ID

EXPECTED_CSV_SHA256 = "f649579e286085325a881bec1168e88bbb6f5d67e10b7ef8cb5c65e916a34a2e"
EXPECTED_RECORDS = 21_953
SOURCE_ID = ATTRIBUTION_SOURCE_ID

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


class AttributionError(ValueError):
    """Raised for malformed attribution inputs or hash mismatches."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash160(data: bytes) -> bytes:
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


def base58check_encode(payload: bytes) -> str:
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    data = payload + checksum
    num = int.from_bytes(data, "big")
    encoded = ""
    while num:
        num, rem = divmod(num, 58)
        encoded = _BASE58_ALPHABET[rem] + encoded
    # Preserve leading zero bytes as '1'
    pad = 0
    for byte in data:
        if byte == 0:
            pad += 1
        else:
            break
    return ("1" * pad) + (encoded or "1")


def p2pk_script_hex(pubkey_hex: str) -> str:
    pubkey = _parse_pubkey_hex(pubkey_hex)
    return f"41{pubkey.hex()}ac"


def p2pkh_address_mainnet(pubkey_hex: str) -> str:
    pubkey = _parse_pubkey_hex(pubkey_hex)
    return base58check_encode(b"\x00" + hash160(pubkey))


def _parse_pubkey_hex(pubkey_hex: str) -> bytes:
    if not isinstance(pubkey_hex, str) or len(pubkey_hex) not in (66, 130):
        raise AttributionError("public key must be 33-byte or 65-byte hex")
    try:
        raw = bytes.fromhex(pubkey_hex)
    except ValueError as exc:
        raise AttributionError("public key is not valid hex") from exc
    if raw[0] not in (0x02, 0x03, 0x04):
        raise AttributionError("unsupported public key prefix")
    if raw[0] == 0x04 and len(raw) != 65:
        raise AttributionError("uncompressed public key must be 65 bytes")
    if raw[0] in (0x02, 0x03) and len(raw) != 33:
        raise AttributionError("compressed public key must be 33 bytes")
    return raw


@dataclass(frozen=True)
class AttributionRecord:
    source_id: str
    block_height: int
    output_index: int
    public_key_hex: str
    amount_btc: str
    script_type: str
    p2pk_script_hex: str
    p2pkh_address: str
    derived_identifiers_note: str = (
        "p2pkh_address is derived from the listed public key for exact matching only"
    )

    def match_keys(self) -> set[str]:
        return {
            f"pubkey:{self.public_key_hex.lower()}",
            f"script:{self.p2pk_script_hex.lower()}",
            f"address:{self.p2pkh_address}",
        }


def verify_csv_bytes(data: bytes) -> str:
    digest = sha256_hex(data)
    if digest != EXPECTED_CSV_SHA256:
        raise AttributionError(
            f"Patoshi CSV SHA-256 mismatch: got {digest}, expected {EXPECTED_CSV_SHA256}"
        )
    return digest


def load_patoshi_csv(path: Path) -> list[AttributionRecord]:
    data = path.read_bytes()
    verify_csv_bytes(data)
    text = data.decode("utf-8")
    reader = csv.DictReader(text.splitlines())
    required = {"Block Height", "Output Index", "Address/Pubkey", "Amount (BTC)", "Script Type"}
    if reader.fieldnames is None or set(reader.fieldnames) != required:
        raise AttributionError(f"unexpected CSV columns: {reader.fieldnames}")
    records: list[AttributionRecord] = []
    seen_keys: set[str] = set()
    seen_height_vout: set[tuple[int, int]] = set()
    for index, row in enumerate(reader, start=1):
        try:
            height = int(row["Block Height"])
            vout = int(row["Output Index"])
        except (TypeError, ValueError) as exc:
            raise AttributionError(f"malformed height/vout at row {index}") from exc
        pubkey = row["Address/Pubkey"].strip().lower()
        script_type = row["Script Type"].strip().lower()
        if script_type != "p2pk":
            raise AttributionError(f"unexpected script type at row {index}: {script_type}")
        if (height, vout) in seen_height_vout:
            raise AttributionError(f"duplicate height/vout at row {index}")
        if pubkey in seen_keys:
            raise AttributionError(f"duplicate public key at row {index}")
        seen_height_vout.add((height, vout))
        seen_keys.add(pubkey)
        records.append(
            AttributionRecord(
                source_id=SOURCE_ID,
                block_height=height,
                output_index=vout,
                public_key_hex=pubkey,
                amount_btc=str(row["Amount (BTC)"]),
                script_type=script_type,
                p2pk_script_hex=p2pk_script_hex(pubkey),
                p2pkh_address=p2pkh_address_mainnet(pubkey),
            )
        )
    if len(records) != EXPECTED_RECORDS:
        raise AttributionError(f"expected {EXPECTED_RECORDS} records, got {len(records)}")
    return records


def build_match_index(records: Iterable[AttributionRecord]) -> dict[str, list[str]]:
    """Map normalized match keys to source record fingerprints."""
    index: dict[str, list[str]] = {}
    for record in records:
        fingerprint = f"{record.block_height}:{record.output_index}:{record.public_key_hex}"
        for key in record.match_keys():
            index.setdefault(key, []).append(fingerprint)
    return index


def derived_set_payload(records: list[AttributionRecord]) -> dict[str, Any]:
    match_index = build_match_index(records)
    payload = {
        "policy_id": ATTRIBUTION_POLICY_ID,
        "source_id": SOURCE_ID,
        "csv_sha256": EXPECTED_CSV_SHA256,
        "record_count": len(records),
        "match_key_count": len(match_index),
        "records": [asdict(record) for record in records],
        "match_index_keys_sample": sorted(match_index)[:5],
    }
    return payload


def derived_set_hash(records: list[AttributionRecord]) -> str:
    # Hash only stable match material, not pretty-printed JSON whitespace.
    match_index = build_match_index(records)
    canonical = {
        "policy_id": ATTRIBUTION_POLICY_ID,
        "source_id": SOURCE_ID,
        "csv_sha256": EXPECTED_CSV_SHA256,
        "record_count": len(records),
        "match_keys": sorted(match_index),
        "fingerprints": sorted({fp for fps in match_index.values() for fp in fps}),
    }
    return sha256_hex(json.dumps(canonical, separators=(",", ":"), sort_keys=True).encode())


@dataclass(frozen=True)
class CurrentOutputIdentity:
    outpoint: str | None = None
    script_pubkey_hex: str | None = None
    address: str | None = None
    public_key_hex: str | None = None


def match_current_output(
    identity: CurrentOutputIdentity, match_index: dict[str, list[str]]
) -> dict[str, Any]:
    """Exact-match a candidate's current output against the frozen set."""
    probes: list[str] = []
    if identity.public_key_hex:
        probes.append(f"pubkey:{identity.public_key_hex.lower()}")
    if identity.script_pubkey_hex:
        probes.append(f"script:{identity.script_pubkey_hex.lower()}")
    if identity.address:
        probes.append(f"address:{identity.address}")
    matched: list[str] = []
    for probe in probes:
        matched.extend(match_index.get(probe, []))
    matched = sorted(set(matched))
    excluded = bool(matched)
    return {
        "policy_id": ATTRIBUTION_POLICY_ID,
        "excluded": excluded,
        "match_source_ids": [SOURCE_ID] if excluded else [],
        "sources_checked": [SOURCE_ID],
        "matched_fingerprints": matched,
        "claim": (
            "Exact match in the frozen public Satoshi-attribution set; "
            "this is a public heuristic, not proof of ownership."
            if excluded
            else ATTRIBUTION_PASS_CLAIM
        ),
    }


def write_derived_metadata(records: list[AttributionRecord], dest: Path) -> dict[str, Any]:
    """Write scrubbed metadata suitable for Git (no full CSV, no full key dump)."""
    digest = derived_set_hash(records)
    meta = {
        "policy_id": ATTRIBUTION_POLICY_ID,
        "source_id": SOURCE_ID,
        "csv_sha256": EXPECTED_CSV_SHA256,
        "record_count": len(records),
        "derived_set_sha256": digest,
        "match_key_count": len(build_match_index(records)),
        "required_answer_language": ATTRIBUTION_PASS_CLAIM,
        "note": "Full derived records remain outside Git under the private raw directory.",
    }
    dest.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta
