"""
AEGIS Capability Registry — Declare-before-use enforcement for all executable capabilities.

No tool or side-effect runs unless it is registered in the CapabilityRegistry.
Unknown capability calls are rejected (fail closed).

Architecture: AEGIS Phase 8
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from omega.envelope import ActionClass


class RiskClass(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_CLASS_SCORE: dict[RiskClass, float] = {
    RiskClass.LOW: 0.1,
    RiskClass.MEDIUM: 0.4,
    RiskClass.HIGH: 0.7,
    RiskClass.CRITICAL: 0.95,
}


@dataclass
class CapabilityManifest:
    """Typed declaration of an executable capability."""
    id: str
    name: str
    action_class: ActionClass
    risk_class: RiskClass
    requires_human_approval: bool
    allowed_contexts: list[str]
    input_schema_ref: str
    output_schema_ref: str
    description: str = ""
    registered_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "action_class": self.action_class.value,
            "risk_class": self.risk_class.value,
            "requires_human_approval": self.requires_human_approval,
            "allowed_contexts": self.allowed_contexts,
            "input_schema_ref": self.input_schema_ref,
            "output_schema_ref": self.output_schema_ref,
            "description": self.description,
            "registered_at": self.registered_at,
        }

    @property
    def base_risk_score(self) -> float:
        return RISK_CLASS_SCORE[self.risk_class]


@dataclass
class CapabilityCheck:
    """Result of a capability lookup / validation."""
    allowed: bool
    capability_id: str
    reason: str
    manifest: CapabilityManifest | None = None

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "capability_id": self.capability_id,
            "reason": self.reason,
            "manifest": self.manifest.to_dict() if self.manifest else None,
        }


class CapabilityRegistry:
    """
    Central registry of all declared capabilities.
    Capabilities must be registered before use. Unregistered calls are rejected.
    """

    def __init__(self):
        self._capabilities: dict[str, CapabilityManifest] = {}

    def register(self, manifest: CapabilityManifest) -> None:
        """Register a capability. Overwrites if same id already exists."""
        self._capabilities[manifest.id] = manifest

    def unregister(self, capability_id: str) -> bool:
        """Remove a capability. Returns True if it existed."""
        return self._capabilities.pop(capability_id, None) is not None

    def get(self, capability_id: str) -> CapabilityManifest | None:
        return self._capabilities.get(capability_id)

    def check(self, capability_id: str, context: str = "default") -> CapabilityCheck:
        """
        Validate that a capability is registered and allowed in the given context.
        Fail closed: unknown capabilities are rejected.
        """
        manifest = self._capabilities.get(capability_id)
        if manifest is None:
            return CapabilityCheck(
                allowed=False,
                capability_id=capability_id,
                reason=f"Capability '{capability_id}' is not registered",
            )

        if manifest.allowed_contexts and context not in manifest.allowed_contexts:
            return CapabilityCheck(
                allowed=False,
                capability_id=capability_id,
                reason=f"Context '{context}' not in allowed_contexts {manifest.allowed_contexts}",
                manifest=manifest,
            )

        return CapabilityCheck(
            allowed=True,
            capability_id=capability_id,
            reason="registered_and_allowed",
            manifest=manifest,
        )

    def list_capabilities(self) -> list[CapabilityManifest]:
        return list(self._capabilities.values())

    def list_by_action_class(self, action_class: ActionClass) -> list[CapabilityManifest]:
        return [m for m in self._capabilities.values() if m.action_class == action_class]

    def list_by_risk_class(self, risk_class: RiskClass) -> list[CapabilityManifest]:
        return [m for m in self._capabilities.values() if m.risk_class == risk_class]

    @property
    def count(self) -> int:
        return len(self._capabilities)

    def to_dict(self) -> dict:
        return {
            "count": self.count,
            "capabilities": [m.to_dict() for m in self._capabilities.values()],
        }


# ------------------------------------------------------------------
# Built-in capabilities (registered at import time if desired)
# ------------------------------------------------------------------

def default_capabilities() -> list[CapabilityManifest]:
    """Return the default set of built-in OmegA capabilities."""
    return [
        CapabilityManifest(
            id="cap.memory.read",
            name="Read Memory",
            action_class=ActionClass.READ,
            risk_class=RiskClass.LOW,
            requires_human_approval=False,
            allowed_contexts=["default", "runtime", "api"],
            input_schema_ref="schemas/memory_record.schema.json",
            output_schema_ref="schemas/memory_record.schema.json",
            description="Read a node from the MYELIN memory graph",
        ),
        CapabilityManifest(
            id="cap.memory.write",
            name="Write Memory",
            action_class=ActionClass.WRITE,
            risk_class=RiskClass.MEDIUM,
            requires_human_approval=False,
            allowed_contexts=["default", "runtime", "api"],
            input_schema_ref="schemas/memory_record.schema.json",
            output_schema_ref="schemas/memory_record.schema.json",
            description="Write a node to the MYELIN memory graph under policy",
        ),
        CapabilityManifest(
            id="cap.docstore.ingest",
            name="Ingest Document",
            action_class=ActionClass.WRITE,
            risk_class=RiskClass.LOW,
            requires_human_approval=False,
            allowed_contexts=["default", "runtime", "api", "ingest"],
            input_schema_ref="schemas/ingest_job.schema.json",
            output_schema_ref="schemas/answer_object.schema.json",
            description="Ingest a document into the canonical doc store",
        ),
        CapabilityManifest(
            id="cap.docstore.retrieve",
            name="Retrieve Documents",
            action_class=ActionClass.READ,
            risk_class=RiskClass.LOW,
            requires_human_approval=False,
            allowed_contexts=["default", "runtime", "api"],
            input_schema_ref="schemas/retrieval_result.schema.json",
            output_schema_ref="schemas/retrieval_result.schema.json",
            description="Retrieve chunks from the canonical doc store",
        ),
        CapabilityManifest(
            id="cap.llm.generate",
            name="LLM Generate",
            action_class=ActionClass.NETWORK,
            risk_class=RiskClass.MEDIUM,
            requires_human_approval=False,
            allowed_contexts=["default", "runtime", "api"],
            input_schema_ref="inline:prompt+model",
            output_schema_ref="inline:text",
            description="Generate text via an LLM provider",
        ),
        CapabilityManifest(
            id="cap.action.execute",
            name="Execute Action",
            action_class=ActionClass.EXECUTE,
            risk_class=RiskClass.HIGH,
            requires_human_approval=True,
            allowed_contexts=["runtime"],
            input_schema_ref="schemas/action_envelope.schema.json",
            output_schema_ref="schemas/action_envelope.schema.json",
            description="Execute a gated action through the AEGIS shell",
        ),
        CapabilityManifest(
            id="cap.reconcile",
            name="Memory Reconciliation",
            action_class=ActionClass.WRITE,
            risk_class=RiskClass.MEDIUM,
            requires_human_approval=False,
            allowed_contexts=["default", "runtime", "maintenance"],
            input_schema_ref="schemas/reconciliation_event.schema.json",
            output_schema_ref="schemas/reconciliation_event.schema.json",
            description="Run memory reconciliation to resolve conflicts and staleness",
        ),
    ]
