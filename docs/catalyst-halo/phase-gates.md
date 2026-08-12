# Experiment Phase Gates

## Phase 0 — Environment Isolation

Status: complete.

Accepted facts:

- Only this public repository is available.
- No named secrets are configured.
- The setup contains `requests` and a local Bitcoin Core regtest process with
  placeholder credentials.
- No other repository or private data was found.

## Phase 1 — Offline Harness and Static Audit

Status: complete.

Allowed:

- Modify this branch.
- Build and test the offline evaluator.
- Generate deterministic public/synthetic fixtures.
- Define development and held-out task suites and hidden scorers.
- Download vendor archives for safe static inspection.
- Use public documentation and registry metadata.
- Commit and push Phase 1 source, tests, docs, manifests, hashes, and scrubbed
  offline results.

Not allowed:

- Real credentials.
- Vendor-code execution.
- Model calls.
- Catalyst/HALO/Codex execution.
- Hosted upload, evaluation, training, or deployment.

## Phase 2 — Local HALO and Synthetic Hosted Testing

Status: initial plumbing run complete on 2026-08-12.

Requires a separate human review of:

- The Phase 1 branch and tests.
- Every supply-chain target recommendation.
- Proposed package versions and exact install commands.
- Proposed egress allowlist.
- Temporary credential scopes and spend caps.
- Data fields exported by each tracing path.
- Written authorization for hosted benchmarking if required by applicable
  service terms.

The authorization accepts execution of the pinned packages in the disposable
public-repository VM and hosted transfer of synthetic/public benchmark data.
Follow [`phase-2-overnight-work-order.md`](phase-2-overnight-work-order.md),
including its credential, cost, isolation, and reporting rules. This is not
approval to use private code, private prompts, production traffic, unrelated
credentials, or the user's local Codex state.

Evidence and handoff: [`phase-2-report.md`](phase-2-report.md).

## Phase 2B — Heavy Sat-Hunt Harness Optimization

Status: authorized on 2026-08-12.

Training-free work is allowed under
[`phase-2b-sat-hunt-work-order.md`](phase-2b-sat-hunt-work-order.md):

- Build a deterministic Bitcoin Core/ord fixture and hidden evaluator.
- Build an instrumented coding-agent harness with bounded Bitcoin, ord, file,
  shell, and test tools.
- Compare inexpensive Gateway models on development tasks.
- Let HALO inspect development traces and propose harness or repository-toolkit
  improvements.
- Compare baseline, harness-only, toolkit-only, and combined arms.
- Run the frozen held-out final exam only after the model and arms are frozen.
- Attempt a live mainnet result only with infrastructure capable of proving a
  global minimum; otherwise report the exact infrastructure gap.

Correctness is a gate. Cost and time comparisons are invalid for wrong or
unproven answers.

## Phase 3 — Fine-Tuning

Status: out of scope for current work.

Requires:

- Frozen, leak-free train/validation/evaluation splits.
- A successful synthetic Gateway/data-capture test.
- Approved cost and hardware budget.
- Exact base model, recipe, artifact ownership, export, and deletion terms.
- Separate causal and cross-harness comparison labels.

Do not call training create, submit, deploy, or pricing dry-run endpoints during
Phase 2B. Preserve the prior ready-to-submit artifact without acting on it.

## External GPU Experiment

Status: not authorized and not part of the initial Catalyst validation.

Any later external GPU test must use public weights, synthetic data, disposable
credentials, and no private source or traces. It must be reported as a separate
infrastructure/training experiment rather than evidence about Catalyst Train.

## Universal Stop Conditions

- Another repository or private data becomes visible.
- A credential other than the designated disposable Inference project key
  appears.
- A privacy check fails.
- A budget or timeout is reached.
- An unavailable model or package would require an unapproved substitution.
- A deletion or data-export control cannot be verified where required.
- Work would cross into the next phase without explicit approval.
