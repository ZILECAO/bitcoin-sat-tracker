# Phase 2 Overnight Report

Internal demonstration run continued on 2026-08-12 against public
`ZILECAO/bitcoin-sat-tracker` on branch `diligence/catalyst-halo`.

This is **not** a statistically reliable benchmark. Hosted Gateway, Catalyst
ingest, HALO analysis, datasets/evals, and training preparation were completed
under the overnight work order after Inference.net egress became reachable.
Held-out HALO comparison is a reduced offline demonstration only.

## Completed and Blocked Stages

| Stage | Status | Notes |
| --- | --- | --- |
| 1. Revalidate harness | **Completed (prior)** | 16/16 offline tests still pass; 8 held-out families frozen |
| 2. Dynamic package audit | **Completed** | Phase 1 SHA-256s re-verified; isolated install OK |
| 3. Trace fidelity | **Completed** | Synthetic nested OTLP probe received by Catalyst; fields recorded |
| 4. Gateway and dataset | **Completed (partial eval)** | Serverless Gateway suite on 6 development tasks; datasets created; hosted eval runs failed |
| 5. HALO improvement loop | **Completed (reduced demo)** | HALO ran on development traces; generic timeouts/retries applied; held-out 0/8→0/8 |
| 6. Training path | **Prepared only** | Tiny Qwen 0.8B recipe dry-run ready; **not submitted** (no explicit $0 price) |

### Stop conditions checked

- No unexpected private repos/credentials beyond dedicated Inference key.
- Package hashes matched Phase 1.
- No secret values printed into committed docs.
- Metered spend remained far under the USD $5 cap.
- Training not submitted: dry-run shows no explicit total price of USD $0;
  selected recipe specifies `H100` × 8 GPUs.

## Exact Packages, Models, Endpoints, Costs

### Packages (re-verified)

All Phase 1 archives in `supply-chain-hashes.md` matched again
(`docs/catalyst-halo/results/phase2/package-hash-verify-rerun.json`).

### Models / endpoints

| Setting | Value |
| --- | --- |
| `CATALYST_OTLP_ENDPOINT` | `https://telemetry.inference.net` |
| `CATALYST_SERVICE_NAME` | `bitcoin-sat-tracker-diligence` |
| `INFERENCE_BASE_URL` | `https://api.inference.net/v1` |
| Primary Gateway / HALO model | `deepseek-v4-flash` (`openai:deepseek-v4-flash`) |
| Training candidate base | `qwen3.5-0.8b` via recipe `inf-public-training-recipe:qwen-3.5-0.8b-fft` |
| `gpt56-reference` | unavailable (authorized; no Codex login routing) |

### Costs

| Item | USD |
| --- | --- |
| Platform-reported inference `totalCost` (project, ~1d page) | **0.011893** |
| Training job | not started |
| Cap | 5.00 |
| Cap remaining (est.) | ~4.99 |

Source: `docs/catalyst-halo/results/phase2/cost-ledger.json` and
`inferences-scrubbed.json`.

## Trace Fidelity (Catalyst confirmation)

### Probe

- SDK: `catalyst-tracing==0.1.8`, `batching=simple`
- Service: `bitcoin-sat-tracker-diligence`
- **Trace ID:** `8af7ffa20f5d60e073b01d6c827014e4`
- Marker: `diligence-otlp-probe-eb05beec9bf3`
- Confirmed via:
  `inf --project b69a2722-d305-47e9-9931-b28b6dfcbd6d traces list --service bitcoin-sat-tracker-diligence --range 1d --json`
  and `inf ... traces get <trace-id> --all`

### Exact fields observed as captured

Present on the hosted trace/spans:

- `traceId`, `serviceName`, `serviceVersion`
- `agentName` / `agentId` = `synthetic-bitcoin-agent`
- `rootSpanName` = `synthetic.otlp.probe.root`
- `rootObservationKind` = `AGENT`
- Nested children: LLM `chat.completions.create`, TOOL canary tool name
- `parentSpanId` nesting (root ← LLM, root ← TOOL)
- `spanCount` = 3, `llmSpanCount` = 1, `totalTokens` = 40
- `startTime` / `endTime` / `durationNs`
- `inputPreview` / `outputPreview`
- `statusCode` OK; `hasError` false
- Token fields on spans (`inputTokens` / `outputTokens` / `totalTokens`)

Notable / unexpected:

- Hosted `source` field showed `file` for an SDK OTLP export.
- Summary `outputPreview` preferred nested TOOL output over root AGENT
  `output.value`.
- Span records include `apiKeyId` (identifier, not secret); scrubbed from
  committed summaries.

Details: `docs/catalyst-halo/results/phase2/otlp-probe-fidelity.json`.

Development JSONL (outside Git) sha256
`065ce5d63783593ee3f77f1d8316e0e1078d0cd394373a022e52c3d51d3fa0d0`
(18 spans, 6 development tasks, held-out excluded). Also uploaded via
`inf traces upload` (`traceImportId=7e9c2cc5-976b-40f9-9d60-c2b603bbbe40`,
18/18 lines processed).

