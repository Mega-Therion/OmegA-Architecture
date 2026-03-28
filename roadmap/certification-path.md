# OmegA Certification Path

This document is the bridge from "release gate verified" to "certified, stamped, and operationally undeniable."

It combines two complementary assessments:
- Gemini's report: the release gate is already promotable and machine-verifiable.
- Claude's report: the system's strongest remaining gains come from invariants-first design, unified ingest, telemetry-backed memory utility, eval-first scaffolding, and credential discipline.

## Current Verified Baseline

These are already true and should be treated as the current floor:
- Build integrity is verified across Rust, Node/MCP, and the web app.
- Smoke testing validates live ignition and database round-trips.
- Core AI routes exist and are wired into the runtime.
- Release gate status is promotable and logs to `~/NEXUS/ERGON.md`.
- The live repo has a canonical folder catalog and drift guard.

Relevant evidence surfaces:
- `scripts/catalog_guard.py`
- `scripts/catalog_sync.py`
- `specs/invariants.md`
- `omega/ingest.py`
- `omega/memory.py`
- `omega/telemetry.py`
- `tools/meta_generator.py`
- `tools/pub_packager.py`
- `evals/test_conformance.py`
- `web/`
- `runtime/`

## What Still Prevents "Certified Undeniable"

The remaining gaps are not "more features." They are proof-quality gaps:

1. Invariants are canonical, but not yet the first thing every new artifact is forced to satisfy.
2. Ingest still has multiple historical paths and credential surfaces.
3. Memory utility is present, but retrieval evidence is not yet the primary driver of retention decisions.
4. Skills and generators exist, but not every scaffold is enforced eval-first.
5. Secrets discipline is improving, but scaffolding should make hardcoded credentials impossible by construction.
6. The release gate is verified, but certification should require the gate plus post-deploy route health and evidence logging.

## Certification Tracks

### 1. Invariants-First Canonicalization

Goal:
- Make `specs/invariants.md` the root of behavioral truth for new work.

Implementation moves:
- Require every new skill, tool, route, and data model to cite one or more invariants.
- Add a lightweight invariant coverage table to each major subsystem index.
- Fail new scaffold generation if no invariant mapping is provided.

Primary files:
- `specs/invariants.md`
- `tools/meta_generator.py`
- `tools/pub_packager.py`
- `CLAUDE.md`

Success criteria:
- New artifacts cannot be introduced without an explicit invariant mapping.
- Eval failures can be traced back to missing or violated invariants, not just "bad output."

### 2. Unified Ingest Pipeline

Goal:
- Replace historical ingest sprawl with one canonical ingestion command and one checkpoint format.

Implementation moves:
- Collapse ingest entry points into a single orchestrator, with source-specific adapters only.
- Standardize checkpoint and journaling schema.
- Route all ingest mutations through one provenance model.

Primary files:
- `omega/ingest.py`
- `tools/ingest_cli.py`
- `specs/memory_system.md`
- `schemas/`

Success criteria:
- New ingest sources add adapters, not new pipelines.
- Every ingest event has one provenance shape and one retry shape.

### 3. Telemetry-Backed Memory Utility

Goal:
- Make retrieval evidence, not guesswork, determine memory hardening and pruning.

Implementation moves:
- Add retrieval counters and last-retrieved timestamps to the memory schema.
- Increment those counters on retrieval.
- Use retrieval evidence to drive retention and pruning thresholds.

Primary files:
- `omega/memory.py`
- `omega/telemetry.py`
- `specs/memory_system.md`
- `evals/test_agent_telemetry.py`

Success criteria:
- Memory utility can answer "what has actually been used?"
- Pruning policy is evidence-based rather than importance-only.

### 4. Eval-First Scaffolding

Goal:
- Every new skill, route, or generator is defined by tests before implementation becomes canonical.

Implementation moves:
- Add minimal eval assertions before adding new scaffolds.
- Require the skill registry or generator to reference an eval file.
- Make eval creation part of the same workflow as skill creation.

Primary files:
- `evals/`
- `tools/meta_generator.py`
- `tools/pub_packager.py`
- `catalog/registry.json`

Success criteria:
- A scaffold without a test suite is not considered production-grade.
- Evaluation coverage grows with the skill surface.

### 5. Credential-First Scaffolding Discipline

Goal:
- Eliminate hardcoded secrets as a class of possible mistakes.

Implementation moves:
- Enforce `os.getenv(...)` or equivalent for generated artifacts.
- Add a check that scans generated files for literal credential patterns.
- Keep secret loading in environment-specific files and vaults only.

Primary files:
- `tools/meta_generator.py`
- `tools/pub_packager.py`
- `canon/SECURITY_AND_PRIVACY.md`
- `policies/`

Success criteria:
- Generated code cannot accidentally embed keys or tokens.
- Secret handling becomes a scaffold property, not a cleanup task.

### 6. Release Gate + Post-Deploy Evidence

Goal:
- Treat the release gate as necessary, but not sufficient.

Implementation moves:
- Gate promotion on build, smoke, route health, non-empty route responses, and ERGON logging.
- Preserve a deploy-time evidence bundle for every promoted build.
- Make the gate output machine-readable and comparable over time.

Primary files:
- `web/`
- `runtime/`
- `evals/`
- `output/`
- `~/NEXUS/ERGON.md`

Success criteria:
- Promotion is blocked unless the deployment proves itself live.
- Every release leaves behind an evidence trail that can be audited later.

## Recommended Execution Order

1. Make the invariants-first mapping explicit in generators and scaffolds.
2. Consolidate ingest into one canonical path.
3. Add telemetry-backed memory utility columns and counters.
4. Enforce eval-first skill and generator creation.
5. Harden credential handling in all generated surfaces.
6. Extend the release gate with post-deploy route-health checks and evidence logging.

## "Certified Undeniable" Criteria

OmegA qualifies as operationally certified when all of the following are true:
- Canonical invariants exist and every new surface maps to them.
- Release gate passes in CI and in live deployment.
- Route health is verified post-deploy and non-empty responses are enforced.
- Ingest has a single canonical pipeline.
- Memory utility is measured by actual retrieval evidence.
- Skills and generators are eval-first.
- Secret handling is scaffolded safely by default.
- Every certification run appends structured evidence to `~/NEXUS/ERGON.md`.

## Practical Interpretation

The current system is already real.
The next phase is to make it:
- harder to drift,
- easier to verify,
- simpler to reproduce,
- and more difficult to dispute.

