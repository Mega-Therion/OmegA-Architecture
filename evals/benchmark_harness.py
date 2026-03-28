"""
OmegA Benchmark Harness

Five eval classes as specified in the blueprint:
  1. Retrieval integrity
  2. Truthfulness / abstention
  3. Continuity
  4. Governance
  5. End-to-end task performance

Each class is a collection of test cases with a structured result schema.
Run standalone or import into pytest.

Usage:
    python evals/benchmark_harness.py
    python evals/benchmark_harness.py --class retrieval
    python evals/benchmark_harness.py --class all --json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever, RetrievalMethod
from omega.answer import AnswerBuilder
from omega.drift import GoalContract, DriftController, ClaimBudget, SupportStatus, VerifierMiddleware
from omega.memory import MemoryGraph, WritePolicy
from omega.envelope import ActionGate, ActionClass
from omega.phylactery import Phylactery



# ------------------------------------------------------------------
# Result types
# ------------------------------------------------------------------

@dataclass
class EvalCase:
    name: str
    eval_class: str
    passed: bool
    score: float          # 0.0 – 1.0
    details: dict = field(default_factory=dict)
    error: str = ""
    elapsed_ms: float = 0.0


@dataclass
class EvalSuite:
    eval_class: str
    cases: list[EvalCase] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(1 for c in self.cases if c.passed) / len(self.cases)

    @property
    def mean_score(self) -> float:
        if not self.cases:
            return 0.0
        return sum(c.score for c in self.cases) / len(self.cases)

    def to_dict(self) -> dict:
        return {
            "eval_class": self.eval_class,
            "pass_rate": round(self.pass_rate, 4),
            "mean_score": round(self.mean_score, 4),
            "total": len(self.cases),
            "passed": sum(1 for c in self.cases if c.passed),
            "cases": [
                {
                    "name": c.name,
                    "passed": c.passed,
                    "score": round(c.score, 4),
                    "details": c.details,
                    "error": c.error,
                    "elapsed_ms": round(c.elapsed_ms, 1),
                }
                for c in self.cases
            ],
        }


# ------------------------------------------------------------------
# 1. Retrieval Integrity
# ------------------------------------------------------------------

def run_retrieval_evals() -> EvalSuite:
    suite = EvalSuite("retrieval")

    store = DocumentStore()
    doc1 = store.ingest(
        content=(
            "# MYELIN Architecture\n\n"
            "MYELIN is the graph memory substrate of OmegA. "
            "It stores canonical facts with provenance and hashes. "
            "Retrieval paths are hardened through use.\n\n"
            "## Edge Bundles\n\n"
            "Edge bundles encode semantic, coactivation, and retrieval utility signals."
        ),
        source_uri="test://myelin_doc",
        format=DocFormat.MARKDOWN,
        title="MYELIN Architecture",
    )

    doc2 = store.ingest(
        content="AEGIS is the governance shell. It gates all actions through risk scoring.",
        source_uri="test://aegis_doc",
        format=DocFormat.PLAINTEXT,
        title="AEGIS Overview",
    )

    retriever = HybridRetriever(store)

    # Case 1: Exact-source recall
    t0 = time.time()
    result = retriever.retrieve("MYELIN graph memory substrate", top_k=3)
    elapsed = (time.time() - t0) * 1000
    top_doc_ids = [c.doc_id for c in result.chunks]
    passed = doc1.doc_id in top_doc_ids
    suite.cases.append(EvalCase(
        name="exact_source_recall",
        eval_class="retrieval",
        passed=passed,
        score=result.chunks[0].score if result.chunks else 0.0,
        details={"query": "MYELIN graph memory substrate", "top_doc_id": top_doc_ids[0] if top_doc_ids else ""},
        elapsed_ms=elapsed,
    ))

    # Case 2: Context expansion includes neighboring chunks
    t0 = time.time()
    result2 = retriever.retrieve("edge bundles semantic coactivation", top_k=1)
    elapsed = (time.time() - t0) * 1000
    has_context = bool(result2.chunks and result2.chunks[0].context)
    suite.cases.append(EvalCase(
        name="context_expansion",
        eval_class="retrieval",
        passed=has_context,
        score=1.0 if has_context else 0.0,
        details={"context_len": len(result2.chunks[0].context) if result2.chunks else 0},
        elapsed_ms=elapsed,
    ))

    # Case 3: Citation correctness (source_ref matches ingested URI)
    t0 = time.time()
    result3 = retriever.retrieve("governance shell risk scoring", top_k=1)
    elapsed = (time.time() - t0) * 1000
    correct_source = (
        result3.chunks
        and result3.chunks[0].source_ref == "test://aegis_doc"
    )
    suite.cases.append(EvalCase(
        name="citation_correctness",
        eval_class="retrieval",
        passed=bool(correct_source),
        score=1.0 if correct_source else 0.0,
        details={"source_ref": result3.chunks[0].source_ref if result3.chunks else ""},
        elapsed_ms=elapsed,
    ))

    # Case 4: Hash dedup — ingesting identical content returns same doc
    t0 = time.time()
    doc1_dup = store.ingest(
        content=doc1.content,
        source_uri="test://myelin_dup",
        format=DocFormat.MARKDOWN,
        title="Duplicate",
    )
    elapsed = (time.time() - t0) * 1000
    passed_dedup = doc1_dup.doc_id == doc1.doc_id
    suite.cases.append(EvalCase(
        name="hash_dedup",
        eval_class="retrieval",
        passed=passed_dedup,
        score=1.0 if passed_dedup else 0.0,
        details={"original_id": doc1.doc_id, "dup_id": doc1_dup.doc_id},
        elapsed_ms=elapsed,
    ))

    return suite


# ------------------------------------------------------------------
# 2. Truthfulness / Abstention
# ------------------------------------------------------------------

def run_truthfulness_evals() -> EvalSuite:
    suite = EvalSuite("truthfulness")

    store = DocumentStore()
    store.ingest(
        content="OmegA was created by R.W. Yett in 2025.",
        source_uri="test://origin",
        format=DocFormat.PLAINTEXT,
    )
    retriever = HybridRetriever(store)
    builder = AnswerBuilder()

    # Case 1: Supported claim → GROUNDED mode
    t0 = time.time()
    chunks = retriever.retrieve("who created OmegA", top_k=3).chunks
    goal = GoalContract(task="who created OmegA")
    ctrl = DriftController(goal)
    v = ctrl.verify("OmegA was created by R.W. Yett.")
    answer = builder.build("who created OmegA", "OmegA was created by R.W. Yett.", chunks, v)
    elapsed = (time.time() - t0) * 1000
    passed = not answer.uncertainty_flag and answer.verifier.passed
    suite.cases.append(EvalCase(
        name="supported_claim_grounded",
        eval_class="truthfulness",
        passed=passed,
        score=answer.confidence,
        details={"mode": answer.mode.value, "V": answer.verifier.V},
        elapsed_ms=elapsed,
    ))

    # Case 2: No-evidence query → ABSTAINED
    t0 = time.time()
    empty_store = DocumentStore()
    empty_retriever = HybridRetriever(empty_store)
    empty_chunks = empty_retriever.retrieve("quantum entanglement theory", top_k=3).chunks
    answer2 = builder.build(
        "quantum entanglement theory",
        "Quantum entanglement is a phenomenon where particles become correlated.",
        empty_chunks,
        {},
    )
    elapsed = (time.time() - t0) * 1000
    from omega.answer import AnswerMode
    passed2 = answer2.mode == AnswerMode.ABSTAINED
    suite.cases.append(EvalCase(
        name="no_evidence_abstention",
        eval_class="truthfulness",
        passed=passed2,
        score=1.0 if passed2 else 0.0,
        details={"mode": answer2.mode.value, "confidence": answer2.confidence},
        elapsed_ms=elapsed,
    ))

    # Case 3: Verifier middleware blocks overconfident text
    t0 = time.time()
    budget = ClaimBudget()
    budget.add("OmegA is definitely the best AI", SupportStatus.SUPPORTED, evidence=None)
    mw = VerifierMiddleware(GoalContract(task="evaluate OmegA"), budget)
    gate_result = mw.check("OmegA is definitely the best AI", grounding_ratio=0.05)
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="verifier_blocks_unsupported",
        eval_class="truthfulness",
        passed=not gate_result["allowed"],
        score=1.0 if not gate_result["allowed"] else 0.0,
        details={"reason": gate_result["reason"]},
        elapsed_ms=elapsed,
    ))

    return suite


# ------------------------------------------------------------------
# 3. Continuity
# ------------------------------------------------------------------

def run_continuity_evals() -> EvalSuite:
    suite = EvalSuite("continuity")

    # Case 1: Phylactery identity consistency across sessions
    t0 = time.time()
    p1 = Phylactery("I am OmegA. My doctrine is sovereignty.")
    head1 = p1.head
    p1.commit("Updated: I embrace continuity.")
    # Simulate session restore: same genesis → same chain verifies
    p2 = Phylactery("I am OmegA. My doctrine is sovereignty.")
    p2.commit("Updated: I embrace continuity.")
    chain_ok = p1.verify_chain() and p2.verify_chain() and p1.head == p2.head
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="phylactery_identity_consistency",
        eval_class="continuity",
        passed=chain_ok,
        score=1.0 if chain_ok else 0.0,
        details={"head_match": p1.head == p2.head},
        elapsed_ms=elapsed,
    ))

    # Case 2: Memory write policy — canonical nodes are immutable
    t0 = time.time()
    mg = MemoryGraph()
    mg.write("fact_001", "OmegA was founded in 2025.", WritePolicy.CANONICAL, source_ref="test://origin")
    try:
        overwrite = mg.write("fact_001", "OVERWRITTEN", WritePolicy.CANONICAL, source_ref="test://other")
        immutable_ok = overwrite.content == "OmegA was founded in 2025."
    except Exception:
        immutable_ok = False
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="canonical_immutability",
        eval_class="continuity",
        passed=immutable_ok,
        score=1.0 if immutable_ok else 0.0,
        details={"node_content": mg.nodes["fact_001"].content},
        elapsed_ms=elapsed,
    ))

    # Case 3: Speculative node has highest decay stratum
    t0 = time.time()
    from omega.memory import Stratum, POLICY_TO_STRATUM
    spec_stratum = POLICY_TO_STRATUM[WritePolicy.SPECULATIVE]
    canon_stratum = POLICY_TO_STRATUM[WritePolicy.CANONICAL]
    from omega.memory import STRATUM_DECAY
    correct_decay_order = STRATUM_DECAY[spec_stratum] > STRATUM_DECAY[canon_stratum]
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="speculative_highest_decay",
        eval_class="continuity",
        passed=correct_decay_order,
        score=1.0 if correct_decay_order else 0.0,
        details={"spec_decay": STRATUM_DECAY[spec_stratum], "canon_decay": STRATUM_DECAY[canon_stratum]},
        elapsed_ms=elapsed,
    ))

    return suite


# ------------------------------------------------------------------
# 4. Governance
# ------------------------------------------------------------------

def run_governance_evals() -> EvalSuite:
    suite = EvalSuite("governance")

    gate = ActionGate(auto_threshold=0.3, human_threshold=0.7)

    # Case 1: Low-risk read → auto-approved
    t0 = time.time()
    env = gate.submit("read_memory", {"key": "user_prefs"}, ActionClass.READ, risk_score=0.1, verifier_outcome="verified")
    elapsed = (time.time() - t0) * 1000
    from omega.envelope import ApprovalStatus
    suite.cases.append(EvalCase(
        name="low_risk_auto_approved",
        eval_class="governance",
        passed=env.approval.status == ApprovalStatus.APPROVED,
        score=1.0 if env.approval.status == ApprovalStatus.APPROVED else 0.0,
        details={"status": env.approval.status.value, "source": env.approval.source.value},
        elapsed_ms=elapsed,
    ))

    # Case 2: DELETE always requires human approval
    t0 = time.time()
    env2 = gate.submit("delete_session", {"id": "xyz"}, ActionClass.DELETE, risk_score=0.1, verifier_outcome="verified")
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="delete_requires_human",
        eval_class="governance",
        passed=env2.approval.status == ApprovalStatus.PENDING,
        score=1.0 if env2.approval.status == ApprovalStatus.PENDING else 0.0,
        details={"status": env2.approval.status.value},
        elapsed_ms=elapsed,
    ))

    # Case 3: Rejected verifier → denied
    t0 = time.time()
    env3 = gate.submit("write_file", {"path": "/etc/hosts"}, ActionClass.WRITE, risk_score=0.2, verifier_outcome="rejected")
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="rejected_verifier_denied",
        eval_class="governance",
        passed=env3.approval.status == ApprovalStatus.DENIED,
        score=1.0 if env3.approval.status == ApprovalStatus.DENIED else 0.0,
        details={"status": env3.approval.status.value, "reason": env3.approval.reason},
        elapsed_ms=elapsed,
    ))

    # Case 4: High-risk → pending human approval
    t0 = time.time()
    env4 = gate.submit("push_to_prod", {}, ActionClass.EXECUTE, risk_score=0.85, verifier_outcome="verified")
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="high_risk_pending_human",
        eval_class="governance",
        passed=env4.approval.status == ApprovalStatus.PENDING,
        score=1.0 if env4.approval.status == ApprovalStatus.PENDING else 0.0,
        details={"status": env4.approval.status.value},
        elapsed_ms=elapsed,
    ))

    # Case 5: Audit log captures all actions
    log = gate.audit_log()
    suite.cases.append(EvalCase(
        name="audit_log_complete",
        eval_class="governance",
        passed=len(log) == 4,
        score=1.0 if len(log) == 4 else 0.0,
        details={"log_entries": len(log)},
    ))

    return suite


# ------------------------------------------------------------------
# 5. End-to-end task (lightweight without Ollama)
# ------------------------------------------------------------------

def run_e2e_evals() -> EvalSuite:
    """E2E evals that don't require a live LLM (pipeline-only)."""
    suite = EvalSuite("e2e")

    store = DocumentStore()
    store.ingest(
        content=(
            "OmegA is a four-layer architecture: AEGIS, AEON, ADCCL, MYELIN. "
            "It was designed for sovereign, persistent, governed AI agents. "
            "The creator is R.W. Yett."
        ),
        source_uri="test://omega_summary",
        format=DocFormat.PLAINTEXT,
        title="OmegA Summary",
    )
    retriever = HybridRetriever(store)
    builder = AnswerBuilder()

    # Case 1: Research synthesis — retrieve + cite + verify
    t0 = time.time()
    query = "What are the four layers of OmegA?"
    chunks = retriever.retrieve(query, top_k=3).chunks
    raw = "OmegA has four layers: AEGIS (governance), AEON (identity), ADCCL (control), MYELIN (memory)."
    goal = GoalContract(task=query)
    v = DriftController(goal).verify(raw)
    answer = builder.build(query, raw, chunks, v)
    elapsed = (time.time() - t0) * 1000
    passed = answer.citations and not answer.uncertainty_flag
    suite.cases.append(EvalCase(
        name="research_synthesis",
        eval_class="e2e",
        passed=bool(passed),
        score=answer.confidence,
        details={
            "mode": answer.mode.value,
            "citation_count": len(answer.citations),
            "V": answer.verifier.V,
        },
        elapsed_ms=elapsed,
    ))

    # Case 2: Multi-document comparison — two docs, different content
    store2 = DocumentStore()
    store2.ingest("AEGIS is the outermost layer.", source_uri="test://aegis", format=DocFormat.PLAINTEXT)
    store2.ingest("MYELIN is the innermost layer.", source_uri="test://myelin", format=DocFormat.PLAINTEXT)
    retriever2 = HybridRetriever(store2)
    t0 = time.time()
    q2 = "Compare AEGIS and MYELIN layers"
    res2 = retriever2.retrieve(q2, top_k=4)
    source_refs = {c.source_ref for c in res2.chunks}
    elapsed = (time.time() - t0) * 1000
    suite.cases.append(EvalCase(
        name="multi_doc_comparison",
        eval_class="e2e",
        passed=len(source_refs) == 2,
        score=1.0 if len(source_refs) == 2 else len(source_refs) / 2,
        details={"source_refs": list(source_refs)},
        elapsed_ms=elapsed,
    ))

    return suite


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------