## Gateway, Dataset, Eval

### Gateway (serverless Inference path)

Ran public/synthetic development tasks only through
`https://api.inference.net/v1/chat/completions` with project key and
`x-inference-task-id` / `x-inference-environment: diligence-phase2`.

| Task | HTTP | Latency s | Tokens in/out | OK |
| --- | --- | --- | --- | --- |
| btc-dev-001 | 200 | ~1.7 | 160/69 | yes |
| btc-dev-002 | 200 | ~1.9 | 158/75 | yes |
| btc-dev-003 | 200 | ~1.5 | 153/67 | yes |
| btc-dev-004 | 200 | ~2.1 | 159/93 | yes |
| btc-dev-005 | 200 | ~2.0 | 149/71 | yes |
| btc-dev-006 | 200 | ~2.7 | 164/144 | yes |

Streaming probe on `btc-dev-001`: HTTP 200, SSE (`data:`) observed,
TTFB ~0.51s.

Provider-proxy Gateway path (third-party provider key headers) was **not**
tested: work order forbids other provider credentials.

Cloudflare note: bare Python `urllib` to `api.inference.net` returns CF 1010;
browser-like `User-Agent` via curl works. Telemetry OTLP accepts Python
`requests` without that workaround.

### Datasets (held-out excluded)

| Dataset | ID | Type | Count |
| --- | --- | --- | --- |
| btc-diligence-dev-train | `5b27b3ac-eba8-47ec-bef9-13d491fe208b` | training | 4 |
| btc-diligence-dev-eval | `fcef9681-7c9c-4519-81c6-2dc0a1fa9458` | eval | 2 |
| btc-diligence-gateway-dev-eval | `608376bc-c436-4702-8400-106af94ed45e` | eval (traffic `btc-dev-001`) | 4 |

### Hosted evaluation

Rubric `btc-diligence-generic-harness`
(`84869062-18a3-479f-8300-6b05ea706f1b`) created.

Two eval run groups launched against the development eval dataset and failed
quickly (`failedCount=2`, error `2 of 2 results failed`) for both
`openai:deepseek-v4-flash` and `openai:gpt-4.1-nano`. Dataset creation and
rubric wiring succeeded; scoring path remains unproven. See
`docs/catalyst-halo/results/phase2/datasets-and-evals.json`.

## HALO Improvement Loop

### Input

Development-only JSONL traces (held-out excluded). Disposable baseline-only
repo checkout for `--repo-path` (no `diligence/`, docs, scorers, or answers).

### Run

```text
halo development-traces.jsonl \
  -m deepseek-v4-flash \
  --base-url https://api.inference.net/v1 \
  -H "User-Agent: Mozilla/5.0 ..." \
  --repo-path <disposable-baseline> \
  --max-depth 1 --max-turns 8 --max-output-tokens 800
```

API key passed via `OPENAI_API_KEY` env only (never argv). Exit 0, but
`final_answer` JSON truncated by max output tokens; suggestions recovered from
tool/analysis transcript.

### Suggestions (classified)

| ID | Category | Suggestion | Applied? |
| --- | --- | --- | --- |
| halo-s1 | actionable | Add HTTP `timeout=` on `requests` calls | yes |
| halo-s2 | actionable | Bounded retries + exponential backoff helper | yes |
| halo-s3 | generic but unproven | Improve child-span agent identity completeness | no |

No task-specific leakage suggestions applied.

### Held-out comparison (reduced demonstration)

Static offline scorers on immutable baseline vs same checkout after generic
HALO patch only; one repeat; randomized arm order per task.

| Arm | Held-out passes |
| --- | --- |
| baseline | **0 / 8** |
| improved (timeouts + retries) | **0 / 8** |
| Absolute improvement | **0 pp** |

Label: **workflow demonstration only — not efficacy evidence**. Generic
network-hardening patches do not satisfy held-out family scorers (satpoint
validation, CLI layer, etc.), which is the expected non-leaky outcome.

Artifacts:
`halo-suggestion-map.json`, `halo-holdout-compare.json`,
`halo-improved-harness.diff`.

## Training Path

Ready-to-submit configuration recorded; **job not started**.

- Recipe: `inf-public-training-recipe:qwen-3.5-0.8b-fft` (Tiny Qwen 3.5 0.8B)
- GPU plan in recipe: `H100`, 8 GPUs/node, 1 node
- Datasets/rubric wired as above (holdout excluded from train/eval datasets)
- `inf training create ... --dry-run` returns create payload **without** an
  explicit total price field
- Stop rule: submit only when platform shows **exactly USD $0** → **stopped**

Unchanged serverless smoke on development eval tasks (`btc-dev-005/006`) with
`deepseek-v4-flash` succeeded before any training attempt
(`base-model-pretrain-eval.json`). The trainable `qwen3.5-0.8b` weights are
catalogued for training but were not confirmed as a serverless chat route for
a like-for-like base-model held-out comparison.

No deployment and no GPU rental performed.

