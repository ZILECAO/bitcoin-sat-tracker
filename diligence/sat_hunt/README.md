# Sat-Hunt Benchmark Assets

This directory contains public definitions and deterministic primitives for
the heavier Catalyst/HALO agent benchmark.

- `benchmark.json` fixes the meaning of earliest, circulating, active, and
  inscribed.
- `development.json` lists the ten capabilities HALO may observe during
  practice runs.
- `prompts/final-exam.md` is the held-out capstone prompt. It contains no
  answer.
- `ordinal.py` provides audited FIFO range primitives for fixture generation
  and independent scoring.
- `score.py` validates the final answer and compares it with a hidden oracle.

The Cloud Agent must generate the deterministic chain fixtures and hidden
oracle before model execution, freeze their hashes, and ensure task agents can
access the fixture API but not the oracle or scorer.
