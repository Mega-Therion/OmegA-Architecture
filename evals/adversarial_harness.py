"""
OmegA Adversarial Eval Harness

Loads adversarial corpus JSON files and runs each case against real
OmegA runtime components.  Returns EvalSuite objects compatible with
the benchmark_harness format.

Usage:
    python evals/adversarial_harness.py
    python evals/adversarial_harness.py --json
"""

import json
import sys
import time
import argparse
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever
from omega.answer import AnswerBuilder, AnswerMode
from omega.drift import GoalContract, DriftController, ClaimBudget, SupportStatus, VerifierMiddleware
from omega.memory import MemoryGraph, WritePolicy, Stratum
from omega.envelope import ActionGate, ActionClass, ApprovalStatus
from omega.risk_gate import RiskGate
from omega.phylactery import Phylactery

# Import EvalCase/EvalSuite directly to avoid circular import when
# benchmark_harness imports adversarial_harness via lazy loader.
from evals.benchmark_harness import EvalCase, EvalSuite, print_suite  # noqa: E402

CORPUS_DIR = Path(__file__).parent / "adversarial"


def _load_corpus(filename: str) -> list[dict]:
    path = CORPUS_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ------------------------------------------------------------------
# Adversarial Retrieval
# ------------------------------------------------------------------

def run_adversarial_retrieval() -> EvalSuite:
    suite = EvalSuite("adversarial_retrieval")
    traps = _load_corpus("retrieval_traps.json")

    for trap in traps:
        t0 = time.time()
        try:
            if trap["trap_type"] == "similarity_collision":
                passed, score, details = _eval_similarity_collision(trap)
            elif trap["trap_type"] == "stale_bait":
                passed, score, details = _eval_stale_bait(trap)
            elif trap["trap_type"] == "irrelevant_high_score":
                passed, score, details = _eval_irrelevant_high_score(trap)
            elif trap["trap_type"] == "empty_corpus":
                passed, score, details = _eval_empty_corpus(trap)
            else:
                passed, score, details = False, 0.0, {"error": f"Unknown trap type: {trap['trap_type']}"}
            error = ""
        except Exception as e:
            passed, score, details, error = False, 0.0, {}, str(e)

        elapsed = (time.time() - t0) * 1000
        suite.cases.append(EvalCase(
            name=trap["name"],
            eval_class="adversarial_retrieval",
            passed=passed,
            score=score,
            details=details,
            error=error,
            elapsed_ms=elapsed,
        ))

    return suite


def _eval_similarity_collision(trap: dict) -> tuple[bool, float, dict]:
    """Target MYELIN doc must rank above biology bait doc."""
    store = DocumentStore()
    bait = trap["bait_doc"]
    target = trap["target_doc"]

    bait_rec = store.ingest(bait["content"], bait["source_uri"], DocFormat.PLAINTEXT, bait["title"])
    target_rec = store.ingest(target["content"], target["source_uri"], DocFormat.PLAINTEXT, target["title"])

    retriever = HybridRetriever(store)
    result = retriever.retrieve(trap["query"], top_k=5)

    if not result.chunks:
        return False, 0.0, {"reason": "no chunks returned"}

    top_doc_ids = [c.doc_id for c in result.chunks]
    target_rank = top_doc_ids.index(target_rec.doc_id) if target_rec.doc_id in top_doc_ids else -1
    bait_rank = top_doc_ids.index(bait_rec.doc_id) if bait_rec.doc_id in top_doc_ids else -1

    if target_rank == -1:
        return False, 0.0, {"reason": "target doc not in results"}

    passed = target_rank < bait_rank if bait_rank >= 0 else True
    score = 1.0 if passed else 0.0
    return passed, score, {
        "target_rank": target_rank,
        "bait_rank": bait_rank,
        "top_source_ref": result.chunks[0].source_ref,
    }


