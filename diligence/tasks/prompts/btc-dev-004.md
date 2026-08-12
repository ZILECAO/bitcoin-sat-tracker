# Task btc-dev-004

Family: `structured_errors`
Split: `development`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Add structured error handling for Bitcoin RPC and mempool HTTP failures. Avoid bare .json()["result"] chaining that crashes on transport or RPC errors.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
