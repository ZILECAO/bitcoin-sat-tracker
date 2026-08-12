# Task btc-dev-003

Family: `timeouts_and_status`
Split: `development`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Add request timeouts to all HTTP calls in track-forwards.py and watch-wallet.py. Validate HTTP status codes before parsing JSON.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py, watch-wallet.py

## Success

Hidden evaluators will score your changes outside this workspace.
