"""
Session Continuity Store — Persistent session state across runs.

Tracks session lifecycle, snapshots state for crash recovery,
and produces continuity summaries for resumed sessions.

Architecture: AEON Phase 7 — Session Persistence
"""

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class SessionStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RESUMED = "resumed"
    CRASHED = "crashed"
    COMPLETED = "completed"


@dataclass
class SessionState:
    session_id: str
    run_ids: list[str] = field(default_factory=list)
    phylactery_head: str = ""
    memory_snapshot: dict = field(default_factory=dict)
    task_summaries: list[str] = field(default_factory=list)
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "run_ids": self.run_ids,
            "phylactery_head": self.phylactery_head,
            "memory_snapshot": self.memory_snapshot,
            "task_summaries": self.task_summaries,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SessionState":
        return cls(
            session_id=d["session_id"],
            run_ids=d.get("run_ids", []),
            phylactery_head=d.get("phylactery_head", ""),
            memory_snapshot=d.get("memory_snapshot", {}),
            task_summaries=d.get("task_summaries", []),
            status=SessionStatus(d.get("status", "active")),
            created_at=d.get("created_at", 0.0),
            updated_at=d.get("updated_at", 0.0),
            version=d.get("version", 1),
        )


@dataclass
class SessionSnapshot:
    snapshot_id: str
    session_id: str
    state: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "state": self.state,
            "created_at": self.created_at,
        }


@dataclass
class ContinuitySummary:
    summary_id: str
    session_id: str
    text: str
    claims_made: int
    evidence_cited: int
    unresolved: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "summary_id": self.summary_id,
            "session_id": self.session_id,
            "text": self.text,
            "claims_made": self.claims_made,
            "evidence_cited": self.evidence_cited,
            "unresolved": self.unresolved,
            "created_at": self.created_at,
        }


class SessionStore:
    """
    Manages session lifecycle: save, load, resume, and crash recovery.
    Optionally persists snapshots to disk as JSON files.
    """

    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = persist_dir
        self._sessions: dict[str, SessionState] = {}
        self._snapshots: dict[str, list[SessionSnapshot]] = {}

        if persist_dir and not os.path.isdir(persist_dir):
            os.makedirs(persist_dir, exist_ok=True)

        # Load existing snapshots from disk
        if persist_dir and os.path.isdir(persist_dir):
            self._load_from_disk()

    def save(self, state: SessionState) -> SessionSnapshot:
        """Save current session state and return a snapshot."""
        state.updated_at = time.time()
        state.version += 1
        self._sessions[state.session_id] = state

        snapshot = SessionSnapshot(
            snapshot_id=str(uuid.uuid4()),
            session_id=state.session_id,
            state=state.to_dict(),
        )

        if state.session_id not in self._snapshots:
            self._snapshots[state.session_id] = []
        self._snapshots[state.session_id].append(snapshot)

        self._persist(snapshot)
        return snapshot

    def load(self, session_id: str) -> SessionState | None:
        """Load the most recent state for a session."""
        if session_id in self._sessions:
            return self._sessions[session_id]

        snapshots = self._snapshots.get(session_id, [])
        if not snapshots:
            return None

        latest = max(snapshots, key=lambda s: s.created_at)
        state = SessionState.from_dict(latest.state)
        self._sessions[session_id] = state
        return state

    def resume(self, session_id: str) -> SessionState:
        """Load a session and mark it RESUMED."""
        state = self.load(session_id)
        if state is None:
            raise KeyError(f"Session '{session_id}' not found")
        state.status = SessionStatus.RESUMED
        state.updated_at = time.time()
        self._sessions[session_id] = state
        return state

    def crash_recover(self, session_id: str) -> SessionState:
        """
        Recover a crashed session. Loads the last known state,
        marks it RESUMED, and increments version.
        """
        state = self.load(session_id)
        if state is None:
            raise KeyError(f"Session '{session_id}' not found for crash recovery")
        state.status = SessionStatus.RESUMED
        state.updated_at = time.time()
        state.version += 1
        self._sessions[session_id] = state
        return state

    def list_sessions(self) -> list[dict]:
        """Return summary dicts for all known sessions."""
        result = []
        seen = set()
        for sid, state in self._sessions.items():
            seen.add(sid)
            result.append({
                "session_id": sid,
                "status": state.status.value,
                "run_count": len(state.run_ids),
                "version": state.version,
                "created_at": state.created_at,
                "updated_at": state.updated_at,
            })
        # Include sessions only known via snapshots
        for sid, snaps in self._snapshots.items():
            if sid not in seen and snaps:
                latest = max(snaps, key=lambda s: s.created_at)
                d = latest.state
                result.append({
                    "session_id": sid,
                    "status": d.get("status", "unknown"),
                    "run_count": len(d.get("run_ids", [])),
                    "version": d.get("version", 0),
                    "created_at": d.get("created_at", 0.0),
                    "updated_at": d.get("updated_at", 0.0),
                })
        return result

    def _persist(self, snapshot: SessionSnapshot) -> None:
        """Write snapshot to disk as JSON if persist_dir is set."""
        if not self.persist_dir:
            return
        filename = f"{snapshot.session_id}_{snapshot.snapshot_id}.json"
        filepath = os.path.join(self.persist_dir, filename)
        with open(filepath, "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    def _load_from_disk(self) -> None:
        """Load all snapshot files from persist_dir."""
        if not self.persist_dir:
            return
        for fname in os.listdir(self.persist_dir):
            if not fname.endswith(".json"):
                continue
            filepath = os.path.join(self.persist_dir, fname)
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                snap = SessionSnapshot(
                    snapshot_id=data["snapshot_id"],
                    session_id=data["session_id"],
                    state=data["state"],
                    created_at=data.get("created_at", 0.0),
                )
                sid = snap.session_id
                if sid not in self._snapshots:
                    self._snapshots[sid] = []
                self._snapshots[sid].append(snap)
            except (json.JSONDecodeError, KeyError):
                continue
