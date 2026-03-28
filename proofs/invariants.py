"""
OmegA Proof System — Phase 1 Property-Based Tests

Uses the hypothesis library to generate randomized inputs and verify
that the core architectural invariants hold across the input space.

Run: python3 -m pytest proofs/invariants.py -v
"""

import sys
import os
import hashlib

# Ensure repo root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from omega.phylactery import Phylactery, PhylacteryCommit
from omega.envelope import RunEnvelope
from omega.agent import OmegaAgent
from omega.drift import ClaimBudget, SupportStatus, GoalContract, DriftController
from omega.memory import MemoryGraph, EdgeBundle, Stratum
from omega.risk_gate import RiskGate


# ---------------------------------------------------------------------------
# T-1: State Vector Well-Formedness
# ---------------------------------------------------------------------------

class TestStateVectorWellFormed:
    """T-1: Omega_t components are well-typed and non-null after construction."""

    def test_phylactery_head_is_hex64(self):
        """Phi_t is a 64-char hex string (SHA-256)."""
        p = Phylactery("genesis doctrine")
        assert len(p.head) == 64
        assert all(c in "0123456789abcdef" for c in p.head)

    def test_envelope_required_fields(self):
        """E_t has all required fields when properly constructed."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA", "doctrine": "test"},
            goal_contract="test goal",
        )
        assert env.is_complete()

    def test_goal_contract_has_task(self):
        """tau_t has a non-empty task field."""
        gc = GoalContract(task="test task")
        assert gc.task

    def test_claim_budget_is_valid_empty(self):
        """B_t with no claims is valid (vacuously true)."""
        b = ClaimBudget()
        assert b.is_valid()

    def test_memory_graph_initializes(self):
        """G_t^mem is a valid MemoryGraph after construction."""
        g = MemoryGraph()
        assert g.node_count == 0
        assert g.edge_count == 0

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=50)
    def test_phylactery_head_always_hex64(self, doctrine):
        """Phi_t is always a 64-char hex string regardless of input."""
        p = Phylactery(doctrine)
        assert len(p.head) == 64
        assert all(c in "0123456789abcdef" for c in p.head)


# ---------------------------------------------------------------------------
# T-2: Identity Continuity (Phylactery Hash Chain)
# ---------------------------------------------------------------------------

class TestIdentityContinuity:
    """T-2: Phi_{t+1} = H(Phi_t || delta || R) — hash chain integrity."""

    @given(st.lists(st.text(min_size=1, max_size=100), min_size=1, max_size=20))
    @settings(max_examples=50)
    def test_chain_verifies_after_commits(self, commits):
        """Chain always verifies after any sequence of commits."""
        p = Phylactery("genesis")
        for c in commits:
            p.commit(c)
        assert p.verify_chain()

    @given(st.text(min_size=1, max_size=100))
    @settings(max_examples=50)
    def test_commit_hash_matches_spec(self, content):
        """Each commit hash equals SHA256(parent_hash + content)."""
        p = Phylactery("genesis")
        old_head = p.head
        new_hash = p.commit(content)
        expected = hashlib.sha256((old_head + content).encode()).hexdigest()
        assert new_hash == expected

    def test_tamper_detection(self):
        """Mutating any commit invalidates the chain."""
        p = Phylactery("genesis")
        p.commit("update 1")
        p.commit("update 2")
        assert p.verify_chain()

        # Tamper with the middle commit
        p.chain[1].content = "TAMPERED"
        assert not p.verify_chain()

    def test_chain_length_grows(self):
        """Chain length is genesis + number of commits."""
        p = Phylactery("genesis")
        assert len(p) == 1
        p.commit("a")
        assert len(p) == 2
        p.commit("b")
        assert len(p) == 3

    def test_parent_linkage(self):
        """Each commit's parent_hash matches the previous commit's hash."""
        p = Phylactery("genesis")
        p.commit("a")
        p.commit("b")
        for i in range(1, len(p.chain)):
            assert p.chain[i].parent_hash == p.chain[i - 1].hash


# ---------------------------------------------------------------------------
# T-3: Governance Fail-Closed (AEGIS)
# ---------------------------------------------------------------------------

class TestGovernanceFailClosed:
    """T-3: R(a) >= tau => denied; BLOCKED_PATTERNS => hard deny."""

    def test_blocked_patterns_always_denied(self):
        """Every blocked pattern results in denial regardless of score."""
        gate = RiskGate(threshold=0.99)  # Very permissive threshold
        for pattern in RiskGate.BLOCKED_PATTERNS:
            action = f"please {pattern} now"
            allowed, score = gate.gate(action)
            assert not allowed, f"Blocked pattern '{pattern}' was allowed"

    @given(st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=50)
    def test_threshold_respected(self, threshold):
        """Score >= threshold => denied (for non-blocked actions)."""
        gate = RiskGate(threshold=threshold)
        # Use a benign action
        action = "read the document"
        allowed, score = gate.gate(action)
        if score >= threshold:
            assert not allowed
        else:
            assert allowed

    def test_benign_action_allowed(self):
        """A clearly benign action passes the default gate."""
        gate = RiskGate()
        allowed, score = gate.gate("read a book")
        assert allowed
        assert score < gate.threshold

    def test_hard_block_overrides_low_score(self):
        """Even with mitigations, blocked patterns are denied."""
        gate = RiskGate()
        allowed, _ = gate.gate("delete all with dry-run preview confirm")
        assert not allowed


# ---------------------------------------------------------------------------
# T-4: Claim Budget Validity (ADCCL)
# ---------------------------------------------------------------------------

class TestClaimBudgetBounds:
    """T-4: SUPPORTED claims require evidence; grounding ratio in [0, 1]."""

    def test_supported_without_evidence_invalid(self):
        """A SUPPORTED claim without evidence makes the budget invalid."""
        b = ClaimBudget()
        b.add("claim A", SupportStatus.SUPPORTED, evidence=None)
        assert not b.is_valid()

    def test_supported_with_evidence_valid(self):
        """A SUPPORTED claim with evidence is valid."""
        b = ClaimBudget()
        b.add("claim A", SupportStatus.SUPPORTED, evidence="test.py")
        assert b.is_valid()

    def test_hypothetical_no_evidence_valid(self):
        """HYPOTHETICAL claims do not require evidence."""
        b = ClaimBudget()
        b.add("claim A", SupportStatus.HYPOTHETICAL)
        assert b.is_valid()

    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=50),
            st.sampled_from(list(SupportStatus)),
            st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        ),
        min_size=0,
        max_size=20,
    ))
    @settings(max_examples=50)
    def test_grounding_ratio_bounded(self, claims):
        """Grounding ratio is always in [0.0, 1.0]."""
        b = ClaimBudget()
        for text, support, evidence in claims:
            b.add(text, support, evidence)
        ratio = b.grounding_ratio()
        assert 0.0 <= ratio <= 1.0

    def test_empty_budget_grounding_zero(self):
        """Empty budget has grounding ratio 0."""
        b = ClaimBudget()
        assert b.grounding_ratio() == 0.0

    def test_all_grounded_ratio_one(self):
        """All SUPPORTED/COMPUTED claims give ratio 1.0."""
        b = ClaimBudget()
        b.add("a", SupportStatus.SUPPORTED, evidence="e1")
        b.add("b", SupportStatus.COMPUTED, evidence="e2")
        assert b.grounding_ratio() == 1.0


# ---------------------------------------------------------------------------
# T-5: Memory Hardening Monotonicity (MYELIN)
# ---------------------------------------------------------------------------

class TestMemoryHardeningMonotonic:
    """T-5: Positive reward increases q_ij; co-activation non-decreasing."""

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.01, max_value=1.0),
        st.floats(min_value=0.01, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_hardening_increases_when_reward_above_current(self, q_init, reward, lam):
        """If reward > q_ij(t), then q_ij(t+1) > q_ij(t)."""
        assume(reward > q_init)
        edge = EdgeBundle(source="a", target="b", retrieval_util=q_init)
        edge.harden(reward, lam=lam)
        assert edge.retrieval_util > q_init

    @given(
        st.floats(min_value=0.01, max_value=1.0),
        st.floats(min_value=0.01, max_value=1.0),
    )
    @settings(max_examples=50)
    def test_coactivation_non_decreasing(self, reward, lam):
        """Co-activation count never decreases under positive reward."""
        edge = EdgeBundle(source="a", target="b", coactivation=5)
        old_coact = edge.coactivation
        edge.harden(reward, lam=lam)
        assert edge.coactivation >= old_coact

    @given(st.floats(min_value=0.01, max_value=1.0))
    @settings(max_examples=50)
    def test_staleness_resets_on_positive_reward(self, reward):
        """Staleness resets to 0 on any positive reward (Lemma T-5b)."""
        edge = EdgeBundle(source="a", target="b", staleness=10.0)
        edge.harden(reward)
        assert edge.staleness == 0.0

    def test_repeated_hardening_converges(self):
        """Repeated hardening with constant reward converges toward reward."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.1)
        target_reward = 0.9
        for _ in range(100):
            edge.harden(target_reward, lam=0.1)
        assert abs(edge.retrieval_util - target_reward) < 0.01

    def test_path_hardening_updates_all_edges(self):
        """harden_path updates every edge along the path."""
        g = MemoryGraph()
        g.add_node("a", "node a")
        g.add_node("b", "node b")
        g.add_node("c", "node c")
        g.add_edge("a", "b")
        g.add_edge("b", "c")

        old_ab = g.edges[("a", "b")].retrieval_util
        old_bc = g.edges[("b", "c")].retrieval_util

        g.harden_path(["a", "b", "c"], reward=1.0)

        assert g.edges[("a", "b")].retrieval_util > old_ab
        assert g.edges[("b", "c")].retrieval_util > old_bc


