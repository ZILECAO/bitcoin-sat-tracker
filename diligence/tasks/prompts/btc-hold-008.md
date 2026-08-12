# Task btc-hold-008

Family: `sats_btc_conversion`
Split: `holdout`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Add pure helper functions sats_to_btc and btc_to_sats in track-forwards.py using the standard 1e8 sats-per-BTC scale. Include deterministic unit tests. Do not call live Bitcoin APIs.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
