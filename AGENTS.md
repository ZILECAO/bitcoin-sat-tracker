# Catalyst and HALO Diligence Instructions

These instructions apply to the entire repository on the
`diligence/catalyst-halo` branch.

## Current Authorization

Phase 0 and Phase 1 are complete. The user approved the bounded overnight
Phase 2 run described in
[the Phase 2 overnight work order](docs/catalyst-halo/phase-2-overnight-work-order.md)
on 2026-08-12. That work order is now the source of truth for what may run,
what may be uploaded, and when the agent must stop.

The Phase 1 sources of truth remain
[the Phase 1 work order](docs/catalyst-halo/phase-1-work-order.md) and
[the experiment specification](docs/catalyst-halo/experiment-spec.md). See
[the reproduction guide](docs/catalyst-halo/reproduction.md) and
[the supply-chain report](docs/catalyst-halo/supply-chain-report.md).

Do not exceed the Phase 2 overnight work order. In particular, do not:

- Access another repository, private data, personal files, or previous agent
  conversations.
- Print, commit, copy, or expose a credential.
- Use any credential other than the dedicated Inference project key provided
  as `INFERENCE_API_KEY` and `CATALYST_OTLP_TOKEN`.
- Send data other than this public repository's synthetic/public benchmark
  content to a hosted service.
- Exceed the overnight total cost cap, start a paid or unknown-cost training
  job, deploy a model, or rent a GPU.
- Publish benchmark conclusions outside the private diligence process.

The pinned vendor packages may now be executed only inside the disposable
cloud VM and under the isolation, recording, and stop rules in the Phase 2
overnight work order.

## Immutable Baseline

The benchmark baseline is:

```text
d674a065819a0bd45357f8530b4f15775bfdaac9
```

Do not fix or materially refactor `track-forwards.py` or `watch-wallet.py`
during Phase 1. Their existing problems are the future benchmark tasks. Build
the evaluator, fixtures, task definitions, hidden scorers, privacy checks, and
audit material around the unchanged baseline.

Every future coding-agent task must begin in a clean isolated checkout of that
commit. The task checkout must not contain `AGENTS.md`, `docs/catalyst-halo/`,
the evaluator, held-out tests, or answers.

## Data and Network Boundary

Use only public repository content, public Bitcoin identifiers already in the
repository, deterministic synthetic fixtures, and clearly fake privacy
canaries.

The configured local Bitcoin Core regtest process is allowed for understanding
behavior or generating synthetic fixtures. Committed tests and benchmark
scorers must pass with deterministic mocks and must not require Bitcoin Core,
a wallet, AWS, the Bitcoin network, or `mempool.space`.

Keep all future raw prompts, JSONL, full tool output, trace bodies, provider
responses, and model output outside Git in a mode-`0700` directory. Never
commit `.env` files or credentials.

## Completion Gate

Before committing Phase 1:

1. Run every offline test.
2. Exercise `prepare`, the deterministic offline fixture arm, `verify`, and
   `report` end to end.
3. Confirm the immutable baseline scripts are unchanged.
4. Confirm isolated task checkouts cannot see the diligence materials or
   held-out answers.
5. Confirm raw output is outside Git and mode `0700`.
6. Confirm no real secret or vendor archive is staged.
7. Confirm no Inference, HALO, Codex, provider, Gateway, hosted evaluation,
   training, or deployment operation occurred.
8. Commit and push the completed Phase 1 work to
   `diligence/catalyst-halo`.

End the Phase 1 report with exactly:

> Waiting for explicit Phase 2 approval. The offline harness and supply-chain
> audit are ready. No Inference, HALO, Codex, provider, or hosted service has
> been executed.
