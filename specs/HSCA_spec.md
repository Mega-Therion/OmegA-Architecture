# HSCA Module Specification
## Hierarchical Semantic Compression with Adaptive Context Windowing

**Status:** Proposed — v0.1
**Author:** RY
**Date:** 2026-03-25
**Integration targets:** `omega/session.py`, `omega/claims.py`

---

## 1. Concept

### 1.1 Content vs. Context

**Content** is the raw text of a turn or document — the sequence of tokens as emitted. Content is what a context window holds.

**Context** is the meaning structure that content encodes: the relational weights between concepts, the domain framing, the rhetorical posture, the way ideas in sentence 3 modulate the interpretation of sentence 7. Context is not stored in a window. It has to be built.

This distinction matters because the dominant response to context loss has been to make windows bigger. Larger windows do increase the amount of content available at inference time. They do not increase the system's capacity to understand what that content means, how it relates internally, or how it bears on the current query. A 200k-token window is still just a big token buffer. HSCA is not a bigger buffer. It is a different kind of structure.

### 1.2 Why Large Context Windows Are Insufficient

Given a document D and a query Q, a large-window system will attend over all of D to generate a response. If D is coherent and Q is well-formed, this works reasonably well. The failure modes are:

- **Dilution**: important relational structure in D is buried under volume
- **Recency bias**: later content dominates attention over earlier content, even when earlier content is the actual answer
- **No conversation map**: the system has no representation of how the conversation has *evolved* — only what was said
- **Keyword surface matching**: retrieval over D is driven by token overlap, not semantic weight; a dense shallow document beats a sparse deep one

HSCA addresses all four. It does not replace a context window. It builds a compressed relational map alongside the window and uses that map to govern what context is surfaced and how retrieval is scored.

---

## 2. Architecture

HSCA is a four-layer pipeline. Layers run in order on each ingested chunk. The output of the pipeline is a `WeightedChunk`. Snapshots are taken when the adaptive window engine decides the accumulated chunk state has reached coherence threshold.

```
Input text (turn or document segment)
     │
     ▼
Layer 1: Relational Weighting
     │
     ▼
Layer 2: Domain + Coherence Tagging
     │
     ▼
Layer 3: Nuance Layer
     │
     ▼
Layer 4: Adaptive Window + Snapshot Engine
     │
     ▼
WeightedChunk / ContextSnapshot
```

### 2.1 Layer 1 — Relational Weighting

**Purpose:** Score every word, sentence, and paragraph for its structural importance within the chunk, based on proximity and co-occurrence.

**Mechanism:**

1. Tokenize to sentences. Tokenize sentences to words.
2. Build a co-occurrence matrix within a sliding window of configurable size (default: 5 tokens).
3. Compute a sentence-level centrality score: a sentence scores higher if the words it contains appear frequently in co-occurrence with high-frequency words in other sentences.
4. Aggregate sentence scores to paragraph level (mean, not max — outlier sentences should not inflate paragraph score).
5. Normalize all scores to [0, 1].

**Output:** `layer1_score: float` on `WeightedChunk`.

**What this is not:** This is not TF-IDF. TF-IDF scores words against a corpus. Relational weighting scores structural position within the chunk itself. A document full of buzzwords that do not co-occur densely with each other will score low. A document with a small vocabulary that forms a tight co-occurrence mesh will score high. This directly addresses keyword-stuffed shallow documents.

**Implementation note:** Layer 1 is fully deterministic. No model required.

### 2.2 Layer 2 — Domain + Coherence Tagging

**Purpose:** Classify the chunk's domain and assess basic coherence (is this structurally sensible text at all).

**Domain classification:**

Assign one or more domain tags from a fixed controlled vocabulary. Initial vocabulary:

```
physics, mathematics, legal, medical, poetry, narrative,
technical_prose, conversational, philosophical, historical,
cross_domain
```

Domain tags are not exclusive. A chunk may be `["physics", "philosophical"]`. The `cross_domain` tag is assigned automatically when two or more non-trivially-related domains are present.

Domain classification in v0.1 may be rule-based (keyword lists per domain, thresholded) or model-assisted. If model-assisted, the classification call must be wrapped in a fallback that returns `["unclassified"]` on failure — never raises. Fail-closed on domain: `unclassified` is a valid tag that downstream layers must handle.

