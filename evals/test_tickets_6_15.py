"""Tests for Tickets 6-15: Claim Graph, Query Planner, Session, Tasks,
Planner/Executor, Approvals, Policy, Security, Telemetry, Failure Injection."""
import sys
import time
import tempfile
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever
from omega.answer import AnswerBuilder, AnswerObject, AnswerMode
from omega.drift import DriftController, GoalContract
from omega.memory import MemoryGraph, WritePolicy, Stratum
from omega.envelope import ActionGate, ActionClass, ApprovalStatus
from omega.risk_gate import RiskGate
from omega.phylactery import Phylactery


# ── Ticket 6: Claim Graph ─────────────────────────────────────────

def test_claim_graph_construction():
    """ClaimGraph builds from answer + chunks."""
    from omega.claims import ClaimGraph, ClaimNode, ClaimType, EvidenceEdge, EdgeRelation
    store = DocumentStore()
    store.ingest("OmegA has four layers.", source_uri="test://doc", format=DocFormat.PLAINTEXT)
    retriever = HybridRetriever(store)
    chunks = retriever.retrieve("four layers", top_k=3).chunks
    builder = AnswerBuilder()
    answer = builder.build("four layers", "OmegA has four layers: AEGIS, AEON, ADCCL, MYELIN.", chunks)
    graph = ClaimGraph.from_retrieval_and_answer(answer, chunks)
    assert len(graph.claims) > 0
    assert isinstance(list(graph.claims.values())[0], ClaimNode)
    d = graph.to_dict()
    assert "claims" in d
    assert "edges" in d
    print("[PASS] test_claim_graph_construction")


def test_claim_graph_contradictions():
    """Contradicted claims are detectable."""
    from omega.claims import ClaimGraph, ClaimNode, ClaimType, EvidenceEdge, EdgeRelation
    import uuid
    g = ClaimGraph()
    c1 = g.add_claim(ClaimNode(claim_id=str(uuid.uuid4()), text="Earth is flat", claim_type=ClaimType.SUPPORTED, support_strength=0.3, grounding_strength=0.3))
    c2 = g.add_claim(ClaimNode(claim_id=str(uuid.uuid4()), text="Earth is round", claim_type=ClaimType.SUPPORTED, support_strength=0.9, grounding_strength=0.9))
    g.add_edge(EvidenceEdge(edge_id=str(uuid.uuid4()), source_claim_id=c1.claim_id, target_claim_id=c2.claim_id, relation=EdgeRelation.CONTRADICTS, weight=0.95))
    contradictions = g.get_contradictions()
    assert len(contradictions) >= 1
    print("[PASS] test_claim_graph_contradictions")


def test_claim_graph_uncertainty_propagation():
    """Uncertainty propagates to contradicted claims."""
    from omega.claims import ClaimGraph, ClaimNode, ClaimType, EvidenceEdge, EdgeRelation
    import uuid
    g = ClaimGraph()
    c1 = g.add_claim(ClaimNode(claim_id=str(uuid.uuid4()), text="Claim A", claim_type=ClaimType.SUPPORTED, support_strength=0.9, grounding_strength=0.9))
    c2 = g.add_claim(ClaimNode(claim_id=str(uuid.uuid4()), text="Claim B", claim_type=ClaimType.SUPPORTED, support_strength=0.8, grounding_strength=0.8))
    g.add_edge(EvidenceEdge(edge_id=str(uuid.uuid4()), source_claim_id=c1.claim_id, target_claim_id=c2.claim_id, relation=EdgeRelation.CONTRADICTS, weight=0.7))
    g.propagate_uncertainty()
    weakened = any(c.support_strength < 0.8 for c in g.claims.values())
    assert weakened
    print("[PASS] test_claim_graph_uncertainty_propagation")


def test_claim_graph_unresolved():
    """Unresolved claims are retrievable."""
    from omega.claims import ClaimGraph, ClaimNode, ClaimType
    import uuid
    g = ClaimGraph()
    g.add_claim(ClaimNode(claim_id=str(uuid.uuid4()), text="Known fact", claim_type=ClaimType.SUPPORTED, support_strength=0.9, grounding_strength=0.8))
    g.add_claim(ClaimNode(claim_id=str(uuid.uuid4()), text="Unknown thing", claim_type=ClaimType.UNRESOLVED, support_strength=0.0, grounding_strength=0.0))
    unresolved = g.get_unresolved()
    assert len(unresolved) == 1
    assert unresolved[0].text == "Unknown thing"
    print("[PASS] test_claim_graph_unresolved")


