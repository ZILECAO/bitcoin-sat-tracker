# Phase 2B Sat-Hunt Report

Training-free Catalyst + HALO diligence for a specialized Bitcoin/ordinal
coding-agent workflow on public `ZILECAO/bitcoin-sat-tracker`.

This is an execution report of the Phase 2B work order. It is **not**
statistical efficacy evidence: sample sizes are small, and HALO did not produce
an accepted machine-readable change set.

## 1. Final branch and commit

- Branch: `cursor-cloud-zile/phase-2-overnight-18c7` (also fast-forwarded to
  `diligence/catalyst-halo`)
- Tip at report freeze: `de1fbe94ef9cde502ec31701bb819ae3c0a02c6f`
- Required start commit: `7381af42856c2b9a52f3dd58546c0b2ba4992d29`
- Immutable task baseline: `d674a065819a0bd45357f8530b4f15775bfdaac9`

## 2. Draft PR

https://github.com/ZILECAO/bitcoin-sat-tracker/pull/1

## 3. Benchmark version

`sat-hunt-v2` (`diligence/sat_hunt/benchmark.json`)

## 4. Frozen benchmark hashes

See `diligence/sat_hunt/freeze-hashes.json` and
`docs/catalyst-halo/results/phase2b/freeze-hashes.json`.

Notable values:

| Item | SHA-256 |
| --- | --- |
| Patoshi CSV (private) | `f649579e286085325a881bec1168e88bbb6f5d67e10b7ef8cb5c65e916a34a2e` |
| Derived attribution set | `c9641d86ba93c71fc550c63fd97b6da8246f46a9410125a6c2d4326fc461c71d` |
| Deterministic fixture | `5ff3dbbb1c11c7b0ba4e34959c94385cc9b69cfb17b384a4f01e2847d8c7dd08` |
| Selected model | `gemini-2.5-flash-lite` |
| Baseline harness prompt | `b7b1fabb7403b7ca77efc9ca37eaf546a60b65d1c677d2b6c739c8cda5e78a36` |
| Toolkit `fixture_api.py` | `8b1cecd465ebfe17e8f4a4cad44ebc50e4144fa94390ce8372d44ca2d1793c0a` |

## 5. Attribution sources

Pinned in `diligence/sat_hunt/attribution-sources.json`:

1. **patoshi-addresses** commit `414637ce52aa4819926bf1934b2235ed182a0280`,
   file `patoshi_pubkeys_COMPLETE.csv`, 21,953 records (verified).
2. **Lerner Patoshi method** (bitslog) — attribution-method context only.
3. **Arkham Satoshi entity / announcement** — intended aggregate cross-check.

## 6. Attribution-source limitations

- The Patoshi CSV has **no declared license**; raw CSV stays outside Git.
- Exact-match on current output only; no graph clustering / origin-only guilt.
- Arkham pages were **not** retrieved from this VM (TLS reset). Recorded as
  aggregate-cross-check unavailable; **not** used for membership.
- Required uncertainty language for non-matches:
  “No exact match in the frozen public Satoshi-attribution set; this does not
  prove who controls the output.”

## 7. Derived attribution-set hash

`c9641d86ba93c71fc550c63fd97b6da8246f46a9410125a6c2d4326fc461c71d`

Committed metadata only: `diligence/sat_hunt/attribution-derived-meta.json`.
Full match index remains under `~/diligence-raw-phase2b/patoshi/` (mode 0700).

## 8. Model candidates and prices

Queried Inference catalog (`context_length` from `/v1/models`):

| Model | Context | Notes |
| --- | --- | --- |
| `deepseek-v4-flash` | 163840 | Prior Phase 2 Gateway path worked |
| `gpt-4.1-nano` | 1047576 | Inexpensive; prior hosted eval failed |
| `gemini-2.5-flash-lite` | 1048576 | Selected |

Local accounting used the prior deepseek-style estimate
`$0.14 / $0.28` per 1M in/out tokens for ledger estimates. Platform
`/v1/inferences` returned HTTP 503 during later spend probes; incremental spend
below uses the local Gateway ledger.

## 9. Model-selection results

