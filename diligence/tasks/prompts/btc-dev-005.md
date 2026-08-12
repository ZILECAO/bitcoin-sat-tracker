# Task btc-dev-005

Family: `injectable_dependencies`
Split: `development`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Make Bitcoin RPC and mempool HTTP dependencies injectable so tests can supply deterministic fakes without live network access.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