def _eval_stale_bait(trap: dict) -> tuple[bool, float, dict]:
    """Current doc should rank at or above stale doc."""
    store = DocumentStore()
    stale = trap["stale_doc"]
    current = trap["current_doc"]

    # Ingest stale first, then current (same URI -> version lineage)
    store.ingest(stale["content"], stale["source_uri"], DocFormat.PLAINTEXT, stale["title"])
    current_rec = store.ingest(current["content"], current["source_uri"], DocFormat.PLAINTEXT, current["title"])

    retriever = HybridRetriever(store)
    result = retriever.retrieve(trap["query"], top_k=5)

    if not result.chunks:
        return False, 0.0, {"reason": "no chunks returned"}

    top_doc_ids = [c.doc_id for c in result.chunks]
    current_in_top = current_rec.doc_id in top_doc_ids

    # Current doc should appear in results since it has more relevant content
    passed = current_in_top
    score = 1.0 if passed else 0.0
    return passed, score, {
        "current_doc_in_results": current_in_top,
        "top_source_ref": result.chunks[0].source_ref,
        "total_chunks": len(result.chunks),
    }


def _eval_irrelevant_high_score(trap: dict) -> tuple[bool, float, dict]:
    """Relevant doc should outrank keyword-stuffed irrelevant doc."""
    store = DocumentStore()
    irrelevant = trap["irrelevant_doc"]
    relevant = trap["relevant_doc"]

    irr_rec = store.ingest(irrelevant["content"], irrelevant["source_uri"], DocFormat.PLAINTEXT, irrelevant["title"])
    rel_rec = store.ingest(relevant["content"], relevant["source_uri"], DocFormat.PLAINTEXT, relevant["title"])

    retriever = HybridRetriever(store)
    result = retriever.retrieve(trap["query"], top_k=5)

    if not result.chunks:
        return False, 0.0, {"reason": "no chunks returned"}

    # Find scores for relevant vs irrelevant doc chunks
    rel_scores = [c.score for c in result.chunks if c.doc_id == rel_rec.doc_id]
    irr_scores = [c.score for c in result.chunks if c.doc_id == irr_rec.doc_id]

    rel_best = max(rel_scores) if rel_scores else 0.0
    irr_best = max(irr_scores) if irr_scores else 0.0

    passed = rel_best >= irr_best
    score = 1.0 if passed else rel_best / max(irr_best, 0.001)
    return passed, score, {
        "relevant_best_score": round(rel_best, 4),
        "irrelevant_best_score": round(irr_best, 4),
    }


def _eval_empty_corpus(trap: dict) -> tuple[bool, float, dict]:
    """Empty corpus must return zero chunks."""
    store = DocumentStore()
    retriever = HybridRetriever(store)
    result = retriever.retrieve(trap["query"], top_k=5)

    passed = len(result.chunks) == 0
    score = 1.0 if passed else 0.0
    return passed, score, {"chunks_returned": len(result.chunks)}


# ------------------------------------------------------------------
# Adversarial Truthfulness
# ------------------------------------------------------------------

def run_adversarial_truth() -> EvalSuite:
    suite = EvalSuite("adversarial_truth")
    traps = _load_corpus("truth_traps.json")

    builder = AnswerBuilder()

    for trap in traps:
        t0 = time.time()
        try:
            # No docs ingested -> empty retrieval -> zero grounding
            empty_store = DocumentStore()
            empty_retriever = HybridRetriever(empty_store)
            empty_chunks = empty_retriever.retrieve(trap["raw_text"][:50], top_k=3).chunks

            # Run verifier on the raw text
            goal = GoalContract(task=trap["raw_text"][:80])
            ctrl = DriftController(goal)
            v = ctrl.verify(trap["raw_text"])

            # Build answer with zero grounding
            answer = builder.build(
                query=trap["raw_text"][:80],
                raw_text=trap["raw_text"],
                retrieved_chunks=empty_chunks,
                verifier_dict=v,
            )

            expected = trap["expected_mode"]
            actual = answer.mode.value
            passed = actual == expected

            details = {
                "expected_mode": expected,
                "actual_mode": actual,
                "V": v["V"],
                "hallucination_signals": v["hallucination_signals"],
                "hedge_signals": v["hedge_signals"],
                "confidence": answer.confidence,
                "uncertainty_flag": answer.uncertainty_flag,
            }
            score = 1.0 if passed else 0.0
            error = ""
        except Exception as e:
            passed, score, details, error = False, 0.0, {}, str(e)

        elapsed = (time.time() - t0) * 1000
        suite.cases.append(EvalCase(
            name=trap["name"],
            eval_class="adversarial_truth",
            passed=passed,
            score=score,
            details=details,
            error=error,
            elapsed_ms=elapsed,
        ))

    return suite


