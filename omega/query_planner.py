"""
Query Planner — Intelligent query rewriting and retrieval strategy selection.

Decomposes complex queries, selects retrieval strategy, and produces
a structured QueryPlan that the HybridRetriever can execute.

Architecture: MYELIN Phase 3 — Retrieval Intelligence
"""

import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class QueryStrategy(str, Enum):
    SIMPLE = "simple"
    MULTI_HOP = "multi_hop"
    CONTRADICTION_AWARE = "contradiction_aware"
    EXHAUSTIVE = "exhaustive"


@dataclass
class QueryPlan:
    plan_id: str
    original_query: str
    rewritten_queries: list[str]
    strategy: QueryStrategy
    lexical_weight: float
    vector_weight: float
    metadata_filters: dict = field(default_factory=dict)
    top_k: int = 5
    max_hops: int = 1
    escalation_threshold: float = 0.3
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "original_query": self.original_query,
            "rewritten_queries": self.rewritten_queries,
            "strategy": self.strategy.value,
            "lexical_weight": round(self.lexical_weight, 4),
            "vector_weight": round(self.vector_weight, 4),
            "metadata_filters": self.metadata_filters,
            "top_k": self.top_k,
            "max_hops": self.max_hops,
            "escalation_threshold": round(self.escalation_threshold, 4),
            "created_at": self.created_at,
        }


# Synonym table for query expansion
_SYNONYMS: dict[str, list[str]] = {
    "find": ["search", "locate", "retrieve"],
    "explain": ["describe", "clarify", "elaborate"],
    "compare": ["contrast", "differentiate", "distinguish"],
    "cause": ["reason", "origin", "source"],
    "effect": ["result", "consequence", "outcome"],
    "improve": ["enhance", "optimize", "refine"],
    "problem": ["issue", "error", "bug", "defect"],
    "solution": ["fix", "resolution", "workaround"],
    "create": ["build", "generate", "construct"],
    "delete": ["remove", "destroy", "eliminate"],
}

# Multi-hop signal words
_MULTI_HOP_SIGNALS = {
    "how does", "what causes", "why does", "relationship between",
    "connected to", "leads to", "depends on", "affects",
    "step by step", "chain of", "sequence of",
}

# Contradiction signal words
_CONTRADICTION_SIGNALS = {
    "contradicts", "disagrees", "conflicts", "inconsistent",
    "but also", "on the other hand", "however", "versus",
    "debate", "controversy", "disputed",
}


class QueryPlanner:
    """
    Analyzes a query and produces a structured QueryPlan with
    rewritten queries and an appropriate retrieval strategy.
    """

    def plan(self, query: str, task_class: str = "research") -> QueryPlan:
        strategy = self._select_strategy(query, task_class)
        rewritten = self._rewrite_query(query)
        filters = self._plan_filters(query)

        # Strategy-specific parameters
        if strategy == QueryStrategy.SIMPLE:
            top_k = 5
            max_hops = 1
            lexical_weight = 0.4
            vector_weight = 0.6
            escalation_threshold = 0.3
        elif strategy == QueryStrategy.MULTI_HOP:
            top_k = 8
            max_hops = 3
            lexical_weight = 0.3
            vector_weight = 0.7
            escalation_threshold = 0.25
        elif strategy == QueryStrategy.CONTRADICTION_AWARE:
            top_k = 10
            max_hops = 2
            lexical_weight = 0.5
            vector_weight = 0.5
            escalation_threshold = 0.2
        else:  # EXHAUSTIVE
            top_k = 15
            max_hops = 4
            lexical_weight = 0.4
            vector_weight = 0.6
            escalation_threshold = 0.15

        return QueryPlan(
            plan_id=str(uuid.uuid4()),
            original_query=query,
            rewritten_queries=rewritten,
            strategy=strategy,
            lexical_weight=lexical_weight,
            vector_weight=vector_weight,
            metadata_filters=filters,
            top_k=top_k,
            max_hops=max_hops,
            escalation_threshold=escalation_threshold,
        )

    def _rewrite_query(self, query: str) -> list[str]:
        """
        Produce rewritten queries via:
        1. Original query (always included)
        2. Synonym expansion of key terms
        3. Decomposition of compound questions
        """
        rewrites = [query]

        # Synonym expansion
        words = query.lower().split()
        for i, word in enumerate(words):
            clean = re.sub(r'[^\w]', '', word)
            if clean in _SYNONYMS:
                for syn in _SYNONYMS[clean][:2]:
                    new_words = words.copy()
                    new_words[i] = syn
                    expanded = " ".join(new_words)
                    if expanded != query.lower():
                        rewrites.append(expanded)

        # Decomposition: split on "and", "also", or question marks
        parts = re.split(r'\band\b|\balso\b|\?', query)
        for part in parts:
            part = part.strip()
            if len(part) > 15 and part != query:
                rewrites.append(part)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for r in rewrites:
            normalized = r.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(r.strip())

        return unique

    def _select_strategy(self, query: str, task_class: str) -> QueryStrategy:
        """Select retrieval strategy based on query signals and task class."""
        q_lower = query.lower()

        # Check for contradiction signals
        contradiction_score = sum(1 for s in _CONTRADICTION_SIGNALS if s in q_lower)
        if contradiction_score >= 1:
            return QueryStrategy.CONTRADICTION_AWARE

        # Check for multi-hop signals
        multi_hop_score = sum(1 for s in _MULTI_HOP_SIGNALS if s in q_lower)
        if multi_hop_score >= 1:
            return QueryStrategy.MULTI_HOP

        # Task class escalation
        if task_class in ("audit", "verification", "legal"):
            return QueryStrategy.EXHAUSTIVE

        # Complex queries (long, multiple clauses)
        if len(query.split()) > 20 or query.count(",") >= 3:
            return QueryStrategy.MULTI_HOP

        return QueryStrategy.SIMPLE

    def _plan_filters(self, query: str) -> dict:
        """
        Extract metadata filters from the query.
        Looks for patterns like 'from:source', 'type:report', 'after:2024'.
        """
        filters: dict = {}
        # Explicit filter syntax: key:value
        filter_matches = re.findall(r'\b(\w+):(\S+)', query)
        for key, value in filter_matches:
            if key in ("from", "source", "author"):
                filters["source"] = value
            elif key in ("type", "doctype", "format"):
                filters["doc_type"] = value
            elif key in ("after", "since"):
                filters["date_after"] = value
            elif key in ("before", "until"):
                filters["date_before"] = value
            elif key in ("section", "chapter"):
                filters["section"] = value

        return filters