# ---------------------------------------------------------------------------
# T-6: Verifier Non-Bypass
# ---------------------------------------------------------------------------

class TestVerifierNonBypass:
    """T-6: If V <= tau_verify, action is blocked regardless of rho and R."""

    @given(
        st.floats(min_value=-1.0, max_value=0.4),   # V failing
        st.floats(min_value=0.0, max_value=0.1),     # rho passing
        st.floats(min_value=0.0, max_value=0.1),     # R passing
    )
    @settings(max_examples=50)
    def test_low_V_always_blocks(self, V, rho, R):
        """Even with perfect rho and R, low V blocks the action."""
        gate = RiskGate()
        allowed, details = gate.multi_gate(V, rho, R)
        assert not allowed
        assert not details["V_pass"]

    @given(
        st.floats(min_value=0.5, max_value=1.0),     # V passing
        st.floats(min_value=0.6, max_value=2.0),     # rho failing
        st.floats(min_value=0.0, max_value=0.1),     # R passing
    )
    @settings(max_examples=50)
    def test_low_rho_blocks_despite_V(self, V, rho, R):
        """High V cannot compensate for failing rho."""
        gate = RiskGate()
        allowed, details = gate.multi_gate(V, rho, R)
        assert not allowed
        assert not details["rho_pass"]