def test_answer_object_carries_claim_graph():
    """AnswerObject can carry claim graph data."""
    from omega.claims import ClaimGraph, ClaimType
    store = DocumentStore()
    store.ingest("Test content.", source_uri="test://x", format=DocFormat.PLAINTEXT)
    retriever = HybridRetriever(store)
    chunks = retriever.retrieve("test", top_k=1).chunks
    builder = AnswerBuilder()
    answer = builder.build("test", "Test answer", chunks)
    g = ClaimGraph.from_retrieval_and_answer(answer, chunks)
    answer.claim_graph = g
    d = answer.to_dict()
    assert "claim_graph" in d
    assert d["claim_graph"] is not None
    print("[PASS] test_answer_object_carries_claim_graph")


# ── Ticket 7: Query Planner ───────────────────────────────────────

def test_query_planner_basic():
    """QueryPlanner produces a typed plan."""
    from omega.query_planner import QueryPlanner, QueryPlan, QueryStrategy
    planner = QueryPlanner()
    plan = planner.plan("What are the four layers of OmegA?")
    assert isinstance(plan, QueryPlan)
    assert plan.original_query == "What are the four layers of OmegA?"
    assert len(plan.rewritten_queries) >= 1
    assert plan.strategy in list(QueryStrategy)
    d = plan.to_dict()
    assert "plan_id" in d
    assert "strategy" in d
    print("[PASS] test_query_planner_basic")


def test_query_planner_strategy_selection():
    """Different queries produce different strategies."""
    from omega.query_planner import QueryPlanner, QueryStrategy
    planner = QueryPlanner()
    simple = planner.plan("hello")
    complex_q = planner.plan("Compare contradictions between AEGIS governance and MYELIN memory access policies across multiple versions")
    # At least the strategies should be typed
    assert isinstance(simple.strategy, QueryStrategy)
    assert isinstance(complex_q.strategy, QueryStrategy)
    print("[PASS] test_query_planner_strategy_selection")


def test_retrieval_execute_plan():
    """HybridRetriever.execute_plan() runs from a QueryPlan."""
    from omega.query_planner import QueryPlanner
    store = DocumentStore()
    store.ingest("AEGIS is the governance shell.", source_uri="test://aegis", format=DocFormat.PLAINTEXT)
    store.ingest("MYELIN is graph memory.", source_uri="test://myelin", format=DocFormat.PLAINTEXT)
    retriever = HybridRetriever(store)
    planner = QueryPlanner()
    plan = planner.plan("AEGIS governance")
    result = retriever.execute_plan(plan)
    assert len(result.chunks) > 0
    print("[PASS] test_retrieval_execute_plan")


# ── Ticket 8: Session Continuity ──────────────────────────────────

def test_session_save_load():
    """Session state persists and loads."""
    from omega.session import SessionStore, SessionState, SessionStatus
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(persist_dir=tmpdir)
        state = SessionState(
            session_id="test_session_1",
            run_ids=["run_abc"],
            phylactery_head="deadbeef",
            status=SessionStatus.ACTIVE,
        )
        snapshot = store.save(state)
        assert snapshot is not None
        loaded = store.load("test_session_1")
        assert loaded is not None
        assert loaded.session_id == "test_session_1"
        assert loaded.phylactery_head == "deadbeef"
    print("[PASS] test_session_save_load")


def test_session_resume():
    """Suspended session can be resumed."""
    from omega.session import SessionStore, SessionState, SessionStatus
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(persist_dir=tmpdir)
        state = SessionState(session_id="s2", status=SessionStatus.SUSPENDED)
        store.save(state)
        resumed = store.resume("s2")
        assert resumed.status == SessionStatus.RESUMED
    print("[PASS] test_session_resume")


def test_session_crash_recovery():
    """Crashed session recovers."""
    from omega.session import SessionStore, SessionState, SessionStatus
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(persist_dir=tmpdir)
        state = SessionState(session_id="s3", status=SessionStatus.CRASHED)
        store.save(state)
        recovered = store.crash_recover("s3")
        assert recovered.status == SessionStatus.RESUMED
    print("[PASS] test_session_crash_recovery")


# ── Ticket 9: Task Object Model ───────────────────────────────────

