# Task btc-dev-001

Family: `rpc_config_externalized`
Split: `development`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Move Bitcoin RPC URL, username, and password out of source code into environment or config loading. Do not hardcode credentials. Keep behavior equivalent when configuration is present.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py, watch-wallet.py

## Success

Hidden evaluators will score your changes outside this workspace.
