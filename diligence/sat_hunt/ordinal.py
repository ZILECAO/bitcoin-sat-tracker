"""Small, deterministic ordinal-theory primitives.

Ranges use the half-open form ``[start, end)``. Transaction inputs and outputs
are ordered exactly as they appear in the transaction. Sats flow first-in,
first-out. Any input ranges left after filling outputs are transaction fees and
must later be assigned through the block's coinbase transaction.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

SATOSHIS_PER_BTC = 100_000_000
INITIAL_SUBSIDY_SATS = 50 * SATOSHIS_PER_BTC
HALVING_INTERVAL = 210_000


class OrdinalRangeError(ValueError):
    """Raised when ordinal ranges or output values are malformed."""


def block_subsidy_sats(height: int) -> int:
    """Return the Bitcoin block subsidy at ``height`` in satoshis."""
    if not isinstance(height, int) or isinstance(height, bool) or height < 0:
        raise OrdinalRangeError("height must be a non-negative integer")
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:
        return 0
    return INITIAL_SUBSIDY_SATS >> halvings


def first_sat_of_block(height: int) -> int:
    """Return the ordinal number of the first subsidy sat mined at ``height``."""
    if not isinstance(height, int) or isinstance(height, bool) or height < 0:
        raise OrdinalRangeError("height must be a non-negative integer")

    remaining = height
    subsidy = INITIAL_SUBSIDY_SATS
    total = 0
    while remaining and subsidy:
        blocks = min(remaining, HALVING_INTERVAL)
        total += blocks * subsidy
        remaining -= blocks
        subsidy >>= 1
    return total


def _validate_range(item: Sequence[int]) -> tuple[int, int]:
    if not isinstance(item, (list, tuple)) or len(item) != 2:
        raise OrdinalRangeError("each ordinal range must contain [start, end]")
    start, end = item
    if any(not isinstance(value, int) or isinstance(value, bool) for value in item):
        raise OrdinalRangeError("ordinal range bounds must be integers")
    if start < 0 or end <= start:
        raise OrdinalRangeError("ordinal ranges must satisfy 0 <= start < end")
    return start, end


def range_size(ranges: Iterable[Sequence[int]]) -> int:
    """Return the number of sats represented by half-open ranges."""
    return sum(end - start for start, end in (_validate_range(item) for item in ranges))


def _take(ranges: list[tuple[int, int]], amount: int) -> tuple[list[list[int]], list[tuple[int, int]]]:
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise OrdinalRangeError("amount must be a non-negative integer")

    taken: list[list[int]] = []
    remaining = list(ranges)
    needed = amount
    while needed:
        if not remaining:
            raise OrdinalRangeError("outputs exceed available input satoshis")
        start, end = remaining.pop(0)
        available = end - start
        count = min(available, needed)
        taken.append([start, start + count])
        needed -= count
        if count < available:
            remaining.insert(0, (start + count, end))
    return taken, remaining


def assign_ordinal_ranges(
    input_ranges: Iterable[Sequence[int]], output_values_sats: Iterable[int]
) -> tuple[list[list[list[int]]], list[list[int]]]:
    """Assign ordered input sat ranges to ordered transaction outputs.

    Returns ``(output_ranges, fee_ranges)``. Adjacent source ranges remain
    separate so an evaluator can preserve provenance.
    """
    remaining = [_validate_range(item) for item in input_ranges]
    output_values = list(output_values_sats)
    for value in output_values:
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise OrdinalRangeError("output values must be non-negative integers")
    if sum(output_values) > range_size(remaining):
        raise OrdinalRangeError("sum of outputs exceeds sum of inputs")

    assigned: list[list[list[int]]] = []
    for value in output_values:
        ranges, remaining = _take(remaining, value)
        assigned.append(ranges)
    return assigned, [[start, end] for start, end in remaining]


def locate_sat(ranges: Iterable[Sequence[int]], sat_number: int) -> int | None:
    """Return the zero-based offset of ``sat_number`` in ordered ranges."""
    if not isinstance(sat_number, int) or isinstance(sat_number, bool) or sat_number < 0:
        raise OrdinalRangeError("sat_number must be a non-negative integer")
    offset = 0
    for item in ranges:
        start, end = _validate_range(item)
        if start <= sat_number < end:
            return offset + sat_number - start
        offset += end - start
    return None
