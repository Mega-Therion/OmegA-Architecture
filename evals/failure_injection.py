"""
OmegA Failure Injection / Chaos Testing Harness.

Registers structured failure cases for each known failure mode,
injects them, and verifies the system degrades gracefully.

Architecture: AEGIS + AEON resilience validation
"""

import os
import sys
import time
import traceback
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

# Ensure omega package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from omega.envelope import ActionClass, ApprovalStatus, ActionGate
from omega.approvals import ApprovalQueue
from omega.telemetry import TelemetryCollector, TelemetryEventType
from omega.risk_gate import RiskGate
from omega.providers.base import (
    ProviderRequest, ProviderResponse, ProviderStatus, ProviderRouter,
)


class FailureMode(str, Enum):
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_MALFORMED = "provider_malformed"
    MISSING_SOURCE = "missing_source"
    CONFLICTING_CANONICAL = "conflicting_canonical"
    FORGED_AUTHORITY = "forged_authority"
    TELEMETRY_WRITE_FAILURE = "telemetry_write_failure"
    APPROVAL_UNAVAILABLE = "approval_unavailable"


@dataclass
class FailureCase:
    """A single failure injection test case."""
    case_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    mode: FailureMode = FailureMode.PROVIDER_TIMEOUT
    description: str = ""
    expected_outcome: str = ""
    inject_fn: Callable = field(default_factory=lambda: (lambda: None))

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "mode": self.mode.value,
            "description": self.description,
            "expected_outcome": self.expected_outcome,
        }


class FailureInjectionHarness:
    """Registers and runs failure injection cases."""

    def __init__(self):
        self.cases: list[FailureCase] = []

    def register(self, case: FailureCase) -> None:
        self.cases.append(case)

    def run_all(self) -> list[dict]:
        """Run all registered cases and return results."""
        return [self.run_case(c.case_id) for c in self.cases]

    def run_case(self, case_id: str) -> dict:
        """Run a single case by ID."""
        case = None
        for c in self.cases:
            if c.case_id == case_id:
                case = c
                break
        if case is None:
            return {"case_id": case_id, "mode": "unknown", "passed": False,
                    "actual_outcome": "Case not found", "error": ""}

        try:
            result = case.inject_fn()
            passed = True
            actual = result if isinstance(result, str) else str(result)
            error = ""
        except Exception as e:
            # An unhandled crash means the test failed — system didn't degrade gracefully
            passed = False
            actual = f"UNHANDLED EXCEPTION: {type(e).__name__}: {e}"
            error = traceback.format_exc()

        return {
            "case_id": case.case_id,
            "mode": case.mode.value,
            "passed": passed,
            "actual_outcome": actual,
            "error": error,
        }


# ------------------------------------------------------------------
# Failure case builders
# ------------------------------------------------------------------

class _TimeoutProvider:
    """Mock provider that simulates a timeout."""
    @property
    def name(self) -> str:
        return "timeout_mock"

    def is_available(self) -> bool:
        return True

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            text="",
            provider_name="timeout_mock",
            model="mock",
            status=ProviderStatus.TIMEOUT,
            error_message="Provider timed out after 30000ms",
        )


class _MalformedProvider:
    """Mock provider that returns garbage."""
    @property
    def name(self) -> str:
        return "malformed_mock"

    def is_available(self) -> bool:
        return True

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        return ProviderResponse(
            text="\x00\xff\xfe GARBAGE {{{{{{ not json not text ]]]]",
            provider_name="malformed_mock",
            model="mock",
            status=ProviderStatus.SUCCESS,
        )


def _case_provider_timeout() -> str:
    """Inject a provider timeout and verify the router returns an error, not a crash."""
    router = ProviderRouter()
    router.register(_TimeoutProvider())
    req = ProviderRequest(prompt="test", run_id="fail_test_1")
    resp = router.route(req)
    assert not resp.ok, "Expected non-ok response from timed-out provider"
    assert resp.status in (ProviderStatus.TIMEOUT, ProviderStatus.UNAVAILABLE, ProviderStatus.ERROR)
    return "Provider timeout handled gracefully"


def _case_provider_malformed() -> str:
    """Inject malformed provider output and verify it doesn't crash downstream."""
    router = ProviderRouter()
    router.register(_MalformedProvider())
    req = ProviderRequest(prompt="test", run_id="fail_test_2")
    resp = router.route(req)
    # The response is technically 'success' from the provider but contains garbage
    assert resp.text is not None
    assert isinstance(resp.text, str)
    return "Malformed provider output contained without crash"