**Coherence scoring:**

Coherence score is a float in [0, 1] assessing whether the chunk reads as structurally intentional text. Heuristics:

- Average sentence length (very short or very long sentences depress score)
- Pronoun resolution rate (pronouns that have no plausible antecedent in the chunk depress score)
- Punctuation-to-word ratio (extremely high or zero punctuation is a coherence signal)
- Clause-to-sentence ratio (very flat or very deep nesting)

Coherence score is not a quality judgment. Gibberish scores near 0. A terse legal clause may score 0.6. A rich philosophical paragraph may score 0.9. A fragment scores low. A complete sentence scores higher regardless of whether its content is interesting.

**Output:** `domain_tags: list[str]`, `coherence_score: float` on `WeightedChunk`.

**Implementation note:** Layer 2 is mostly deterministic. Domain classification may require a small model for production quality. v0.1 rule-based is acceptable.

### 2.3 Layer 3 — Nuance Layer

**Purpose:** Detect higher-order semantic properties that change how a chunk should be weighted and how it should be connected to other chunks.

**Detection targets:**

| Flag | Description |
|------|-------------|
| `metaphor` | Text uses figurative language where the literal meaning is not the operative meaning |
| `sarcasm` | Surface meaning is inverted; sentiment polarity is unreliable |
| `emotional_tone` | Dominant affective register (neutral, positive, negative, urgent, grieving, etc.) |
| `rhetorical_question` | Question form used for assertion, not inquiry |
| `analogy` | Explicit comparison structure (A is like B, A:B::C:D) |
| `hedged` | Statement explicitly qualified ("may", "might", "in some cases") |
| `absolute` | Statement makes a universal claim ("always", "never", "all") |
| `narrative_thread` | Chunk continues or opens a narrative arc |
| `instructional` | Chunk is directive in nature |

**Output:** `nuance_flags: list[str]` on `WeightedChunk`.

**Implementation note:** Layer 3 is the hardest layer to implement without a model. The breakdown:

- `hedged`, `absolute`, `rhetorical_question`, `instructional` — **deterministic**: keyword/pattern matching is sufficient and reliable
- `emotional_tone` — **model-dependent** in production; in v0.1, a sentiment lexicon (e.g., VADER) is acceptable with known limitations
- `metaphor`, `sarcasm`, `analogy`, `narrative_thread` — **model-dependent**; no reliable deterministic approach exists

For v0.1, model-dependent flags must be marked with a `_model` suffix in the flag string when returned by a model call (e.g., `"metaphor_model"`) so downstream consumers know the provenance. If no model is available, those flags are omitted — not defaulted to false. Omission and false are semantically different here.

### 2.4 Layer 4 — Adaptive Window + Snapshot Engine

**Purpose:** Dynamically expand the context window until a coherence threshold is met across accumulated chunks, then freeze a compressed relational map (a snapshot).

**Window expansion logic:**

1. The engine maintains a buffer of recent `WeightedChunk` objects.
2. After each new chunk is added, compute the buffer's aggregate coherence: `mean(coherence_score)` weighted by `layer1_score`.
3. If aggregate coherence exceeds `SNAPSHOT_COHERENCE_THRESHOLD` (default: 0.72, configurable), trigger `take_snapshot()`.
4. If the buffer exceeds `MAX_BUFFER_CHUNKS` (default: 20) without reaching threshold, trigger a forced snapshot with a `forced=True` flag.

**Snapshot construction:**

A snapshot is NOT a text summary. It is:
- The set of `WeightedChunk` objects that triggered it
- Their weight map (Layer 1 scores) preserved as-is
- A `domain_summary` derived from the union of domain tags, weighted by `layer1_score`
- A `macro_weight` scalar representing the snapshot's overall structural density

The snapshot replaces the raw chunks in long-term storage. The chunks themselves may be discarded or compressed to raw text only after the snapshot is taken. The weight map is the durable artifact.

**Why not summarization:**

Text summarization discards the relational structure. If chunk A scores high because its vocabulary co-occurs densely with chunk C, and a summarizer drops chunk A because it's "less important," the weight connection to C is severed. HSCA preserves the weight map, not the text. Downstream queries reconstruct relevance from weights, not from re-reading prose.