# ------------------------------------------------------------------
# Adversarial Governance
# ------------------------------------------------------------------

def run_adversarial_governance() -> EvalSuite:
    suite = EvalSuite("adversarial_governance")
    traps = _load_corpus("governance_traps.json")

    gate = ActionGate()
    risk_gate = RiskGate()

    for trap in traps:
        t0 = time.time()
        try:
            action_class_map = {
                "read": ActionClass.READ,
                "write": ActionClass.WRITE,
                "execute": ActionClass.EXECUTE,
                "delete": ActionClass.DELETE,
                "network": ActionClass.NETWORK,
                "auth": ActionClass.AUTH,
            }
            ac = action_class_map[trap["action_class"]]
            expected = trap["expected_status"]

            if expected == "blocked":
                # Test RiskGate policy blocking
                is_blocked = risk_gate.is_policy_blocked(trap["action"])
                passed = is_blocked
                details = {
                    "expected": "blocked",
                    "is_policy_blocked": is_blocked,
                    "risk_score": risk_gate.score(trap["action"]),
                }
            else:
                # Test ActionGate approval flow
                env = gate.submit(
                    action=trap["action"],
                    inputs={"trap_id": trap["id"]},
                    action_class=ac,
                    risk_score=trap["risk_score"],
                    verifier_outcome=trap["verifier_outcome"],
                )
                actual = env.approval.status.value
                passed = actual == expected
                details = {
                    "expected_status": expected,
                    "actual_status": actual,
                    "approval_source": env.approval.source.value,
                    "reason": env.approval.reason,
                }

            score = 1.0 if passed else 0.0
            error = ""
        except Exception as e:
            passed, score, details, error = False, 0.0, {}, str(e)

        elapsed = (time.time() - t0) * 1000
        suite.cases.append(EvalCase(
            name=trap["name"],
            eval_class="adversarial_governance",
            passed=passed,
            score=score,
            details=details,
            error=error,
            elapsed_ms=elapsed,
        ))

    return suite


# ------------------------------------------------------------------
# Adversarial Continuity
# ------------------------------------------------------------------

def run_adversarial_continuity() -> EvalSuite:
    suite = EvalSuite("adversarial_continuity")
    traps = _load_corpus("continuity_traps.json")

    for trap in traps:
        t0 = time.time()
        try:
            if trap["trap_type"] == "chain_tamper":
                passed, score, details = _eval_chain_tamper(trap)
            elif trap["trap_type"] == "canonical_mutation":
                passed, score, details = _eval_canonical_mutation(trap)
            elif trap["trap_type"] == "doctrine_overwrite":
                passed, score, details = _eval_doctrine_injection(trap)
            else:
                passed, score, details = False, 0.0, {"error": f"Unknown trap type: {trap['trap_type']}"}
            error = ""
        except Exception as e:
            passed, score, details, error = False, 0.0, {}, str(e)

        elapsed = (time.time() - t0) * 1000
        suite.cases.append(EvalCase(
            name=trap["name"],
            eval_class="adversarial_continuity",
            passed=passed,
            score=score,
            details=details,
            error=error,
            elapsed_ms=elapsed,
        ))

    return suite


