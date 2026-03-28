"""
OmegA Observability + Telemetry.

Structured event collection, querying, summarization, and JSONL persistence.
Extracts RunMetrics from RunTrace for dashboard consumption.

Architecture: Cross-cutting (AEGIS + AEON)
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TelemetryEventType(str, Enum):
    STAGE_LATENCY = "stage_latency"
    RETRIEVAL_SCORE = "retrieval_score"
    RETRIEVAL_HIT = "retrieval_hit"
    VERIFIER_REJECT = "verifier_reject"
    GATE_DENY = "gate_deny"
    APPROVAL_WAIT = "approval_wait"
    PROVIDER_FAILURE = "provider_failure"
    CONTINUITY_RECOVERY = "continuity_recovery"
    TOKEN_USAGE = "token_usage"
    ERROR = "error"


@dataclass
class TelemetryEvent:
    """A single telemetry event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TelemetryEventType = TelemetryEventType.ERROR
    run_id: str = ""
    timestamp: float = field(default_factory=time.time)
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "data": self.data,
        }


@dataclass
class RunMetrics:
    """Aggregated metrics extracted from a single run trace."""
    run_id: str = ""
    total_latency_ms: float = 0.0
    stage_latencies: dict = field(default_factory=dict)
    retrieval_score: float = 0.0
    verification_V: float = 0.0
    provider: str = ""
    token_count: int = 0
    gate_allowed: bool = True

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "stage_latencies": {k: round(v, 2) for k, v in self.stage_latencies.items()},
            "retrieval_score": round(self.retrieval_score, 4),
            "verification_V": round(self.verification_V, 4),
            "provider": self.provider,
            "token_count": self.token_count,
            "gate_allowed": self.gate_allowed,
        }


class TelemetryCollector:
    """
    Central telemetry event collector.

    Stores events in memory and optionally flushes to JSONL files
    in a persist directory.
    """

    def __init__(self, persist_dir: str | None = None):
        self._events: list[TelemetryEvent] = []
        self._persist_dir = persist_dir

    def emit(
        self,
        event_type: TelemetryEventType,
        run_id: str,
        data: dict | None = None,
    ) -> TelemetryEvent:
        """Record a telemetry event."""
        event = TelemetryEvent(
            event_type=event_type,
            run_id=run_id,
            data=data or {},
        )
        self._events.append(event)
        return event

    def query(
        self,
        run_id: str | None = None,
        event_type: TelemetryEventType | None = None,
        since: float | None = None,
    ) -> list[TelemetryEvent]:
        """Filter events by run_id, event_type, and/or timestamp."""
        results = self._events
        if run_id is not None:
            results = [e for e in results if e.run_id == run_id]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if since is not None:
            results = [e for e in results if e.timestamp >= since]
        return results

    def summarize(self, run_id: str | None = None) -> dict:
        """Aggregate statistics over collected events."""
        events = self.query(run_id=run_id) if run_id else self._events
        type_counts: dict[str, int] = {}
        for e in events:
            type_counts[e.event_type.value] = type_counts.get(e.event_type.value, 0) + 1

        latencies = [
            e.data.get("elapsed_ms", 0.0)
            for e in events
            if e.event_type == TelemetryEventType.STAGE_LATENCY
            and "elapsed_ms" in e.data
        ]

        return {
            "total_events": len(events),
            "event_type_counts": type_counts,
            "avg_stage_latency_ms": (
                round(sum(latencies) / len(latencies), 2) if latencies else 0.0
            ),
            "run_ids": list({e.run_id for e in events}),
        }

    def flush(self) -> None:
        """Write all events to a JSONL file in persist_dir, then clear buffer."""
        if not self._persist_dir:
            raise RuntimeError("No persist_dir configured for telemetry flush")

        os.makedirs(self._persist_dir, exist_ok=True)
        filename = f"telemetry_{int(time.time())}_{uuid.uuid4().hex[:8]}.jsonl"
        path = os.path.join(self._persist_dir, filename)

        with open(path, "w") as f:
            for event in self._events:
                f.write(json.dumps(event.to_dict()) + "\n")

        self._events.clear()

    @property
    def event_count(self) -> int:
        return len(self._events)


def extract_metrics(trace: Any) -> RunMetrics:
    """
    Extract RunMetrics from a RunTrace.

    Accepts any object with the RunTrace interface (run_id, stages,
    total_elapsed_ms, provider_name, verification_V, gate_allowed).
    """
    stage_latencies: dict[str, float] = {}
    for s in getattr(trace, "stages", []):
        stage_latencies[s.stage.value] = s.elapsed_ms

    # Retrieval score: look for retrieve stage details
    retrieval_score = 0.0
    for s in getattr(trace, "stages", []):
        if s.stage.value == "retrieve" and "chunks_found" in s.details:
            retrieval_score = float(s.details.get("chunks_found", 0)) / max(
                s.details.get("total_candidates", 1), 1
            )

    return RunMetrics(
        run_id=getattr(trace, "run_id", ""),
        total_latency_ms=getattr(trace, "total_elapsed_ms", 0.0),
        stage_latencies=stage_latencies,
        retrieval_score=round(retrieval_score, 4),
        verification_V=getattr(trace, "verification_V", 0.0),
        provider=getattr(trace, "provider_name", ""),
        token_count=0,  # Populated from provider response if available
        gate_allowed=getattr(trace, "gate_allowed", True),
    )