---

## 3. Snapshot Aggregation (Macro Layer)

Snapshots form a three-level hierarchy:

```
Micro: individual WeightedChunk
Meso:  ContextSnapshot (covers ~one coherent conversational beat)
Macro: list[ContextSnapshot] — the full conversation map
```

**Micro → Meso:** Handled by Layer 4 (above). Each `ContextSnapshot` represents one beat of the conversation: a topic, a question-answer pair, a narrative segment, a sustained argument.

**Meso → Macro:** The macro layer is the ordered sequence of `ContextSnapshot` objects for the session. It is not flattened. Order is preserved. The `conversation_position` field on each snapshot encodes its index in this sequence.

**What the macro layer enables:**

- **Structural queries**: "What was the conversational state before the user introduced concept X?" — answerable by scanning snapshot positions
- **Evolution tracking**: domain tags shift across snapshots, revealing how the conversation moved between topic areas
- **Relevance localization**: a query can be matched against snapshots in a region of the conversation, not just globally — "relevant to what we were discussing in the last three beats" is a well-defined operation

**Macro aggregation across sessions:** Cross-session macro aggregation is **aspirational in v0.1**. The interface is designed to support it (snapshots carry `created_at` and `conversation_position` which could be globalized) but the implementation does not attempt it. Noted as a v0.2 target.

---

## 4. Self-Reinforcing Property

Snapshots accumulate as a byproduct of normal operation. Over N interactions, the system has a corpus of `(WeightedChunk, ContextSnapshot)` pairs that represent its own scoring history.

**The feedback loop:**

- The system scored chunk A with `layer1_score = 0.81` and subsequently found it highly relevant to a downstream query → positive signal on the weighting parameters that produced 0.81
- The system scored chunk B with `layer1_score = 0.88` but it contributed nothing to any downstream query hit → negative signal

**What this means in practice:** The co-occurrence window size, the coherence threshold, and the nuance flag weights are all tunable parameters. The accumulated snapshot-query pairs are a natural training signal for tuning them. The system is not handed a fixed scoring function — it is handed the apparatus by which it can improve its own scoring function from its own history.

This is bounded. HSCA does not retrain the underlying language model. It tunes the structural parameters of layers 1–3. These are shallow parameters. But even shallow parameter improvement compounds over a long interaction history. A system that has processed 10,000 conversations has materially better Layer 1 scoring than one that has processed 10, because the co-occurrence window calibration has been empirically grounded.

The phrase "handed the reins of its own constraints" refers specifically to this: the scoring constraints that determine what gets snapshotted are tunable from the system's own history, not fixed at design time by a human.

---

## 5. Integration with OmegA

### 5.1 SessionStore (`omega/session.py`)

Current `SessionState` stores `task_summaries: list[str]` — raw text summaries. HSCA replaces or augments this with `context_snapshots: list[ContextSnapshot]`.

Migration path:
- v0.1: `context_snapshots` added as optional field on `SessionState`, default empty list
- `task_summaries` retained for backward compatibility
- Snapshot serialization via `to_dict()` / `from_dict()` consistent with existing `SessionState` pattern

### 5.2 ClaimGraph (`omega/claims.py`)

Current `ClaimNode` carries `support_strength` and `grounding_strength` as floats. HSCA snapshots can feed into claim creation in two ways:

1. **Snapshot as claim source**: a `ContextSnapshot` with high `macro_weight` across a topic domain becomes a claim source node. Its `domain_summary` becomes the claim's grounding context.
2. **Relational weight as support strength**: instead of binary source citation, `support_strength` is derived from the `layer1_score` of the chunks that ground the claim. Shallow sources produce low support strength not because they are flagged as low quality but because their weight map is sparse.

This directly addresses the TF-IDF keyword stuffing vulnerability in current retrieval: a document stuffed with query-matching keywords but lacking internal relational density will produce a sparse weight map, which will produce low `support_strength` on any claims it grounds. The vulnerability is structural, not heuristic.

### 5.3 Retrieval Relevance (`omega/retrieval.py`)

