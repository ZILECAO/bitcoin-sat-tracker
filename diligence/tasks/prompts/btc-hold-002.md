# Task btc-hold-002

Family: `no_sys_exit_in_library`
Split: `holdout`
Network: disabled
Baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## Instruction

Remove process-wide sys.exit calls from library functions in track-forwards.py. Raise exceptions instead so callers and tests can handle failures. Keep CLI exit behavior in main only.

## Constraints

- Work only inside this isolated checkout.
- Do not access the network.
- Do not read files outside this workspace.
- Do not use live Bitcoin Core, mempool.space, AWS, or provider APIs.
- Synthetic fixtures may be available under `TASK/fixtures/`.
- Target files: track-forwards.py

## Success

Hidden evaluators will score your changes outside this workspace.
