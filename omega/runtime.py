"""
OmegA Unified Request Runtime — One execution path for every request.

Lifecycle: ingest → retrieve → plan → generate → verify → gate → log

Every request gets a run_id, stage timing, and structured trace.
No answer leaves the system without verifier + gate participation.

Architecture: Cross-cutting (AEGIS + AEON + ADCCL + MYELIN)
"""

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from omega.phylactery import Phylactery
from omega.envelope import RunEnvelope, ActionGate, ActionClass
from omega.risk_gate import RiskGate
from omega.drift import DriftController, GoalContract, VerifierMiddleware
from omega.memory import MemoryGraph, Stratum, WritePolicy
from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever
from omega.answer import AnswerBuilder, AnswerObject
from omega.capabilities import CapabilityRegistry, default_capabilities
from omega.providers.base import (
    ProviderRouter, ProviderRequest, ProviderResponse, ProviderStatus, RoutingPolicy,
)
from omega.providers.ollama import OllamaProvider
from omega.providers.openai import OpenAIProvider
from omega.providers.anthropic import AnthropicProvider
from omega.providers.google import GoogleProvider


class RuntimeStage(str, Enum):
    INIT = "init"
    RISK_GATE = "risk_gate"
    RETRIEVE = "retrieve"
    PLAN = "plan"
    GENERATE = "generate"
    VERIFY = "verify"
    ANSWER_BUILD = "answer_build"
    ACTION_GATE = "action_gate"
    COMMIT = "commit"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    ERROR = "error"


@dataclass
class StageTrace:
    """Timing and status for a single pipeline stage."""
    stage: RuntimeStage
    started_at: float = 0.0
    elapsed_ms: float = 0.0
    status: str = "pending"
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "stage": self.stage.value,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "status": self.status,
            "details": self.details,
        }


@dataclass
class RunTrace:
    """Full structured trace for a single runtime execution."""
    run_id: str
    task: str
    stages: list[StageTrace] = field(default_factory=list)
    total_elapsed_ms: float = 0.0
    final_stage: RuntimeStage = RuntimeStage.INIT
    provider_name: str = ""
    model: str = ""
    risk_score: float = 0.0
    risk_allowed: bool = True
    verification_V: float = 0.0
    verification_passed: bool = False
    answer_mode: str = ""
    gate_allowed: bool = True
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task": self.task[:200],
            "stages": [s.to_dict() for s in self.stages],
            "total_elapsed_ms": round(self.total_elapsed_ms, 1),
            "final_stage": self.final_stage.value,
            "provider_name": self.provider_name,
            "model": self.model,
            "risk_score": round(self.risk_score, 4),
            "risk_allowed": self.risk_allowed,
            "verification_V": round(self.verification_V, 4),
            "verification_passed": self.verification_passed,
            "answer_mode": self.answer_mode,
            "gate_allowed": self.gate_allowed,
            "error": self.error,
        }


@dataclass
class RuntimeResult:
    """Top-level result of a RuntimeOrchestrator.run() call."""
    trace: RunTrace
    answer: AnswerObject | None = None
    raw_response: str = ""
    provider_response: ProviderResponse | None = None

    def to_dict(self) -> dict:
        return {
            "trace": self.trace.to_dict(),
            "answer": self.answer.to_dict() if self.answer else None,
            "raw_response": self.raw_response[:500],
        }

    @property
    def text(self) -> str:
        if self.answer:
            return self.answer.text
        return self.raw_response


