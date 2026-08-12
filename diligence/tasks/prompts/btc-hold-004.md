# Task btc-hold-004

Family: `bounded_wallet_polling`
Split: `holdout`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Bound and test wallet-monitor polling in watch-wallet.py. Make the poll interval configurable and ensure the monitor can stop without an infinite-only loop design. Add tests.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: watch-wallet.py

## Success

Hidden evaluators will score your changes outside this workspace.