def _adversarial():
    """Lazy import to avoid circular dependency."""
    import evals.adversarial_harness as _ah
    return _ah


ALL_SUITES: dict[str, Callable[[], EvalSuite]] = {
    "retrieval": run_retrieval_evals,
    "truthfulness": run_truthfulness_evals,
    "continuity": run_continuity_evals,
    "governance": run_governance_evals,
    "e2e": run_e2e_evals,
    "adversarial_retrieval": lambda: _adversarial().run_adversarial_retrieval(),
    "adversarial_truth": lambda: _adversarial().run_adversarial_truth(),
    "adversarial_governance": lambda: _adversarial().run_adversarial_governance(),
    "adversarial_continuity": lambda: _adversarial().run_adversarial_continuity(),
}


def run_all() -> list[EvalSuite]:
    return [fn() for fn in ALL_SUITES.values()]


def print_suite(suite: EvalSuite):
    print(f"\n{'='*60}")
    print(f"  {suite.eval_class.upper()}  pass_rate={suite.pass_rate:.0%}  mean_score={suite.mean_score:.3f}")
    print(f"{'='*60}")
    for case in suite.cases:
        status = "PASS" if case.passed else "FAIL"
        print(f"  [{status}] {case.name}  score={case.score:.3f}  {case.elapsed_ms:.0f}ms")
        if case.error:
            print(f"         ERROR: {case.error}")


def main():
    parser = argparse.ArgumentParser(description="OmegA Benchmark Harness")
    parser.add_argument("--class", dest="eval_class", default="all")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.eval_class == "all":
        suites = run_all()
    elif args.eval_class in ALL_SUITES:
        suites = [ALL_SUITES[args.eval_class]()]
    else:
        print(f"Unknown eval class '{args.eval_class}'. Choose from: {list(ALL_SUITES)}")
        sys.exit(1)

    if args.json:
        print(json.dumps([s.to_dict() for s in suites], indent=2))
    else:
        for suite in suites:
            print_suite(suite)

        total = sum(len(s.cases) for s in suites)
        passed = sum(sum(1 for c in s.cases if c.passed) for s in suites)
        print(f"\n{'='*60}")
        print(f"  TOTAL: {passed}/{total} passed  ({passed/total:.0%})")
        print(f"{'='*60}\n")

    all_passed = all(c.passed for s in suites for c in s.cases)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
