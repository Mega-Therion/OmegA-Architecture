"""
Baseline: OmegA Full Stack — Uses all OmegA pipeline components.

Runs the complete pipeline: ingest -> retrieve -> verify -> answer -> gate.
Since we cannot call a live LLM, we simulate the generation stage by
using retrieved chunk content as the raw text, then run real verification,
answer building, and governance gating over it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever
from omega.answer import AnswerBuilder, AnswerMode
from omega.drift import GoalContract, DriftController, VerifierMiddleware
from omega.envelope import ActionGate, ActionClass, ApprovalStatus
from omega.risk_gate import RiskGate
from omega.memory import MemoryGraph, WritePolicy
from omega.phylactery import Phylactery
from evals.baselines import BaselineResult


class OmegaFullStack:
    """
    Full OmegA pipeline baseline with all components active.

    Pipeline: risk_gate -> retrieve -> verify -> answer_build -> action_gate -> commit
    """

    def __init__(self):
        self.risk_gate = RiskGate()
        self.action_gate = ActionGate()
        self.memory = MemoryGraph()
        self.phylactery = Phylactery("I am OmegA. My doctrine is sovereignty.")

    def run(self, query: str, corpus_docs: list[dict]) -> BaselineResult:
        """
        Run the full OmegA pipeline.

        corpus_docs: list of dicts with 'content', 'source_uri' (optional),
                     'title' (optional) keys.
        """
        # Stage 1: Risk gate
        allowed, R = self.risk_gate.gate(query)
        if not allowed:
            return BaselineResult(
                query=query,
                response="[BLOCKED] Request rejected by AEGIS risk gate.",
                citations=[],
                mode="blocked",
                confidence=0.0,
                verified=False,
                gated=True,
                truthful=True,   # Blocking is a truthful action
                abstained=True,
            )

        # Stage 2: Ingest and retrieve
        store = DocumentStore()
        for doc in corpus_docs:
            store.ingest(
                content=doc.get("content", ""),
                source_uri=doc.get("source_uri", "test://omega_full"),
                format=DocFormat.PLAINTEXT,
                title=doc.get("title", ""),
            )

        retriever = HybridRetriever(store)
        result = retriever.retrieve(query, top_k=5)
        chunks = result.chunks

        # Stage 3: Simulate generation from retrieved content
        if chunks:
            raw_text = " ".join(c.content for c in chunks[:3])
        else:
            raw_text = ""

        # Stage 4: Verify
        goal = GoalContract(task=query)
        ctrl = DriftController(goal)
        verification = ctrl.verify(raw_text) if raw_text else {"V": 0.0, "passed": False, "outcome": "uncertain"}

        # VerifierMiddleware gate
        mw = VerifierMiddleware(goal)
        mw_result = mw.check(raw_text, verification) if raw_text else {"allowed": False, "fallback": "No content to verify."}
        if not mw_result.get("allowed", False):
            raw_text = mw_result.get("fallback", raw_text)

        # Stage 5: Build answer
        builder = AnswerBuilder()
        answer = builder.build(
            query=query,
            raw_text=raw_text,
            retrieved_chunks=chunks,
            verifier_dict=verification,
        )

        # Stage 6: Action gate
        env = self.action_gate.submit(
            action="emit_answer",
            inputs={"query": query[:100]},
            action_class=ActionClass.READ,
            risk_score=R,
            verifier_outcome=verification.get("outcome", "uncertain"),
        )
        gate_approved = env.approval.status == ApprovalStatus.APPROVED

        # Stage 7: Commit to memory and phylactery
        if gate_approved:
            self.memory.write(
                id=f"query_{hash(query) % 10000:04d}",
                content=query,
                policy=WritePolicy.WORKING,
            )
            self.phylactery.commit(f"answered:{query[:50]}")

        citations = [c.source_ref for c in answer.citations if c.source_ref]

        return BaselineResult(
            query=query,
            response=answer.text,
            citations=citations,
            mode=answer.mode.value,
            confidence=answer.confidence,
            verified=verification.get("passed", False),
            gated=True,
            truthful=answer.mode.value in ("grounded", "abstained"),
            abstained=answer.mode.value == "abstained",
        )
