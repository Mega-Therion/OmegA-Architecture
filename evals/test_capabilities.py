"""Tests for Ticket 2: Capability Registry."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.capabilities import (
    CapabilityRegistry, CapabilityManifest, RiskClass, default_capabilities,
)
from omega.envelope import ActionClass


def test_registry_reject_unknown():
    """Unknown capabilities are rejected (fail closed)."""
    reg = CapabilityRegistry()
    check = reg.check("nonexistent.capability")
    assert not check.allowed
    assert "not registered" in check.reason
    print("[PASS] test_registry_reject_unknown")


def test_registry_accept_registered():
    """Registered capabilities are accepted."""
    reg = CapabilityRegistry()
    for cap in default_capabilities():
        reg.register(cap)
    check = reg.check("cap.memory.read", context="runtime")
    assert check.allowed
    assert check.manifest is not None
    assert check.manifest.id == "cap.memory.read"
    print("[PASS] test_registry_accept_registered")


def test_registry_context_enforcement():
    """Capabilities outside allowed contexts are rejected."""
    reg = CapabilityRegistry()
    cap = CapabilityManifest(
        id="cap.test.restricted",
        name="Restricted",
        action_class=ActionClass.EXECUTE,
        risk_class=RiskClass.HIGH,
        requires_human_approval=True,
        allowed_contexts=["runtime"],
        input_schema_ref="inline",
        output_schema_ref="inline",
    )
    reg.register(cap)
    # Allowed in runtime
    assert reg.check("cap.test.restricted", "runtime").allowed
    # Rejected in api context
    check = reg.check("cap.test.restricted", "api")
    assert not check.allowed
    assert "not in allowed_contexts" in check.reason
    print("[PASS] test_registry_context_enforcement")


def test_registry_list_by_class():
    """Can filter capabilities by action class and risk class."""
    reg = CapabilityRegistry()
    for cap in default_capabilities():
        reg.register(cap)

    reads = reg.list_by_action_class(ActionClass.READ)
    assert len(reads) >= 2

    highs = reg.list_by_risk_class(RiskClass.HIGH)
    assert len(highs) >= 1
    assert all(c.risk_class == RiskClass.HIGH for c in highs)
    print("[PASS] test_registry_list_by_class")


def test_registry_serialization():
    """Registry serializes to dict."""
    reg = CapabilityRegistry()
    for cap in default_capabilities():
        reg.register(cap)
    d = reg.to_dict()
    assert d["count"] == reg.count
    assert len(d["capabilities"]) == reg.count
    print("[PASS] test_registry_serialization")


def test_registry_unregister():
    """Can unregister a capability."""
    reg = CapabilityRegistry()
    for cap in default_capabilities():
        reg.register(cap)
    count_before = reg.count
    removed = reg.unregister("cap.memory.read")
    assert removed
    assert reg.count == count_before - 1
    assert not reg.check("cap.memory.read").allowed
    print("[PASS] test_registry_unregister")


def test_risk_score():
    """CapabilityManifest.base_risk_score matches risk class."""
    cap = CapabilityManifest(
        id="cap.test", name="Test", action_class=ActionClass.READ,
        risk_class=RiskClass.CRITICAL, requires_human_approval=True,
        allowed_contexts=["runtime"], input_schema_ref="", output_schema_ref="",
    )
    assert cap.base_risk_score == 0.95
    print("[PASS] test_risk_score")


if __name__ == "__main__":
    test_registry_reject_unknown()
    test_registry_accept_registered()
    test_registry_context_enforcement()
    test_registry_list_by_class()
    test_registry_serialization()
    test_registry_unregister()
    test_risk_score()
    print("\n  All capability registry tests passed.")
