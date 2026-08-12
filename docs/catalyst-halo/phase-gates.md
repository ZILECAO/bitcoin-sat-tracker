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

Status: authorized.

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

Status: not authorized.

Requires a separate human review of:

- The Phase 1 branch and tests.
- Every supply-chain target recommendation.
- Proposed package versions and exact install commands.
- Proposed egress allowlist.
- Temporary credential scopes and spend caps.
- Data fields exported by each tracing path.
- Written authorization for hosted benchmarking if required by applicable
  service terms.

Phase 2 should begin locally with fake canaries and no hosted upload. Hosted
Catalyst calls require an additional data-transfer approval after local
verification.

## Phase 3 — Fine-Tuning

Status: not authorized.

Requires:

- Frozen, leak-free train/validation/evaluation splits.
- A successful synthetic Gateway/data-capture test.
- Approved cost and hardware budget.
- Exact base model, recipe, artifact ownership, export, and deletion terms.
- Separate causal and cross-harness comparison labels.

## External GPU Experiment

Status: not authorized and not part of the initial Catalyst validation.

Any later external GPU test must use public weights, synthetic data, disposable
credentials, and no private source or traces. It must be reported as a separate
infrastructure/training experiment rather than evidence about Catalyst Train.

## Universal Stop Conditions

- Another repository or private data becomes visible.
- A real credential appears.
- A privacy check fails.
- A budget or timeout is reached.
- An unavailable model or package would require an unapproved substitution.
- A deletion or data-export control cannot be verified where required.
- Work would cross into the next phase without explicit approval.
