"""
OmegA Proof System — State Machine Tests (T-1, T-6, T-9)

These tests use hypothesis stateful testing to verify state-machine
properties that would ideally be checked with TLA+ model checking.
Since TLA+ requires Java (not installed), these provide equivalent
coverage using Python-native stateful property testing.

  T-1: State vector well-formedness is maintained across all transitions
  T-6: Verifier non-bypass — V gate cannot be circumvented
  T-9: Self-tag immutability — phylactery chain is append-only

Run: python3 -m pytest proofs/state_machines.py -v
"""

import sys
import os
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize

from omega.phylactery import Phylactery, PhylacteryCommit
from omega.envelope import RunEnvelope, EnvelopeClock
from omega.drift import ClaimBudget, SupportStatus, GoalContract, DriftController
from omega.memory import MemoryGraph, EdgeBundle, Stratum
from omega.risk_gate import RiskGate


# ---------------------------------------------------------------------------
# T-1: State Vector Well-Formedness State Machine
#
# TLA+ equivalent: StateVectorSpec
#   TypeOK == /\ Phi_t \in STRING
#             /\ E_t \in RunEnvelope
#             /\ tau_t \in GoalContract
#             /\ B_t \in ClaimBudget
#             /\ S_t \in PhylacteryChain
#             /\ G_t_mem \in MemoryGraph
#
# We verify that no sequence of operations can leave the state vector
# in an inconsistent (null, wrong-type, or violated-invariant) state.
# ---------------------------------------------------------------------------

class StateVectorMachine(RuleBasedStateMachine):
    """Stateful test: OmegA state vector remains well-formed across all transitions."""

    def __init__(self):
        super().__init__()
        self.phylactery = None
        self.envelope = None
        self.clock = None
        self.goal = None
        self.budget = None
        self.memory = None
        self.risk_gate = None

    @initialize()
    def init_state(self):
        self.phylactery = Phylactery("genesis doctrine")
        self.clock = EnvelopeClock()
        self.envelope = RunEnvelope(
            identity_kernel={"name": "OmegA", "doctrine": "test"},
            goal_contract="initial task",
            version=self.clock.next(),
        )
        self.goal = GoalContract(task="test task")
        self.budget = ClaimBudget()
        self.memory = MemoryGraph()
        self.risk_gate = RiskGate()

    @rule(content=st.text(min_size=1, max_size=100))
    def commit_to_phylactery(self, content):
        self.phylactery.commit(content)

    @rule(task=st.text(min_size=1, max_size=100))
    def update_goal(self, task):
        self.goal = GoalContract(task=task)

    @rule(
        text=st.text(min_size=1, max_size=50),
        support=st.sampled_from(list(SupportStatus)),
        evidence=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
    )
    def add_claim(self, text, support, evidence):
        self.budget.add(text, support, evidence)

    @rule(
        node_id=st.text(min_size=1, max_size=20, alphabet="abcdefghij"),
        content=st.text(min_size=1, max_size=50),
    )
    def add_memory_node(self, node_id, content):
        self.memory.add_node(node_id, content)

    @rule(
        source=st.text(min_size=1, max_size=20, alphabet="abcdefghij"),
        dest=st.text(min_size=1, max_size=20, alphabet="abcdefghij"),
    )
    def add_memory_edge(self, source, dest):
        if source in self.memory.nodes and dest in self.memory.nodes and source != dest:
            self.memory.add_edge(source, dest)

    @rule()
    def advance_envelope(self):
        self.envelope = RunEnvelope(
            identity_kernel={"name": "OmegA", "doctrine": "test"},
            goal_contract=self.goal.task,
            version=self.clock.next(),
        )

    # -- Invariant checks (verified after EVERY transition) --

    @invariant()
    def phi_t_is_valid_hash(self):
        """Phi_t is always a 64-char hex SHA-256 string."""
        assert len(self.phylactery.head) == 64
        assert all(c in "0123456789abcdef" for c in self.phylactery.head)

    @invariant()
    def chain_is_always_valid(self):
        """The phylactery chain verifies after every transition."""
        assert self.phylactery.verify_chain()

    @invariant()
    def envelope_is_well_formed(self):
        """E_t is always complete and carries identity."""
        assert self.envelope.is_complete()
        assert self.envelope.has_identity()

    @invariant()
    def envelope_version_positive(self):
        """Envelope version is always positive."""
        assert self.envelope.version > 0

    @invariant()
    def goal_contract_has_task(self):
        """tau_t always has a non-empty task."""
        assert self.goal.task

    @invariant()
    def grounding_ratio_bounded(self):
        """B_t grounding ratio is always in [0, 1]."""
        ratio = self.budget.grounding_ratio()
        assert 0.0 <= ratio <= 1.0

    @invariant()
    def memory_graph_consistent(self):
        """G_t^mem edges reference existing nodes."""
        for (src, tgt) in self.memory.edges:
            assert src in self.memory.nodes, f"Edge source {src} not in nodes"
            assert tgt in self.memory.nodes, f"Edge target {tgt} not in nodes"


