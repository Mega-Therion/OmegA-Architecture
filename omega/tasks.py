"""
Task Object Model — Structured task lifecycle with state machine transitions.

Every unit of work in OmegA is a TaskObject with typed status transitions,
parent-child relationships, and output tracking.

Architecture: AEON Phase 8 — Task Governance
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


# Legal state transitions
_LEGAL_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED, TaskStatus.AWAITING_APPROVAL},
    TaskStatus.BLOCKED: {TaskStatus.RUNNING, TaskStatus.FAILED},
    TaskStatus.AWAITING_APPROVAL: {TaskStatus.RUNNING, TaskStatus.BLOCKED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
}


@dataclass
class TaskTransition:
    from_status: TaskStatus
    to_status: TaskStatus
    reason: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class TaskObject:
    task_id: str
    objective: str
    parent_id: str | None = None
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    transitions: list[TaskTransition] = field(default_factory=list)
    outputs: list[dict] = field(default_factory=list)
    run_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def transition(self, new_status: TaskStatus, reason: str) -> TaskTransition:
        """
        Transition to a new status. Validates the transition is legal.
        Raises ValueError if the transition is not allowed.
        """
        allowed = _LEGAL_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Illegal transition: {self.status.value} -> {new_status.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )
        t = TaskTransition(
            from_status=self.status,
            to_status=new_status,
            reason=reason,
        )
        self.transitions.append(t)
        self.status = new_status
        self.updated_at = time.time()
        return t

    def add_output(self, output: dict) -> None:
        self.outputs.append(output)
        self.updated_at = time.time()

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "parent_id": self.parent_id,
            "objective": self.objective,
            "constraints": self.constraints,
            "success_criteria": self.success_criteria,
            "unknowns": self.unknowns,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "transitions": [t.to_dict() for t in self.transitions],
            "outputs": self.outputs,
            "run_ids": self.run_ids,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class TaskRegistry:
    """Central registry for all tasks with parent-child tracking."""

    def __init__(self):
        self.tasks: dict[str, TaskObject] = {}

    def create(
        self,
        objective: str,
        parent_id: str | None = None,
        constraints: list[str] | None = None,
        success_criteria: list[str] | None = None,
        unknowns: list[str] | None = None,
        dependencies: list[str] | None = None,
    ) -> TaskObject:
        task = TaskObject(
            task_id=str(uuid.uuid4()),
            objective=objective,
            parent_id=parent_id,
            constraints=constraints or [],
            success_criteria=success_criteria or [],
            unknowns=unknowns or [],
            dependencies=dependencies or [],
        )
        self.tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> TaskObject | None:
        return self.tasks.get(task_id)

    def transition(self, task_id: str, new_status: TaskStatus, reason: str) -> TaskTransition:
        task = self.tasks.get(task_id)
        if task is None:
            raise KeyError(f"Task '{task_id}' not found")
        return task.transition(new_status, reason)

    def children(self, task_id: str) -> list[TaskObject]:
        return [t for t in self.tasks.values() if t.parent_id == task_id]

    def active_tasks(self) -> list[TaskObject]:
        return [t for t in self.tasks.values() if not t.is_terminal]

    def to_dict(self) -> dict:
        return {
            "total": len(self.tasks),
            "active": len(self.active_tasks()),
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
        }
