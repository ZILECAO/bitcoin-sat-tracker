# Phase 1 Work Order: Offline Harness and Supply-Chain Audit

Phase 0 has been accepted. This work order authorizes Phase 1 only.

## Branch and Baseline

Work on:

```text
diligence/catalyst-halo
```

The immutable benchmark baseline is:

```text
d674a065819a0bd45357f8530b4f15775bfdaac9
```

Before modifying files, verify the repository, branch, and baseline ancestry.
Do not rewrite or materially improve `track-forwards.py` or `watch-wallet.py`.

## Required Package Interface

Add a standard-library-first Python package under `diligence/` exposing:

```text
python -m diligence prepare
python -m diligence run --arm <arm> --split <dev|holdout> --repeats <n>
python -m diligence verify --run-dir <path>
python -m diligence report --run-dir <path>
```

Do not add a third-party dependency merely for convenience.

### `prepare`

`prepare` must:

1. Verify the exact repository and immutable baseline.
2. Refuse to operate on an unexpected repository or commit.
3. Create fresh, isolated future task checkouts from the baseline commit.
4. Ensure task checkouts exclude the diligence package, root `AGENTS.md`, task
   definitions, evaluators, held-out tests, scorers, and answers.
5. Materialize deterministic fake Bitcoin RPC and mempool fixtures for the
   evaluator, outside the task checkout where appropriate.
6. Create a mode-`0700` raw-results directory outside Git.
7. Refuse to copy `.env` files or credential material into a task checkout.
8. Produce a manifest containing baseline, evaluator, task, fixture, package,
   and future model-version fields.
9. Set up a network-disabled execution contract for future model-backed task
   workspaces.

### `run`

`run` must implement validation and orchestration interfaces for:

```text
codex-native-otel
codex-openinference
codex-baseline
codex-halo
gateway-base
small-base
small-tuned
gpt56-reference
offline-fixture
```

In Phase 1, every model-backed arm must fail closed with a clear “Phase 2 not
configured” result. Do not call a model as a fallback.

The `offline-fixture` arm must exercise task selection, isolated checkout
creation, deterministic scoring, budgets, result recording, verification, and
reporting without a model call.

Enforce per-task timeout, maximum token, and maximum cost fields even though
the offline fixture arm does not incur token or monetary cost.

### `verify`

`verify` must:

1. Validate the run-record schema and required files.
2. Check the exact baseline commit.
3. Confirm the task's network policy is disabled.
4. Confirm every expected task and scorer result exists.
5. Validate the fake privacy-canary matrix.
6. Reject raw prompts, trace bodies, provider responses, model output, `.env`
   files, unexpected absolute paths, or secret-like material proposed for
   commit.
7. Compare a future real secret only in memory and output only pass/fail.
8. Refuse to validate a run when a privacy or isolation check fails.

### `report`

`report` must:

1. Consume verified scrubbed run records only.
2. Aggregate task success, duration, token use, cost, retries, tool errors,
   trace completeness, and privacy checks.
3. Keep raw prompts, output, tool results, trace bodies, and provider responses
   out of the report.
4. Clearly distinguish observed metrics from unavailable metrics.
5. Never invent a zero for a metric that was not collected.

## Task and Scorer Design

Define separate development and held-out manifests. Create at least eight
meaningful task families across the two splits.

Candidate families:

1. Move Bitcoin RPC configuration out of source.
2. Validate missing configuration without logging secret values.
3. Add request timeouts and HTTP status validation.
4. Add structured Bitcoin RPC and mempool error handling.
5. Make RPC and mempool dependencies injectable.
6. Add deterministic block-reward tests.
7. Validate satpoint and output-boundary inputs.
8. Remove process-wide `sys.exit` from library functions.
9. Add a safe command-line layer.
10. Bound and test wallet-monitor polling.
11. Correct fee-flow and coinbase edge cases.
12. Correct transaction-output edge cases with generated fixtures.

Do not solve these tasks in the baseline scripts. Build prompts, fixtures,
hidden tests, and deterministic scorers for future agents.

Development and held-out manifests must be frozen before the first HALO
analysis. HALO will eventually see development traces only. It must not see
held-out outcomes before the improved harness is frozen.

Task workspaces must have network access disabled so a later agent cannot fetch
this branch or its held-out material.

## Tests

Add offline unit and integration tests covering at least:

- Repository and baseline refusal behavior.
- Task-workspace content isolation.
- Held-out-answer isolation.
- Raw-results path and permission enforcement.
- No-network contract enforcement.
- Model-backed arm fail-closed behavior.
- Offline-fixture end-to-end execution.
- Run-record validation.
- Missing versus zero metric behavior.
- Privacy-canary detection.
- Secret-pattern and prohibited-artifact rejection.
- Deterministic report generation.

Tests must pass without Bitcoin Core or live internet access.

## Supply-Chain Audit

Follow [`supply-chain-protocol.md`](supply-chain-protocol.md) for:

1. `@inference/cli`
2. `@inference/tracing`
3. `inference-catalyst-tracing`
4. HALO Engine
5. HALO Desktop
6. Required OpenTelemetry exporters
7. OpenAI Codex CLI version `0.146.1`

Do not execute any of them.

## Documentation and Reproduction

Document:

- The immutable baseline and why it remains unchanged.
- Development versus held-out tasks.
- How task workspaces cannot see the evaluator or answers.
- Every evaluator command.
- Raw versus committed data.
- Privacy-canary behavior.
- Supply-chain methodology and limitations.
- Everything still blocked until Phase 2.
- Exact reproduction steps for another engineer.

## Verification Before Commit

1. Run all offline tests.
2. Run `python -m diligence prepare`.
3. Run the `offline-fixture` arm.
4. Run `python -m diligence verify` on its output.
5. Run `python -m diligence report` on the verified output.
6. Confirm all live network dependencies are mocked.
7. Confirm the original baseline scripts are unchanged from the baseline SHA.
8. Confirm isolated task checkouts do not contain the diligence materials.
9. Confirm isolated task checkouts cannot see held-out tests or answers.
10. Confirm raw output is outside Git and its directory mode is `0700`.
11. Confirm no `.env`, real secret, raw trace, provider payload, vendor archive,
    or extracted vendor source is staged.
12. Confirm no Phase 2 or Phase 3 operation occurred.
13. Review the complete Git diff.

Commit and push to `diligence/catalyst-halo`. Do not open a pull request unless
asked.

## Final Report

Report:

1. Branch and commit links.
2. Files and capabilities added.
3. Development and held-out task counts.
4. Exact tests and commands run.
5. Supply-chain findings by package.
6. Packages that should not be approved for Phase 2.
7. Known audit limitations.
8. Confirmation that the baseline scripts remain unchanged.
9. Confirmation that no real key was present.
10. Confirmation that no Inference, HALO, Codex, provider, Gateway, tracing,
    upload, evaluation, training, or deployment operation occurred.
11. Exact decisions required before Phase 2.

End with exactly:

> Waiting for explicit Phase 2 approval. The offline harness and supply-chain
> audit are ready. No Inference, HALO, Codex, provider, or hosted service has
> been executed.
