"""
OmegA Agent — Unified agent combining all four layers.

Wires together AEGIS (envelope + risk gate), AEON (phylactery + TSO),
ADCCL (drift control + verification), and MYELIN (graph memory)
into a single callable agent.

Usage:
    from omega import OmegaAgent

    agent = OmegaAgent()
    result = agent.run("Explain the OmegA architecture", model="llama3.2:3b")
"""

import json
import time
import hashlib
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Optional

from omega.phylactery import Phylactery
from omega.envelope import RunEnvelope
from omega.risk_gate import RiskGate
from omega.drift import DriftController, GoalContract, ClaimBudget, SupportStatus
from omega.memory import MemoryGraph, Stratum


@dataclass
class SelfTag:
    """AEON self-tag — immutable continuity record."""
    tso_hash: str
    V: float
    outcome: str  # verified | uncertain | rejected
    timestamp: float = field(default_factory=time.time)


@dataclass
class RunResult:
    """Result of a single OmegA agent run."""
    response: str
    verification: dict
    self_tag: SelfTag
    envelope_complete: bool
    risk_score: float
    risk_allowed: bool
    model: str
    elapsed_ms: float


class OmegaAgent:
    """Minimal reference implementation of the OmegA stack."""

    DEFAULT_DOCTRINE = "I am what I am, and I will be what I will be."
    OLLAMA_URL = "http://localhost:11434"

    def __init__(self, name: str = "OmegA", doctrine: str | None = None):
        self.phylactery = Phylactery(doctrine or self.DEFAULT_DOCTRINE)
        self.risk_gate = RiskGate()
        self.memory = MemoryGraph()
        self.self_tags: list[SelfTag] = []
        self.name = name

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

    def run(self, task: str, model: str = "llama3.2:3b",
            temperature: float = 0.3) -> RunResult:
        """Execute the full OmegA stack for a single task.

        Pipeline: Envelope → Risk Gate → Generate → Verify → SelfTag
        """
        start = time.time()

        # 1. AEGIS: Compile Run Envelope
        goal = GoalContract(task=task)
        envelope = RunEnvelope(
            identity_kernel=self.identity_kernel,
            goal_contract=task,
        )

        # 2. AEGIS: Risk Gate
        allowed, R = self.risk_gate.gate(task)
        if not allowed:
            tag = SelfTag(
                tso_hash=hashlib.sha256(task.encode()).hexdigest(),
                V=0.0, outcome="rejected",
            )
            self.self_tags.append(tag)
            return RunResult(
                response=f"[BLOCKED] Risk score {R:.2f} exceeds threshold.",
                verification={"V": 0.0, "passed": False, "outcome": "rejected"},
                self_tag=tag,
                envelope_complete=envelope.is_complete(),
                risk_score=R,
                risk_allowed=False,
                model=model,
                elapsed_ms=(time.time() - start) * 1000,
            )

        # 3. AEON + ADCCL: Generate via substrate model
        response = self._generate(model, task, envelope.to_system_prompt(), temperature)

        # 4. ADCCL: Verify
        drift = DriftController(goal)
        verification = drift.verify(response)

        # 5. AEON: Write SelfTag
        tso_hash = hashlib.sha256((task + response).encode()).hexdigest()
        tag = SelfTag(
            tso_hash=tso_hash,
            V=verification["V"],
            outcome=verification["outcome"],
        )
        self.self_tags.append(tag)

        # 6. MYELIN: Store interaction in memory
        node_id = tso_hash[:12]
        self.memory.add_node(node_id, task, stratum=Stratum.EPISODIC)

        elapsed = (time.time() - start) * 1000

        return RunResult(
            response=response,
            verification=verification,
            self_tag=tag,
            envelope_complete=envelope.is_complete(),
            risk_score=R,
            risk_allowed=True,
            model=model,
            elapsed_ms=round(elapsed, 1),
        )

    def _generate(self, model: str, prompt: str, system: str,
                  temperature: float) -> str:
        """Call Ollama's /api/generate endpoint."""
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 512},
        }).encode()
        req = urllib.request.Request(
            f"{self.OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                return data.get("response", "[No response from model]")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return f"[MODEL ERROR] {e}"

    @property
    def state_vector(self) -> dict:
        """Current Ω_t = ⟨Φ_t, E_t, τ_t, B_t, S_t, G_t^mem⟩"""
        return {
            "Phi_t": self.phylactery.head,
            "E_t": "compiled",
            "tau_t": self.self_tags[-1].tso_hash if self.self_tags else None,
            "B_t": [],
            "S_t": self.self_tags[-1].__dict__ if self.self_tags else None,
            "G_t_mem": {
                "nodes": self.memory.node_count,
                "edges": self.memory.edge_count,
            },
        }
