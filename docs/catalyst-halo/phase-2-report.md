# Phase 2 Overnight Report

Internal demonstration run on 2026-08-12 against public
`ZILECAO/bitcoin-sat-tracker` on branch `diligence/catalyst-halo`.

This is **not** a statistically reliable benchmark. Hosted Gateway, Catalyst
ingest verification, HALO model analysis, and zero-cost training were blocked
by VM egress policy before any metered Inference.net usage accrued.

## Completed and Blocked Stages

| Stage | Status | Notes |
| --- | --- | --- |
| 1. Revalidate harness | **Completed** | 16/16 offline tests; prepare/run/verify/report; held-out expanded to 8; freeze hashes written |
| 2. Dynamic package audit | **Completed (local)** / **Blocked (hosted)** | All Phase 1 package SHA-256s matched; isolated install + no-key help/import OK; hosted CLI calls reset by egress |
| 3. Trace fidelity | **Partial** | Local nested AGENT/LLM/TOOL spans generated; SDK setup/shutdown OK; Catalyst arrival **not verified** (egress) |
| 4. Gateway and dataset | **Blocked** | No Inference API reachability; no Gateway traffic; no hosted dataset create |
| 5. HALO improvement loop | **Blocked** | Local development JSONL ready; `halo` could not reach model API / jsDelivr Pyodide |
| 6. Training path | **Prepared only** | Non-overlapping synthetic splits hashed; price unknown; **not submitted** |

### Stop condition hit

Hosted/vendor network calls to `*.inference.net` (and HALO’s
`cdn.jsdelivr.net` dependency) fail with TLS `Connection reset by peer` under
the environment’s restricted egress allowlist. Package registries remain
reachable. Estimated metered spend: **USD $0.00**.

Requested allowlist additions (pending user approval):

- `api.inference.net`
- `telemetry.inference.net`
- `observability-api.inference.net`
- `cdn.jsdelivr.net`
- `deno.land`

## Exact Packages, Models, Endpoints, Costs

### Packages (verified against `supply-chain-hashes.md`)

| Artifact | Version | SHA-256 match |
| --- | --- | --- |
| `@inference/cli` | 0.0.180 | yes |
| `@inference/cli-linux-x64` | 0.0.180 | yes |
| `@inference/tracing` | 0.1.9 | yes |
| `inference-catalyst-tracing` | 0.1.8 | yes |
| `catalyst-tracing` | 0.1.8 | yes |
| `halo-engine` | 0.3.4 | yes |
| `@opentelemetry/api` | 1.9.0 | yes |
| `@opentelemetry/exporter-trace-otlp-http` | 0.206.0 | yes |
| `@opentelemetry/exporter-trace-otlp-proto` | 0.206.0 | yes |
| `@opentelemetry/sdk-trace-node` | 2.2.0 | yes |

HALO Desktop linux setup was **not** downloaded (headless / low priority).

### Models / endpoints

| Setting | Value |
| --- | --- |
| `CATALYST_OTLP_ENDPOINT` | `https://telemetry.inference.net` |
| `CATALYST_SERVICE_NAME` | `bitcoin-sat-tracker-diligence` |
| `INFERENCE_BASE_URL` | `https://api.inference.net/v1` |
| Selected Inference model | **unavailable** (models list failed) |
| HALO attempted model id | `meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo` (not confirmed available) |
| `gpt56-reference` | unavailable (as authorized; no Codex login routing) |

### Costs

| Item | USD |
| --- | --- |
| Metered model/API usage observed | 0.00 |
| Training job | not started |
| Cap remaining | 5.00 |

## Observed Runtime Behavior

### Isolation

- Branch confirmed: `diligence/catalyst-halo`.
- Only Git repo: `/workspace` (public bitcoin-sat-tracker).
- Baseline scripts match `d674a065819a0bd45357f8530b4f15775bfdaac9`.
- Vendor work used mode-`0700` raw root `~/diligence-raw-phase2`, fresh vendor
  home, and a baseline-only disposable checkout (no `diligence/`, `docs/`,
  scorers, or held-out answers).
- Credentials passed only via environment / config file write from env; never
  as CLI argv for the real key.

### Package / CLI behavior

- `inf --version` → `0.0.180`.
- `inf auth login` requires browser device authorization → recorded; continued
  with API-key path.
- Writing `~/.inf/config.json` `{"apiKey": ...}` from env enables
  `inf auth status` (`method: API Key`,
  `apiUrl: https://observability-api.inference.net`).
- **Privacy finding:** `inf auth status --json` prints a truncated `apiKey`
  value. Outputs were scrubbed; do not commit raw status dumps.
- `inf models list` and `inf whoami` fail with unexpected socket close
  (egress).
- `inf instrument --print-prompt` prompts for session login / hangs without
  browser session. Disposable workspace diff empty — nothing applied to the
  harness.
- Python: `catalyst_tracing` / `inference_catalyst_tracing` import OK
  (`0.1.8`). `halo` CLI help OK; default model string in help is
  `gpt-5.4-mini`.

### Trace export fields (intended / local)

Local synthetic spans include nested parent/child structure with:

- prompts / outputs (fake canaries)
- tool name / args / results (deterministic Bitcoin tools + canaries)
- timing (`start_time` / `end_time`)
- token counts
- task IDs (`inference.task_id` / metadata)
- status / errors

SDK `setup()` + `shutdown()` succeeded for both Python `catalyst-tracing` and
JS `@inference/tracing`, but **Catalyst dashboard arrival was not verified**.
No screenshots or hosted trace IDs are available.