TestStateVectorStateMachine = StateVectorMachine.TestCase
TestStateVectorStateMachine.settings = settings(
    max_examples=50, stateful_step_count=20
)


# ---------------------------------------------------------------------------
# T-6: Verifier Non-Bypass State Machine
#
# TLA+ equivalent: VerifierSpec
#   Safety == \A state \in States:
#     state.V <= tau_verify => ~state.permitted
#
# We verify that across any sequence of gate evaluations with varying
# parameters, the verifier gate can NEVER be bypassed by the other gates.
# ---------------------------------------------------------------------------

class VerifierNonBypassMachine(RuleBasedStateMachine):
    """Stateful test: V gate can never be bypassed by rho or R."""

    def __init__(self):
        super().__init__()
        self.gate = None
        self.history = []

    @initialize()
    def init_gate(self):
        self.gate = RiskGate(threshold=0.8)
        self.history = []

    @rule(
        V=st.floats(min_value=-1.0, max_value=2.0),
        rho=st.floats(min_value=-1.0, max_value=2.0),
        R=st.floats(min_value=-1.0, max_value=2.0),
        tau_v=st.floats(min_value=0.1, max_value=0.9),
        theta=st.floats(min_value=0.1, max_value=0.9),
    )
    def evaluate_gate(self, V, rho, R, tau_v, theta):
        allowed, details = self.gate.multi_gate(V, rho, R,
                                                 tau_verify=tau_v,
                                                 theta_allow=theta)
        self.history.append({
            "V": V, "rho": rho, "R": R,
            "tau_v": tau_v, "theta": theta,
            "allowed": allowed, "details": details,
        })

    @rule(threshold=st.floats(min_value=0.01, max_value=0.99))
    def change_threshold(self, threshold):
        self.gate = RiskGate(threshold=threshold)

    # -- Invariants --

    @invariant()
    def verifier_never_bypassed(self):
        """If V <= tau_verify in any evaluation, action was denied."""
        for entry in self.history:
            if entry["V"] <= entry["tau_v"]:
                assert not entry["allowed"], (
                    f"BYPASS: V={entry['V']} <= tau_v={entry['tau_v']} "
                    f"but action was permitted"
                )

    @invariant()
    def bridge_never_bypassed(self):
        """If rho >= theta in any evaluation, action was denied."""
        for entry in self.history:
            if entry["rho"] >= entry["theta"]:
                assert not entry["allowed"], (
                    f"BYPASS: rho={entry['rho']} >= theta={entry['theta']} "
                    f"but action was permitted"
                )

    @invariant()
    def conjunction_holds(self):
        """Every permitted action has all three gates passing."""
        for entry in self.history:
            if entry["allowed"]:
                d = entry["details"]
                assert d["V_pass"] and d["rho_pass"] and d["R_pass"]


TestVerifierNonBypass = VerifierNonBypassMachine.TestCase
TestVerifierNonBypass.settings = settings(
    max_examples=50, stateful_step_count=30
)


