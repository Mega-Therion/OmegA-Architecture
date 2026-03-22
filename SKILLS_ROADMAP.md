# OmegA Skills Roadmap

This document captures the first serious skill roadmap for OmegA as a sovereign, CLI-first agent system.

The goal is not to collect generic "agent skills." The goal is to build command-grade modules that let OmegA maintain itself, audit itself, evaluate itself, and operate with less architecture drift.

## Design Principle

OmegA should not be constrained by an oversized command list. The operating model should be:

- the human states the goal clearly
- OmegA infers intent and constraints
- OmegA selects tools and execution steps
- OmegA verifies outcomes and reports clearly

These skills exist to strengthen that loop.

## Priority Skills

### 1. One-Block Builder

Purpose:
- Emit exact reproducible shell scripts and one-line launch commands for installs, upgrades, validation, recovery, and subsystem bring-up.

Why first:
- It matches the preferred operating style exactly.
- It reduces operator friction immediately.
- It improves reproducibility before deeper automation.

Inputs:
- target subsystem
- desired outcome
- environment constraints

Outputs:
- generated script file
- one-line execution command
- validation checklist

### 2. Repo Cartographer

Purpose:
- Scan the repo, map modules, trace relationships, detect dead zones, and produce a living architecture manifest.

Why next:
- OmegA needs a stable self-model of the codebase and publication structure.
- This skill reduces hidden structure drift.

Inputs:
- repository root
- scope filters

Outputs:
- module map
- dependency graph
- stale file report
- architecture manifest

### 3. Spec-to-Code Auditor

Purpose:
- Compare architecture papers, README claims, canon docs, and runtime code to detect mismatches.

Why next:
- OmegA’s value depends on alignment between formal architecture and implementation reality.

Inputs:
- canonical papers
- overview docs
- runtime/config paths

Outputs:
- mismatch report
- severity ranking
- proposed remediation plan

### 4. Eval Forge

Purpose:
- Generate evaluations, regression suites, prompt batteries, and pass/fail reports for routing, memory, identity, safety, and behavior.

Why next:
- This creates measurable quality rather than informal confidence.

Inputs:
- target subsystem
- behavior claims
- acceptance rules

Outputs:
- eval cases
- execution harness
- result summaries
- regression artifacts

## Second Wave

### Provider Router Simulator
- Stress-test routing, latency, quotas, and failover policy across local and cloud providers.

### Telegram Agent Ops
- Provision, validate, and maintain the Telegram-facing portions of the agent mesh.

### n8n Round-Trip Manager
- Version, export, import, validate, and restore n8n workflows and related assets.

### Secure Agent Mesh
- Manage trust boundaries, authentication, registration, and service-to-service security rules for local and LAN agent coordination.

## Third Wave

### Persona Consistency Linter
- Check prompts, configs, docs, and outputs against OmegA’s canonical identity and personality rules.

### Publication Packager
- Prepare GitHub, Zenodo, arXiv, figures, citations, changelogs, and release bundles.

### Research Harvester
- Continuously gather papers, APIs, model changes, and implementation notes relevant to sovereign AI and the OmegA stack.

## Skill Contract Standard

Every OmegA skill should define:

1. Inputs
2. Permissions
3. Observable execution steps
4. Output artifacts
5. Rollback behavior

Each skill should emit:

- machine-readable output for chaining
- human-readable markdown summaries
- exact shell scripts when execution is required

## Recommended Build Order

1. One-Block Builder
2. Repo Cartographer
3. Spec-to-Code Auditor
4. Eval Forge
5. Provider Router Simulator
6. Telegram Agent Ops

This order prioritizes:

- deployment reliability
- codebase self-understanding
- architecture integrity
- measurable quality
- systems operations scale

## Immediate Next Step

If building starts now, the first implementation target should be One-Block Builder, followed immediately by Repo Cartographer.

That pairing gives OmegA:

- a reliable execution format
- a reliable self-map

Without those two, every later skill is operating on weaker ground.
