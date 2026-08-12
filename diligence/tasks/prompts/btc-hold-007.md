# Task btc-hold-007

Family: `mempool_url_config`
Split: `holdout`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Externalize the hardcoded mempool.space URL in track-forwards.py. Load the mempool API base URL from environment or config so tests and deployments can point at a synthetic endpoint. Do not leave https://mempool.space/ hardcoded.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