Artifact: `docs/catalyst-halo/results/phase2b/model-selection.json`

- Smoke (2 tasks × 3 models): `gpt-4.1-nano` 1/2; others 0/2.
- Full development once each for top two: both `gpt-4.1-nano` and
  `gemini-2.5-flash-lite` scored **1/11**; gemini selected on lower cost then
  duration.

## 10. Selected model

**`gemini-2.5-flash-lite`** (frozen before HALO / held-out / final).

## 11. Catalyst trace IDs and dashboard verification

Service: `bitcoin-sat-tracker-sat-hunt`  
Project: `b69a2722-d305-47e9-9931-b28b6dfcbd6d`

Verified nested AGENT → LLM/TOOL tree example (passing baseline checkpoint task):

- Trace ID: `798b053b04602517f40c679a218fc18e`
- Root: `sat-hunt.sat-dev-008:baseline-dev:r1` (AGENT)
- Children: `llm.gemini-2.5-flash-lite` (LLM), `tool.cache_put` /
  `tool.checkpoint_save` (TOOL)

Scrubbed verify artifact:
`docs/catalyst-halo/results/phase2b/catalyst-trace-verify.json`

Additional baseline development traces are listed in
`docs/catalyst-halo/results/phase2b/baseline-dev-runs.json` and
`development-traces-meta.json` (11 traces / 58 spans exported for HALO).

## 12. HALO run / result identifiers

| Attempt | Model | Result |
| --- | --- | --- |
| 1 | `gemini-2.5-flash-lite` | Engine `TypeError` in event mapper (`NoneType` text part) |
| 2 (bounded retry) | `deepseek-v4-flash`, `--max-output-tokens 6000` | Exit 0, but `final_answer` JSON invalid/truncated twice |

Raw stdout SHA-256 (private):
`67b7e9d413bc9754e268de84fecf69bc7f8c9e34981fc906031a46811bb1dd40`

Status: **fail_closed_incomplete_final_answer**  
Map: `docs/catalyst-halo/results/phase2b/halo-suggestion-map.json`

No hosted `inf halo run create` was executed with expensive eligible models
(opus / pro class) under the $5 Phase 2B cap.

## 13. HALO suggestion classification

No authoritative suggestion list was accepted. Per work order: do not
reconstruct recommendations from a truncated fragment after the one allowed
retry.

## 14. Exact accepted changes

**None.**

## 15. Exact rejected suggestions and reasons

All potential transcript fragments rejected with reason:
`HALO final_answer malformed/truncated after one bounded retry; fail-closed`.

## 16. Held-out results by arm

Artifact: `docs/catalyst-halo/results/phase2b/heldout-results.json`  
4 tasks × 4 arms × 3 reps = **48** runs; randomized order (seed 42).

| Arm | Attempted | Correct | Success | Total cost (est.) | Complete traces |
| --- | --- | --- | --- | --- | --- |
| baseline-harness | 12 | 0 | 0% | 0.0091959 | 12 |
| halo-harness-only | 12 | 0 | 0% | 0.0091959 | 12 |
| halo-repo-toolkit-only | 12 | 0 | 0% | 0.0091959 | 12 |
| halo-combined | 12 | 0 | 0% | 0.0091959 | 12 |

Arms were intentionally identical after HALO fail-closed (same harness hash,
toolkit not injected). Median cost/duration/tokens among correct runs: **n/a**
(no correct runs). Uncertainty: small sample; zero successes → no paired
efficiency comparison.

## 17. Deterministic final results (Track A)

Artifact: `docs/catalyst-halo/results/phase2b/final-exam-results.json`

| Arm | Attempted | Correct | Success | Total cost (est.) |
| --- | --- | --- | --- | --- |
| baseline-harness | 3 | 0 | 0% | 0.00305466 |
| halo-harness-only | 3 | 0 | 0% | 0.00305466 |
| halo-repo-toolkit-only | 3 | 0 | 0% | 0.00305466 |
| halo-combined | 3 | 0 | 0% | 0.00305466 |

Hidden oracle (deterministic fixture, not a live claim): earliest active sat
**100**; earliest active inscribed sat **250**. No arm produced a passing
final-answer artifact.

