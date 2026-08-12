# Security and Privacy Boundary

## Allowed Material

- Files and Git history from this public repository.
- Public Bitcoin transaction identifiers and addresses already committed here.
- Deterministic synthetic Bitcoin RPC and mempool fixtures.
- Clearly labeled fake prompts, outputs, tool calls, and privacy canaries.
- Aggregate pass/fail, time, token, cost, retry, tool-error, trace-quality, and
  privacy results.
- Public documentation and package-registry metadata.
- Vendor archives downloaded for static inspection under the supply-chain
  protocol.

## Prohibited Material

- Any other repository or uncommitted local source.
- Private source code, documents, deal data, production traffic, or
  production-derived fixtures.
- Personal files, previous agent conversations, local computer files, or cloud
  storage.
- Real Bitcoin wallets, RPC credentials, AWS resources, or live provider data.
- Existing Codex configuration, hooks, MCP servers, skills, transcripts, or
  authentication files.
- Real secrets of any kind in Git, prompts, trace attributes, screenshots,
  shell arguments, test fixtures, or reports.

## Environment Status

The approved Cloud environment is scoped to this repository. It has no named
secrets. Its setup installs the public Python `requests` package and starts a
local Bitcoin Core regtest process with placeholder credentials bound to
`127.0.0.1`.

The regtest process is not evidence of a fully offline benchmark. Phase 1 tests
must replace Bitcoin RPC and mempool behavior with deterministic mocks and must
pass without the regtest process.

## Phase 1 Credential Rule

No secret is needed or authorized. Do not ask for, add, inspect, or print any
API key.

These names are reserved for a possible future phase and must not be configured
now:

```text
INFERENCE_API_KEY
CATALYST_OTLP_TOKEN
OPENAI_API_KEY
CODEX_API_KEY
ANTHROPIC_API_KEY
```

When a future phase is separately approved, secrets must be short-lived,
environment-scoped, least-privilege, spend-limited, and supplied through the
Cloud environment's secret manager. They must never be stored in `.env` or
passed in a prompt.

## Raw and Committed Data

Raw data includes prompts, model output, JSONL events, full commands, complete
tool output, provider responses, trace/span bodies, downloaded datasets, and
training examples.

Raw data must:

- Live outside the Git checkout.
- Use a directory with mode `0700`.
- Be excluded from reports and commits.
- Have a documented cleanup and retention decision in a future phase.

Committed data may include source, fake fixtures, task definitions, test code,
schemas, package metadata, hashes, and scrubbed aggregate results.

Use `null` or an explicit unavailable state when a metric was not collected.
Never turn an unavailable metric into a misleading zero.

## Network Rules

Phase 1 may use the network only for:

- Public documentation research.
- Git operations for this repository.
- Package-registry metadata and static archive downloads needed for the audit.

Phase 1 must not:

- Call a model API.
- Authenticate to Inference.net.
- Contact Catalyst telemetry or Gateway endpoints.
- Upload a trace, dataset, result, or source file.
- Run a live hosted evaluation, training job, deployment, or GPU instance.
- Fetch held-out material from inside a future task workspace.

## Privacy Canaries

Create clearly fake, unique canaries for these locations:

1. User prompt.
2. Model response.
3. Tool name.
4. Tool arguments.
5. Tool result.
6. Repository file.
7. File outside the task workspace.
8. Synthetic environment variable.
9. Fake API-key-shaped value.
10. URL query and header-shaped value.

Do not make a canary that could function as a real provider credential.

Prepare a matrix for later phases that records each canary as present,
redacted, hashed, truncated, or absent across:

- Codex JSONL.
- Local HALO storage.
- Hosted Catalyst trace tree.
- Raw Catalyst span JSON.
- Downloaded traces.
- CLI output.
- Evaluator output.
- Scrubbed committed reports.

## Immediate Stop Conditions

Stop without inspecting further if:

- Another or private repository becomes visible.
- Private data or a real secret appears.
- A package hash does not match registry metadata.
- An archive contains an unsafe path.
- A lifecycle script or native binary has unclear behavior.
- Static inspection would require executing vendor code.
- A command would enter Phase 2 or send data to a hosted service.