# ---------------------------------------------------------------------------
# T-9: Self-Tag Immutability State Machine
#
# TLA+ equivalent: SelfTagSpec
#   AppendOnly == \A t1, t2 \in Time:
#     t1 < t2 => IsPrefix(Chain_t1, Chain_t2)
#   Immutable == \A t, i: i < Len(Chain_t) =>
#     Chain_t[i] = Chain_{t+1}[i]
#
# We verify that the phylactery chain is truly append-only: existing
# entries never change, the chain only grows, and all historical
# snapshots remain prefixes of the current chain.
# ---------------------------------------------------------------------------

class SelfTagImmutabilityMachine(RuleBasedStateMachine):
    """Stateful test: phylactery chain is append-only and immutable."""

    def __init__(self):
        super().__init__()
        self.phylactery = None
        self.snapshots = []

    @initialize()
    def init_chain(self):
        self.phylactery = Phylactery("genesis doctrine")
        self.snapshots = [self._snapshot()]

    def _snapshot(self):
        return [(c.hash, c.content, c.parent_hash) for c in self.phylactery.chain]

    @rule(content=st.text(min_size=1, max_size=100))
    def commit(self, content):
        self.phylactery.commit(content)
        self.snapshots.append(self._snapshot())

    # -- Invariants --

    @invariant()
    def chain_only_grows(self):
        """Chain length is monotonically non-decreasing."""
        for i in range(1, len(self.snapshots)):
            assert len(self.snapshots[i]) >= len(self.snapshots[i - 1])

    @invariant()
    def historical_entries_immutable(self):
        """No historical entry has changed between snapshots."""
        if len(self.snapshots) < 2:
            return
        prev = self.snapshots[-2]
        curr = self.snapshots[-1]
        for i in range(len(prev)):
            assert curr[i] == prev[i], (
                f"Entry {i} changed between snapshots: {prev[i]} != {curr[i]}"
            )

    @invariant()
    def all_snapshots_are_prefixes(self):
        """Every historical snapshot is a prefix of the current chain."""
        current = self.snapshots[-1]
        for snap in self.snapshots:
            assert current[:len(snap)] == snap, (
                "Historical snapshot is not a prefix of current chain"
            )

    @invariant()
    def chain_always_verifies(self):
        """The chain verifies at every step."""
        assert self.phylactery.verify_chain()

    @invariant()
    def genesis_never_changes(self):
        """The genesis commit (position 0) never changes."""
        genesis = self.snapshots[0][0]
        current_genesis = self.snapshots[-1][0]
        assert genesis == current_genesis, "Genesis commit was modified"


TestSelfTagImmutability = SelfTagImmutabilityMachine.TestCase
TestSelfTagImmutability.settings = settings(
    max_examples=50, stateful_step_count=20
)


# ---------------------------------------------------------------------------
# T-10: Envelope Version Monotonicity (bonus state machine)
# ---------------------------------------------------------------------------

class EnvelopeClockMachine(RuleBasedStateMachine):
    """Stateful test: EnvelopeClock.next() is strictly monotonic."""

    def __init__(self):
        super().__init__()
        self.clock = None
        self.versions = []

    @initialize()
    def init_clock(self):
        self.clock = EnvelopeClock()
        self.versions = []

    @rule()
    def advance(self):
        v = self.clock.next()
        self.versions.append(v)

    @invariant()
    def strictly_increasing(self):
        """All versions are strictly increasing."""
        for i in range(1, len(self.versions)):
            assert self.versions[i] > self.versions[i - 1]

    @invariant()
    def no_gaps(self):
        """Versions increment by exactly 1 each time."""
        for i in range(1, len(self.versions)):
            assert self.versions[i] == self.versions[i - 1] + 1

    @invariant()
    def always_positive(self):
        """All versions are positive."""
        for v in self.versions:
            assert v > 0


TestEnvelopeClockMonotonic = EnvelopeClockMachine.TestCase
TestEnvelopeClockMonotonic.settings = settings(
    max_examples=30, stateful_step_count=20
)