## 18. Pinned-mainnet replay results (Track B)

Replay bundle meta:
`docs/catalyst-halo/results/phase2b/pinned-mainnet-replay-bundle-meta.json`

Same frozen fixture/oracle shapes for every arm; **0/12** correct.
No executable inscription content committed.

## 19. Live global result proven?

**No.** Track C status:

`Live global result not run — complete sat index unavailable.`

Regtest Bitcoin Core was available for fixture research; a full mainnet
`ord --index-sats`-equivalent index was not present on this disposable VM.

## 20. Candidate sat and inscription result if proven

Not proven by any arm. Deterministic oracle values (for harness validation only):

- Earliest active uninscribed: sat **100**
- Earliest active inscribed: sat **250** (two inscription IDs in fixture)

## 21. Total incremental Inference spend

Local Gateway ledger (`~/diligence-raw-phase2b/spend/phase2b-spend-ledger.json`):

- Cap: **USD $5.00**
- Incremental agent-run estimate: **≈ USD $0.101**
- HALO engine calls used additional Gateway traffic (deepseek retry) not fully
  attributed in the agent-run ledger; platform `/v1/inferences` was **503**
  during later probes, so platform-exact Phase 2B delta is **unavailable**.
- Prior Phase 2 project page spend (~$0.012) is separate historical context.
- No training, deploy, GPU rental, or weight upload.

## 22. Total wall-clock time

Approximately several hours of autonomous execution on the Cloud Agent VM for
Stages 1–10 (including model selection, baseline, HALO attempts, held-out,
final). Exact wall clock is environment-run duration, not Inference billing.

## 23. Product failures and bugs

1. **HALO `final_answer` truncation / invalid JSON** after raised
   `--max-output-tokens` (repeat of Phase 2 failure mode).
2. **HALO + `gemini-2.5-flash-lite`**: engine crash mapping assistant message
   text parts (`NoneType`).
3. **Platform inferences/org spend APIs**: intermittent **HTTP 503**.
4. **Python urllib Cloudflare 1010** to `api.inference.net` (mitigated via curl
   + browser User-Agent; same as Phase 2).
5. **Arkham** fetch TLS reset from this VM.
6. Agent harness correctness remains low on this curriculum without accepted
   HALO harness/toolkit diffs (frequent missing `answers/*.json` / tests).

## 24. Hosted-eval status

Phase 2 hosted evals previously failed (`2 of 2 results failed`). **No second
spam retry** in Phase 2B (no concrete schema fix identified beyond prior
attempts). Local hidden scorers remain the correctness source of truth.

## 25. Privacy / security observations

- Credentials never printed; staged diffs scanned for live key material.
- Patoshi CSV and raw traces stay mode-0700 outside Git.
- Task workspaces built from baseline archive only; diligence/docs/scorers
  excluded.
- Catalyst traces verified without committing raw provider payloads.
- Fake canaries remain for future privacy probes; no unexpected private-repo
  access.

## 26. Reproduction commands

```bash
# Offline tests
python3 -m unittest tests.test_diligence_offline -v
python3 -m unittest tests.test_sat_hunt -v
python3 -m unittest tests.test_sat_hunt_phase2b -v

# Validate manifests
python3 -m json.tool diligence/sat_hunt/benchmark.json >/dev/null
python3 -m json.tool diligence/sat_hunt/attribution-sources.json >/dev/null

# Private raw dir + pinned Patoshi CSV (do not commit)
mkdir -p ~/diligence-raw-phase2b && chmod 700 ~/diligence-raw-phase2b
# download + sha256 verify expected f649579e... then:
export DILIGENCE_RAW_DIR=~/diligence-raw-phase2b
export CATALYST_SERVICE_NAME=bitcoin-sat-tracker-sat-hunt
export CATALYST_OTLP_ENDPOINT=https://telemetry.inference.net
export INFERENCE_BASE_URL=https://api.inference.net/v1
# Gateway via curl+UA (see diligence/sat_hunt/agent/gateway.py)

python3 -m diligence.sat_hunt.run_phase2b select
python3 -m diligence.sat_hunt.run_phase2b baseline --model <selected>
python3 -m diligence.sat_hunt.run_phase2b freeze-arms --model <selected>
python3 -m diligence.sat_hunt.run_phase2b heldout --model <selected> --reps 3
python3 -m diligence.sat_hunt.run_phase2b final --model <selected> --reps 3
```