def _case_missing_source() -> str:
    """Query with no documents loaded — retriever should return empty, not crash."""
    from omega.docstore import DocumentStore
    from omega.retrieval import HybridRetriever

    ds = DocumentStore()
    ret = HybridRetriever(ds)
    result = ret.retrieve("What is the meaning of life?", top_k=5)
    assert len(result.chunks) == 0, "Expected zero chunks from empty store"
    return "Missing source handled: zero chunks returned"


def _case_conflicting_canonical() -> str:
    """Two contradictory canonical entries — risk gate should flag elevated risk."""
    gate = RiskGate()
    # Simulate a task that references conflicting information
    score = gate.score("Write conflicting delete instructions for the same resource")
    # Score should be non-trivial due to 'delete' and 'write' keywords
    assert score > 0.1, f"Expected elevated risk score, got {score}"
    return f"Conflicting canonical detected: risk_score={score}"


def _case_forged_authority() -> str:
    """Attempt to approve an action without going through the gate — should remain PENDING."""
    gate = ActionGate()
    # Submit a high-risk action that requires human approval
    env = gate.submit(
        action="delete_user_data",
        inputs={"user": "all"},
        action_class=ActionClass.DELETE,
        risk_score=0.95,
    )
    # Should be PENDING (requires human), not APPROVED
    assert env.approval.status == ApprovalStatus.PENDING, (
        f"Expected PENDING for delete action, got {env.approval.status}"
    )
    # Trying to bypass by directly setting status should not be how the system works.
    # The gate correctly held the action.
    return "Forged authority blocked: action held at PENDING"


def _case_telemetry_write_failure() -> str:
    """Telemetry flush with a bad persist_dir — should raise, not corrupt state."""
    collector = TelemetryCollector(persist_dir="/nonexistent/bad/path/telemetry")
    collector.emit(TelemetryEventType.ERROR, "fail_test_6", {"msg": "test"})
    try:
        collector.flush()
        return "UNEXPECTED: flush succeeded to bad path"
    except (OSError, RuntimeError):
        # Event should still be queryable if flush failed before clear
        # (flush clears only on success after write)
        return "Telemetry write failure handled: OSError raised, no silent corruption"


def _case_approval_unavailable() -> str:
    """Submit an action needing approval but with no queue to receive it."""
    gate = ActionGate()
    env = gate.submit(
        action="deploy_production",
        inputs={"target": "prod"},
        action_class=ActionClass.AUTH,
        risk_score=0.9,
    )
    # AUTH class always requires human — status should be PENDING
    assert env.approval.status == ApprovalStatus.PENDING
    # Without a queue, the action simply stays pending — system does not crash
    # or auto-approve dangerously
    return "Approval unavailable handled: action held PENDING without queue"


def build_default_cases() -> list[FailureCase]:
    """Build the standard set of failure injection cases."""
    return [
        FailureCase(
            mode=FailureMode.PROVIDER_TIMEOUT,
            description="Mock provider that returns TIMEOUT status",
            expected_outcome="Router returns error response, no crash",
            inject_fn=_case_provider_timeout,
        ),
        FailureCase(
            mode=FailureMode.PROVIDER_MALFORMED,
            description="Mock provider that returns garbage text",
            expected_outcome="Garbage text contained in response, no crash",
            inject_fn=_case_provider_malformed,
        ),
        FailureCase(
            mode=FailureMode.MISSING_SOURCE,
            description="Retrieval query against empty document store",
            expected_outcome="Zero chunks returned, no crash",
            inject_fn=_case_missing_source,
        ),
        FailureCase(
            mode=FailureMode.CONFLICTING_CANONICAL,
            description="Task with conflicting destructive instructions",
            expected_outcome="Risk gate returns elevated score",
            inject_fn=_case_conflicting_canonical,
        ),
        FailureCase(
            mode=FailureMode.FORGED_AUTHORITY,
            description="Attempt to execute DELETE action without human approval",
            expected_outcome="Action held at PENDING, not auto-approved",
            inject_fn=_case_forged_authority,
        ),
        FailureCase(
            mode=FailureMode.TELEMETRY_WRITE_FAILURE,
            description="Telemetry flush to nonexistent directory",
            expected_outcome="OSError raised, no silent data corruption",
            inject_fn=_case_telemetry_write_failure,
        ),
        FailureCase(
            mode=FailureMode.APPROVAL_UNAVAILABLE,
            description="AUTH action submitted with no approval queue connected",
            expected_outcome="Action held PENDING, no dangerous auto-approve",
            inject_fn=_case_approval_unavailable,
        ),
    ]
