# Catalyst and HALO Public-Sandbox Diligence

This branch is a public, synthetic-only sandbox for evaluating Inference.net
Catalyst and HALO without exposing private source, prompts, files, credentials,
or production traffic.

## Current State

- Phase 0 environment isolation: complete.
- Phase 1 offline harness and static supply-chain audit: authorized.
- Phase 2 local HALO and synthetic Catalyst testing: not authorized.
- Phase 3 fine-tuning: not authorized.
- External GPU rental: not authorized.

No real API key belongs in this branch or in a Phase 1 environment.

## Start Here

1. Read the root [`AGENTS.md`](../../AGENTS.md).
2. Execute [`phase-1-work-order.md`](phase-1-work-order.md).
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
3. **Gateway and training value:** can captured synthetic LLM calls produce a
   useful dataset and a small tuned model that beats the unchanged base model?

The first two claims will eventually use fresh, isolated Codex subprocesses.
The Gateway/training claim will use a separate minimal OpenAI-compatible agent.
Codex's internal authentication and model traffic must not be redirected
through Catalyst Gateway.

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
