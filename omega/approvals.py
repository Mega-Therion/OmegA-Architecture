"""
AEGIS Human Approval Cockpit Backend — Queued approval workflow for gated actions.

Provides a structured queue for actions requiring human review, with
expiration, decision tracking, and audit statistics.

Architecture: AEGIS Phase 9
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from omega.envelope import ActionClass, ApprovalStatus


@dataclass
class ApprovalRequest:
    """A pending request for human approval of a gated action."""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    task_id: str | None = None
    action_envelope_id: str = ""
    action: str = ""
    action_class: ActionClass = ActionClass.READ
    risk_score: float = 0.0
    context: dict = field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: float = field(default_factory=time.time)
    expires_at: float | None = None

    def to_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "action_envelope_id": self.action_envelope_id,
            "action": self.action,
            "action_class": self.action_class.value,
            "risk_score": round(self.risk_score, 4),
            "context": self.context,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


@dataclass
class ApprovalDecision:
    """A recorded decision on an approval request."""
    decision_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    status: ApprovalStatus = ApprovalStatus.APPROVED
    decided_by: str = ""
    reason: str = ""
    modifications: dict = field(default_factory=dict)
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "status": self.status.value,
            "decided_by": self.decided_by,
            "reason": self.reason,
            "modifications": self.modifications,
            "decided_at": self.decided_at,
        }


class ApprovalQueue:
    """
    Central queue for human approval requests.

    Actions that exceed auto-approval thresholds are enqueued here.
    Human operators (or automated escalation policies) call decide()
    to approve or deny pending requests.
    """

    def __init__(self, default_ttl: float = 3600.0):
        self._pending: list[ApprovalRequest] = []
        self._decisions: list[ApprovalDecision] = []
        self._default_ttl = default_ttl

    def submit(
        self,
        run_id: str,
        action: str,
        action_class: ActionClass,
        risk_score: float,
        action_envelope_id: str = "",
        task_id: str | None = None,
        context: dict | None = None,
        ttl: float | None = None,
    ) -> ApprovalRequest:
        """Create and enqueue an approval request. Returns the request."""
        now = time.time()
        expires = now + (ttl if ttl is not None else self._default_ttl)
        req = ApprovalRequest(
            run_id=run_id,
            task_id=task_id,
            action_envelope_id=action_envelope_id,
            action=action,
            action_class=action_class,
            risk_score=risk_score,
            context=context or {},
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=expires,
        )
        self._pending.append(req)
        return req

    def decide(
        self,
        request_id: str,
        status: ApprovalStatus,
        decided_by: str,
        reason: str = "",
        modifications: dict | None = None,
    ) -> ApprovalDecision:
        """Record a decision for a pending request."""
        # Find and update the request
        for req in self._pending:
            if req.request_id == request_id:
                req.status = status
                break
        else:
            raise ValueError(f"No pending request with id '{request_id}'")

        decision = ApprovalDecision(
            request_id=request_id,
            status=status,
            decided_by=decided_by,
            reason=reason,
            modifications=modifications or {},
        )
        self._decisions.append(decision)
        return decision

    def pending(self) -> list[ApprovalRequest]:
        """Return all requests still in PENDING status (excluding expired)."""
        now = time.time()
        return [
            r for r in self._pending
            if r.status == ApprovalStatus.PENDING
            and (r.expires_at is None or r.expires_at > now)
        ]

    def get_decision(self, request_id: str) -> ApprovalDecision | None:
        """Look up the decision for a request, if one exists."""
        for d in reversed(self._decisions):
            if d.request_id == request_id:
                return d
        return None

    def is_expired(self, request_id: str) -> bool:
        """Check whether a request has expired."""
        now = time.time()
        for req in self._pending:
            if req.request_id == request_id:
                if req.expires_at is None:
                    return False
                return now >= req.expires_at
        return False

    def stats(self) -> dict:
        """Aggregate statistics about the queue."""
        now = time.time()
        total = len(self._pending)
        pending_count = sum(
            1 for r in self._pending
            if r.status == ApprovalStatus.PENDING
            and (r.expires_at is None or r.expires_at > now)
        )
        approved = sum(1 for r in self._pending if r.status == ApprovalStatus.APPROVED)
        denied = sum(1 for r in self._pending if r.status == ApprovalStatus.DENIED)
        expired = sum(
            1 for r in self._pending
            if r.status == ApprovalStatus.PENDING
            and r.expires_at is not None and now >= r.expires_at
        )
        return {
            "total_submitted": total,
            "pending": pending_count,
            "approved": approved,
            "denied": denied,
            "expired": expired,
            "decisions_recorded": len(self._decisions),
        }

    def to_dict(self) -> dict:
        return {
            "pending": [r.to_dict() for r in self.pending()],
            "decisions": [d.to_dict() for d in self._decisions],
            "stats": self.stats(),
        }
