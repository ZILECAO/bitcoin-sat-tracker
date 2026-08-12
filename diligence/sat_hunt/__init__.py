"""Deterministic building blocks for the Catalyst/HALO sat-hunt benchmark."""

from diligence.sat_hunt.ordinal import (
    assign_ordinal_ranges,
    block_subsidy_sats,
    first_sat_of_block,
    locate_sat,
    range_size,
)
from diligence.sat_hunt.score import (
    SatHuntValidationError,
    score_final_answer,
    validate_final_answer,
)

__all__ = [
    "SatHuntValidationError",
    "assign_ordinal_ranges",
    "block_subsidy_sats",
    "first_sat_of_block",
    "locate_sat",
    "range_size",
    "score_final_answer",
    "validate_final_answer",
]
