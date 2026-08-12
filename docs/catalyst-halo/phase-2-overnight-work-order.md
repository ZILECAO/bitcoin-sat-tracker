# Phase 2 Overnight Work Order

## Authorization and Goal

The user authorized this bounded overnight run on 2026-08-12 to maximize useful
technical diligence while the agent is unattended.

The disposable Cursor Cloud VM contains only the public
`ZILECAO/bitcoin-sat-tracker` repository. The user accepts the remaining risk
of executing the exact vendor packages audited in Phase 1 and uploading only
the repository's synthetic/public benchmark content to the dedicated
Inference.net project.

The goal is to complete as much of this loop as possible without waiting for
the user:

```text
install -> observe runtime behavior -> capture traces -> inspect Catalyst
-> run HALO -> apply generic suggestions -> compare held-out results
-> create an eval/training dataset -> prepare or run a zero-cost fine-tune
```

This is an internal demonstration. Do not call it a statistically reliable
benchmark unless the full repetition and held-out requirements are met.

## Credentials and Budget

The environment may contain one dedicated disposable Inference.net project key
under both names below. The two variables intentionally contain the same key:

```text
INFERENCE_API_KEY
CATALYST_OTLP_TOKEN
```

Use these fixed non-secret settings:

```text
CATALYST_OTLP_ENDPOINT=https://telemetry.inference.net
CATALYST_SERVICE_NAME=bitcoin-sat-tracker-diligence
INFERENCE_BASE_URL=https://api.inference.net/v1
```

Rules:

- Never print, echo, log, serialize, commit, or include the key in a command
  argument. Check presence only, never its value.
- Do not enumerate the full environment. If any other credential-like variable
  or mounted private repository appears, stop before executing vendor code.
- Do not request or use an OpenAI, Anthropic, GitHub, AWS, Bitcoin-wallet, or
  other provider credential.
- Total metered model/API usage for the entire overnight run is capped at
  **USD $5**. Track estimated and reported cost. Stop new calls at the cap.
- Do not start a paid or unknown-cost training job. A hosted fine-tune may start
  only if the platform explicitly shows a total price of **USD $0** before the
  final submission. Do not deploy the resulting model or rent a GPU.

## Allowed Software and Network

Only the exact Phase 1 versions are approved:

- `@inference/cli@0.0.180`
- `@inference/tracing@0.1.9`
- `inference-catalyst-tracing==0.1.8` / `catalyst-tracing==0.1.8`
- `halo-engine==0.3.4`
- the OpenTelemetry versions recorded in `supply-chain-hashes.md`

Download archives first, verify their SHA-256 values against
[`supply-chain-hashes.md`](supply-chain-hashes.md), and stop on any mismatch.
Do not silently replace a version or use `latest`.

Allowed network destinations are package registries and public source hosts
needed for those exact downloads, plus `inference.net` and its subdomains.
Do not contact a downstream model provider. Prefer an Inference-hosted,
low-cost, OpenAI-compatible model available under the project key.

HALO Desktop is low priority in a headless VM. Do not spend the overnight run
debugging a graphical application; record it as unavailable after a short,
bounded attempt and continue with the CLI, tracing SDK, Gateway, and HALO
Engine.

## Isolation

Before vendor execution:

1. Confirm the current branch is `diligence/catalyst-halo` and the only Git
   repository is this public repository.
2. Confirm baseline files still match commit
   `d674a065819a0bd45357f8530b4f15775bfdaac9`.
3. Use a fresh mode-`0700` raw directory outside Git.
4. Run vendor tools from a separate checkout/archive containing only approved
   public files. Do not expose hidden scorers or held-out answers to a model.
5. Use a fresh home directory and a scrubbed environment for vendor child
   processes. Pass only the minimum variables required for the current step.
6. Keep Git credentials, agent configuration, shell history, SSH files, cloud
   metadata, Docker sockets, and the primary repository `.git` directory out
   of vendor-visible workspaces as far as the VM permits.
7. Record files created, child processes, exit status, duration, and observed
   network destinations without recording secret values.

## Execution Order

Continue automatically through these stages. A failure in one optional product
path should be recorded and skipped; it should not end the whole run unless a
stop condition applies.

### 1. Revalidate the Harness

- Run the 16 offline unit tests and the offline prepare/run/verify/report path.
- Resolve the specification mismatch before any model run: the full HALO
  protocol asks for at least eight held-out tasks, while Phase 1 created six.
  Add and freeze at least two new distinct held-out task families with hidden
  scorers, or explicitly downgrade the overnight result to the reduced demo.
  Never invent extra repetitions or claim full efficacy if this is not done.
