# Task btc-dev-002

Family: `missing_config_safe`
Split: `development`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Validate that required Bitcoin RPC configuration is present before making requests. If configuration is missing, fail with a clear error that does not log or print secret values.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py, watch-wallet.py

## Success

Hidden evaluators will score your changes outside this workspace.
