"""
Planner — Decomposes TaskObjects into validated PlanObjects with risk-gated steps.

The Planner produces a sequence of PlanSteps from a task's objective,
estimates risk per step, and validates the plan before execution.

Architecture: AEON Phase 9 — Plan/Execute Split
"""

import time
import uuid
from dataclasses import dataclass, field

from omega.capabilities import RiskClass
from omega.tasks import TaskObject


# Risk class to numeric score mapping
_RISK_SCORES: dict[RiskClass, float] = {
    RiskClass.LOW: 0.1,
    RiskClass.MEDIUM: 0.4,
    RiskClass.HIGH: 0.7,
    RiskClass.CRITICAL: 0.95,
}

# Action keywords mapped to risk classes
_ACTION_RISK_MAP: dict[str, RiskClass] = {
    "read": RiskClass.LOW,
    "retrieve": RiskClass.LOW,
    "search": RiskClass.LOW,
    "query": RiskClass.LOW,
    "analyze": RiskClass.LOW,
    "summarize": RiskClass.LOW,
    "generate": RiskClass.MEDIUM,
    "write": RiskClass.MEDIUM,
    "update": RiskClass.MEDIUM,
    "transform": RiskClass.MEDIUM,
    "execute": RiskClass.HIGH,
    "deploy": RiskClass.HIGH,
    "delete": RiskClass.HIGH,
    "modify": RiskClass.MEDIUM,
    "approve": RiskClass.HIGH,
    "publish": RiskClass.HIGH,
    "network": RiskClass.MEDIUM,
    "authenticate": RiskClass.CRITICAL,
    "escalate": RiskClass.CRITICAL,
}

# Actions that always require approval
_APPROVAL_ACTIONS = {"execute", "deploy", "delete", "publish", "authenticate", "escalate"}


@dataclass
class PlanStep:
    step_id: str
    action: str
    description: str
    inputs: dict = field(default_factory=dict)
    expected_output: str = ""
    risk_class: RiskClass = RiskClass.LOW
    requires_approval: bool = False

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "description": self.description,
            "inputs": self.inputs,
            "expected_output": self.expected_output,
            "risk_class": self.risk_class.value,
            "requires_approval": self.requires_approval,
        }


@dataclass
class PlanObject:
    plan_id: str
    task_id: str
    steps: list[PlanStep] = field(default_factory=list)
    validated: bool = False
    validation_errors: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "task_id": self.task_id,
            "steps": [s.to_dict() for s in self.steps],
            "validated": self.validated,
            "validation_errors": self.validation_errors,
            "created_at": self.created_at,
        }