## Privacy Canaries

Fake canaries from `diligence/privacy/canaries.json` appeared in the Catalyst
trace previews as expected for the intentional synthetic probe. Scrubbed
committed Phase 2 JSON was re-checked for accidental secret material.
`inf auth status --json` was **not** run in visible logs (truncated key echo).

## Failures, Unknowns, Unproven Claims

- Hosted eval scoring: **failed** (dataset/rubric created; runs failed).
- Provider-proxy Gateway semantics: **untested** (no third-party key).
- HALO efficacy: **unproven** (0 pp held-out change; reduced offline demo).
- Training improvement: **unproven** (not submitted).
- Exact weight revision hash for `qwen3.5-0.8b`: **unknown** via CLI.
- HALO Desktop: **not pursued** (headless; low priority).
- Cloudflare bot scoring can block non-browser Python HTTP clients to
  `api.inference.net`.

Do not claim overnight efficacy, statistically significant improvement, or
successful hosted fine-tuning.

## Exact Reproduction Commands

```bash
git fetch origin diligence/catalyst-halo
git checkout diligence/catalyst-halo

# Offline harness still green
python3 -m unittest tests.test_diligence_offline -v

# Non-secret settings
export CATALYST_OTLP_ENDPOINT=https://telemetry.inference.net
export CATALYST_SERVICE_NAME=bitcoin-sat-tracker-diligence
export INFERENCE_BASE_URL=https://api.inference.net/v1
# INFERENCE_API_KEY / CATALYST_OTLP_TOKEN must already be present; never echo them

# Write CLI config from env (do not pass key on argv; do not run auth status --json)
python3 -c 'import json,os; from pathlib import Path; p=Path.home()/".inf"/"config.json"; p.parent.mkdir(mode=0o700, exist_ok=True); p.write_text(json.dumps({"apiKey": os.environ["INFERENCE_API_KEY"]})+"\n"); p.chmod(0o600)'

PROJECT=$(inf project auth-context --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["resolvedProject"]["id"])')

# Confirm prior probe
inf --project "$PROJECT" traces get 8af7ffa20f5d60e073b01d6c827014e4 --view summary

# Gateway call example (browser-like UA recommended)
# curl ... -H "Authorization: Bearer $INFERENCE_API_KEY" \
#   -H "x-inference-task-id: btc-dev-001" \
#   -H "x-inference-environment: diligence-phase2" \
#   -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"ping"}],"max_tokens":8}' \
#   https://api.inference.net/v1/chat/completions

# Training remains dry-run only unless UI/CLI shows total price == 0
inf --project "$PROJECT" training create --dry-run \
  --name btc-diligence-small-ft-dryrun \
  --recipe inf-public-training-recipe:qwen-3.5-0.8b-fft \
  --training-dataset 5b27b3ac-eba8-47ec-bef9-13d491fe208b \
  --eval-dataset fcef9681-7c9c-4519-81c6-2dc0a1fa9458 \
  --rubric 84869062-18a3-479f-8300-6b05ea706f1b
```

## Revoke Key and Delete Hosted Data

1. Rotate/revoke the disposable Inference project API key used as
   `INFERENCE_API_KEY` / `CATALYST_OTLP_TOKEN`.
2. Delete Catalyst traces, uploads, datasets, eval runs, and any training
   artifacts under project `My First Project`
   (`b69a2722-d305-47e9-9931-b28b6dfcbd6d`), especially service
   `bitcoin-sat-tracker-diligence` and datasets named `btc-diligence-*`.
3. Remove local vendor state: `rm -rf ~/diligence-raw-phase2`
   (contains `curl-headers.txt` and `vendor-home/.inf/config.json`).
4. Confirm Cloud Agent secrets are removed or rotated in Cursor environment
   settings.

## Morning Handoff / Founder-Call Demo

### What you can demo

1. **Live Catalyst trace** `8af7ffa20f5d60e073b01d6c827014e4` for service
   `bitcoin-sat-tracker-diligence` with AGENT→LLM/TOOL nesting, previews, and
   token counts.
2. **Gateway capture loop**: development task IDs on inferences, streaming SSE,
   plus created train/eval datasets from synthetic traffic (holdout excluded).
3. **Honest HALO + training posture**: HALO produced generic timeout/retry
   guidance; held-out offline compare stayed 0/8→0/8; tiny-model training is
   queued as a ready dry-run and intentionally **not** submitted without an
   explicit **$0** price.

### Three most important questions raised by evidence

1. Why do hosted eval runs fail immediately (`2 of 2 results failed`) on a
   just-created JSONL eval dataset and simple rubric even when Gateway chat
   completions succeed for the same models?
2. Should Catalyst document/require a browser-like User-Agent (or provide a
   first-party SDK path) so non-browser agents are not CF-1010 blocked on
   `api.inference.net` while OTLP ingest already works?
3. Can training `create` expose an explicit total price (including $0 offers)
   before submit, and can `qwen3.5-0.8b` be evaluated serverless pre/post train
   without renting the recipe’s H100×8 plan?
