# Catalyst and HALO Public-Sandbox Diligence

This branch is a public-data-only sandbox for evaluating Inference.net Catalyst
and HALO without exposing private source, prompts, files, credentials, or
production traffic. It uses deterministic fixtures first and may replay public
Bitcoin mainnet data under the active work order.

## Current State

- Phase 0 environment isolation: complete.
- Phase 1 offline harness and static supply-chain audit: complete.
- Phase 2 Catalyst/Gateway/HALO plumbing test: complete. Catalyst traces,
  Gateway calls, and datasets worked; hosted eval failed; HALO showed no
  held-out improvement. See [`phase-2-report.md`](phase-2-report.md).
- Phase 2B heavier sat-hunt benchmark: authorized and specified in
  [`phase-2b-sat-hunt-work-order.md`](phase-2b-sat-hunt-work-order.md).
- Phase 3 fine-tuning: explicitly out of scope for the current work.
- External GPU rental: not authorized.

No real API key belongs in this branch. Disposable overnight keys must stay in
the Cloud Agent secret store / local raw dirs, never in Git.

Phase 1 deliverables:

- Offline evaluator: `python -m diligence {prepare,run,verify,report}`
- Reproduction guide: [`reproduction.md`](reproduction.md)
- Supply-chain report: [`supply-chain-report.md`](supply-chain-report.md)
- Scrubbed offline results: [`results/`](results/)

## Start Here

1. Read the root [`AGENTS.md`](../../AGENTS.md).
2. For active work, execute
   [`phase-2b-sat-hunt-work-order.md`](phase-2b-sat-hunt-work-order.md).
3. Implement the interfaces and controls in
   [`experiment-spec.md`](experiment-spec.md).
4. Follow [`security-boundary.md`](security-boundary.md) for every file,
   process, credential, and network decision.
5. Follow [`supply-chain-protocol.md`](supply-chain-protocol.md) before
   downloading any vendor archive.
6. Use [`phase-gates.md`](phase-gates.md) to determine when to stop.

## What This Experiment Separates

The diligence tests three independent claims:

1. **Trace fidelity:** can Catalyst/HALO represent a Codex coding-agent run as
   a useful agent/model/tool trace tree?
2. **HALO efficacy:** does a HALO-recommended harness change improve a frozen
   held-out coding evaluation?
3. **Workflow specialization:** can model selection plus HALO-guided harness
   and repository-toolkit changes make an agent correct, faster, and cheaper
   on a demanding Bitcoin/ordinal research task without training?

The active test uses a separate, minimal OpenAI-compatible coding agent through
Catalyst Gateway. Codex's internal authentication and model traffic must not
be redirected through Catalyst Gateway.

## Core Experimental Rule

Do not improve the two original Python scripts while building the benchmark.
If the baseline is fixed before measurement, the later baseline-versus-HALO
comparison becomes meaningless.

The immutable baseline is:

```text
d674a065819a0bd45357f8530b4f15775bfdaac9
```

## Expected Phase 1 Deliverables

- An offline evaluator exposed through `python -m diligence`.
- Deterministic Bitcoin RPC and mempool fixtures.
- Development and held-out task manifests.
- Hidden scorers unavailable inside future task workspaces.
- A privacy-canary matrix and commit-safety verifier.
- A schema for private raw results and scrubbed committed results.
- Offline unit and end-to-end tests.
- A static supply-chain report covering the proposed vendor packages.
- Reproduction instructions for another engineer.

Phase 1 must finish without running a model, HALO, Catalyst, `inf`, or Codex.