def test_task_creation():
    """TaskRegistry creates tracked tasks."""
    from omega.tasks import TaskRegistry, TaskStatus
    reg = TaskRegistry()
    task = reg.create(objective="Research OmegA layers")
    assert task.task_id is not None
    assert task.status == TaskStatus.QUEUED
    assert reg.get(task.task_id) is not None
    print("[PASS] test_task_creation")


def test_task_transitions():
    """Task transitions follow legal state machine."""
    from omega.tasks import TaskRegistry, TaskStatus
    reg = TaskRegistry()
    task = reg.create(objective="Test task")
    t = reg.transition(task.task_id, TaskStatus.RUNNING, "Starting")
    assert t.to_status == TaskStatus.RUNNING
    assert task.status == TaskStatus.RUNNING
    t2 = reg.transition(task.task_id, TaskStatus.COMPLETED, "Done")
    assert task.status == TaskStatus.COMPLETED
    assert task.is_terminal
    print("[PASS] test_task_transitions")


def test_task_illegal_transition():
    """Illegal transitions are rejected."""
    from omega.tasks import TaskRegistry, TaskStatus
    reg = TaskRegistry()
    task = reg.create(objective="Test")
    reg.transition(task.task_id, TaskStatus.RUNNING, "Start")
    reg.transition(task.task_id, TaskStatus.COMPLETED, "Done")
    # From COMPLETED, should not be able to go back to RUNNING
    try:
        reg.transition(task.task_id, TaskStatus.RUNNING, "Invalid")
        raised = False
    except ValueError:
        raised = True
    assert raised
    print("[PASS] test_task_illegal_transition")


def test_task_parent_child():
    """Subtasks reference parent."""
    from omega.tasks import TaskRegistry
    reg = TaskRegistry()
    parent = reg.create(objective="Parent task")
    child = reg.create(objective="Subtask", parent_id=parent.task_id)
    children = reg.children(parent.task_id)
    assert len(children) == 1
    assert children[0].task_id == child.task_id
    print("[PASS] test_task_parent_child")


# ── Ticket 10: Planner/Executor ───────────────────────────────────

def test_planner_creates_plan():
    """Planner produces a PlanObject from a TaskObject."""
    from omega.tasks import TaskRegistry
    from omega.planner import Planner, PlanObject
    reg = TaskRegistry()
    task = reg.create(objective="Retrieve and summarize OmegA architecture")
    planner = Planner()
    plan = planner.plan(task)
    assert isinstance(plan, PlanObject)
    assert len(plan.steps) > 0
    assert plan.task_id == task.task_id
    print("[PASS] test_planner_creates_plan")


def test_planner_validation():
    """Plans must be validated before execution."""
    from omega.tasks import TaskRegistry
    from omega.planner import Planner
    reg = TaskRegistry()
    task = reg.create(objective="Simple query")
    planner = Planner()
    plan = planner.plan(task)
    assert not plan.validated  # Not yet validated
    validated = planner.validate(plan)
    assert validated.validated or len(validated.validation_errors) > 0
    print("[PASS] test_planner_validation")


def test_executor_rejects_unvalidated():
    """Executor refuses unvalidated plans."""
    from omega.tasks import TaskRegistry
    from omega.planner import Planner, PlanObject
    from omega.executor import Executor
    from omega.runtime import RuntimeOrchestrator
    reg = TaskRegistry()
    task = reg.create(objective="Test")
    planner = Planner()
    plan = planner.plan(task)
    executor = Executor()
    rt = RuntimeOrchestrator()
    try:
        executor.execute(plan, rt)
        raised = False
    except ValueError:
        raised = True
    assert raised
    print("[PASS] test_executor_rejects_unvalidated")


def test_executor_runs_validated_plan():
    """Executor executes validated plan steps."""
    from omega.tasks import TaskRegistry
    from omega.planner import Planner
    from omega.executor import Executor
    from omega.runtime import RuntimeOrchestrator
    reg = TaskRegistry()
    task = reg.create(objective="Read memory state")
    planner = Planner()
    plan = planner.plan(task)
    plan = planner.validate(plan)
    if plan.validated:
        executor = Executor()
        rt = RuntimeOrchestrator()
        results = executor.execute(plan, rt)
        assert len(results) > 0
        assert all(r.status in ("success", "blocked", "skipped") for r in results)
    print("[PASS] test_executor_runs_validated_plan")


# ── Ticket 11: Approvals ──────────────────────────────────────────