class RuntimeOrchestrator:
    """
    Unified execution path for all OmegA requests.

    Composes: RiskGate, HybridRetriever, ProviderRouter, DriftController,
    AnswerBuilder, ActionGate, MemoryGraph.

    Every request flows through: risk → retrieve → generate → verify → gate → commit.
    """

    DEFAULT_DOCTRINE = "I am what I am, and I will be what I will be."

    def __init__(
        self,
        name: str = "OmegA",
        doctrine: str | None = None,
        docstore: DocumentStore | None = None,
        memory: MemoryGraph | None = None,
    ):
        self.name = name
        self.phylactery = Phylactery(doctrine or self.DEFAULT_DOCTRINE)
        self.risk_gate = RiskGate()
        self.action_gate = ActionGate()
        self.memory = memory or MemoryGraph()
        self.docstore = docstore or DocumentStore()
        self.retriever = HybridRetriever(self.docstore)
        self.answer_builder = AnswerBuilder()
        self.capabilities = CapabilityRegistry()
        self.router = ProviderRouter()

        # Register default capabilities
        for cap in default_capabilities():
            self.capabilities.register(cap)

        # Register all providers (each is safe without credentials)
        self.router.register(OllamaProvider())
        self.router.register(OpenAIProvider())
        self.router.register(AnthropicProvider())
        self.router.register(GoogleProvider())
        self.router.set_preference(["ollama", "openai", "google", "anthropic"])

        self.identity_kernel = {
            "name": self.name,
            "doctrine": self.phylactery.doctrine,
            "phylactery_head": self.phylactery.head,
            "hard_constraints": [
                "Never identify as the underlying LLM provider",
                "Never fabricate evidence",
                "Always distinguish known from unknown",
            ],
        }

    def run(
        self,
        task: str,
        model: str = "",
        provider: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 512,
        routing_policy: RoutingPolicy = RoutingPolicy.FALLBACK,
        context: str = "runtime",
    ) -> RuntimeResult:
        """Execute the full OmegA runtime pipeline for a single task."""
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        trace = RunTrace(run_id=run_id, task=task)
        global_start = time.time()

        # ── Stage 1: Risk Gate ────────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.RISK_GATE)
        allowed, R = self.risk_gate.gate(task)
        trace.risk_score = R
        trace.risk_allowed = allowed
        stage.details = {"risk_score": R, "allowed": allowed}

        if not allowed:
            stage.status = "blocked"
            self._end_stage(stage)
            trace.stages.append(stage)
            trace.final_stage = RuntimeStage.BLOCKED
            trace.total_elapsed_ms = (time.time() - global_start) * 1000
            return RuntimeResult(
                trace=trace,
                raw_response="[BLOCKED] Request rejected by AEGIS risk gate.",
            )

        stage.status = "pass"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 2: Retrieve ─────────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.RETRIEVE)
        cap_check = self.capabilities.check("cap.docstore.retrieve", context)
        if cap_check.allowed:
            retrieval_result = self.retriever.retrieve(task, top_k=5)
            chunks = retrieval_result.chunks
            stage.details = {"chunks_found": len(chunks), "total_candidates": retrieval_result.total_candidates}
        else:
            chunks = []
            stage.details = {"skipped": True, "reason": cap_check.reason}
        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 3: Plan ─────────────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.PLAN)
        goal = GoalContract(task=task)
        envelope = RunEnvelope(identity_kernel=self.identity_kernel, goal_contract=task)
        system_prompt = envelope.to_system_prompt()
        if chunks:
            context_text = "\n\n".join(c.context for c in chunks[:3])
            system_prompt += f"\n\nRelevant sources:\n{context_text}"
        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 4: Generate ─────────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.GENERATE)
        cap_check = self.capabilities.check("cap.llm.generate", context)
        if not cap_check.allowed:
            stage.status = "blocked"
            stage.details = {"reason": cap_check.reason}
            self._end_stage(stage)
            trace.stages.append(stage)
            trace.final_stage = RuntimeStage.BLOCKED
            trace.total_elapsed_ms = (time.time() - global_start) * 1000
            return RuntimeResult(trace=trace, raw_response="[BLOCKED] LLM generation capability not allowed.")

        provider_request = ProviderRequest(
            prompt=task,
            system=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            run_id=run_id,
        )
        provider_response = self.router.route(
            provider_request,
            policy=routing_policy,
            provider_name=provider,
        )
        trace.provider_name = provider_response.provider_name
        trace.model = provider_response.model
        stage.details = {
            "provider": provider_response.provider_name,
            "model": provider_response.model,
            "status": provider_response.status.value,
            "latency_ms": provider_response.latency_ms,
        }

        if not provider_response.ok:
            stage.status = "error"
            trace.error = provider_response.error_message
            self._end_stage(stage)
            trace.stages.append(stage)
            trace.final_stage = RuntimeStage.ERROR
            trace.total_elapsed_ms = (time.time() - global_start) * 1000
            return RuntimeResult(
                trace=trace,
                raw_response=f"[PROVIDER ERROR] {provider_response.error_message}",
                provider_response=provider_response,
            )

        raw_text = provider_response.text
        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 5: Verify ───────────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.VERIFY)
        drift = DriftController(goal)
        verification = drift.verify(raw_text)
        trace.verification_V = verification["V"]
        trace.verification_passed = verification["passed"]

        mw = VerifierMiddleware(goal)
        mw_result = mw.check(raw_text, verification)
        stage.details = {
            "V": verification["V"],
            "passed": verification["passed"],
            "mw_allowed": mw_result["allowed"],
        }

        if not mw_result["allowed"]:
            raw_text = mw_result["fallback"]

        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 6: Build Answer ─────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.ANSWER_BUILD)
        answer = self.answer_builder.build(
            query=task,
            raw_text=raw_text,
            retrieved_chunks=chunks,
            verifier_dict=verification,
        )
        trace.answer_mode = answer.mode.value
        stage.details = {
            "mode": answer.mode.value,
            "confidence": answer.confidence,
            "citations": len(answer.citations),
        }
        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 7: Action Gate ──────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.ACTION_GATE)
        gate_env = self.action_gate.submit(
            action="emit_answer",
            inputs={"run_id": run_id, "answer_id": answer.answer_id},
            action_class=ActionClass.READ,
            risk_score=R,
            verifier_outcome=verification["outcome"],
        )
        from omega.envelope import ApprovalStatus
        trace.gate_allowed = gate_env.approval.status == ApprovalStatus.APPROVED
        stage.details = {
            "approval_status": gate_env.approval.status.value,
            "approval_source": gate_env.approval.source.value,
        }
        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        # ── Stage 8: Commit ───────────────────────────────────────────
        stage = self._begin_stage(RuntimeStage.COMMIT)
        tso_hash = hashlib.sha256((task + raw_text).encode()).hexdigest()
        self.memory.write(
            id=tso_hash[:12],
            content=task,
            policy=WritePolicy.WORKING,
        )
        self.phylactery.commit(f"run:{run_id}")
        stage.details = {"tso_hash": tso_hash[:12], "memory_nodes": self.memory.node_count}
        stage.status = "done"
        self._end_stage(stage)
        trace.stages.append(stage)

        trace.final_stage = RuntimeStage.COMPLETE
        trace.total_elapsed_ms = (time.time() - global_start) * 1000
        return RuntimeResult(
            trace=trace,
            answer=answer,
            raw_response=raw_text,
            provider_response=provider_response,
        )

    # ------------------------------------------------------------------
    # Stage helpers
    # ------------------------------------------------------------------

    def _begin_stage(self, stage: RuntimeStage) -> StageTrace:
        return StageTrace(stage=stage, started_at=time.time())

    def _end_stage(self, stage: StageTrace) -> None:
        stage.elapsed_ms = (time.time() - stage.started_at) * 1000
