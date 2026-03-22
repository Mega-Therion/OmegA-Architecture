"""
OmegA — Sovereign, Persistent, and Self-Knowing AI Architecture

Minimal reference implementation of the four-layer OmegA stack:
  AEGIS  → Governance shell (risk gate, run envelope, action gating)
  AEON   → Identity OS (Phylactery, TSO lifecycle, MUSE, continuity)
  ADCCL  → Cognitive control loop (drift penalty, verification, claim budgets)
  MYELIN → Graph memory (edge hardening, strata, spatial energy)
"""

__version__ = "0.1.0"

from omega.phylactery import Phylactery
from omega.envelope import RunEnvelope
from omega.risk_gate import RiskGate
from omega.drift import DriftController, ClaimBudget
from omega.memory import MemoryGraph
from omega.agent import OmegaAgent