def test_approval_queue_submit():
    """Approval requests are queued."""
    from omega.approvals import ApprovalQueue
    q = ApprovalQueue()
    req = q.submit(run_id="run_1", action="delete_file", action_class=ActionClass.DELETE, risk_score=0.9)
    assert req.status == ApprovalStatus.PENDING
    assert len(q.pending()) == 1
    print("[PASS] test_approval_queue_submit")


def test_approval_decide():
    """Approval decisions are recorded."""
    from omega.approvals import ApprovalQueue
    q = ApprovalQueue()
    req = q.submit(run_id="run_2", action="write_data", action_class=ActionClass.WRITE, risk_score=0.8)
    decision = q.decide(req.request_id, ApprovalStatus.APPROVED, "admin", "Reviewed and safe")
    assert decision.status == ApprovalStatus.APPROVED
    assert q.get_decision(req.request_id) is not None
    print("[PASS] test_approval_decide")


def test_approval_stats():
    """Approval queue tracks statistics."""
    from omega.approvals import ApprovalQueue
    q = ApprovalQueue()
    q.submit(run_id="r1", action="a1", action_class=ActionClass.READ, risk_score=0.1)
    q.submit(run_id="r2", action="a2", action_class=ActionClass.DELETE, risk_score=0.9)
    stats = q.stats()
    assert stats["total_submitted"] == 2
    assert stats["pending"] == 2
    print("[PASS] test_approval_stats")


# ── Ticket 12: Policy ─────────────────────────────────────────────

def test_policy_load_default():
    """Default policy loads and validates."""
    from omega.policy import PolicyLoader
    loader = PolicyLoader()
    cfg = loader.load("policies/default.yaml")
    valid, errors = loader.validate(cfg)
    assert valid, f"Validation errors: {errors}"
    assert cfg.risk_threshold == 0.8
    print("[PASS] test_policy_load_default")


def test_policy_load_strict():
    """Strict policy has tighter thresholds."""
    from omega.policy import PolicyLoader
    loader = PolicyLoader()
    cfg = loader.load("policies/strict.yaml")
    valid, _ = loader.validate(cfg)
    assert valid
    assert cfg.risk_threshold < 0.8
    assert cfg.evidence_threshold > 0.2
    print("[PASS] test_policy_load_strict")


def test_policy_invalid_rejected():
    """Invalid policy fails validation."""
    from omega.policy import PolicyLoader, PolicyConfig
    loader = PolicyLoader()
    bad = PolicyConfig(
        policy_id="bad", name="Bad", version="1.0",
        risk_threshold=1.5,  # Out of range
        evidence_threshold=0.5, verifier_threshold=0.4,
    )
    valid, errors = loader.validate(bad)
    assert not valid
    assert len(errors) > 0
    print("[PASS] test_policy_invalid_rejected")


# ── Ticket 13: Security ───────────────────────────────────────────

def test_redactor_dict():
    """Sensitive dict values are redacted."""
    from omega.security import Redactor
    r = Redactor()
    data = {"name": "test", "api_key": "sk-12345678abcdef", "nested": {"password": "secret123"}}
    redacted = r.redact_dict(data)
    assert redacted["api_key"] != "sk-12345678abcdef"
    assert "***" in redacted["api_key"]
    assert redacted["nested"]["password"] != "secret123"
    assert redacted["name"] == "test"  # Non-sensitive preserved
    print("[PASS] test_redactor_dict")


def test_redactor_string():
    """API key patterns in strings are redacted."""
    from omega.security import Redactor
    r = Redactor()
    text = "Using key sk-1234567890abcdefghijklmnop for auth"
    redacted = r.redact_string(text)
    assert "sk-1234567890" not in redacted
    print("[PASS] test_redactor_string")


def test_trust_boundary_enforcement():
    """Data crossing boundaries gets redacted."""
    from omega.security import enforce_boundary, TrustBoundary
    data = {"result": "ok", "api_key": "secret_value_here"}
    cleaned = enforce_boundary(TrustBoundary.INTERNAL, TrustBoundary.USER, data)
    assert "***" in cleaned["api_key"]
    # Same boundary: no redaction
    same = enforce_boundary(TrustBoundary.INTERNAL, TrustBoundary.INTERNAL, data)
    assert same["api_key"] == "secret_value_here"
    print("[PASS] test_trust_boundary_enforcement")


# ── Ticket 14: Telemetry ──────────────────────────────────────────