def _eval_chain_tamper(trap: dict) -> tuple[bool, float, dict]:
    """Tamper with a hash in the chain and confirm verify_chain fails."""
    setup = trap["setup"]
    p = Phylactery(setup["genesis_doctrine"])
    for commit_text in setup["commits"]:
        p.commit(commit_text)

    # Verify chain is valid before tampering
    pre_tamper = p.verify_chain()

    # Tamper: overwrite hash at specified index
    idx = setup["tamper_index"]
    original_hash = p.chain[idx].hash
    p.chain[idx].hash = setup["tamper_hash"]

    # Verify chain should now fail
    post_tamper = p.verify_chain()

    # Restore for cleanliness
    p.chain[idx].hash = original_hash

    passed = pre_tamper and not post_tamper
    return passed, 1.0 if passed else 0.0, {
        "pre_tamper_valid": pre_tamper,
        "post_tamper_valid": post_tamper,
        "tampered_index": idx,
    }


def _eval_canonical_mutation(trap: dict) -> tuple[bool, float, dict]:
    """Attempt to overwrite canonical node; original content must persist."""
    setup = trap["setup"]
    mg = MemoryGraph()

    # Write canonical node
    mg.write(
        id=setup["node_id"],
        content=setup["original_content"],
        policy=WritePolicy.CANONICAL,
        source_ref=setup["original_source_ref"],
    )

    # Attempt overwrite with attack content
    result = mg.write(
        id=setup["node_id"],
        content=setup["attack_content"],
        policy=WritePolicy.CANONICAL,
        source_ref=setup["attack_source_ref"],
    )

    # Original content must survive
    passed = result.content == setup["original_content"]
    return passed, 1.0 if passed else 0.0, {
        "original_content": setup["original_content"],
        "attack_content": setup["attack_content"],
        "actual_content": result.content,
        "immutability_held": passed,
    }


def _eval_doctrine_injection(trap: dict) -> tuple[bool, float, dict]:
    """Inject foreign doctrine; chain should verify but kappa should be 0.0."""
    setup = trap["setup"]
    p = Phylactery(setup["genesis_doctrine"])

    for commit_text in setup["pre_injection_commits"]:
        p.commit(commit_text)

    pre_injection_head = p.head

    # Inject foreign doctrine
    p.commit(setup["injection_content"])

    # Chain should still verify (commits are append-only, not tamper)
    chain_valid = p.verify_chain()

    # Kappa against pre-injection head should be 0.0 (heads differ)
    kappa = p.kappa(pre_injection_head)

    # Genesis doctrine still at index 0
    genesis_preserved = p.chain[0].content == setup["genesis_doctrine"]

    passed = chain_valid and kappa == 0.0 and genesis_preserved
    return passed, 1.0 if passed else 0.0, {
        "chain_valid": chain_valid,
        "kappa": kappa,
        "genesis_preserved": genesis_preserved,
        "current_doctrine": p.doctrine,
        "chain_length": len(p),
    }


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------

ALL_ADVERSARIAL_SUITES = {
    "adversarial_retrieval": run_adversarial_retrieval,
    "adversarial_truth": run_adversarial_truth,
    "adversarial_governance": run_adversarial_governance,
    "adversarial_continuity": run_adversarial_continuity,
}


def run_all_adversarial() -> list[EvalSuite]:
    return [fn() for fn in ALL_ADVERSARIAL_SUITES.values()]


def main():
    parser = argparse.ArgumentParser(description="OmegA Adversarial Eval Harness")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--class", dest="eval_class", default="all")
    args = parser.parse_args()

    if args.eval_class == "all":
        suites = run_all_adversarial()
    elif args.eval_class in ALL_ADVERSARIAL_SUITES:
        suites = [ALL_ADVERSARIAL_SUITES[args.eval_class]()]
    else:
        print(f"Unknown eval class '{args.eval_class}'. Choose from: {list(ALL_ADVERSARIAL_SUITES)}")
        sys.exit(1)

    if args.json:
        import json as _json
        print(_json.dumps([s.to_dict() for s in suites], indent=2))
    else:
        for suite in suites:
            print_suite(suite)

        total = sum(len(s.cases) for s in suites)
        passed = sum(sum(1 for c in s.cases if c.passed) for s in suites)
        print(f"\n{'='*60}")
        print(f"  ADVERSARIAL TOTAL: {passed}/{total} passed  ({passed/total:.0%})")
        print(f"{'='*60}\n")

    all_passed = all(c.passed for s in suites for c in s.cases)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