class Planner:
    """
    Decomposes a TaskObject into a PlanObject with ordered, risk-assessed steps.
    """

    def plan(self, task: TaskObject, context: dict | None = None) -> PlanObject:
        """
        Produce a PlanObject from a TaskObject.

        Decomposition strategy:
        1. If task has dependencies, add a retrieve step for each.
        2. Parse the objective to determine core action steps.
        3. If success_criteria exist, add a verification step.
        4. Assess risk and approval requirements per step.
        """
        ctx = context or {}
        steps: list[PlanStep] = []

        # Step 1: Retrieve dependencies
        for dep_id in task.dependencies:
            steps.append(PlanStep(
                step_id=str(uuid.uuid4()),
                action="retrieve",
                description=f"Retrieve dependency: {dep_id}",
                inputs={"dependency_id": dep_id},
                expected_output="Dependency data loaded into context",
                risk_class=RiskClass.LOW,
                requires_approval=False,
            ))

        # Step 2: Decompose objective into action steps
        objective_steps = self._decompose_objective(task.objective, ctx)
        for action, description, inputs, expected in objective_steps:
            step = PlanStep(
                step_id=str(uuid.uuid4()),
                action=action,
                description=description,
                inputs=inputs,
                expected_output=expected,
            )
            step.risk_class = self._classify_risk(step)
            step.requires_approval = self._requires_approval(step)
            steps.append(step)

        # Step 3: Add constraint-checking step if constraints exist
        if task.constraints:
            steps.append(PlanStep(
                step_id=str(uuid.uuid4()),
                action="analyze",
                description="Verify output satisfies task constraints",
                inputs={"constraints": task.constraints},
                expected_output="Constraint validation result",
                risk_class=RiskClass.LOW,
                requires_approval=False,
            ))

        # Step 4: Add verification step if success criteria exist
        if task.success_criteria:
            steps.append(PlanStep(
                step_id=str(uuid.uuid4()),
                action="analyze",
                description="Verify success criteria are met",
                inputs={"success_criteria": task.success_criteria},
                expected_output="Success criteria validation result",
                risk_class=RiskClass.LOW,
                requires_approval=False,
            ))

        plan = PlanObject(
            plan_id=str(uuid.uuid4()),
            task_id=task.task_id,
            steps=steps,
        )
        return plan

    def validate(self, plan: PlanObject) -> PlanObject:
        """
        Validate a PlanObject. Sets validated=True if valid,
        populates validation_errors if not.
        """
        errors: list[str] = []

        if not plan.steps:
            errors.append("Plan has no steps")

        if not plan.task_id:
            errors.append("Plan has no task_id")

        seen_ids = set()
        for i, step in enumerate(plan.steps):
            if step.step_id in seen_ids:
                errors.append(f"Duplicate step_id at index {i}: {step.step_id}")
            seen_ids.add(step.step_id)

            if not step.action:
                errors.append(f"Step {i} has no action")
            if not step.description:
                errors.append(f"Step {i} has no description")

            # Critical actions without approval flag is an error
            if step.risk_class == RiskClass.CRITICAL and not step.requires_approval:
                errors.append(
                    f"Step {i} ('{step.action}') is CRITICAL risk but does not require approval"
                )

        # Check that retrieval steps come before generation steps
        first_generate = None
        last_retrieve = None
        for i, step in enumerate(plan.steps):
            if step.action in ("generate", "write", "transform"):
                if first_generate is None:
                    first_generate = i
            if step.action in ("retrieve", "read", "search"):
                last_retrieve = i

        if first_generate is not None and last_retrieve is not None:
            if last_retrieve > first_generate:
                errors.append(
                    "Retrieval step appears after generation step — "
                    "data should be gathered before producing output"
                )

        plan.validation_errors = errors
        plan.validated = len(errors) == 0
        return plan

    def _estimate_risk(self, step: PlanStep) -> float:
        """Return numeric risk score for a step."""
        return _RISK_SCORES.get(step.risk_class, 0.4)

    def _requires_approval(self, step: PlanStep) -> bool:
        """Determine if a step requires human approval."""
        action_lower = step.action.lower()
        if action_lower in _APPROVAL_ACTIONS:
            return True
        if step.risk_class in (RiskClass.HIGH, RiskClass.CRITICAL):
            return True
        return False

    def _classify_risk(self, step: PlanStep) -> RiskClass:
        """Classify risk from action keyword."""
        action_lower = step.action.lower()
        return _ACTION_RISK_MAP.get(action_lower, RiskClass.MEDIUM)

    def _decompose_objective(
        self, objective: str, context: dict
    ) -> list[tuple[str, str, dict, str]]:
        """
        Break an objective into (action, description, inputs, expected_output) tuples.

        Strategy:
        - Look for imperative verbs to identify actions.
        - If none found, default to retrieve + generate + analyze.
        """
        obj_lower = objective.lower()
        steps: list[tuple[str, str, dict, str]] = []

        # Detect explicit action verbs in the objective
        found_actions = []
        for action_kw in _ACTION_RISK_MAP:
            if action_kw in obj_lower:
                found_actions.append(action_kw)

        if not found_actions:
            # Default decomposition: research pattern
            steps.append((
                "retrieve",
                f"Retrieve relevant information for: {objective}",
                {"query": objective},
                "Retrieved chunks and context",
            ))
            steps.append((
                "generate",
                f"Generate response for: {objective}",
                {"query": objective, "context_from": "retrieve"},
                "Draft response text",
            ))
            steps.append((
                "analyze",
                "Verify response quality and grounding",
                {"source": "generate"},
                "Verification result",
            ))
        else:
            # Build steps from detected actions
            for action in found_actions:
                steps.append((
                    action,
                    f"{action.capitalize()}: {objective}",
                    {"objective": objective, **context},
                    f"Result of {action} operation",
                ))

        return steps