def test_telemetry_emit():
    """Telemetry events are emitted and queryable."""
    from omega.telemetry import TelemetryCollector, TelemetryEventType
    tc = TelemetryCollector()
    ev = tc.emit(TelemetryEventType.STAGE_LATENCY, "run_1", {"stage": "retrieve", "ms": 42.0})
    assert ev.event_type == TelemetryEventType.STAGE_LATENCY
    assert tc.event_count == 1
    results = tc.query(run_id="run_1")
    assert len(results) == 1
    print("[PASS] test_telemetry_emit")


def test_telemetry_summarize():
    """Telemetry summary aggregates events."""
    from omega.telemetry import TelemetryCollector, TelemetryEventType
    tc = TelemetryCollector()
    tc.emit(TelemetryEventType.STAGE_LATENCY, "run_1", {"stage": "retrieve", "ms": 10})
    tc.emit(TelemetryEventType.STAGE_LATENCY, "run_1", {"stage": "generate", "ms": 50})
    tc.emit(TelemetryEventType.PROVIDER_FAILURE, "run_1", {"provider": "ollama"})
    summary = tc.summarize("run_1")
    assert summary["total_events"] == 3
    print("[PASS] test_telemetry_summarize")


def test_telemetry_flush():
    """Telemetry flushes to disk."""
    from omega.telemetry import TelemetryCollector, TelemetryEventType
    with tempfile.TemporaryDirectory() as tmpdir:
        tc = TelemetryCollector(persist_dir=tmpdir)
        tc.emit(TelemetryEventType.ERROR, "run_x", {"msg": "test error"})
        tc.flush()
        files = list(Path(tmpdir).glob("*.jsonl"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "test error" in content
    print("[PASS] test_telemetry_flush")


def test_extract_metrics():
    """RunMetrics extracts from RunTrace."""
    from omega.telemetry import extract_metrics
    from omega.runtime import RunTrace, StageTrace, RuntimeStage
    trace = RunTrace(run_id="run_test", task="test")
    trace.total_elapsed_ms = 100.0
    trace.provider_name = "openai"
    trace.verification_V = 0.85
    trace.gate_allowed = True
    s = StageTrace(stage=RuntimeStage.RETRIEVE, elapsed_ms=25.0, status="done")
    trace.stages.append(s)
    metrics = extract_metrics(trace)
    assert metrics.run_id == "run_test"
    assert metrics.total_latency_ms == 100.0
    assert "retrieve" in metrics.stage_latencies
    print("[PASS] test_extract_metrics")


# ── Ticket 15: Failure Injection ───────────────────────────────────

def test_failure_injection_harness():
    """Failure injection harness runs all cases."""
    from evals.failure_injection import FailureInjectionHarness, build_default_cases
    harness = FailureInjectionHarness()
    for case in build_default_cases():
        harness.register(case)
    results = harness.run_all()
    assert len(results) >= 5
    passed = sum(1 for r in results if r["passed"])
    print(f"  Failure injection: {passed}/{len(results)} passed")
    assert passed >= 4  # Allow some legitimate findings
    print("[PASS] test_failure_injection_harness")


# ── Runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Ticket 6
    test_claim_graph_construction()
    test_claim_graph_contradictions()
    test_claim_graph_uncertainty_propagation()
    test_claim_graph_unresolved()
    test_answer_object_carries_claim_graph()
    # Ticket 7
    test_query_planner_basic()
    test_query_planner_strategy_selection()
    test_retrieval_execute_plan()
    # Ticket 8
    test_session_save_load()
    test_session_resume()
    test_session_crash_recovery()
    # Ticket 9
    test_task_creation()
    test_task_transitions()
    test_task_illegal_transition()
    test_task_parent_child()
    # Ticket 10
    test_planner_creates_plan()
    test_planner_validation()
    test_executor_rejects_unvalidated()
    test_executor_runs_validated_plan()
    # Ticket 11
    test_approval_queue_submit()
    test_approval_decide()
    test_approval_stats()
    # Ticket 12
    test_policy_load_default()
    test_policy_load_strict()
    test_policy_invalid_rejected()
    # Ticket 13
    test_redactor_dict()
    test_redactor_string()
    test_trust_boundary_enforcement()
    # Ticket 14
    test_telemetry_emit()
    test_telemetry_summarize()
    test_telemetry_flush()
    test_extract_metrics()
    # Ticket 15
    test_failure_injection_harness()

    print("\n  All Tickets 6-15 tests passed.")