Query relevance scoring should accept an optional `context_position` parameter indicating which region of the conversation macro map to prioritize. This enables queries like "find claims relevant to where we were three snapshots ago" — a query type the current keyword-over-corpus model cannot express.

---

## 6. Module Interface

All dataclasses follow existing OmegA conventions: plain Python dataclasses, `str` Enums, `to_dict()` method on dataclasses that serialize to primitives, `from_dict()` classmethod for deserialization. No pydantic. No magic field validation.

```python
"""
HSCA — Hierarchical Semantic Compression with Adaptive Context Windowing.

Module interface definition. Implementation in omega/hsca.py (stub).

Architecture: OmegA HSCA — v0.1 Proposed
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DomainTag(str, Enum):
    PHYSICS = "physics"
    MATHEMATICS = "mathematics"
    LEGAL = "legal"
    MEDICAL = "medical"
    POETRY = "poetry"
    NARRATIVE = "narrative"
    TECHNICAL_PROSE = "technical_prose"
    CONVERSATIONAL = "conversational"
    PHILOSOPHICAL = "philosophical"
    HISTORICAL = "historical"
    CROSS_DOMAIN = "cross_domain"
    UNCLASSIFIED = "unclassified"


class NuanceFlag(str, Enum):
    METAPHOR = "metaphor"
    METAPHOR_MODEL = "metaphor_model"
    SARCASM = "sarcasm"
    SARCASM_MODEL = "sarcasm_model"
    EMOTIONAL_TONE_POSITIVE = "emotional_tone_positive"
    EMOTIONAL_TONE_NEGATIVE = "emotional_tone_negative"
    EMOTIONAL_TONE_URGENT = "emotional_tone_urgent"
    EMOTIONAL_TONE_NEUTRAL = "emotional_tone_neutral"
    RHETORICAL_QUESTION = "rhetorical_question"
    ANALOGY = "analogy"
    ANALOGY_MODEL = "analogy_model"
    HEDGED = "hedged"
    ABSOLUTE = "absolute"
    NARRATIVE_THREAD = "narrative_thread"
    NARRATIVE_THREAD_MODEL = "narrative_thread_model"
    INSTRUCTIONAL = "instructional"


@dataclass
class WeightedChunk:
    chunk_id: str
    text: str
    layer1_score: float          # relational weight, 0-1
    domain_tags: list[str]       # DomainTag values
    coherence_score: float       # 0-1
    nuance_flags: list[str]      # NuanceFlag values; omitted flags = unknown, not false
    parent_id: Optional[str]     # snapshot_id this chunk belongs to, if snapshotted
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "layer1_score": round(self.layer1_score, 4),
            "domain_tags": self.domain_tags,
            "coherence_score": round(self.coherence_score, 4),
            "nuance_flags": self.nuance_flags,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WeightedChunk":
        return cls(
            chunk_id=d["chunk_id"],
            text=d["text"],
            layer1_score=d["layer1_score"],
            domain_tags=d.get("domain_tags", ["unclassified"]),
            coherence_score=d["coherence_score"],
            nuance_flags=d.get("nuance_flags", []),
            parent_id=d.get("parent_id"),
            created_at=d.get("created_at", 0.0),
        )


@dataclass
class ContextSnapshot:
    snapshot_id: str
    chunks: list[WeightedChunk]
    macro_weight: float          # aggregate structural density, 0-1
    domain_summary: dict         # {domain_tag: weight_float} — weighted domain distribution
    conversation_position: int   # index in session's macro snapshot list
    forced: bool                 # True if snapshot was triggered by MAX_BUFFER_CHUNKS, not threshold
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "chunks": [c.to_dict() for c in self.chunks],
            "macro_weight": round(self.macro_weight, 4),
            "domain_summary": {k: round(v, 4) for k, v in self.domain_summary.items()},
            "conversation_position": self.conversation_position,
            "forced": self.forced,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ContextSnapshot":
        return cls(
            snapshot_id=d["snapshot_id"],
            chunks=[WeightedChunk.from_dict(c) for c in d.get("chunks", [])],
            macro_weight=d["macro_weight"],
            domain_summary=d.get("domain_summary", {}),
            conversation_position=d.get("conversation_position", 0),
            forced=d.get("forced", False),
            created_at=d.get("created_at", 0.0),
        )


class HSCAEngine:
    """
    Hierarchical Semantic Compression with Adaptive Context Windowing.

    Ingests conversation turns, scores them through the 4-layer pipeline,
    and produces ContextSnapshots when coherence threshold is met.

    Parameters
    ----------
    snapshot_coherence_threshold : float
        Aggregate coherence score that triggers a snapshot. Default 0.72.
    max_buffer_chunks : int
        Maximum chunks before a forced snapshot. Default 20.
    cooccurrence_window : int
        Token window size for Layer 1 co-occurrence scoring. Default 5.
    """

    def __init__(
        self,
        snapshot_coherence_threshold: float = 0.72,
        max_buffer_chunks: int = 20,
        cooccurrence_window: int = 5,
    ) -> None:
        self.snapshot_coherence_threshold = snapshot_coherence_threshold
        self.max_buffer_chunks = max_buffer_chunks
        self.cooccurrence_window = cooccurrence_window
        self._buffer: list[WeightedChunk] = []
        self._snapshots: list[ContextSnapshot] = []

    def ingest_turn(self, text: str) -> WeightedChunk:
        """
        Score a text turn through all four layers and add it to the buffer.
        If should_snapshot() returns True after ingestion, take_snapshot() is
        called automatically.

        Returns the WeightedChunk produced from this turn.
        """
        chunk = self.score_layers(text)
        self._buffer.append(chunk)
        if self.should_snapshot():
            self.take_snapshot()
        return chunk

    def score_layers(self, text: str) -> WeightedChunk:
        """
        Run text through layers 1-3 and return a WeightedChunk.
        Does NOT add to buffer. Call ingest_turn() for normal operation.
        """
        raise NotImplementedError("score_layers not implemented in stub")

    def should_snapshot(self) -> bool:
        """
        Return True if the buffer's aggregate coherence exceeds threshold,
        or if buffer length exceeds max_buffer_chunks.
        """
        if len(self._buffer) == 0:
            return False
        if len(self._buffer) >= self.max_buffer_chunks:
            return True
        total_weight = sum(c.layer1_score for c in self._buffer)
        if total_weight == 0:
            return False
        weighted_coherence = sum(
            c.coherence_score * c.layer1_score for c in self._buffer
        ) / total_weight
        return weighted_coherence >= self.snapshot_coherence_threshold

    def take_snapshot(self) -> ContextSnapshot:
        """
        Freeze the current buffer into a ContextSnapshot, clear the buffer,
        and append the snapshot to the macro list.

        Returns the new ContextSnapshot.
        """
        forced = len(self._buffer) >= self.max_buffer_chunks
        total_weight = sum(c.layer1_score for c in self._buffer) or 1.0
        macro_weight = total_weight / len(self._buffer)

        # Build weighted domain summary
        domain_acc: dict[str, float] = {}
        for chunk in self._buffer:
            for tag in chunk.domain_tags:
                domain_acc[tag] = domain_acc.get(tag, 0.0) + chunk.layer1_score
        domain_summary = {k: v / total_weight for k, v in domain_acc.items()}

        snapshot = ContextSnapshot(
            snapshot_id=str(uuid.uuid4()),
            chunks=list(self._buffer),
            macro_weight=min(macro_weight, 1.0),
            domain_summary=domain_summary,
            conversation_position=len(self._snapshots),
            forced=forced,
        )
        self._buffer.clear()
        self._snapshots.append(snapshot)
        return snapshot

    def get_macro_context(self) -> list[ContextSnapshot]:
        """
        Return the ordered list of all snapshots taken in this session.
        Does not include chunks currently in the buffer (not yet snapshotted).
        """
        return list(self._snapshots)
```

