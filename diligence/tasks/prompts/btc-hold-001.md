# Task btc-hold-001

Family: `satpoint_validation`
Split: `holdout`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Validate satpoint and transaction-output boundary inputs before tracking. Reject malformed satpoints and out-of-range values with clear errors instead of crashing later.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
