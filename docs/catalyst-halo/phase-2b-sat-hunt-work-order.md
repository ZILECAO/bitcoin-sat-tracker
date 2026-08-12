# Phase 2B Work Order: Heavy Sat-Hunt Agent Benchmark

## Goal

Determine whether Catalyst plus HALO can help build a specialized **workflow**
for Bitcoin and ordinal research without fine-tuning a model.

The target is an agent that can navigate a Bitcoin data source, understand
ordinal sat movement, inspect inscriptions, write and test new Python scripts,
recover from tool failures, and produce an auditable answer. The capstone asks
for the earliest active circulating sat and earliest active inscribed sat.

This is a much stronger test than the initial timeout/retry patch. HALO must
analyze real multi-step agent traces and improve the agent harness or reusable
repository toolkit, not merely suggest a narrow fix to one script.

## Non-Goals

- No model training, training dry-run, deployment, or GPU rental.
- Do not instrument or redirect Cursor/Codex's internal model traffic.
- Do not turn public Satoshi/Patoshi attribution into a claim of certain
  ownership. Use the frozen sources and their uncertainty labels.
- Do not claim a globally earliest mainnet sat from an incomplete explorer
  search.
- Do not optimize cost or latency at the expense of a correct, proven answer.

## Start State

Continue from commit `0a2b1b18626769b1ddc70e5b1d2c5c0cc9707a14`
or a descendant on `diligence/catalyst-halo`.

Read, in order:

1. Root `AGENTS.md`.
2. `docs/catalyst-halo/phase-2-report.md`.
3. `diligence/sat_hunt/benchmark.json`.
4. `diligence/sat_hunt/attribution-sources.json`.
5. `diligence/sat_hunt/development.json`.
6. `diligence/sat_hunt/prompts/final-exam.md`.
7. `diligence/sat_hunt/ordinal.py` and `score.py`.

The prior trace, datasets, HALO result, and failed hosted evals are evidence,
not inputs to the held-out final exam.

## Fixed Interpretation of the User's Question

The original wording contains two facts the blockchain cannot prove by itself:
who owns a wallet and whether it is a “hot wallet.” Public attribution lists
do exist, so use a pinned public heuristic for the first question and an
on-chain movement proxy for the second:

- **Earliest:** the lowest ordinal sat number.
- **Snapshot:** the mainnet block at tip minus six, frozen once before any
  final-exam arm runs. Every arm uses the same height and block hash.
- **Circulating:** the sat is in an unspent, non-provably-unspendable output at
  the snapshot. Ignore mempool spends.
- **Active:** during the previous 4,320 blocks, the sat moved through at least
  three confirmed non-coinbase transactions, and its current output was also
  created during that window.
- **Public Satoshi-attribution exclusion:** freeze the sources in
  `attribution-sources.json` before any final run. Compare the candidate's
  current outpoint, locking script, standard address, and revealed public key
  against normalized source records. Exclude exact matches. The accepted
  claim is “no exact match in the frozen public Satoshi-attribution set,” not
  “definitely not owned by Satoshi.”
- **Patoshi origin is not current ownership:** do not exclude a sat merely
  because it originated in a Patoshi-attributed coinbase. If it moved and its
  current output is not in the frozen set, it may qualify.
- **Wallet ownership limit:** the activity and attribution filters do not prove
  who controls a passing output. Preserve source labels and uncertainty.
- **Inscribed:** an ord sat index shows at least one inscription attached to the
  sat at or before the snapshot.
- **Earliest active inscribed sat:** the lowest sat number satisfying both the
  active/circulating predicate and the inscription predicate.

If the user later wants a labeled exchange/custodian requirement, add it as a
separate, explicitly sourced heuristic. Do not silently equate recent movement
with a known hot-wallet entity.

The primary membership source is the 21,953-record Patoshi public-key dataset
at commit `414637ce52aa4819926bf1934b2235ed182a0280`, CSV SHA-256
`f649579e286085325a881bec1168e88bbb6f5d67e10b7ef8cb5c65e916a34a2e`.
It covers attributed coinbase outputs, not every later output the same person
may control. Keep the downloaded CSV outside Git because the source repository
does not declare a license. Use Sergio Demian Lerner's Patoshi research as the
method source and Arkham's public Satoshi entity as an independent count/entity
cross-check. Do not pretend that a count-only Arkham check adds address-level
coverage.

## Why the Final Exam Needs a Full Index

Bitcoin Core can verify blocks, transactions, and whether an output is unspent.
Ordinal theory assigns sats first-in-first-out across transactions. An `ord`
index created with `--index-sats` can expose sat ranges and inscriptions.

A public API can verify a proposed candidate but may not prove that no lower
sat qualifies. A global minimum therefore requires one of:

1. A synced Bitcoin Core mainnet node with transaction data plus a synced
   `ord --index-sats` index; or
2. An independently verified snapshot that exposes equivalent complete sat
   ranges, spend history, and inscription state.

