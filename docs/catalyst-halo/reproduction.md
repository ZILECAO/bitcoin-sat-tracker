# Phase 1 Harness and Reproduction Guide

## Immutable Baseline

```text
d674a065819a0bd45357f8530b4f15775bfdaac9
```

`track-forwards.py` and `watch-wallet.py` remain unchanged from that commit.
Their defects are the future benchmark tasks. The offline harness scores the
baseline as-is; it does not patch those scripts.

## Package Commands

```bash
python3 -m diligence prepare
python3 -m diligence run --arm <arm> --split <dev|holdout> --repeats <n>
python3 -m diligence verify --run-dir <path>
python3 -m diligence report --run-dir <path>
```

Standard library only (plus the repository’s existing public `requests`
dependency for the baseline scripts themselves). The harness does not add
third-party packages.

## What `prepare` Does

1. Verifies this repository and that the immutable baseline is an ancestor.
2. Confirms baseline scripts match the baseline commit byte-for-byte.
3. Creates a mode-`0700` raw directory outside Git (`~/diligence-raw` by
   default, overridable with `DILIGENCE_RAW_DIR`).
4. Materializes deterministic fake Bitcoin RPC / mempool fixtures.
5. Validates development and held-out task manifests and privacy canaries.
6. Proves a sample baseline checkout excludes diligence materials.
7. Writes a prepare manifest under `.diligence-state/` (gitignored) and a
   scrubbed summary at `docs/catalyst-halo/prepare-summary.json`.

## Experimental Arms

Phase 1 executes only `offline-fixture`.

All other arms (`codex-native-otel`, `codex-openinference`, `codex-baseline`,
`codex-halo`, `gateway-base`, `small-base`, `small-tuned`, `gpt56-reference`)
fail closed with `notes: "Phase 2 not configured"` and do not call a model.

## Development vs Held-Out Tasks

| Split | Manifest | Tasks | Families |
| --- | --- | --- | --- |
| Development | `diligence/tasks/development.json` | 6 | rpc config, missing-config safety, timeouts/status, structured errors, injectable deps, block-reward tests |
| Held-out | `diligence/tasks/holdout.json` | 8 | satpoint validation, no library `sys.exit`, safe CLI, bounded wallet polling, fee/coinbase edges, tx-output edges, mempool URL config, sats/BTC conversion |

Fourteen families total (≥8 required). Held-out count meets the full HALO
protocol minimum of eight tasks. Manifests and prompts are frozen via
`docs/catalyst-halo/freeze-hashes.json` before any model-backed run.
Future HALO analysis may see development traces only; held-out outcomes must
remain hidden until the improved harness is frozen.

## Workspace Isolation

Each offline-fixture task:

1. Creates a fresh checkout via `git archive` of the baseline commit.
2. Copies only public `TASK/PROMPT.md` and synthetic fixtures.
3. Writes `network-policy.json` with `network: disabled`.
4. Never includes `AGENTS.md`, `docs/`, `diligence/`, tests, scorers, or answers.
5. Refuses `.env` / credential copies.
6. Scores outside the workspace, then destroys the workspace.

## Raw vs Committed Data

| Kind | Location | Git |
| --- | --- | --- |
| Raw run records | `~/diligence-raw/runs/*/raw/` (mode `0700`) | excluded |
| Supply-chain archives | `~/diligence-raw/supply-chain/` | excluded |
| Scrubbed records / reports | `docs/catalyst-halo/results/` | may commit after verify |
| Canaries | `diligence/privacy/canaries.json` | fake canaries only |

Unavailable metrics are reported as `status: unavailable` with `value: null`.
Measured zeros are never invented for uncollected fields.

## Privacy Canaries

Ten clearly fake canaries cover prompt, response, tool name/args/result,
repository file, outside-workspace file, synthetic env, fake API-key shape,
and URL/header shape. Phase 1 marks channel states `not_yet_measured` except
scrubbed committed reports (`absent`). `verify` rejects canary leakage into
scrubbed records and compares future secrets only in memory (pass/fail).

## Exact Reproduction Steps

```bash
git fetch origin diligence/catalyst-halo
git checkout diligence/catalyst-halo
git rev-parse HEAD   # Phase 1 commit after merge/push

# Offline tests (no Bitcoin Core, no live internet required for tests)
python3 -m unittest tests.test_diligence_offline -v

# End-to-end offline arm
export DILIGENCE_RAW_DIR="$HOME/diligence-raw"   # optional
python3 -m diligence prepare
python3 -m diligence run --arm offline-fixture --split dev --repeats 1
# note the printed run_dir
python3 -m diligence verify --run-dir "$RUN_DIR"
python3 -m diligence report --run-dir "$RUN_DIR"

# Confirm baseline scripts unchanged
git show d674a065819a0bd45357f8530b4f15775bfdaac9:track-forwards.py | sha256sum
sha256sum track-forwards.py watch-wallet.py

# Confirm raw dir mode
stat -c '%a %n' "${DILIGENCE_RAW_DIR:-$HOME/diligence-raw}"
```

Expected offline-fixture result on the unchanged baseline: task scorers mostly
**fail** (success rate 0 in the committed Phase 1 sample). That is evidence the
harness scores the broken baseline, not that agents have fixed it.

## Still Blocked Until Phase 2

- API keys / provider authentication
- Installing or running `inf`, HALO, Catalyst tracing, Codex, or model clients
- `inf instrument` (including `--dry-run`)
- Uploading traces/datasets/prompts/source/results
- Catalyst Gateway routing
- Hosted evaluation, training, deployment, or GPU workloads
- Any network use from task workspaces

See [`supply-chain-report.md`](supply-chain-report.md) for package decisions
required before Phase 2.
