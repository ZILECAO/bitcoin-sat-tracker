# Experiment Specification

## Research Questions

### Trace Fidelity

Can the system faithfully represent a coding-agent run, including agent steps,
model calls, tool calls, parallel work, errors, timing, usage, and parent/child
relationships, without exporting prohibited content?

### HALO Efficacy

Does applying HALO suggestions derived from development traces improve a frozen
held-out task suite compared with the unchanged baseline harness?

### Gateway and Training Value

Can synthetic Gateway traffic produce a dataset and small tuned model that
outperforms the same unchanged base model on a task-level held-out split?

## Experimental Arms

| Arm | Purpose | Earliest phase |
| --- | --- | --- |
| `offline-fixture` | Validate evaluator, isolation, scoring, privacy, and reporting without a model | Phase 1 |
| `codex-native-otel` | Test direct Codex OTLP compatibility with prompt logging disabled | Phase 2 |
| `codex-openinference` | Test explicit allowlisted Codex JSONL-to-OpenInference adapter | Phase 2 |
| `codex-baseline` | Frozen Codex harness baseline | Phase 2 |
| `codex-halo` | Same harness plus accepted HALO-derived changes | Phase 2 |
| `gateway-base` | Synthetic minimal agent routed through Catalyst Gateway | Phase 2 |
| `small-base` | Unchanged small open-source model in neutral agent harness | Phase 3 |
| `small-tuned` | Same model family/checkpoint after Catalyst training | Phase 3 |
| `gpt56-reference` | GPT-5.6 Codex end-to-end quality reference | Phase 2/3 |

The causal fine-tuning comparison is `small-tuned` versus `small-base`.
`gpt56-reference` is a cross-harness reference and must not be described as the
unchanged base for a fine-tune.

## Task Manifest Schema

Every task contains at least:

```json
{
  "id": "btc-001",
  "prompt": "Public synthetic coding task",
  "baseline_commit": "d674a065819a0bd45357f8530b4f15775bfdaac9",
  "fixture_id": "offline fixture identifier",
  "scorer_id": "deterministic scorer identifier",
  "timeout_seconds": 900,
  "network": "disabled",
  "max_tokens": 50000,
  "max_cost_usd": 10
}
```

Validate schemas strictly. Reject unknown task IDs, duplicated IDs, invalid
splits, network policies other than `disabled`, non-positive timeouts, and
missing immutable baseline values.

## Run Record Schema

Every future run writes a private raw record outside Git and a scrubbed record
that may be committed after verification.

The scrubbed record contains at least:

```json
{
  "task_id": "btc-001",
  "arm": "codex-baseline",
  "split": "holdout",
  "repeat": 1,
  "model": "exact model identifier",
  "codex_version": "0.146.1",
  "adapter_version": "Git SHA",
  "started_at": "RFC 3339 timestamp",
  "duration_ms": 1234,
  "input_tokens": null,
  "output_tokens": null,
  "cost_usd": null,
  "exit_status": 0,
  "tests_passed": true,
  "trace_complete": null,
  "privacy_checks_passed": true,
  "trace_id": null,
  "suggestion_ids": []
}
```

Use `null` when a metric was not collected. A measured zero is valid only when
the evaluator has positive evidence that the value is zero.

## Workspace Isolation

For every future coding task:

1. Create a fresh checkout from the immutable baseline.
2. Copy only public task instructions and task-specific synthetic fixtures into
   the workspace.
3. Do not include this branch's `AGENTS.md`, `docs/`, evaluator, task manifests,
   hidden tests, scorers, expected outputs, or previous runs.
4. Disable network access before launching an agent.
5. Apply and score the produced patch outside the task workspace.
6. Destroy or archive the workspace according to an explicit retention policy
   after recording a verified scrubbed result.

The agent must not be able to fetch the held-out branch or query a scorer.

## HALO Paired Evaluation

1. Freeze model, Codex version, prompt, tools, task manifests, budgets, scorers,
   and adapter versions.
2. Run development tasks with the baseline harness.
3. Give HALO development traces only.
4. Classify every suggestion as actionable, generic but unproven,
   task-specific leakage, incorrect, or unverifiable.
5. Apply only generic harness changes that do not encode held-out solutions.
6. Record a suggestion-to-change mapping and freeze the improved harness.
7. Randomize baseline and improved arm order on held-out tasks.
8. Use at least eight held-out tasks and three repetitions per arm for the full
   evaluation.
9. Compare paired task success, duration, token use, cost, retries, tool errors,
   and trace completeness.
10. Report paired bootstrap confidence intervals and all negative results.

A reduced demonstration may use two development and two held-out tasks once
each, but it demonstrates workflow only and is not efficacy evidence.

An initial positive HALO signal requires either:

- At least a 10-percentage-point absolute held-out task-success improvement
  without meaningful cost regression; or
- At least a 20% cost or latency reduction without task-success regression.

Do not claim improvement when the paired confidence interval includes no
effect.

## Gateway Evaluation

Gateway testing uses a separate minimal agent with only synthetic Bitcoin
tasks and deterministic tools. It must:

- Use a disposable, spend-limited provider credential in a future phase.
- Assign stable task and trace IDs.
- Record request semantics before and after proxying.
- Measure end-to-end latency, time to first token when available, errors,
  retries, and streaming behavior.
- Never receive a real wallet, credential, private path, or private prompt.

Do not route Codex internal traffic or a Codex/ChatGPT OAuth credential through
Catalyst Gateway.

## Training Evaluation

Use task-level train, validation, and evaluation splits established before
training. Prove that no task, fixture, prompt, or expected answer overlaps.

Record:

- Dataset hashes and construction code.
- Base model and exact revision.
- Recipe, random seed, hardware, duration, and cost.
- Evaluation configuration and complete per-task results.
- Serving configuration and latency/cost measurements.
- Whether full weights, tokenizer, adapters, and metadata can be exported to
  customer-controlled storage and deleted from the training platform.

An initial positive training signal requires:

- At least a 10-percentage-point held-out improvement over the unchanged base.
- No split overlap or near-duplicate leakage.
- Reproducible dataset and model identifiers.
- Complete training and serving cost accounting.
- Demonstrated artifact export or an explicit platform-lock-in finding.

## Reporting Integrity

Every report must separate:

- Observed evidence.
- Vendor claims.
- Inferences.
- Unknown or unavailable metrics.
- Failed or negative experiments.

Do not summarize a demonstration as a benchmark or a cross-harness reference as
a causal comparison.
