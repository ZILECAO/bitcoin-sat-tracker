# Phase 1 Static Supply-Chain Report

Static inspection only. No vendor package was installed, imported, or executed.
Archives were downloaded into `/home/ubuntu/diligence-raw/supply-chain/` (mode
`0700`, outside Git) and are not committed.

Inspection date: 2026-08-12.

## Methodology

For each target:

1. Query public registry/release metadata.
2. Record version, download URL, and registry integrity.
3. Download the archive outside Git.
4. Compute a local cryptographic hash.
5. List archive members and reject absolute/`..`/unsafe link/device paths.
6. Extract without lifecycle scripts or code execution where source was readable.
7. Record endpoints, scripts, native binaries, and limitations.

“No issue found” is **not** equivalent to “safe.”

## Summary Recommendations

| Target | Resolved version | Recommendation |
| --- | --- | --- |
| `@inference/cli` | `0.0.180` | **Hold** — opaque platform binaries; no npm `repository` field |
| `@inference/tracing` | `0.1.9` | **Hold** — readable JS, but missing npm provenance/`repository` |
| `inference-catalyst-tracing` (+ `catalyst-tracing`) | `0.1.8` | **Hold** — thin alias; real code in `catalyst-tracing`; no license/repo commit pin |
| HALO Engine (`halo-engine`) | `0.3.4` | **Hold pending evidence** — hash matches PyPI; source repo claimed, not reproducibly pinned to artifact |
| HALO Desktop | `app-v0.1.17` | **Hold / reject for Phase 2 install-by-curl** — opaque installer binary |
| OpenTelemetry exporters used by tracing | pinned below | **Approve for isolated Phase 2** (standard packages) |
| OpenAI Codex CLI | `0.146.1` | **Hold pending isolated-home controls** — official package, but large native vendor binaries |

Packages that should **not** be approved for Phase 2 as currently packaged:

1. `@inference/cli` (and its `@inference/cli-*` platform packages)
2. HALO Desktop installer / `install.sh | sh` path
3. Any path that requires executing opaque binaries before additional provenance work

---

## 1. `@inference/cli`

- **Version:** `0.0.180` (npm `latest`; published `2026-08-12T02:01:53Z`)
- **Registry:** `https://registry.npmjs.org/@inference/cli`
- **Tarball:** `https://registry.npmjs.org/@inference/cli/-/cli-0.0.180.tgz`
- **License:** MIT
- **Maintainers (npm):** ifharry, sam-inference, francesco-kuzco, inference-mike, abeatkuzco
- **Repository field:** **missing** on npm metadata
- **Registry integrity:** `sha512-oujaU3NtAp6NATeZUIUniJc0ZFV+vqOubMReN+JlWmDQCwYEA+BYu/kzxeCy/OxIkMcslKCuefWLLiiMlxiB1g==`
- **Registry shasum:** `5dad24544e9524c66acafb9a569bf30cf254f248`
- **Local sha256:** `a5518fd6d59bbfa5597e4082252bc5acb79de13cb9a03600c76535cea561ac1b`
- **Archive entries:** `package/README.md`, `package/package.json`, `package/bin/inf.cjs` (safe paths)
- **Direct dependencies:** `react@19.2.7`
- **Optional platform packages:** `@inference/cli-{darwin-arm64,darwin-x64,linux-x64,linux-arm64}@0.0.180`
- **Lifecycle scripts in published tarball:** none (build scripts exist in package.json metadata for the source project, not executed here)
- **Behavior of wrapper (`inf.cjs`):** resolves optional platform package and `execFileSync`s the `inf` binary. Does not itself authenticate.
- **Native binaries:** yes — linux-x64 package unpacks to ~101 MB single binary `package/bin/inf`
  - linux-x64 tarball local sha256: `6ce7b89e5e32d4d0599d9b7bf990e2172b54a058bcadceb7b3669cec2df5f800`
  - registry integrity recorded; archive paths safe (`package/bin/inf`, `package/package.json`)