## 27. Five-minute founder-call demonstration

1. Open `diligence/sat_hunt/benchmark.json` (`sat-hunt-v2` definitions).
2. Show Patoshi pin + SHA-256 in `attribution-sources.json` (CSV not in Git).
3. Contrast current-output exact match vs coinbase-origin (attribution tests).
4. Open Catalyst trace `798b053b04602517f40c679a218fc18e` (AGENT→LLM/TOOL).
5. Show a failed baseline development run in `baseline-dev-runs.json`.
6. Show HALO fail-closed map (incomplete `final_answer`).
7. Show empty accepted diffs / identical `arms-freeze.json` hashes.
8. Show held-out 0/12 per arm before/after (no delta).
9. Correctness-first: no efficiency ranking among correct runs (none correct).
10. Deterministic final Track A: 0/3 per arm; oracle sats 100 / 250.
11. Pinned-mainnet replay Track B: same freeze, 0/12.
12. Live Track C blocker sentence.
13. Hosted-eval still failed / not spam-retried.
14. Incremental spend ≈ $0.10 agent ledger vs $5 cap.

## 28. Ten highest-value founder questions

1. What data does Catalyst store from AGENT/LLM/TOOL spans, and for how long?
2. What retention / deletion guarantees exist per tenant?
3. Regional storage and encryption controls for traces and payloads?
4. Can payload logging be disabled or field-redacted by policy?
5. Is Gateway / HALO data ever used for training by default or by opt-in?
6. Tenant isolation model for traces, datasets, evals, and HALO runs?
7. API-key permission scopes (inference vs telemetry vs HALO vs training)?
8. Trace export formats and self-hosted / VPC deployment options?
9. How should customers debug hosted-eval “N of N failed” with actionable diffs?
10. Evidence that HALO improvements transfer to held-out tasks when
    `final_answer` is required to be complete machine-readable JSON — and
    whether HALO optimizes harness, tools, prompts, model choice, or all four?

## 29. Ticket-ready summary for TEC-714

Phase 2B sat-hunt executed on PR #1 / `diligence/catalyst-halo`: frozen
`sat-hunt-v2` benchmark with verified Patoshi CSV hash, derived attribution set,
deterministic fixtures/oracle/scorers, and Catalyst-instrumented agent
(`bitcoin-sat-tracker-sat-hunt`). Selected model `gemini-2.5-flash-lite`.
Baseline development 1/11. HALO fail-closed after one retry (truncated/invalid
`final_answer`). Four arms frozen identical; held-out 0/48; deterministic final
0/12; replay 0/12; live global not run (no complete sat index). Incremental
Inference agent-ledger ≈ $0.10 / $5. Hosted eval not re-spammed. No training.

## Four-arm results table (aggregate)

| Arm | Tasks attempted | Correct | Success | Median cost correct | Total cost | Median duration correct | Median tokens correct | Median tools correct | Retries | Complete traces | Final-exam correct (A) | Efficiency eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline-harness | 12 hold + 3 final | 0 | 0% | n/a | ~0.0123 | n/a | n/a | n/a | 0 | 15 | 0/3 | 0 |
| halo-harness-only | 12 hold + 3 final | 0 | 0% | n/a | ~0.0123 | n/a | n/a | n/a | 0 | 15 | 0/3 | 0 |
| halo-repo-toolkit-only | 12 hold + 3 final | 0 | 0% | n/a | ~0.0123 | n/a | n/a | n/a | 0 | 15 | 0/3 | 0 |
| halo-combined | 12 hold + 3 final | 0 | 0% | n/a | ~0.0123 | n/a | n/a | n/a | 0 | 15 | 0/3 | 0 |

**HALO improved correctness?** No (no accepted changes; held-out tied at 0).  
**HALO improved cost?** Not measurable among correct runs (none).  
**HALO improved speed?** Not measurable among correct runs (none).