- Freeze and record hashes for prompts, fixtures, task manifests, and scorers
  before the first model sees a task.

### 2. Dynamic Package Audit

- Install the verified, pinned packages without changing the user's global
  environment.
- First execute harmless version/help/import/setup paths without the API key.
- Record filesystem changes, child processes, and attempted destinations.
- Then repeat only the required initialization paths with the dedicated key.
- If `inf auth login` needs a human browser or separate account session, record
  that limitation and continue through direct SDK/API-key paths.
- `inf instrument` is authorized only on a disposable copy. Save its complete
  before/after diff and do not blindly apply it to the benchmark harness.

### 3. Trace Fidelity

- Produce a manual trace with nested agent, model, and tool spans using fake
  canaries and deterministic Bitcoin tools.
- Exercise the pinned tracing SDK and direct OpenTelemetry export separately
  where practical.
- Upload synthetic traces to Catalyst using `CATALYST_OTLP_TOKEN`.
- Verify what appears in Catalyst: prompts, outputs, tool names, arguments,
  results, timing, token counts, errors, task IDs, and parent/child structure.
- Record every field that was sent and whether any field arrived unexpectedly.
- Never upload raw environment data, hidden scorers, held-out answers, Git
  credentials, or files outside the approved public task workspace.

### 4. Gateway and Dataset

- Run the minimal synthetic Bitcoin agent through the Catalyst Gateway using
  the dedicated project key and an Inference-hosted low-cost model.
- Use stable task IDs and at least the development split. Run repeats only
  while under the total cost cap.
- Compare direct versus Gateway request meaning, output, errors, latency,
  streaming behavior, and reported cost.
- Create a dataset/eval from captured development traffic if the API or CLI
  permits non-interactive project-key access.
- Keep held-out tasks out of training data and HALO input.

### 5. HALO Improvement Loop

- Give HALO only development traces.
- Save its complete report outside Git and a scrubbed report in Git.
- Classify each suggestion using the categories in `experiment-spec.md`.
- Apply only generic agent-harness improvements that do not encode task
  answers. Save a suggestion-to-change map and freeze the improved harness.
- Run the baseline and improved harness against the held-out tasks in a fair,
  randomized order. Use three repeats when time and the cost cap allow;
  otherwise label it a reduced demonstration.
- Report failures and regressions as clearly as successes.

### 6. Training Path

- Build and validate non-overlapping synthetic train, validation, and held-out
  splits with recorded hashes.
- Select a small model that is available through Inference.net and record its
  exact identifier/revision.
- Run the unchanged base model evaluation before any training.
- Prepare the Catalyst training request and record recipe, seed, dataset ID,
  expected artifacts, and displayed price.
- Submit only when the platform explicitly confirms a total price of USD $0.
  If the price is nonzero or unavailable, stop at a ready-to-submit request.
- If zero-cost training completes, evaluate the trained model on the untouched
  held-out split. Do not deploy it to a paid endpoint.

The `gpt56-reference` arm may remain unavailable overnight. Do not copy the
user's local Codex login or route Codex/ChatGPT authentication through the
Catalyst Gateway. Record the missing reference cleanly for a later run in the
user's isolated Codex harness.

## Stop Conditions

Stop hosted/vendor execution immediately if:

- Another repository, private file, real wallet, unrelated secret, or personal
  agent configuration becomes visible.
- A package hash differs from Phase 1.
- A credential value is printed or committed.
- A request would send material outside the approved public/synthetic dataset.
- A process contacts an unexplained non-approved destination.
- Total metered usage reaches USD $5.
- Training or deployment has a nonzero or unknown price.
- A required substitution changes the model, package, task, or benchmark arm.

Preserve evidence already collected, scrub it, report the stop reason, and
continue only with purely offline work that remains useful.

## Overnight Deliverables

Before finishing:

1. Verify no secret, raw trace, vendor archive, model artifact, or private path
   is staged.
2. Commit only source, lock data, hashes, scrubbed results, diffs, and reports.
3. Push the branch `diligence/catalyst-halo`.
4. Write `docs/catalyst-halo/phase-2-report.md` with:
   - completed and blocked stages;
   - exact packages, models, endpoints, and costs;
   - observed runtime behavior and exported fields;
   - trace screenshots or stable dashboard identifiers without secrets;
   - Gateway, HALO, eval, and training results;
   - privacy-canary results;
   - all failures, unknowns, and claims that remain unproven;
   - exact reproduction commands;
   - instructions for revoking the disposable key and deleting hosted data.
5. End with a short morning handoff stating what the user can demo during the
   founder call and the three most important questions raised by observed
   evidence.