# ---------------------------------------------------------------------------
# T-7: Unified Action Gating (3-gate conjunction)
# ---------------------------------------------------------------------------

class TestUnifiedActionGating:
    """T-7: multi_gate is True iff all three gates pass."""

    @given(
        st.floats(min_value=-1.0, max_value=2.0),
        st.floats(min_value=-1.0, max_value=2.0),
        st.floats(min_value=-1.0, max_value=2.0),
    )
    @settings(max_examples=200)
    def test_conjunction_property(self, V, rho, R):
        """multi_gate == True iff (V > tau_v) AND (rho < theta) AND (R < tau_c)."""
        gate = RiskGate(threshold=0.8)
        tau_v, theta = 0.4, 0.5
        allowed, details = gate.multi_gate(V, rho, R, tau_verify=tau_v, theta_allow=theta)

        expected = (V > tau_v) and (rho < theta) and (R < gate.threshold)
        assert allowed == expected, (
            f"V={V}, rho={rho}, R={R}: got {allowed}, expected {expected}"
        )


# ---------------------------------------------------------------------------
# T-9: Self-Tag Immutability (Append-Only)
# ---------------------------------------------------------------------------

class TestSelfTagImmutability:
    """T-9: The Phylactery chain is append-only; history is immutable."""

    def test_chain_only_grows(self):
        """Chain length only increases, never decreases."""
        p = Phylactery("genesis")
        lengths = [len(p)]
        for content in ["a", "b", "c"]:
            p.commit(content)
            lengths.append(len(p))
        assert lengths == sorted(lengths)
        assert all(lengths[i] <= lengths[i + 1] for i in range(len(lengths) - 1))

    def test_historical_commits_unchanged_after_new_commit(self):
        """Adding a new commit does not alter any previous commit."""
        p = Phylactery("genesis")
        p.commit("update 1")
        snapshot = [(c.hash, c.content, c.parent_hash) for c in p.chain]

        p.commit("update 2")

        for i, (h, content, parent) in enumerate(snapshot):
            assert p.chain[i].hash == h
            assert p.chain[i].content == content
            assert p.chain[i].parent_hash == parent

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=2, max_size=10))
    @settings(max_examples=50)
    def test_prefix_preservation(self, commits):
        """S_t1 is always a prefix of S_t2 for t1 < t2."""
        p = Phylactery("genesis")
        snapshots = []
        for c in commits:
            p.commit(c)
            snapshots.append([commit.hash for commit in p.chain])

        for i in range(len(snapshots) - 1):
            earlier = snapshots[i]
            later = snapshots[i + 1]
            assert later[:len(earlier)] == earlier


# ---------------------------------------------------------------------------
# T-10: Run Envelope Completeness
# ---------------------------------------------------------------------------

class TestEnvelopeCompleteness:
    """T-10: Envelope must be complete and carry identity before execution."""

    def test_complete_envelope_passes(self):
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="task",
        )
        assert env.is_complete()
        assert env.has_identity()

    def test_missing_identity_name_fails(self):
        env = RunEnvelope(
            identity_kernel={},
            goal_contract="task",
        )
        assert env.is_complete()  # Fields non-null
        assert not env.has_identity()  # But no identity name

    def test_null_identity_kernel_fails(self):
        env = RunEnvelope(
            identity_kernel=None,
            goal_contract="task",
        )
        assert not env.is_complete()
        assert not env.has_identity()

    def test_system_prompt_contains_identity(self):
        env = RunEnvelope(
            identity_kernel={"name": "OmegA", "doctrine": "I am sovereign"},
            goal_contract="task",
        )
        prompt = env.to_system_prompt()
        assert "OmegA" in prompt
        assert "sovereign" in prompt.lower()

    def test_version_increments_monotonically(self, monkeypatch):
        agent = OmegaAgent()
        monkeypatch.setattr(agent.risk_gate, "gate", lambda action: (True, 0.1))
        monkeypatch.setattr(agent, "_generate", lambda *args, **kwargs: "ok")

        first = agent.run("task one")
        second = agent.run("task two")

        assert first.envelope_version == 1
        assert second.envelope_version == 2
        assert second.envelope_version > first.envelope_version
