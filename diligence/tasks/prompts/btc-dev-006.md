# Task btc-dev-006

Family: `block_reward_tests`
Split: `development`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Add deterministic unit tests for block_reward covering pre-halving, halving boundary, and post-halving heights. Use the synthetic fixtures under TASK/fixtures when helpful.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