Development JSONL (outside Git): sha256
`50c9fe6b07381104c2b6b6776149747a6a9a82415320f899e2dfa0bb905009ea`
(18 spans, 6 development tasks, held-out excluded).

## Gateway, HALO, Eval, Training

### Gateway

Not run. Requires Inference-hosted OpenAI-compatible model via allowed egress.

### HALO

- Input prepared: development-only JSONL (held-out excluded).
- Engine start attempted; stderr shows Pyodide download to `cdn.jsdelivr.net`
  reset, then no usable model completion under `api.inference.net` egress deny.
- Scrubbed suggestion map: empty / blocked
  (`docs/catalyst-halo/results/phase2/halo-suggestion-map.json`).
- No harness mutations from HALO. No held-out paired evaluation. Label:
  **workflow incomplete — not efficacy evidence**.

### Offline held-out harness revalidation

After adding `btc-hold-007` (`mempool_url_config`) and `btc-hold-008`
(`sats_btc_conversion`):

- Held-out offline-fixture success rate: **0/8** on immutable baseline
  (expected).
- Development offline-fixture success rate: **0/6** (expected).
- Freeze file: `docs/catalyst-halo/freeze-hashes.json`.

### Training

- Synthetic train / validation / holdout JSONL built with hash metadata under
  `docs/catalyst-halo/results/phase2/training-splits-meta.json`.
- Overlap check: passed (task-id level).
- Base model revision: unset (catalog unreachable).
- Displayed price: unknown → **stop at ready-to-submit**; no job started.

## Privacy Canaries

Fake canaries from `diligence/privacy/canaries.json` were embedded only in
local synthetic development traces (outside Git). Scrubbed committed reports
were re-checked; no canary leakage into committed Phase 2 JSON summaries.
`inf auth status` truncated-key print is a separate privacy concern for CLI
usage in shared logs.

## Failures, Unknowns, Unproven Claims

- Catalyst ingest fidelity: **unproven** (no confirmed hosted spans).
- Gateway vs direct semantics: **unproven**.
- HALO efficacy: **unproven** (no suggestions applied; no paired held-out run).
- Training improvement: **unproven** (no training).
- Whether OTLP exporters silently drop spans on connection reset: **unknown**.
- Exact low-cost Inference model id/revision for this project: **unknown**.
- HALO Desktop: **unavailable** in this headless run (not pursued).

Do not claim overnight efficacy, statistically significant improvement, or
successful hosted fine-tuning.

## Exact Reproduction Commands

```bash
# Offline harness
python3 -m unittest tests.test_diligence_offline -v
export DILIGENCE_RAW_DIR="$HOME/diligence-raw-phase2"
python3 -m diligence prepare
python3 -m diligence run --arm offline-fixture --split holdout --repeats 1
# verify/report using printed run_dir

# Hash-verify downloads against docs/catalyst-halo/supply-chain-hashes.md
# then install into an isolated venv / npm prefix under $DILIGENCE_RAW_DIR

# After egress allows inference.net:
export CATALYST_OTLP_ENDPOINT=https://telemetry.inference.net
export CATALYST_SERVICE_NAME=bitcoin-sat-tracker-diligence
# CATALYST_OTLP_TOKEN and INFERENCE_API_KEY already in environment
# Write CLI config from env (do not pass key on argv):
python3 -c 'import json,os; from pathlib import Path; p=Path.home()/".inf"/"config.json"; p.parent.mkdir(mode=0o700, exist_ok=True); p.write_text(json.dumps({"apiKey": os.environ["INFERENCE_API_KEY"]})+"\n"); p.chmod(0o600)'
inf models list --json
# Then re-run OTLP probe / Gateway / HALO / training steps from the work order
```

Synthetic offline helpers: `diligence/phase2_offline.py`.

## Revoke Key and Delete Hosted Data

1. In the Inference.net project that issued the disposable key, rotate/revoke
   the project API key used as `INFERENCE_API_KEY` / `CATALYST_OTLP_TOKEN`.
2. Delete any Catalyst traces, datasets, eval runs, and training artifacts
   created under project service name `bitcoin-sat-tracker-diligence`
   (none confirmed created in this run).
3. Remove local vendor state: `rm -rf ~/diligence-raw-phase2`
   (contains config with API key under `vendor-home/.inf/config.json`).
4. Confirm Cloud Agent secrets are removed or rotated in the Cursor
   environment settings.

## Morning Handoff

### What you can demo on the founder call

1. **Offline diligence harness** with eight held-out families, freeze hashes,
   and a clean 0/8 baseline failure story.
2. **Supply-chain continuity**: exact Phase 1 archives re-downloaded and
   SHA-256-matched before any vendor execution.
3. **Honest blocker**: dedicated keys are present, packages install and
   initialize, but Catalyst/HALO/Gateway cannot be demonstrated until
   `inference.net` (and HALO’s jsDelivr dependency) are on the egress allowlist.

### Three most important questions raised by evidence

1. Will Catalyst’s OTLP path and `inf` CLI accept project API keys alone for
   traces/datasets/training, or is browser session login still required for
   critical write paths (`instrument`, some project-scoped APIs)?
2. Does `inf auth status`’s truncated API-key echo create an unacceptable log
   leakage risk for CI/shared agent transcripts?
3. Once egress works, what is the cheapest Inference-hosted OpenAI-compatible
   model that still exercises Gateway + HALO + a **confirmed $0** training
   recipe end-to-end under the $5 overnight cap?
