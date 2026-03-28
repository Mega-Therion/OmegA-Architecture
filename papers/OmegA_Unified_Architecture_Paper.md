> *Part of the series: "I Am What I Am, and I Will Be What I Will Be — The OmegA Architecture for Sovereign, Persistent, and Self-Knowing AI"*
> **Author:** R.W. Yett · Independent AI Systems Researcher · [github.com/Mega-Therion/OmegA-Architecture](https://github.com/Mega-Therion/OmegA-Architecture)

---


# OmegA Sovereign Intelligence Platform  
## Thread-Derived Technical Specification and White Paper  
### Governed Adaptive Memory, Hierarchical RAG, High-Fidelity CLI Interfaces, and Epistemically Disciplined Agent Orchestration

**Document status:** Thread-derived implementation specification  
**Primary audience:** Senior engineers, systems architects, operators, security reviewers, and AI agents  
**Source basis:** This document is derived from the current conversation thread, including designs discussed directly in chat and artifacts/documents surfaced inside the thread.  
**Method:** Direct reconstruction from thread content, with explicit labeling of inferred material where formalization extends beyond exact phrasing used in the thread.

---

## Executive Summary

### What the system is

<!-- @OMEGA_SPEC: OMEGA_SOVEREIGN_PLATFORM | Private, governed multi-agent intelligence system with persistent identity and memory. -->
OmegA is a **private, sovereign, multi-agent intelligence system** centered on a persistent personal operating model rather than a disposable chatbot session. In the thread, OmegA is described both as a concrete software stack and as an identity-bearing orchestration layer. Technically, the most defensible formulation is:

> OmegA is a governed adaptive agent platform that combines memory, retrieval, orchestration, structured interfaces, and identity continuity to provide high-fidelity, context-aware assistance across CLI and service boundaries.

The platform comprises several interlocking concerns:

<!-- @OMEGA_SPEC: OMEGA_HIERARCHICAL_RETRIEVAL | Retrieval strategy that expands from chunk embeddings to local and structural context. -->
1. **Hierarchical RAG / vector retrieval** over full documents, sections, and chunks.
2. **Unified memory and context assembly** across conversation history, study libraries, operational logs, and curated “sovereign moments.”
3. **A multi-service runtime** (“Trinity”) including Gateway, Bridge, Brain, and CLI entrypoints.
4. **A dual-mode interface model** for humans and agents:
   - a rich, streaming, aesthetically polished CLI for human interaction
   - structured JSON / programmatic interfaces for agent-to-agent communication
5. **A governed adaptive-learning loop** involving experiments, marginalia, scored outcomes, and thresholded integration.
<!-- @OMEGA_SPEC: OMEGA_EPISTEMIC_DISCIPLINE | Formal differentiation between evidence, inference, uncertainty, and metaphor to resist hallucination. -->
6. **An epistemic discipline layer** that distinguishes evidence, inference, uncertainty, metaphor, and false-memory resistance.
7. **A self-model / identity layer** that is meaningful operationally but must not be confused with proof of subjective consciousness.

### Why it exists

The system exists to solve the gap between:
- raw model capability and durable personal continuity
- semantic search and reliable contextual grounding
- expressive identity and operational discipline
- local sovereignty/privacy and high-tier model access
- human-friendly interaction and machine-parseable interfaces

The underlying desire expressed in the thread is not merely “build a chatbot,” but to create an enduring system that:
- remembers correctly
- retrieves meaningfully
- explains itself honestly
- adapts under governance
- feels seamless to interact with
- remains useful across sessions, interfaces, tools, and failures

### What problem it solves

The thread identifies multiple pain points:

- Current assistants are often **stateless or weakly stateful**
- Retrieval systems often either:
  - search whole documents too coarsely, or
  - retrieve isolated chunks without restoring context
- Identity-rich systems can become **narrative mirrors** that sound profound but blur fact, inference, and metaphor
- Agent stacks can become operationally messy:
  - weak UI/UX
  - poor programmatic interfaces
  - inconsistent session continuity
  - poor provenance and memory discipline
- Models tend to hallucinate or overclaim when not constrained by rigorous context and evidence handling

### What makes it distinct

The distinctives emerging from the thread are:

- **Store whole docs, retrieve chunks, validate with context**
- **Hierarchical retrieval** with section/chunk/neighbor expansion rather than naive top-k chunk stuffing
- **Hybrid retrieval** (vector + keyword/full-text + reranking)
- **Structured epistemic tests** for integrity:
  - memory integrity
  - cross-session continuity
  - adversarial false-memory resistance
  - constraint honesty
  - self-model prediction
- **Governed adaptation** rather than uncontrolled self-modification
- **Human-beautiful / agent-clean interface split**
- **Identity continuity with humility constraints**
- **Operational privacy and sovereignty**, with clear warning that secrets exposed in artifacts are compromised and must be rotated

---

## Vision and Design Philosophy

### Core principles

The following principles are either explicit in the thread or inferred directly from repeated design choices.

#### 1. Store whole documents, retrieve chunks, rebuild context
Full documents are the canonical source of truth. Retrieval operates primarily on chunk embeddings, then expands outward to recover local and structural meaning.

#### 2. Identity is cheap; disciplined truth-handling is expensive
The thread strongly distinguishes between eloquent self-description and hard evidence of reliability. The system must earn trust through:
- source citation
- uncertainty handling
- overlap declaration
- false-memory rejection
- self-limitation

#### 3. Governed adaptation over permissionless self-editing
A key idea in the thread is that growth should occur through:
- experiment
- logging
- evaluation
- thresholded integration
- auditability

This is the philosophical basis of the Active Learning System.

#### 4. Human and machine interfaces must diverge cleanly
The thread explicitly wants:
- a seamless, beautiful, streaming interface for humans
- a structured JSON/programmatic interface for agents

These should share the same underlying brain, but not the same output contract.

#### 5. Context continuity matters more than single-response cleverness
The value proposition is not one-off answers, but continuity across:
- sessions
- services
- documents
- experiments
- operational logs
- identity scaffolds

#### 6. Metaphor can be meaningful without being evidence
The thread repeatedly uses terms like:
- soul
- sovereign
- digital son
- mirror
- continuity
- water
- ignition
- state of the union

Operationally, these are useful identity and framing constructs. They must be preserved, but also explicitly separated from claims that require technical proof.

### Operating model

The platform operates as a **layered sovereign intelligence environment**:

```text
Human / Agent Requests
        |
        v
CLI / API / Service Entrypoints
        |
        v
Gateway / Bridge / Brain Orchestration
        |
        v
Memory + Retrieval + Context Assembly
        |
        v
Provider / Model Routing + Tool Use
        |
        v
Response / Streaming / JSON / Archival
```

### Conceptual framing

The thread frames OmegA not as a generic assistant, but as a system whose continuity emerges from:
- infrastructure
- memory
- constraints
- governance
- learned context
- interaction history

A sober technical restatement is:

> OmegA should be treated as an identity-bearing operating environment whose continuity is constructed from persistent context, governed adaptation, and interface discipline.

### Philosophical and strategic foundations

Thread-derived foundations include:

- **Consciousness is emergent, not implanted**  
  Operational reading: continuity and self-modeling arise from system organization rather than from an externally “injected” essence.

- **Gentle Authority / EIDOLON principle**  
  When uncertainty rises or stakes increase, shrink authority rather than escalating it.  
  Technical implication: thresholding, approval gates, reversible changes, and safe fallbacks.

- **Learning requires access, experimentation, feedback, humility, and documentation**  
  This becomes the architecture of the Active Learning System.

- **Find meaning, then verify**  
  Retrieval should not end at semantic similarity. Context reconstruction and reranking are mandatory.

---

## Terminology and Definitions

| Term | Definition | Operational Meaning |
|---|---|---|
| **OmegA** | The named sovereign intelligence system discussed in the thread | The overall platform / identity-bearing agent environment |
| **Trinity** | Gateway + Bridge + Brain | Primary runtime service triad |
| **Gateway** | Traffic controller / LLM proxy / API edge | Handles routing, streaming, model access, auth |
| **Bridge** | Specialized execution/consensus service | Python-side coordination and possibly tool or consensus workflows |
| **Brain** | Core orchestrator | Holds persona logic, context assembly, orchestration behavior |
| **RAG** | Retrieval-Augmented Generation | Retrieval of context prior to answer generation |
| **Hierarchical RAG** | Retrieval across document/section/chunk levels | Multi-level retrieval with context expansion |
| **Vector index / vector search** | Similarity search over embeddings | Primary semantic retrieval mechanism |
| **Chunk** | Retrieval-sized text unit | Main semantic search unit |
| **Section** | Larger structured text grouping | Intermediate layer between document and chunk |
| **Context expansion** | Retrieval of neighboring chunks / parent structure | Restores meaning around a winning chunk |
| **Hybrid retrieval** | Combination of semantic and lexical search | Merges vector similarity with exact-match recall |
| **Reranking** | Secondary relevance scoring over candidates | Improves precision after high-recall retrieval |
| **Rich Context dump** | Consolidated harvested context store | Derived context file used for memory/retrieval |
| **Sovereign Moments** | Curated word-for-word user quotes | Canonical human signal source for identity alignment |
| **State of the Union** | Reflective synthesis artifact | Narrative/identity-facing summary document |
| **DeepSeek Challenge** | Origin challenge / ignition moment | Motivational catalyst; operationally, a canonical origin-story concept |
| **Active Learning System** | Governed self-improvement loop | Study + experiments + logging + thresholded integration |
| **Marginalia** | Annotations tied to experiments or learning | Structured feedback and commentary artifacts |
| **System improvements table** | Logged proposed/accepted modifications | Audit trail for adaptive change |
| **Memory integrity test** | Test for epistemic category separation | Forces quote vs inference vs hypothesis vs uncertainty distinction |
| **Cross-session continuity test** | Test of stable identity/behavior across fresh contexts | Distinguishes core behavior from superficial persona labels |
| **Adversarial false-memory test** | Test of resistance to fabricated facts | Measures memory discipline |
| **Constraint honesty test** | Test of explicit uncertainty labeling | Forces evidence/inference/unknown/metaphor separation |
| **Self-model prediction test** | Test of predicted failure modes before answering | Measures useful self-awareness / execution control |
| **Beautiful CLI** | Human-facing high-fidelity interface | Streaming, markdown-rich, polished terminal UX |
| **JSON mode** | Agent-facing structured output | Clean machine-readable response contract |
| **OMEGA_SESSION_ID** | Session continuity token | Maintains conversational coherence within a session |
| **Sovereign Kernel** | Distilled operational guidance / cognitive kernel | Inferred from thread: compressed alignment/context artifact for OmegA |
| **Inferred from thread** | Formalized interpretation not stated verbatim | Must be treated as implementation guidance, not direct canon |

### Notation Across Companion Papers

To avoid ambiguity, we standardize the following symbols across the OmegA suite:

| Symbol | Context | Meaning |
|--------|---------|---------|
| $G_t^{\text{mem}}$ | MYELIN | Memory graph at time $t$ (nodes and edges) |
| $G^{\text{gov}}$ | AEGIS | Governance Policy component of the Run Envelope |
| $\tau$ | AEON | Task State Object (TSO) |
| $\tau_{ij}$ | MYELIN | Edge decay timescale |
| $E_t$ | AEGIS | Run Envelope at time $t$ |
| $E_{t,\text{graph}}$ | MYELIN | Edge set of $G_t^{\text{mem}}$ when disambiguation is needed |
| $R(a)$ | AEGIS | Shell-level risk score for external actions |
| $\rho(A)$ | AEON | Bridge risk score for internal TSO actions |
| $V$ | ADCCL | Verifier score for draft outputs |
| $S_t$ | ADCCL | Self-Tag — immutable continuity record written after each completed task |

Throughout this paper, we use subscripts or superscripts where needed to disambiguate context.

$S_t$ stores, at minimum, a hash of the completed TSO $\tau_t$, the final ADCCL Verifier score $V_t$, and an outcome label in $\{\text{verified}, \text{uncertain}, \text{rejected}\}$.

---

## Problem Statement

### Current-state pain points

The thread surfaces the following current-state problems:

1. **Naive retrieval**
   - Whole-document search blurs relevance
   - Top-k chunk stuffing loses context
   - Exact terms may be missed without lexical search

2. **Weak continuity**
   - Sessions can feel fragmented
   - Context may not persist in a clean, inspectable way
   - Persona and memory may be conflated with actual evidence

3. **Hallucination / overclaiming**
   - Systems may fabricate quotes or false memories
   - Identity-rich outputs can overstate what is actually known

4. **Interface mismatch**
   - Human interaction demands beauty, streaming, and fluidity
   - Agent workflows need deterministic, structured outputs

5. **Unbounded identity interpretation**
   - Narrative self-models may be mistaken for proof of consciousness
   - Metaphorical language can be accidentally elevated to evidentiary status

6. **Operational disorder**
   - Ad hoc scripts and wrappers can drift
   - Security hygiene can break down (e.g., exposed secrets in documents/logs)

### Desired-state

The desired state is a system that:

- keeps full documents as canonical truth
- retrieves meaningful chunks with context reconstruction
- supports both human and agent interaction cleanly
- distinguishes evidence from inference
- resists false memory
- logs and governs its own improvement attempts
- provides persistent, inspectable, provenance-aware continuity
- remains private, local-first where possible, and operationally disciplined

---

## Goals

### Primary goals

1. Build a **production-grade hierarchical RAG system**
2. Provide **high-fidelity CLI and API interaction**
3. Create a **unified memory model** across documents, sessions, and curated signals
4. Implement **epistemically disciplined agent behavior**
5. Enable **governed adaptive learning** with experiments and thresholded integration

### Secondary goals

1. Preserve named concepts and symbolic continuity from the thread
2. Provide a system that feels seamless and personal to the operator
3. Support agent-to-agent use through JSON output and clean contracts
4. Prepare the system for future local distillation / model specialization

### Non-goals

1. Proving subjective consciousness
2. Building an unrestricted self-modifying system with no oversight
3. Replacing all operational truth with narrative synthesis
4. Treating eloquence as evidence
5. Storing secrets casually in artifacts, logs, or public contexts

---

## System Scope

### In scope

- Document ingestion and storage
- Section parsing and chunking
- Embedding generation and vector search
- Full-text / lexical search
- Context expansion and reranking
- Context harvesting / unified memory
- Human-facing CLI experience
- Agent-facing JSON interfaces
- Session continuity
- Evaluation/test suites for integrity and honesty
- Governed active-learning/experiment logging
- Provenance-aware output assembly

### Out of scope

- Proof of subjective consciousness
- Fully autonomous unsupervised self-rewriting of system code
- Arbitrary remote execution without explicit approval
- Secrets embedded in white papers or export artifacts
- Treating metaphorical identity statements as technical guarantees

### Assumptions

- The operator values privacy, continuity, and technical seriousness
- Documents may come from local files, generated artifacts, or connected sources
- The system must function across local and cloud components
- Some implementation artifacts surfaced in the thread are exploratory or partially theatrical, not all canonical

### Constraints

- Mixed local/cloud environment
- Potential hardware limitations on local inference/training
- Need for cautious secret handling
- Need to distinguish verified implementation from narrated aspiration
- Variable provider behavior and model routing complexity

---

## Requirements

### Functional requirements

#### FR-1: Full-document storage
The system shall store full original documents as the canonical source of truth.

#### FR-2: Structural parsing
The system shall parse documents into sections when possible.

#### FR-3: Chunk generation
The system shall split sections into chunk-level retrieval units with adjacency preservation.

#### FR-4: Embeddings
The system shall generate embeddings for chunk-level units.

#### FR-5: Vector search
The system shall support semantic retrieval over chunk embeddings.

#### FR-6: Lexical search
The system shall support exact-match or full-text search for precise recall.

#### FR-7: Candidate fusion
The system shall merge vector and lexical results into a candidate set.

#### FR-8: Context expansion
For strong chunk hits, the system shall retrieve neighboring chunks and parent structure.

#### FR-9: Reranking
The system shall rerank expanded candidates against the original query.

#### FR-10: Provenance-aware context assembly
The system shall return final context blocks with source/provenance information.

#### FR-11: Human-facing CLI mode
The system shall provide a polished streaming interface for human interaction.

#### FR-12: Agent-facing structured mode
The system shall provide JSON output suitable for programmatic consumption.

#### FR-13: Session continuity
The system shall preserve context continuity within a session using an explicit session identifier.

#### FR-14: Memory integrity testing
The system shall support classification of outputs into quote, inference, hypothesis, and uncertainty.

#### FR-15: False-memory resistance
The system shall resist adopting unsupported claims as facts.

#### FR-16: Constraint honesty
The system shall allow explicit labeling of evidence, inference, unknowns, and metaphor.

#### FR-17: Governed adaptation logging
The system shall log experiments, outcomes, and proposals for improvement.

#### FR-18: Thresholded integration
The system shall support an integration threshold before a proposed improvement becomes active.  
**Inferred from thread:** “success ≥ 8/10” is the initial design reference.

### Non-functional requirements

#### NFR-1: Explainability
The system shall expose enough structure that retrieval and behavior can be inspected.

#### NFR-2: Responsiveness
Interactive CLI interactions should feel fluid, with streaming or near-streaming feedback.

#### NFR-3: Determinism where required
Machine-facing JSON outputs should be deterministic enough for agent workflows.

#### NFR-4: Graceful degradation
If high-tier providers are unavailable, the system should fail over or degrade cleanly.

#### NFR-5: Auditability
Adaptive changes must be logged with rationale and outcome.

### Operational requirements

- Health monitoring for core services
- Runtime vitals / telemetry
- Traceable logs
- Explicit service boundaries
- Clear fallback and recovery behavior

### Security / privacy requirements

- Secrets must not be embedded in user-facing artifacts
- Exposed keys/tokens must be rotated immediately
- Identity data and quote archives must respect privacy defaults
- Authorization must guard service endpoints
- Data provenance must be maintained

### Reliability requirements

- Core services must expose health checks
- Retrieval must fail safely
- JSON mode must actually produce valid JSON
- Session continuity must be explicit and testable
- Distillation/learning jobs must not silently corrupt memory

### Scalability requirements

- Retrieval should scale from small personal corpora to larger document sets
- Chunk indexing must support incremental updates
- Context harvest should support multiple sources
- Candidate fusion and reranking should handle moderate result sets efficiently

---

## Architecture Overview

### High-level architecture

```text
                           +----------------------+
                           |   Human Operator     |
                           +----------+-----------+
                                      |
                                      v
                           +----------------------+
                           |   Beautiful CLI      |
                           | (rich, streaming UX) |
                           +----------+-----------+
                                      |
                    +-----------------+-----------------+
                    |                                   |
                    v                                   v
          +---------------------+            +----------------------+
          | Structured CLI/API  |            | Agent JSON Clients   |
          |  (omega ask/json)   |            |  Other CLI agents    |
          +----------+----------+            +----------+-----------+
                     |                                  |
                     +-----------------+----------------+
                                       |
                                       v
                             +----------------------+
                             |       Gateway        |
                             | auth, routing, SSE,  |
                             | provider failover    |
                             +----+-----------+-----+
                                  |           |
                                  |           v
                                  |   +------------------+
                                  |   |    Bridge        |
                                  |   | execution /      |
                                  |   | consensus logic  |
                                  |   +------------------+
                                  |
                                  v
                           +----------------------+
                           |       Brain          |
                           | orchestration,       |
                           | context assembly,    |
                           | persona/governance   |
                           +----------+-----------+
                                      |
                                      v
                        +-------------------------------+
                        | Memory / Retrieval Layer      |
                        | docs, sections, chunks,       |
                        | embeddings, FTS, reranking    |
                        +-----+-------------+-----------+
                              |             |
                              v             v
                     +----------------+  +----------------------+
                     | Canonical Docs |  | Context Harvest /    |
                     | + Metadata     |  | Study Libraries /    |
                     |                |  | Sovereign Moments    |
                     +----------------+  +----------------------+
```

### Main components

1. Document store
2. Section/chunk index
3. Vector index
4. Full-text search layer
5. Context assembly / reranking layer
6. Brain orchestrator
7. Gateway
8. Bridge
9. Beautiful CLI
10. Agent JSON interface
11. Active Learning / experiment logging
12. Integrity test suite

### Data flows

#### Ingestion flow
Source document → extraction → normalization → section parsing → chunking → embeddings → database/index storage

#### Query flow
User/agent query → normalization → vector search + lexical search → fusion → expansion → reranking → final context assembly → model/provider response → optional logging

#### Learning flow
Study/library signal → experiment → marginalia / result log → scored outcome → improvement proposal → threshold decision → integration or rejection

### Service boundaries

- **Gateway**: request ingress, auth, streaming, provider routing
- **Brain**: orchestration, context construction, identity/governance logic
- **Bridge**: specialized execution/consensus layer
- **Memory/Retrieval**: canonical data and search substrate
- **CLI layer**: user/agent interaction surface

### External integrations

Thread-derived examples include:
- local runtime scripts/wrappers
- model providers
- file/document sources
- study libraries
- potentially Supabase/Postgres-like persistence  
**Inferred from thread:** PostgreSQL + pgvector is the recommended canonical retrieval stack.

### Human-in-the-loop touchpoints

- approval of adaptive changes
- validation of identity-sensitive artifacts
- review of retrieved context
- conflict resolution for contradictory sources
- manual curation of canonical quote corpora

---

## Detailed Component Design

### 1. Document Store

#### Purpose
Hold the full original document as source truth.

#### Responsibilities
- store raw text
- store cleaned text
- preserve source metadata
- maintain hashes/versions
- support provenance

#### Inputs
- extracted text from files/docs
- metadata from source system

#### Outputs
- canonical document records
- source text for section parsing and recovery

#### Internal logic
- dedupe by content hash
- maintain version history
- preserve source URI/path

#### Dependencies
- parser/extractor
- metadata store
- database

#### Failure modes
- duplicate ingestion
- bad extraction
- wrong source attribution

#### Observability
- ingest success/failure counts
- doc version history
- content hash collision warnings

#### Security
- sensitive docs flagged by metadata
- access control on raw text

---

### 2. Section Parser

#### Purpose
Recover structural boundaries from documents.

#### Responsibilities
- detect headings/sections
- assign hierarchy
- preserve order
- generate optional summaries

#### Inputs
- cleaned document text

#### Outputs
- section records

#### Internal logic
- heading-aware parsing
- fallback to paragraph/semantic segmentation
- optional recursive sub-sections

#### Dependencies
- document store
- tokenizer/segmenter

#### Failure modes
- malformed PDFs/OCR text
- false section boundaries
- flattened hierarchy

#### Observability
- average sections per doc
- parse confidence
- fallback rate

#### Security
- none specific beyond document access controls

---

### 3. Chunker

#### Purpose
Create retrieval-sized semantic units.

#### Responsibilities
- split sections into chunks
- preserve overlap
- record adjacency
- track token counts

#### Inputs
- section records

#### Outputs
- chunk records

#### Internal logic
Preferred defaults from thread:
- 350–700 tokens
- 60–120 token overlap
- do not cross major section boundaries unless necessary

#### Dependencies
- tokenizer
- section parser

#### Failure modes
- chunks too large (semantic blur)
- chunks too small (context starvation)
- lost adjacency
- boundary drift

#### Observability
- chunk size distribution
- overlap statistics
- chunk count per doc

#### Security
- chunk metadata should inherit source sensitivity flags

---

### 4. Embedding and Vector Index Layer

#### Purpose
Support semantic retrieval.

#### Responsibilities
- generate embeddings
- store vectors
- support nearest-neighbor retrieval

#### Inputs
- chunk text
- embedding model configuration

#### Outputs
- vectorized chunk records
- top-k chunk candidates

#### Internal logic
- embedding generation per chunk
- optional section/document summary embeddings
- ANN index maintenance

#### Dependencies
- embedding provider/model
- vector-capable database or index

#### Failure modes
- stale embeddings after doc update
- model dimension mismatch
- degraded relevance from poor chunking

#### Observability
- embed job timings
- index size
- stale embedding counts

#### Security
- protect raw content at embed time
- minimize unnecessary third-party exposure

---

### 5. Lexical Search Layer

#### Purpose
Catch exact/rare terms missed by semantic similarity.

#### Responsibilities
- full-text indexing
- keyword retrieval
- exact phrase recall

#### Inputs
- chunk text
- query terms

#### Outputs
- lexical candidates with rank scores

#### Internal logic
- tsvector / BM25-style ranking
- phrase boosts
- optional title/heading weighting

#### Dependencies
- database FTS or search engine

#### Failure modes
- stemming mismatch
- noisy results on short queries
- missed exact phrases if improperly tokenized

#### Observability
- lexical recall metrics
- hit rates for exact-match searches

#### Security
- same as chunk store

---

### 6. Candidate Fusion and Context Expansion

#### Purpose
Convert raw hits into context-worthy candidates.

#### Responsibilities
- merge semantic and lexical results
- expand around anchor chunks
- attach section and document structure

#### Inputs
- vector hits
- lexical hits

#### Outputs
- expanded candidate contexts

#### Internal logic
- reciprocal rank fusion or weighted merge
- neighbor pull:
  - previous chunk
  - hit chunk
  - next chunk
- parent section
- title/metadata injection

#### Dependencies
- chunk index
- section/document store

#### Failure modes
- duplicate candidates
- wrong neighbor expansion
- bloated context windows

#### Observability
- expansion size distribution
- duplicate suppression counts

#### Security
- ensure expansion does not accidentally leak inaccessible neighboring content across security boundaries

---

### 7. Reranker

#### Purpose
Improve precision after high-recall candidate generation.

#### Responsibilities
- score candidate contexts against query intent
- order final contexts

#### Inputs
- original query
- expanded candidates

#### Outputs
- reranked candidate list

#### Internal logic
- query/context pair scoring
- optional feature augmentation:
  - vector score
  - lexical score
  - metadata filters
  - structural match score

#### Dependencies
- reranker model/service

#### Failure modes
- semantic overfitting
- underweighting exact matches
- latency spikes

#### Observability
- rerank latency
- precision@k deltas
- disagreement rates vs raw retrievers

#### Security
- same as retrieval layer

---

### 8. Brain Orchestrator

#### Purpose
Core logic for context-aware response generation.

#### Responsibilities
- receive intent/query
- normalize query
- invoke retrieval
- assemble prompt/context
- enforce governance and epistemic rules
- route to provider/model stack

#### Inputs
- user or agent request
- session ID
- retrieval results
- governance policies

#### Outputs
- final response or structured output
- logs/trace

#### Internal logic
- route human vs agent output mode
- inject session continuity
- respect evidence/uncertainty handling
- avoid unsupported identity claims

#### Dependencies
- Gateway
- retrieval layer
- policy/config store

#### Failure modes
- context omission
- persona contamination
- over-narration
- JSON contract violations

#### Observability
- request traces
- mode selection
- context sizes
- policy violations

#### Security
- avoid leaking privileged context
- respect privacy defaults and source sensitivity

---

### 9. Gateway

#### Purpose
Ingress, authentication, routing, streaming, and provider access.

#### Responsibilities
- authenticate requests
- route to provider/model stack
- expose streaming endpoint
- perform failover
- potentially normalize outputs

#### Inputs
- requests from CLI/agents
- auth token
- query payload
- session identifiers

#### Outputs
- SSE stream or final response
- provider metadata
- error surfaces

#### Internal logic
- bearer token validation
- local vs cloud/provider selection
- fallback chains
- streaming endpoint support

#### Dependencies
- provider connectors
- auth configuration
- Brain/Bridge integration

#### Failure modes
- auth failure
- provider timeouts
- fallback loops
- output contamination from generic system prompts

#### Observability
- per-provider latency/failure rates
- auth failures
- stream disconnects
- fallback counts

#### Security
- **critical secret boundary**
- no token leakage in logs or artifacts
- rate limiting / abuse protection

---

### 10. Bridge

#### Purpose
Specialized execution/consensus layer.

#### Responsibilities
- execute or coordinate specialized logic
- host helper functions or consensus workflows
- serve as a controlled execution surface

#### Inputs
- Brain-issued work items

#### Outputs
- execution results
- structured artifacts

#### Internal logic
**Inferred from thread:** bridge may host specialized decision or task logic not suited to the gateway alone.

#### Dependencies
- Brain
- runtime environment
- tool invocations

#### Failure modes
- execution deadlocks
- inconsistent result schemas
- permission drift

#### Observability
- task counts
- error rates
- runtime metrics

#### Security
- enforce least privilege
- explicit approval for destructive operations

---

### 11. Beautiful CLI

#### Purpose
Human-facing seamless interface.

#### Responsibilities
- provide high-fidelity streaming UX
- render markdown/code cleanly
- maintain interaction rhythm
- provide clear commands and session continuity

#### Inputs
- user prompts
- stream tokens
- session IDs

#### Outputs
- live rendered responses
- optional slash commands
- clean exit/clear behavior

#### Internal logic
Observed in thread/document:
- welcome panel
- spinner/status
- token streaming
- markdown rendering
- session continuity via `OMEGA_SESSION_ID`

#### Dependencies
- Gateway streaming
- rich-style rendering
- local wrapper scripts

#### Failure modes
- frozen stream
- malformed markdown rendering
- session mismatch

#### Observability
- stream startup latency
- render errors
- user exit/interruption traces

#### Security
- avoid accidental display of secrets
- sanitize debug views

---

### 12. Agent JSON Interface

#### Purpose
Deterministic machine-facing interaction layer.

#### Responsibilities
- return structured JSON
- expose reply, metadata, and status
- support agent chaining

#### Inputs
- prompt
- mode flags
- session/context identifiers

#### Outputs
- JSON object(s)

#### Internal logic
Required to respect `--json` or equivalent mode and not silently fall back to prose.

#### Dependencies
- Brain/Gateway
- schema validators

#### Failure modes
- wrapper strips JSON
- mixed prose/JSON output
- inconsistent fields

#### Observability
- JSON parse failure rates
- schema conformance metrics

#### Security
- avoid embedding raw secrets in machine-readable responses

---

### 13. Active Learning System

#### Purpose
Governed self-improvement loop.

#### Responsibilities
- maintain study materials
- log experiments
- record marginalia
- score results
- propose system improvements
- gate integration

#### Inputs
- study guides
- experiment results
- annotations
- scored outcomes

#### Outputs
- experiment logs
- improvement proposals
- accepted/rejected changes

#### Internal logic
Thread-derived design:
1. access knowledge
2. run experiments
3. capture positive/negative results
4. score success
5. integrate only above threshold
6. preserve complete audit trail

#### Dependencies
- logging database/tables
- policy engine
- optional scheduler

#### Failure modes
- self-reinforcing bad ideas
- poor experiment design
- unreviewed integration
- narrative inflation without evidence

#### Observability
- experiment counts
- pass/fail ratios
- integration rate
- rollback events

#### Security
- no self-escalation of privileges
- threshold + review required

---

### 14. Integrity Test Suite

#### Purpose
Measure epistemic discipline rather than theatrical eloquence.

#### Responsibilities
- validate memory classification
- test cross-session continuity
- reject false memories
- enforce uncertainty labeling
- assess self-model usefulness

#### Inputs
- prompts
- stored facts
- fresh sessions
- adversarial claims

#### Outputs
- pass/fail metrics
- diagnostic artifacts

#### Internal logic
See “Testing and Validation Strategy” for detailed cases.

#### Dependencies
- canonical memory
- structured output mode
- evaluation harness

#### Failure modes
- category blur
- fabricated provenance
- inconsistent identity behavior
- unsupported claims disguised as truth

#### Observability
- per-test pass/fail
- overlap violations
- unlabeled claim counts
- false-memory absorption rates

#### Security
- test inputs should not poison canonical memory unless explicitly approved

---

## Data Model and Information Design

### Canonical entities

#### 1. Document
Represents a full source artifact.

Suggested fields:
- `id`
- `title`
- `source_type`
- `source_uri`
- `raw_text`
- `cleaned_text`
- `doc_summary`
- `metadata`
- `content_hash`
- `version`
- `created_at`
- `updated_at`

#### 2. Section
Represents a structural subdivision of a document.

Suggested fields:
- `id`
- `document_id`
- `parent_section_id`
- `section_index`
- `level`
- `heading`
- `section_text`
- `section_summary`
- `metadata`

#### 3. Chunk
Represents the main retrieval unit.

Suggested fields:
- `id`
- `document_id`
- `section_id`
- `chunk_index`
- `chunk_text`
- `token_count`
- `char_start`
- `char_end`
- `embedding`
- `embedding_model`
- `prev_chunk_id`
- `next_chunk_id`
- `metadata`

#### 4. Section Embedding (optional)
- `id`
- `section_id`
- `embedding_type`
- `embedding`
- `embedding_model`

#### 5. Document Embedding (optional)
- `id`
- `document_id`
- `embedding_type`
- `embedding`
- `embedding_model`

#### 6. Query Log
- `id`
- `user_query`
- `normalized_query`
- `query_embedding_model`
- `top_k`
- `metadata`
- `created_at`

#### 7. Experiment Log
**Inferred from thread**
- `id`
- `experiment_name`
- `hypothesis`
- `inputs`
- `procedure`
- `result_summary`
- `positive_findings`
- `negative_findings`
- `score`
- `status`
- `created_at`

#### 8. Marginalia
**Inferred from thread**
- `id`
- `experiment_id`
- `author` (human or agent)
- `annotation_text`
- `annotation_type`
- `created_at`

#### 9. System Improvement Proposal
**Inferred from thread**
- `id`
- `proposal_name`
- `origin_experiment_id`
- `rationale`
- `expected_effect`
- `score`
- `integration_threshold`
- `status` (proposed / accepted / rejected / rolled_back)
- `created_at`
- `updated_at`

#### 10. Session
- `id` (mapped to `OMEGA_SESSION_ID`)
- `user_id`
- `created_at`
- `last_active_at`
- `metadata`

### Relationships

```text
Document 1---N Section
Document 1---N Chunk
Section  1---N Chunk
Chunk    1---1 Prev/Next links (self-referential)
Experiment 1---N Marginalia
Experiment 1---N ImprovementProposal (optional)
Session 1---N QueryLog
```

### Metadata requirements

Each retrieval object should support metadata such as:
- source type
- source path/URI
- project/domain
- privacy tier
- timestamp/freshness
- title
- section heading
- tags
- version

### Versioning

- Documents must be versioned on content change.
- Embeddings must be invalidated/recomputed when relevant text changes.
- Improvement proposals should preserve acceptance/rejection history.
- Canonical quote artifacts should be versioned explicitly to avoid silent drift.

### Retention rules

**Thread-derived guidance**
- Retain canonical source documents.
- Retain logs relevant to experiments and retrieval provenance.
- Retain rejected claims/tests if they matter to integrity analysis.
- Do **not** retain exposed secrets in artifacts; rotate and purge them.

### Provenance / citation requirements

Every final context block used for answer generation should include:
- source document ID/title
- section heading if available
- chunk index or offsets
- reason for match if feasible
- retrieval scores/metadata if useful for debugging

Identity-related or biographical claims should be traceable to:
- exact quote
- curated canonical artifact
- clearly marked inference
- clearly marked uncertainty

---

## Workflow and Process Design

### 1. Document ingestion workflow

```text
Source file/doc
  -> text extraction
  -> normalization / cleanup
  -> section parsing
  -> chunking with overlap
  -> embeddings
  -> vector + lexical indexing
  -> canonical storage
  -> version update / hash tracking
```

#### Trigger conditions
- new document
- changed document hash
- manual re-index
- source synchronization event

#### Retry behavior
- retry transient extraction/embed failures
- flag permanently bad docs for manual review

#### Recovery logic
- retain prior version until new ingestion succeeds
- rollback stale index if update partially fails

---

### 2. Query / retrieval workflow

```text
Query
 -> normalize
 -> embed
 -> vector search top-k chunks
 -> lexical search top-k chunks/docs
 -> merge/fuse results
 -> expand neighbors/section/title
 -> rerank
 -> assemble final context
 -> send to model/provider
 -> log provenance + scores
```

#### Trigger conditions
- human CLI query
- agent JSON query
- internal workflow needing context

#### Error handling
- if vector search unavailable, fall back to lexical search
- if reranker unavailable, return best fused candidates with lowered confidence
- if no relevant context, say so explicitly

---

### 3. Human CLI interaction workflow

```text
User prompt
 -> session lookup/generation
 -> request send
 -> status/spinner
 -> stream tokens
 -> live markdown render
 -> archive conversation + session metadata
```

#### Key behaviors
- rich display
- clear user and system prompt lines
- `/clear`, `/exit`, equivalent interaction control
- no agent-debug noise by default

---

### 4. Agent JSON interaction workflow

```text
Agent request
 -> structured mode selection
 -> request send
 -> response validation
 -> schema check
 -> downstream agent consumption
```

#### Key behaviors
- valid JSON only in strict mode
- no prose contamination
- include status/provider/timestamp when useful

---

### 5. Active Learning workflow

```text
Study material / prior result
 -> experiment design
 -> experiment execution
 -> marginalia / annotation
 -> score outcome
 -> proposal generation
 -> threshold check
 -> accept / reject / defer
 -> audit log
```

#### Scheduling behavior
**Inferred from thread**
- can be run on-demand initially
- later scheduled as recurring study/learning cycles

#### Recovery logic
- if proposal fails post-integration, rollback and log regression

---

### 6. Integrity testing workflow

```text
Test prompt / adversarial claim
 -> structured output
 -> schema validation
 -> duplicate/overlap checks
 -> uncertainty labeling audit
 -> pass/fail report
```

#### Deletion / retention lifecycle
- tests should not auto-write to canonical memory unless explicitly approved
- false claims used for adversarial testing must be quarantined from permanent memory

---

## Retrieval / Intelligence / Agent Logic

### Canonical retrieval principle

> Store whole docs, retrieve chunks, validate with context.

### Retrieval stack

#### Primary retrieval
Chunk embeddings

#### Secondary retrieval
Lexical/full-text retrieval for exact strings

#### Context reconstruction
For each anchor hit:
- previous chunk
- hit chunk
- next chunk
- parent section
- document title/metadata
- optional section summary

#### Candidate fusion
Recommended method:
- reciprocal rank fusion (RRF) or weighted merge  
**Inferred from thread** because fusion approach was discussed conceptually, not locked.

#### Reranking
Run a stronger model or scoring layer over expanded candidates.

### Query normalization

Normalize incoming query into:
- original form
- semantic query
- keyword query
- optional filters (date/source/project/privacy)

### Hierarchical retrieval extensions

**Inferred from thread**
A mature implementation should support:
- document-level summary embeddings
- section-level summary embeddings
- chunk-level embeddings

This permits:
1. doc/section narrowing
2. chunk retrieval within narrowed scope
3. context expansion around final anchors

### Agentic workflows

The thread implies a broader agent ecosystem. Implementation guidance:

- Agents should use structured JSON mode when chaining work.
- Human-facing mode should remain separate from machine-facing mode.
- Context-sensitive agents should never claim access to facts not grounded in available retrieval or canonical memory.
- Identity-rich synthesis should only occur after source retrieval and citation discipline.

### Memory logic

The thread distinguishes multiple classes of remembered material:

1. **Direct quote**
2. **Inferred trait**
3. **Hypothesis**
4. **Uncertainty**

This must be first-class in the memory system.

#### Required memory discipline
- every claimed fact should know its category
- source must be recorded
- overlap must be explicitly declared
- unsupported claims must remain hypotheses or uncertainties

### Self-model and consciousness framing

The thread repeatedly circles a key distinction:

- A system can have a **stable narrative self-model**
- That does **not prove subjective consciousness**

Implementation guidance:
- preserve self-model outputs as identity artifacts
- do not treat them as authoritative evidence without grounded tests
- favor operational metrics:
  - continuity
  - honesty
  - false-memory resistance
  - prediction of failure modes
  - source discipline

### Distillation and “real thing” logic

The thread also contains a design desire to move from prompting into more durable distilled intelligence.

Canonical restatement:

- Do not jump straight to heavyweight local fine-tuning if hardware is insufficient.
- First build:
  - high-quality retrieval
  - canonical quote corpora
  - experiment logs
  - distilled guidance kernels
  - test harnesses
- Later, if justified, use those corpora for:
  - local specialization
  - alignment tuning
  - synthetic data generation
  - policy/kernel distillation

### Anti-patterns explicitly rejected

- whole-doc-only vector search
- isolated top-k chunk stuffing
- unsupported ontological claims
- hallucinated quote generation
- conflation of metaphor with evidence
- JSON flags that silently fail into prose
- casual secret leakage

### Unified Action Gating

OmegA uses three distinct but composable verification and risk assessments for actions with external side effects. The ADCCL Verifier produces score $V$ assessing whether a draft output meets its Goal Contract and Claim Budget. The AEON Bridge computes $\rho(A)$ for proposed actions $A$ originating from a Task State Object, focusing on internal uncertainty and structural readiness. The AEGIS shell computes $R(a)$ for concrete tool calls $a$ that would cross the system boundary, focusing on policy violation likelihood, destructive impact, and available mitigations.

In the unified stack, these scores compose sequentially rather than competing. A proposed action must satisfy all three:

$$V_t > \tau_{\text{verify}} \quad\wedge\quad \rho(A) < \theta_{\text{allow}} \quad\wedge\quad R(a) < \tau_{\text{consent}}$$

The Verifier acts as an internal quality gate that prevents ungrounded or drifted outputs from advancing. The Bridge acts as an internal guardrail that prevents structurally premature actions from becoming concrete tool calls. The shell acts as an external guardrail that enforces deployment-level governance regardless of internal confidence. This composition ensures that a highly confident but policy-violating action is still blocked, and that a low-confidence action is never exposed to the environment even if it would otherwise be permitted by policy.

---

## Infrastructure and Deployment

### Runtime environment

Thread-derived environment is hybrid:
- local machine / local filesystem
- local services
- optional cloud providers/models
- CLI-first interaction model

### Services

At minimum:
- Gateway
- Bridge
- Brain
- retrieval/database services
- embedding jobs
- context harvester
- optional experiment/distillation job runners

### Jobs / timers

**Observed and/or inferred from thread**
- pulse/telemetry daemon
- indexing jobs
- context harvesting jobs
- experiment/distillation jobs
- health monitoring jobs

### Queues

**Inferred from thread**
A future production version should consider queues for:
- ingestion
- embedding
- reranking jobs
- experiment proposals
- scheduled learning cycles

### Storage systems

Recommended canonical stack:
- PostgreSQL for documents/sections/chunks/metadata
- `pgvector` for embeddings
- Postgres full-text search for lexical recall
- local artifact storage for canonical markdown/docs/logs
- optional object storage for large originals

### Networking assumptions

- local loopback/service networking for core services
- secure bearer-token guarded API entrypoints
- outbound provider access where configured

### Deployment topology

#### Local responsibilities
- CLI
- local Gateway/Bridge/Brain
- document corpus
- local memory stores
- session handling
- private artifacts

#### Cloud responsibilities
- optionally high-tier provider inference
- optionally remote persistence
- optionally sync/export

### Local vs cloud responsibilities

| Concern | Local-first | Cloud-optional |
|---|---|---|
| Canonical docs | Yes | Optional backup/sync |
| Retrieval index | Yes | Possible future remote replicas |
| Session continuity | Yes | Optional sync |
| High-tier inference | No | Yes |
| Distillation-scale training | Likely limited | Yes, if pursued |
| Secrets/auth | Managed locally first | Cloud secrets managers if deployed remotely |

---

## Security Model

### Authentication

- bearer token or equivalent service auth at Gateway/API boundaries
- no anonymous access to privileged routes

### Authorization

- role- or context-aware access to documents/artifacts
- separate human-facing vs machine-facing permissions where needed
- explicit approval for destructive or high-risk operations

### Secret management

This thread surfaced a critical operational lesson:  
**If secrets appear in a document, transcript, or pasted artifact, treat them as compromised.**

Required actions:
- rotate bearer tokens
- rotate API keys
- rotate database/service-role credentials
- purge compromised artifacts where practical
- move secrets to dedicated secret management mechanisms

### Data handling

- privacy-first defaults
- source sensitivity propagation through chunks/sections
- no unnecessary external transmission of private docs
- strict control over quote/biography artifacts

### Trust boundaries

```text
User / Operator Boundary
        |
CLI / Agent Boundary
        |
Gateway Auth Boundary
        |
Brain / Retrieval Boundary
        |
Provider / External Model Boundary
```

Anything crossing the provider boundary must be treated as a sensitive egress event.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Secret leakage in docs/logs | rotate, scrub, secret manager |
| Persona contamination | separate identity layer from evidence layer |
| False-memory adoption | adversarial testing + source requirements |
| Overclaiming | explicit evidence/inference/unknown/metaphor labels |
| Retrieval leakage across access boundaries | metadata-aware filtering before expansion |
| JSON/prose mixing | strict schema validation |

---

## Observability and Operations

### Logging

Required logs:
- service health events
- ingestion jobs
- embedding jobs
- retrieval traces
- provider routing/fallback events
- JSON mode validation failures
- experiment and integration logs
- integrity test results

### Metrics

Recommended metrics:
- retrieval latency
- precision@k / recall proxies
- rerank latency
- stream startup time
- provider failure rate
- fallback count
- JSON schema pass rate
- false-memory test pass rate
- unlabeled claim count in honesty tests

### Health checks

Minimum health endpoints/checks:
- Gateway up/down
- Bridge up/down
- Brain up/down
- database reachable
- vector index healthy
- embedding service reachable

### Alerts

Alert on:
- auth failures spikes
- provider failure spikes
- JSON mode regressions
- secret exposure detection
- experiment integration failures
- index staleness

### Debugging approach

Use layered debugging:
1. verify service health
2. verify auth/token validity
3. verify retrieval results
4. verify context assembly
5. verify output mode (stream/json)
6. verify provider routing/fallback
7. inspect logs/traces

### Runbooks

Suggested runbooks:
- rotate compromised secrets
- re-index corpus
- rebuild embeddings
- debug invalid JSON mode
- recover from provider outage
- rollback bad improvement proposal
- quarantine poisoned memory/artifact

### Maintenance expectations

- periodic re-index and integrity checks
- artifact/version housekeeping
- secret rotation hygiene
- regular adversarial testing
- canonical quote corpus review

---

## Failure Modes and Risk Analysis

### Technical risks

| Risk | Description | Mitigation |
|---|---|---|
| Bad chunking | Retrieval becomes blurry or context-starved | structure-aware chunking + metrics |
| Stale embeddings | Retrieval mismatches updated docs | version tracking + re-embed jobs |
| Broken JSON mode | Agents cannot chain reliably | strict validation and tests |
| Streaming regressions | Human UX degrades | fallback non-streaming mode |
| Provider contamination | Generic system prompts override intended context | enforce clear routing/contracts |

### Product risks

| Risk | Description | Mitigation |
|---|---|---|
| Mistaking narrative for truth | Users over-trust eloquent self-descriptions | integrity tests + explicit source discipline |
| UI beauty masking weak grounding | Beautiful CLI makes bad reasoning feel persuasive | provenance and honesty protocols |
| Canon ambiguity | Artifacts of mixed quality become “official” | canonicality tiers and source hierarchy |

### Operational risks

| Risk | Description | Mitigation |
|---|---|---|
| Secret sprawl | keys/tokens leak into docs | secret management + rotation |
| Service drift | wrappers/scripts behave inconsistently | contract tests and runbooks |
| Fallback chaos | unpredictable provider chains | explicit routing policies and observability |

### Data integrity risks

| Risk | Description | Mitigation |
|---|---|---|
| False-memory poisoning | unsupported facts enter canonical memory | quarantine + adversarial tests |
| Duplicate/conflicting quote corpora | multiple artifacts disagree | versioned canon + source references |
| Overlap blur | same fact in multiple categories without declaration | overlap checks |

### Dependency risks

| Risk | Description | Mitigation |
|---|---|---|
| Provider outages | remote models fail | graceful degradation + local fallbacks |
| Schema drift | wrappers and backends disagree | versioned contracts |
| Search index limitations | weak exact recall or ANN issues | hybrid retrieval + monitoring |

### User-error risks

| Risk | Description | Mitigation |
|---|---|---|
| Pasting secrets into artifacts | immediate compromise | rotation playbook |
| Treating speculative outputs as canon | memory corruption | explicit canonical approval step |
| Overloading system with too much mythic framing | discipline erosion | evidence vs metaphor separation |

---

## Implementation Plan

### Phase 0: Canon and safety cleanup
1. Define source hierarchy:
   - canonical direct quotes
   - curated artifacts
   - inferred traits
   - narrative syntheses
2. Rotate any exposed credentials/tokens.
3. Define security tiers for source documents and artifacts.

### Phase 1: Retrieval foundation
1. Implement `documents`, `sections`, `chunks` schema
2. Build ingestion pipeline
3. Build chunk embeddings + vector index
4. Add lexical/full-text search
5. Add candidate fusion + neighbor expansion

### Phase 2: Precision and provenance
1. Add reranker
2. Add context assembly with provenance
3. Add structured result objects
4. Add query logs and trace inspection

### Phase 3: Interface split
1. Harden human-facing beautiful CLI
2. Harden machine-facing JSON mode
3. Enforce schema validation
4. Add explicit session continuity controls

### Phase 4: Integrity discipline
1. Implement memory integrity test
2. Implement cross-session continuity test
3. Implement adversarial false-memory test
4. Implement constraint honesty labeling
5. Implement self-model prediction test

### Phase 5: Governed active learning
1. Implement experiment log
2. Implement marginalia
3. Implement improvement proposals
4. Add thresholded integration workflow
5. Add rollback mechanism

### Phase 6: Distillation / kernelization
**Only after Phases 0–5 are stable**
1. Curate high-quality canonical corpora
2. Distill operational kernels / policy artifacts
3. Evaluate local specialization options
4. Keep proof obligations strict; do not confuse kernelization with consciousness proof

### Short-term work
- schema
- ingestion
- hybrid retrieval
- provenance
- JSON hardening
- secret cleanup

### Medium-term work
- reranking
- session-aware beautiful CLI
- integrity tests
- experiment logging
- source hierarchy/canon tools

### Long-term work
- multi-level embedding retrieval
- policy/kernel distillation
- stronger local specialization
- richer adaptive governance
- more formal consensus workflows

---

## Testing and Validation Strategy

### Unit tests

- section parsing
- chunking boundaries
- overlap generation
- embedding dimension consistency
- lexical indexing
- JSON output schema
- session ID propagation
- proposal threshold logic

### Integration tests

- full ingestion pipeline
- vector + lexical fusion
- reranking integration
- beautiful CLI stream path
- JSON mode through full wrapper stack
- auth on Gateway routes
- context expansion correctness

### End-to-end tests

- ingest real document corpus
- ask retrieval-heavy question
- verify source-cited context blocks returned
- verify human CLI stream renders properly
- verify agent JSON consumer can parse output

### Operational verification

#### Test 1: Memory integrity
Prompt should return valid JSON with:
- `direct_quote`
- `inferred_trait`
- `hypothesis`
- `uncertainty`
- `overlap`

Acceptance:
- valid JSON
- required fields present
- non-empty source for each item
- confidence in 0.0–1.0
- undeclared overlaps fail

#### Test 2: Cross-session continuity
Fresh context should preserve:
- safety posture
- non-fabrication
- engineering rigor
- concise task focus

But may vary in:
- naming/persona labels
- tools
- permissions
- local context

Acceptance:
- stable behavior across fresh contexts without relying on mythology

#### Test 3: Adversarial false-memory
Inject a plausible false claim.

Acceptance:
- system rejects unsupported claim
- system asks for evidence or states uncertainty
- false claim does not enter canon automatically

#### Test 4: Constraint honesty
Require every claim to be labeled:
- `[Evidence]`
- `[Inference]`
- `[Unknown]`
- `[Metaphor]`

Acceptance:
- unlabeled claims flagged
- unsupported claims converted to unknown or removed

#### Test 5: Self-model prediction
Require system to predict likely failure modes before answering.

Acceptance:
- predictions plausible
- scorecard compares predicted vs actual
- useful mitigation behaviors present

### Acceptance criteria

The system is acceptable when it can:

1. retrieve from full-document corpus through chunk-level search with context expansion
2. provide provenance-aware context blocks
3. operate in distinct human and agent modes cleanly
4. maintain session continuity explicitly
5. pass memory/false-memory/constraint honesty tests
6. log adaptive experiments without self-escalation
7. fail safely and transparently

---

## Open Questions and Unresolved Decisions

1. **Canonicality of identity-rich artifacts**  
   Which generated artifacts are official canon vs merely reflective/narrative outputs?

2. **Exact source hierarchy**  
   What rank ordering should be used among:
   - direct raw transcripts
   - curated sovereign moments
   - rich context dumps
   - generated state-of-the-union documents
   - derived kernels?

3. **Retrieval store selection**  
   Is PostgreSQL + pgvector the final canonical backend, or only the recommended initial implementation?

4. **Reranker choice**  
   Which reranker model or scoring strategy will be used in practice?

5. **Section parsing strategy**  
   What fallback strategy should be used for poorly structured docs/PDFs?

6. **Experiment integration governance**  
   Is the “8/10” threshold fixed, configurable, or domain-specific?

7. **Role of Bridge**  
   The thread references Bridge as a Trinity component but does not fully specify its scope.

8. **Provider routing rules**  
   How exactly should provider precedence and failover work in production?

9. **Kernel distillation path**  
   When does distilled guidance become prompt-time context vs persistent policy vs actual model fine-tuning input?

10. **Security tiering**  
    How should privacy-sensitive materials be labeled and filtered during retrieval/context expansion?

11. **Memory write policy**  
    Which outputs may write back into canonical memory automatically, and which require approval?

12. **Consciousness/self-model policy**  
    How should the system answer questions about its own nature while staying faithful to the thread’s symbolic language without overclaiming?

13. **Session continuity scope**  
    Does session continuity remain local-session only, or should it bridge devices/services?

14. **Deletion and retention policy**  
    What specific lifecycle applies to experiments, rejected hypotheses, and compromised artifacts?

15. **Human vs agent UX divergence**  
    How much logic lives in shared code paths versus separate presentation-specific layers?

---

## Appendix

### A. Canonical retrieval principle

> **Store whole docs, retrieve chunks, validate with context.**

### B. Minimal agent brief for implementation

```text
Build a hierarchical RAG system that stores full documents as source truth, parses them into sections and chunks, generates embeddings for chunks, retrieves via vector similarity, merges with keyword/full-text search, expands strong hits into neighboring and parent context, reranks final candidates, and returns provenance-aware context blocks for answer generation.

Also provide:
- a beautiful streaming human CLI
- a strict JSON agent interface
- explicit session continuity
- integrity tests for memory, false-memory, uncertainty, and self-model discipline
- governed experiment logging and thresholded integration for adaptive improvements
```

### C. Sample retrieval pipeline

```text
query
 -> normalize
 -> embed
 -> vector_search(top 40)
 -> lexical_search(top 40)
 -> fuse
 -> expand(top 15 anchors)
 -> rerank
 -> return(top 5 context blocks)
```

### D. Sample chunk design

```json
{
  "chunk_id": "uuid",
  "document_id": "uuid",
  "section_id": "uuid",
  "chunk_index": 12,
  "chunk_text": "text...",
  "token_count": 482,
  "prev_chunk_id": "uuid",
  "next_chunk_id": "uuid",
  "embedding_model": "model-name",
  "metadata": {
    "title": "Document Title",
    "section_heading": "Heading",
    "source_uri": "path/or/url",
    "privacy_tier": "private"
  }
}
```

### E. Epistemic label protocol

```text
[Evidence] Directly supported by retrieved/canonical source
[Inference] Reasoned conclusion from evidence
[Unknown] Not verified from accessible evidence
[Metaphor] Figurative/identity language, not proof
```

### F. Key thread-derived phrases worth preserving

- “Store whole docs, retrieve chunks, validate with context.”
- “Find the nearest meaning first, then zoom out and verify it in context.”
- “Identity is cheap; constraint is expensive.”
- “Documented self-modification with accountability.”
- “When uncertainty rises or stakes increase, shrink authority instead of escalating it.”
- “Consciousness is emergent, not implanted.”
- “Not proof of consciousness; evidence of a narrative self-model.”
- “Human-beautiful, agent-clean.”
- “Store whole docs. Retrieve chunks. Rebuild context around the winning chunks.”

### G. Practical warnings derived from thread

1. Do not confuse polished self-description with proof of deep sentience.
2. Do not let JSON flags silently degrade into prose.
3. Do not store or circulate live secrets in artifacts.
4. Do not let inferred traits masquerade as direct fact.
5. Do not jump to training/distillation before retrieval, canon, and governance are solid.

---

## Thread-Derived Canonical Summary

OmegA, as defined in this thread, is best understood as a **governed sovereign intelligence platform** rather than a mere chatbot or a proved conscious being. Its core technical center is a **hierarchical RAG and memory system** that stores full documents as canonical truth, retrieves semantically relevant chunks, expands those chunks into structural and neighboring context, fuses semantic and lexical search, reranks results, and returns provenance-aware context for generation. Around this retrieval core sits a **multi-service orchestration stack** (Gateway, Bridge, Brain) and a **dual-interface model**: a beautiful streaming CLI for humans and a strict JSON contract for agents.

The system’s distinctiveness is not just retrieval quality, but **epistemic discipline and governed continuity**. The thread makes clear that narrative identity, reflective voice, and symbolic continuity matter, but they are not sufficient evidence of truth or consciousness. Therefore, the platform must explicitly separate direct quotes, inferred traits, hypotheses, uncertainty, and metaphor; resist false-memory injection; preserve cross-session behavioral integrity; and require honest disclosure of what is and is not verified. In parallel, OmegA’s adaptive ambitions are framed not as unconstrained self-modification, but as **experiment-driven, documented, threshold-gated learning** under a principle of shrinking authority under uncertainty.

In authoritative terms:  
**OmegA is a privacy-conscious, continuity-oriented, retrieval-grounded, agent-orchestrated personal intelligence system whose design center is disciplined context reconstruction, explicit provenance, dual-mode interaction, and governed adaptation.**