- **Network endpoints visible in wrapper/README:** `https://inference.net`, `https://observability-api.inference.net`
- **Docs (not executed):** CLI authenticates via `inf auth login` (browser), stores session for project operations, can run `inf instrument` which launches coding agents.
- **Recommendation:** **Hold.** Opaque compiled Bun binary with no npm repository/source-commit binding. Answering auth storage, telemetry disable, and instrumentation download behavior would require executing the binary.

## 2. `@inference/tracing`

- **Version:** `0.1.9`
- **Tarball:** `https://registry.npmjs.org/@inference/tracing/-/tracing-0.1.9.tgz`
- **License field:** null in package.json
- **Repository field:** **missing**
- **Homepage:** `https://inference.net`
- **Archive:** 104 files; no unsafe paths
- **Direct dependencies (8):**
  - `@opentelemetry/api@1.9.0`
  - `@opentelemetry/context-async-hooks@2.2.0`
  - `@opentelemetry/exporter-trace-otlp-proto@0.206.0`
  - `@opentelemetry/exporter-trace-otlp-http@0.206.0`
  - `@opentelemetry/resources@2.2.0`
  - `@opentelemetry/sdk-trace-base@2.2.0`
  - `@opentelemetry/sdk-trace-node@2.2.0`
  - `@opentelemetry/semantic-conventions@1.40.0`
- **Peer dependencies:** many optional LLM SDKs (`openai`, `@anthropic-ai/sdk`, langchain, `@cursor/sdk`, etc.)
- **Lifecycle:** `prepack` build script in metadata; not run during static extract
- **Endpoints / defaults visible in package content:**
  - default endpoint `http://localhost:8799`
  - docs mention Catalyst OTLP configuration via `CATALYST_OTLP_ENDPOINT`, `CATALYST_OTLP_TOKEN`, `CATALYST_SERVICE_NAME`
- **Native binaries:** none in this package
- **Recommendation:** **Hold** pending public source tag/commit matching and license clarification. Code is readable TypeScript/JS (better than the CLI binary), but provenance is incomplete.

## 3. `inference-catalyst-tracing` (PyPI)

- **Version:** `0.1.8`
- **Sdist:** `inference_catalyst_tracing-0.1.8.tar.gz`
- **Registry sha256 matches local sha256**
- **Archive:** 6 files; safe paths
- **Nature:** company-qualified **alias** that depends on `catalyst-tracing==0.1.8` and re-exports it
- **License:** not declared in inspected metadata

### Underlying `catalyst-tracing==0.1.8`

- **Sdist sha256 verified**
- **Direct runtime deps:** `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-common`, `protobuf`, `requests`
- **Env vars in source:** `CATALYST_OTLP_ENDPOINT`, `CATALYST_OTLP_TOKEN`, `CATALYST_SERVICE_NAME`, `CATALYST_SERVICE_VERSION`, `CATALYST_DEBUG`
- **Default endpoint in source:** `http://localhost:8799`
- **Homepage:** `https://inference.net` (no exact source commit in package metadata)
- **Recommendation:** **Hold** until source repository + commit are pinned and license is explicit. Prefer auditing/installing `catalyst-tracing` directly with a hash pin if Phase 2 proceeds.

## 4. HALO Engine (`halo-engine`)

- **Version:** `0.3.4` (PyPI latest at inspection)
- **Claimed source:** `https://github.com/context-labs/HALO` (also referenced as inference-net/HALO in bundled text)
- **Registry sha256 matches local sha256**
- **Requires-dist count:** 10 direct requirement entries
- **Archive issues:** none observed
- **Endpoints visible in package content (static):** `https://api.openai.com/v1`, `https://api.anthropic.com/v1`, localhost collector ports (`6006`, `8799`-class local URLs), Inference docs URLs
- **Telemetry notes from public docs/package text:** optional `CATALYST_OTLP_TOKEN` upload; without token, local JSONL telemetry file may be written
- **Provider keys:** expected via env (`OPENAI_API_KEY` / compatible base URL) per public docs — not present in this environment
- **Fully local analysis model:** desktop/docs claim local analysis with user-provided provider; not verified by execution
- **Recommendation:** **Hold pending evidence** — artifact hash OK, but reproducible link from PyPI artifact to an exact Git tag/commit was not established in Phase 1 static scope.

## 5. HALO Desktop

