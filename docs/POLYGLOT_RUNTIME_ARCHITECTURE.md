# Polyglot Runtime Architecture

## Objective

OmegA already has a production Rust gateway, a Python cognition/memory layer, and a TypeScript UI + MCP layer. This document defines the missing coordination contract that lets those runtimes behave like one system rather than three unrelated codepaths.

## Language Roles

### Rust

- Hosts the authoritative gateway runtime.
- Owns memory stores, policy gating, provider routing, and low-latency request handling.
- Provides the strongest compile-time guarantees in the stack.
- Acts as the production execution boundary for the sovereign runtime.

### Python

- Owns orchestration glue, offline validation, and repository automation.
- Bridges process boundaries where the runtime needs deterministic scripting instead of long-lived service code.
- Provides the easiest place to build validation and analysis utilities without destabilizing the gateway.

### R

- Owns statistical validation and lightweight analysis.
- Produces numeric summaries from runtime telemetry and validation step data.
- Stays dependency-free here on purpose: base R only, no package manager assumptions, no network fetches.

### TypeScript

- Owns the Next.js UI, the MCP server, and other interactive surfaces.
- Exposes runtime validation to agent-side tooling through a typed JSON contract.
- Serves as the user-facing integration layer while Rust remains the runtime authority.

## IPC and Serialization

The integration strategy is intentionally simple:

- HTTP/JSON for browser-facing and gateway-facing requests.
- JSON over stdout/stderr for command-line orchestration.
- CSV as the exchange format between Python and R for small validation datasets.
- Typed JSON responses from the MCP server so agent tooling can reason about the validation state without parsing prose.

This keeps the system inspectable and avoids introducing gRPC or message-queue complexity before it is actually needed.

## Data Safety and Sovereignty

- Secrets remain in environment variables.
- The validator never prints raw secrets.
- Validation reports are structured, bounded, and suitable for audit logging.
- The runtime can run locally without any external control plane.
- Gateway validation is optional and only probes a base URL when one is explicitly supplied.

## Build and Validation Flow

1. Rust builds the runtime workspace.
2. TypeScript builds the MCP server and the Next.js web app.
3. Python compiles the repository's production modules.
4. Python writes a validation CSV and hands it to R.
5. R computes a statistical summary of the build run.
6. Python combines all results into one JSON report.
7. TypeScript can expose the report through the MCP server.

## Failure Policy

- Any failed build step marks the overall validation as failed.
- Missing R support marks the report as degraded rather than silently passing.
- Validation continues across independent steps so the report shows the full failure surface instead of stopping at the first error.

## Current Practical Outcome

The resulting runtime package is not a language mélange. It is a coordinated stack:

- Rust for production gateway and memory.
- Python for orchestration and validation.
- R for statistical analysis.
- TypeScript for UI and typed tooling.

That division keeps the runtime auditable while still giving each language a concrete, bounded responsibility.