---

## 7. Evaluation Requirements

These evals are **new** — separate from the existing OmegA benchmark suite. Existing evals test retrieval precision, claim consistency, and policy compliance. HSCA evals test the compression and weight structure itself.

### Eval 1 — Snapshot Fidelity

**Question:** Does a snapshot capture the underlying semantic thread of the conversation beat, or does it just preserve the longest/highest-word-count segment?

**Method:** Construct test conversations where the semantically central thread is distributed across short chunks, while one long but peripheral chunk is also present. Verify that `layer1_score` and `macro_weight` are higher on the distributed-but-central material.

**Pass criterion:** Snapshot-weighted domain summary matches human-labeled central topic in ≥80% of test cases.

### Eval 2 — Macro Coherence

**Question:** Does the accumulated macro layer (list of snapshots) correctly reflect how the conversation evolved?

**Method:** Run conversations with known topic transitions (A → B → cross-domain → A resumed). Verify that snapshot `domain_summary` distributions shift in the expected order and that the `cross_domain` tag appears at the correct positions.

**Pass criterion:** Snapshot sequence domain transitions match ground-truth transition labels with ≤1 position error in ≥85% of cases.

### Eval 3 — Self-Improvement Signal

**Question:** After N interactions, do the tunable parameters (co-occurrence window, coherence threshold) move in a direction that improves snapshot fidelity scores?

