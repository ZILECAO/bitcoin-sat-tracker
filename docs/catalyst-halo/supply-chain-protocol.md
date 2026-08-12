# Static Supply-Chain Audit Protocol

Phase 1 permits static inspection of proposed packages. It does not permit
installing, importing, or executing vendor code.

## Targets

1. `@inference/cli`
2. `@inference/tracing`
3. `inference-catalyst-tracing`
4. HALO Engine
5. HALO Desktop
6. Required OpenTelemetry exporters
7. OpenAI Codex CLI `0.146.1`

## Safe Acquisition

For each target:

1. Query public registry or release metadata without executing the package.
2. Record the exact resolved version and download URL.
3. Record the registry-provided integrity value before downloading.
4. Download the archive into a task-owned temporary directory outside Git.
5. Calculate a local cryptographic hash.
6. List archive entries before extraction.
7. Reject absolute paths, `..` traversal, unsafe links, or unexpected device
   entries.
8. Extract without running lifecycle scripts or loading package code.
9. Never commit archives or extracted vendor source.

Do not use commands such as `npm install`, `pip install`, `bun add`, package
execution shims, or an import merely to discover metadata.

## Required Evidence Per Target

Record:

- Package/release name and exact version.
- Registry and download URL.
- Publisher and maintainers.
- Publication date and release cadence.
- License.
- Claimed public source repository and exact source tag/commit when available.
- Whether the published artifact can be reproducibly connected to that source.
- Registry integrity value.
- Locally calculated archive hash.
- Archive paths and extraction result.
- Direct dependency count.
- Transitive dependency count when determinable without installation.
- Lifecycle scripts.
- Native binaries or downloaded executables.
- Telemetry, update, crash-report, and authentication behavior.
- Network endpoints visible in package content.
- Known vulnerability and provenance concerns.
- Static-inspection limitations.
- Recommendation: approve for isolated Phase 2, hold pending evidence, or
  reject.

## Review Priorities

### Inference CLI

Determine how it authenticates, where it stores session material, what
instrumentation instructions it downloads, how it launches coding agents, what
repository metadata it reports, and whether telemetry can be disabled.

### Tracing SDKs

Determine default exporters, auto-instrumentation behavior, modules patched,
content captured, redaction controls, shutdown/flush behavior, batch storage,
and endpoint configuration.

### HALO

Separate the open-source engine from Desktop packaging. Determine how model
provider keys are stored, which trace content goes to an analysis model, what
local telemetry persists, which hosted endpoints are optional, and whether a
fully local analysis model is supported.

### OpenTelemetry

Identify exactly which exporter packages are needed for native Codex OTLP and
manual OpenInference paths. Prefer standard protocol output and explicit
allowlists over broad auto-instrumentation.

### Codex CLI

Verify version `0.146.1` from an official OpenAI source. Do not install or run
it in Phase 1. Record its official package integrity and source/provenance
information. Future runs must use a fresh isolated home, ephemeral sessions,
no user config/rules/MCP/hooks, and an explicitly pinned model.

## Stop Conditions

Stop the target audit and recommend “hold” when:

- Public source provenance is missing or cannot be matched to the artifact.
- A compiled package is materially opaque.
- A lifecycle script is unexpected.
- A native binary or secondary download has unclear provenance.
- Registry integrity and local hash checks disagree.
- An unsafe archive entry exists.
- An unexpected network endpoint appears.
- Answering an important question would require executing package code.

“No issue found” is not equivalent to “safe.” State the scope and limitations
of static inspection in every conclusion.