- **Release inspected:** GitHub `context-labs/HALO` tag `app-v0.1.17` (published `2026-06-24`)
- **Linux asset:** `stable-linux-x64-HALO-Setup.tar.gz`
  - GitHub digest `sha256:e551ade9e2336eb839269b0b054d83a991e7a06c01740bc13c8a1c615035bb7a`
  - **Local sha256 matched**
  - Entries: `README.txt`, `installer` (~168 MB opaque binary); paths safe
- **Installer script:** read from
  `https://raw.githubusercontent.com/context-labs/HALO/main/app/scripts/install.sh`
  (the `https://inference.net/halo/install.sh` URL reset the connection in this environment). Script downloads artifacts from `https://inference.net/halo/releases`, verifies SHA256SUMS, optionally sigstore, then runs platform install. **Not executed.**
- **Recommendation:** **Hold / do not approve curl-pipe install for Phase 2.** Treat Desktop as an opaque binary distribution. If ever approved, require pinned release URL + checksum + isolated machine + no production credentials.

## 6. Required OpenTelemetry exporters

Pinned by `@inference/tracing@0.1.9` and inspected:

| Package | Version | Local archive hash recorded | Archive issues | Recommendation |
| --- | --- | --- | --- | --- |
| `@opentelemetry/api` | `1.9.0` | yes | none | Approve isolated Phase 2 |
| `@opentelemetry/sdk-trace-node` | `2.2.0` | yes | none | Approve isolated Phase 2 |
| `@opentelemetry/exporter-trace-otlp-http` | `0.206.0` | yes | none | Approve isolated Phase 2 |
| `@opentelemetry/exporter-trace-otlp-proto` | `0.206.0` | yes | none | Approve isolated Phase 2 |

These are standard OpenTelemetry JS packages with public repositories. Prefer explicit OTLP exporters and allowlists over broad auto-instrumentation. Transitive dependency closure was not fully expanded without installation (limitation).

## 7. OpenAI Codex CLI `0.146.1`

- **Package:** `@openai/codex@0.146.1`
- **Registry:** npm; published `2026-08-05T16:00:31Z`
- **License:** Apache-2.0
- **Repository:** `git+https://github.com/openai/codex.git` (directory `codex-cli`)
- **Wrapper tarball shasum verified locally** (`016c49faa4bfa60801f3a5949ae42c4d4e095411`)
- **Wrapper contents:** `bin/codex.js`, `package.json`, `README.md` (safe paths)
- **Optional platform packages:** `@openai/codex@0.146.1-<platform>` style native vendor trees
- **linux-x64 native package:**
  - tarball sha1 matches registry shasum `285ae32b51f2053f9c215e6004d3321d5760bc23`
  - contains large native binaries under `package/vendor/x86_64-unknown-linux-musl/` (`codex`, `codex-code-mode-host`, `bwrap`, `rg`, `zsh`)
  - npm attestations/provenance metadata present for the platform version
- **Not installed or executed**
- **Recommendation:** **Hold pending Phase 2 isolation plan** (fresh home, ephemeral sessions, no user config/rules/MCP/hooks, pinned model). Official source exists, but the runnable artifact is still a large opaque binary tree.

---

## Known Audit Limitations

1. Static inspection cannot observe runtime auth storage, telemetry opt-out effectiveness, or dynamic downloads.
2. Compiled CLI/Desktop/Codex binaries are materially opaque.
3. Several Inference packages omit npm/PyPI repository and license fields.
4. Transitive dependency graphs were only partially determined without installation.
5. Reproducible builds from public source tags to published artifacts were not proven.
6. Vulnerability database scanning was not performed.
7. `https://inference.net/halo/install.sh` was unreachable here; GitHub copy of the installer was reviewed instead.

## Phase 2 Decision Inputs Required

Before any Phase 2 approval:

1. Accept or reject each row in the summary table.
2. Pin exact versions and hash-checked install commands.
3. Define egress allowlist (model provider, OTLP endpoint, npm/pypi as needed).
4. Define disposable credential scopes/spend caps (still not configured now).
5. Decide whether opaque binaries (`inf`, HALO Desktop, Codex vendor bins) are acceptable under isolated execution.
6. Require written authorization before any hosted Catalyst upload.
