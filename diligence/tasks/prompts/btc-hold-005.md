# Task btc-hold-005

Family: `fee_flow_edge_cases`
Split: `holdout`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Add tests covering fee-flow and coinbase edge cases for sat tracking when an output is spent as a fee. Use synthetic fixtures; do not call live Bitcoin APIs.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