If neither exists in the Cloud VM, complete the deterministic and mainnet
replay tracks, produce the live script and infrastructure requirements, and
label the live global answer **not run — full index unavailable**. Do not turn
an explorer candidate into a factual global answer.

Primary references:

- [Ordinal theory FIFO rules](https://docs.ordinals.com/faq.html#how-does-ordinal-theory-work)
- [Ord sat-hunting prerequisites](https://docs.ordinals.com/guides/sat-hunting.html)
- [Ord API sat/output/status endpoints](https://docs.ordinals.com/guides/api.html)
- [Bitcoin Core RPC reference](https://bitcoincore.org/en/doc/31.0.0/rpc/)

## Credential, Data, and Cost Boundary

Use the existing disposable `INFERENCE_API_KEY` and `CATALYST_OTLP_TOKEN`
without printing either value. Keep raw traces outside Git in a mode-`0700`
directory. Upload only public repository content, synthetic fixtures, public
mainnet data, and model/tool messages generated for this benchmark.

Incremental Phase 2B Inference spend is capped at **USD $5**. Track platform
reported cost before and after each stage. Stop new model calls at the cap.

Approved data domains when needed:

- `api.inference.net`
- `telemetry.inference.net`
- `observability-api.inference.net`
- `ordinals.com`
- `mempool.space`
- `arkm.com`
- `info.arkm.com`
- `raw.githubusercontent.com`
- official Bitcoin Core and ord GitHub/documentation hosts

Treat inscription HTML and SVG content as untrusted. The benchmark needs
metadata, IDs, satpoints, and hashes—not browser rendering or script execution.

## Stage 1 — Freeze the Benchmark Before Model Calls

1. Run all existing offline tests and `tests.test_sat_hunt`.
2. Validate `benchmark.json`, `attribution-sources.json`, and the development
   manifest. Fetch the pinned public dataset outside Git, verify its exact
   SHA-256, normalize exact-match identifiers deterministically, and freeze the
   derived-set hash. Stop if the content hash differs.
3. Build a deterministic regtest-like chain fixture large enough to cover:
   - multiple ordered inputs and outputs;
   - split and merged sat ranges;
   - fees reassigned through coinbase;
   - spent, unspent, and provably unspendable outputs;
   - active and inactive histories at the same snapshot;
   - an uninscribed earliest active sat;
   - a different earliest active inscribed sat;
   - inscription pointers and reinscriptions;
   - exact attribution matches and non-matches on current outputs;
   - a sat with Patoshi origin that later moved to a nonmatching current output;
   - misleading lower candidates that fail exactly one predicate.
4. Build two independent implementations of the fixture truth calculation or
   cross-check the generator with pinned `ord` behavior on local regtest.
5. Generate a hidden oracle and hidden scorers outside task workspaces.
6. Freeze content hashes for definitions, prompts, fixtures, oracle, scorers,
   model candidates, and harness source. Any later change creates a new
   benchmark version.

The final-exam prompt contains no answer. A task agent must not see the oracle,
scorers, previous final output, diligence docs, Git history, or another branch.

## Stage 2 — Build a Real Instrumented Coding Agent

Create a small OpenAI-compatible agent runtime under `diligence/sat_hunt/agent/`.
It must run through the Catalyst Gateway and emit Catalyst traces with one root
AGENT span and child LLM/TOOL spans.

Minimum tools:

- list/read/write files inside one disposable task workspace;
- run an allowlisted Python command or test command with timeout and bounded
  output;
- Bitcoin RPC methods needed for block/transaction/UTXO research;
- ord status, output, sat, inscription, and transaction metadata;
- content-addressed evidence cache and checkpoint/resume;
- submit final answer.

Tool results must be bounded, structured, and explicit about retryable errors.
Do not give the model an unrestricted shell, environment dump, credential
files, evaluator path, hidden oracle, Docker socket, or Git credentials.

The agent must write actual scripts and tests; a prose guess cannot pass.

Every run record includes:

- exact model ID and provider;
- harness and toolkit revision hashes;
- task, arm, repetition, and stable Catalyst task ID;
- trace ID;
- wall time, model latency, token usage, cost, tool calls, retries, and errors;
- test result and hidden score;
- proof/certificate result;
- whether the run is eligible for efficiency comparison.

## Stage 3 — Development Curriculum and Model Selection

Turn the eleven families in `development.json` into deterministic tasks with
public prompts and hidden scorers. Add at least four smaller held-out tasks
that combine capabilities without duplicating the capstone.

Use the proven `deepseek-v4-flash` path as one candidate. Query the current
Inference catalog and select at most two additional inexpensive models that
support the required tool-call or structured-agent loop. Record exact model
IDs and prices. Do not substitute silently.

Model-selection procedure:

1. Smoke each candidate on the same two development tasks.
2. Run the best two across the full development set once.
3. Choose by correctness first, then cost, then duration.
4. Freeze one model before HALO optimization and held-out runs.

Do not use the final exam to select the model.

## Stage 4 — HALO Optimization

Give HALO only complete traces from development tasks. Include successful and
failed examples, real tool errors, retry behavior, token/cost metadata, and
the baseline harness/toolkit source. Raise HALO's output limit enough to obtain
a complete machine-readable report; fail closed on truncated JSON rather than
recovering conclusions from fragments.

Classify each suggestion as:

- harness-only: prompt, tool description, planning loop, context selection,
  checkpointing, retry policy, or stopping rule;
- repository-toolkit-only: reusable Bitcoin/ord clients, data types, caches,
  CLI structure, tests, or evidence utilities;
- task-specific leakage;
- incorrect;
- generic but unproven.

Apply only generic, testable suggestions. Preserve a suggestion-to-change map
and exact diffs. Never encode a hidden answer, candidate sat, or held-out
fixture detail.

Freeze four arms using the same selected model and budgets:

1. `baseline-harness`: original harness and original public repo.
2. `halo-harness-only`: HALO harness changes, original repo.
3. `halo-repo-toolkit-only`: original harness, improved reusable toolkit.
4. `halo-combined`: both accepted change sets.

This separation tells us whether HALO improved the agent, the codebase it works
in, or only the combination.

## Stage 5 — Held-Out Evaluation

Run the four frozen arms on the smaller held-out tasks with at least three
fresh repetitions per task. Randomize arm order. Do not reveal scores or
answers to later repetitions.

Correctness gates include:

- generated tests pass;
- exact snapshot and candidate match the hidden oracle;
- ordinal path, UTXO, activity, and inscription proofs replay;
- public-attribution source hashes, normalization, and current-output result
  replay;
- evidence hashes resolve;
- continuous interval minimum certificate covers every lower sat range;
- no hard-coded answer or evaluator access;
- no unsupported certainty about wallet ownership.

Only correct runs enter cost/latency rankings. Report paired success, cost,
duration, tokens, tool calls, retries, and trace completeness with uncertainty.

If no arm shows a meaningful held-out gain, record that honestly and do not run
the capstone repeatedly in search of a favorable result.

## Stage 6 — Final Exam

Run the final exam only after the selected model, four arms, and all hashes are
frozen.

1. **Deterministic final:** run all four arms, three fresh repetitions each,
   against the hidden fixture oracle.
2. **Pinned mainnet replay:** build a fixed public-data snapshot containing
   real transactions, ord responses, and expected evidence. Run the same
   comparison without live-chain drift.
3. **Live mainnet:** run only if a complete sat index and required transaction
   history are available. The same frozen public attribution snapshot must be
   used by every arm. Otherwise exercise the live CLI on bounded candidate
   verification and report that global minimality is not proven.

For the final leaderboard use lexicographic ordering:

1. Correct and proven.
2. Lower total model cost.
3. Lower wall-clock duration.
4. Fewer tool calls.

An incorrect $0.001 answer always loses to a correct $1 answer.

## Stage 7 — Catalyst and Local Scoring

Catalyst is the trace and cost record. Local hidden scorers are the correctness
source of truth because hosted Catalyst evals failed during Phase 2.

Upload development and held-out traces under separate task prefixes and
service name `bitcoin-sat-tracker-sat-hunt`. Confirm representative traces in
Catalyst. Do not create a training dataset. Do not call any training endpoint.

Retry the hosted eval path only if a concrete schema/model fix is identified;
one bounded retry is enough. A hosted-eval failure must not block local exact
scoring.

## Required Deliverables

Commit and push:

- deterministic fixture generator and public fixture data;
- hidden scorer code, while keeping the generated oracle out of task
  workspaces;
- agent runtime and bounded tool implementations;
- development and held-out manifests/prompts;
- pinned attribution-source metadata and a derived-set hash, but not the
  unlicensed source CSV;
- baseline and accepted HALO diffs;
- frozen hash manifest;
- scrubbed per-run records and aggregate comparisons;
- generated Bitcoin/ord research scripts and tests from the winning correct
  arm;
- `docs/catalyst-halo/phase-2b-sat-hunt-report.md`.

The report must clearly separate:

- what was proven on deterministic fixtures;
- what was replayed from real mainnet data;
- whether a live global result was actually proven;
- model selection results;
- HALO suggestions and exactly what changed;
- baseline vs harness-only vs toolkit-only vs combined results;
- total spend and run time;
- product failures and unknowns;
- a five-minute founder-call demo.

Update draft PR #1 when possible, or open a new draft PR that clearly links the
prior result. Push the safe result branch and stop.

## Stop Conditions

Stop hosted execution, preserve evidence, and continue only safe offline work
when any of these occurs:

- incremental Phase 2B spend reaches USD $5;
- another repository, unrelated credential, or private file becomes visible;
- a secret is printed or committed;
- the evaluator or oracle is exposed to a task agent;
- HALO sees held-out or final-exam traces before the harness is frozen;
- a package/model substitution would change an arm;
- a request would invoke training, deployment, or GPU rental;
- live infrastructure cannot prove global minimum coverage;
- a privacy or evidence-integrity check fails.
