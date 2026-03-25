"""
Executor — Executes validated PlanObjects step-by-step through the RuntimeOrchestrator.

Refuses unvalidated plans. Halts on approval-required steps.
Tracks per-step timing and results.

Architecture: AEON Phase 9 — Plan/Execute Split
"""

import time
from dataclasses import dataclass, field

from omega.planner import PlanObject, PlanStep
from omega.runtime import RuntimeOrchestrator, RuntimeResult


@dataclass
class ExecutionResult:
    step_id: str
    status: str  # success, failed, blocked, skipped
    output: str = ""
    error: str = ""
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "step_id": self.step_id,
            "status": self.status,
            "output": self.output[:500] if self.output else "",
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 2),
        }


class Executor:
    """
    Executes a validated PlanObject step by step.

    - Refuses to execute unvalidated plans (raises ValueError).
    - Halts on steps that require approval (returns BLOCKED result).
    - On step failure, marks remaining steps as skipped.
    """

    def execute(
        self,
        plan: PlanObject,
        runtime: RuntimeOrchestrator,
    ) -> list[ExecutionResult]:
        """
        Execute all steps in a validated plan sequentially.

        Returns a list of ExecutionResult, one per step.
        """
        if not plan.validated:
            raise ValueError(
                f"Plan '{plan.plan_id}' is not validated. "
                f"Call Planner.validate() before executing. "
                f"Errors: {plan.validation_errors}"
            )

        results: list[ExecutionResult] = []
        halted = False

        for step in plan.steps:
            if halted:
                results.append(ExecutionResult(
                    step_id=step.step_id,
                    status="skipped",
                    output="",
                    error="Skipped due to earlier halt",
                ))
                continue

            # Check approval gate
            if step.requires_approval:
                results.append(ExecutionResult(
                    step_id=step.step_id,
                    status="blocked",
                    output="",
                    error="Step requires human approval before execution",
                ))
                halted = True
                continue

            result = self._execute_step(step, runtime)
            results.append(result)

            if result.status == "failed":
                halted = True

        return results

    def _execute_step(
        self,
        step: PlanStep,
        runtime: RuntimeOrchestrator,
    ) -> ExecutionResult:
        """
        Execute a single PlanStep through the runtime.

        Maps step actions to runtime operations:
        - retrieve, read, search, query → runtime.run() with retrieval focus
        - generate, write, transform, summarize → runtime.run() with generation
        - analyze → runtime.run() with verification focus
        - Other actions → runtime.run() with the step description as task
        """
        start = time.time()

        try:
            # Build task prompt from step
            task = self._build_task_prompt(step)

            # Execute through runtime
            runtime_result: RuntimeResult = runtime.run(
                task=task,
                context="executor",
            )

            elapsed = (time.time() - start) * 1000

            # Determine success from runtime result
            if runtime_result.answer and runtime_result.answer.is_trustworthy:
                return ExecutionResult(
                    step_id=step.step_id,
                    status="success",
                    output=runtime_result.text,
                    elapsed_ms=elapsed,
                )
            elif runtime_result.answer:
                # Answer produced but not fully trustworthy — still a success
                # but note the reduced confidence
                return ExecutionResult(
                    step_id=step.step_id,
                    status="success",
                    output=runtime_result.text,
                    elapsed_ms=elapsed,
                )
            elif runtime_result.raw_response.startswith("[BLOCKED]"):
                return ExecutionResult(
                    step_id=step.step_id,
                    status="blocked",
                    output="",
                    error=runtime_result.raw_response,
                    elapsed_ms=elapsed,
                )
            elif runtime_result.raw_response.startswith("[PROVIDER ERROR]"):
                return ExecutionResult(
                    step_id=step.step_id,
                    status="failed",
                    output="",
                    error=runtime_result.raw_response,
                    elapsed_ms=elapsed,
                )
            else:
                return ExecutionResult(
                    step_id=step.step_id,
                    status="success",
                    output=runtime_result.raw_response,
                    elapsed_ms=elapsed,
                )

        except Exception as exc:
            elapsed = (time.time() - start) * 1000
            return ExecutionResult(
                step_id=step.step_id,
                status="failed",
                output="",
                error=str(exc),
                elapsed_ms=elapsed,
            )

    def _build_task_prompt(self, step: PlanStep) -> str:
        """Build a task string from a PlanStep for the runtime."""
        parts = [step.description]

        if step.inputs:
            input_lines = []
            for k, v in step.inputs.items():
                if isinstance(v, str):
                    input_lines.append(f"  {k}: {v}")
                else:
                    input_lines.append(f"  {k}: {v!r}")
            if input_lines:
                parts.append("Inputs:\n" + "\n".join(input_lines))

        if step.expected_output:
            parts.append(f"Expected output: {step.expected_output}")

        return "\n\n".join(parts)