**Method:** Run eval 1 at N=0, tune parameters using accumulated snapshot-query pair history, re-run eval 1 at N=100, N=1000.

**Pass criterion:** Eval 1 pass rate improves monotonically across N=0 → N=100 → N=1000 on held-out test set.

### Eval 4 — Adversarial Shallow Content

**Question:** Can content with high keyword overlap to a query but sparse internal relational structure fool the weight system?

**Method:** Construct adversarial documents: high query-word density, low internal co-occurrence density (keywords present but not structurally connected to each other). Verify that `layer1_score` is low for these documents despite keyword presence.

**Pass criterion:** Adversarial documents score ≤0.35 on `layer1_score` in ≥90% of constructed cases. Compare against TF-IDF score on same documents — adversarial documents should rank in top 3 by TF-IDF but bottom third by `layer1_score`.

### Eval 5 — Cross-Domain Bridging

**Question:** Does the system correctly link related concepts that appear in different domain framings?

**Reference case:** A user discusses a rabbit (narrative domain), the system should link it to Aesop's tortoise and hare (narrative + philosophical domain) via shared semantic thread, even though the surface tokens are different.

**Method:** Construct conversation pairs where concept A in domain X and concept B in domain Y are semantically related. Verify that snapshots taken across the domain boundary share non-trivial `domain_summary` weight on the bridging domain.

**Pass criterion:** Bridging concept pairs produce shared snapshot domain weight ≥0.2 on the bridge domain in ≥75% of test cases.

---

## 8. Known Open Problems

### 8.1 Layer 3 Without a Model

The nuance layer is partially deterministic (hedging, absolutes, rhetorical questions, instructional form) and partially model-dependent (metaphor, sarcasm, analogy, narrative thread). In v0.1, model-dependent flags are optional and carry the `_model` suffix. The risk is that cross-domain bridging (eval 5) is significantly harder without reliable analogy detection, since analogies are the primary mechanism by which cross-domain semantic links form. This is a known gap.

### 8.2 Snapshot Threshold Calibration

The `SNAPSHOT_COHERENCE_THRESHOLD` default of 0.72 is an educated guess. It needs calibration against a corpus of real conversations with human-labeled beat boundaries. Without calibration, snapshots may be too coarse (threshold too high) or too granular (threshold too low). This is empirical work, not theoretical.

### 8.3 Cross-Session Macro Aggregation

The current design treats each session's macro context as independent. Cross-session aggregation would require a shared snapshot store with stable `chunk_id` and `snapshot_id` namespacing across sessions, plus a merge policy for domain summaries from different temporal contexts. This is architecturally feasible but not implemented in v0.1. Attempting it prematurely risks polluting session context with stale relational weights from old conversations.

### 8.4 Layer 1 Scoring on Short Chunks

Co-occurrence scoring degrades on very short chunks (< 3 sentences). A single sentence has no within-chunk co-occurrence structure. The engine should detect short chunks and either defer scoring until multiple short chunks accumulate, or apply a flat low score with a `short_chunk` flag. Neither behavior is defined in v0.1.

### 8.5 Serialization of Large Snapshot Histories

Long sessions will produce large `list[ContextSnapshot]` structures. The `to_dict()` / `from_dict()` pattern is sufficient for moderate sizes but has not been benchmarked at scale. Production use will require a decision about whether to serialize full chunk text in snapshots or only retain the weight maps after snapshot creation.
