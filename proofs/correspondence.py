"""
OmegA Proof System — Proof-to-Implementation Correspondence Tests

These tests verify that the RUNTIME Python implementations satisfy the
same properties that the Lean4 models prove abstractly. They bridge
the gap between:

  - Lean4 abstract models (proofs/OmegaProofs/*.lean)
  - Python runtime code (omega/*.py)

Each test class maps to a Lean4 proof file and verifies that the live
implementation behaves identically to the formal model.

Run: python3 -m pytest proofs/correspondence.py -v
"""

import sys
import os
import hashlib
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from omega.phylactery import Phylactery, PhylacteryCommit
from omega.memory import EdgeBundle, MemoryGraph
from omega.risk_gate import RiskGate


# ---------------------------------------------------------------------------
# T-2 Correspondence: IdentityContinuity.lean <-> phylactery.py
#
# Lean model:
#   chainValid phi delta r n := forall i, i < n -> phi(i+1) = Hash(phi(i), delta(i), r(i))
#   tamper_detection: same base + same transitions => same chain
#   chain_determinism: two valid chains with same base agree at all positions
#
# Runtime:
#   PhylacteryCommit.__post_init__: hash = sha256(parent_hash + content)
#   Phylactery.commit(): appends with parent_hash = self.head
#   Phylactery.verify_chain(): re-hashes each commit and checks linkage
# ---------------------------------------------------------------------------

class TestT2Correspondence:
    """Verify phylactery.py satisfies IdentityContinuity.lean properties."""

    def test_chain_valid_construction(self):
        """Lean T-2a: chain_by_construction — a chain built by the hash
        rule is valid. Runtime: verify_chain() returns True after commits."""
        p = Phylactery("genesis doctrine")
        p.commit("delta_0")
        p.commit("delta_1")
        p.commit("delta_2")
        assert p.verify_chain(), "Chain built by commit() must verify"

    def test_hash_rule_matches_lean_model(self):
        """Verify the runtime hash rule matches Lean's Hash(phi_i, delta_i, r_i).

        Lean models Hash as an opaque injective function on triples.
        Runtime uses SHA-256(parent_hash + content). This test confirms
        the runtime computes each step deterministically from its parent."""
        p = Phylactery("genesis")
        commits = ["alpha", "beta", "gamma"]
        for content in commits:
            old_head = p.head
            new_hash = p.commit(content)
            expected = hashlib.sha256((old_head + content).encode()).hexdigest()
            assert new_hash == expected, (
                f"Runtime hash rule diverges from spec: "
                f"H('{old_head[:8]}...' + '{content}') != '{new_hash[:8]}...'"
            )

    def test_tamper_detection_correspondence(self):
        """Lean T-2b: tamper_detection — if phi_j is changed, chainValid fails.
        Runtime: mutating commit content causes verify_chain() to return False."""
        p = Phylactery("genesis")
        p.commit("step 1")
        p.commit("step 2")
        p.commit("step 3")
        assert p.verify_chain()

        # Tamper at position 1 (first non-genesis commit)
        p.chain[1].content = "TAMPERED_CONTENT"
        assert not p.verify_chain(), (
            "Lean T-2b requires tamper detection; runtime failed to detect"
        )

    def test_tamper_at_every_position(self):
        """Exhaustive tamper detection: mutating ANY position is caught."""
        p = Phylactery("genesis")
        for i in range(5):
            p.commit(f"step_{i}")

        for tamper_pos in range(len(p.chain)):
            # Fresh chain each time
            q = Phylactery("genesis")
            for i in range(5):
                q.commit(f"step_{i}")
            assert q.verify_chain()

            q.chain[tamper_pos].content = "EVIL"
            assert not q.verify_chain(), (
                f"Tamper at position {tamper_pos} not detected"
            )

    def test_chain_determinism(self):
        """Lean T-2c: chain_determinism — two chains with same base and
        same transitions produce identical hashes at every position."""
        commits = ["alpha", "beta", "gamma", "delta"]

        p1 = Phylactery("same genesis")
        p2 = Phylactery("same genesis")

        for c in commits:
            p1.commit(c)
            p2.commit(c)

        assert len(p1.chain) == len(p2.chain)
        for i in range(len(p1.chain)):
            assert p1.chain[i].hash == p2.chain[i].hash, (
                f"Lean chain_determinism violated at position {i}"
            )

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=15))
    @settings(max_examples=50)
    def test_chain_determinism_fuzz(self, commits):
        """Fuzzed chain determinism: randomized inputs still produce
        identical chains when base and transitions match."""
        p1 = Phylactery("fuzz_genesis")
        p2 = Phylactery("fuzz_genesis")
        for c in commits:
            p1.commit(c)
            p2.commit(c)
        for i in range(len(p1.chain)):
            assert p1.chain[i].hash == p2.chain[i].hash

    def test_parent_linkage_matches_lean_chain_valid(self):
        """Lean chainValid requires phi(i).parent = phi(i-1).hash.
        Runtime: each commit's parent_hash equals prior commit's hash."""
        p = Phylactery("genesis")
        for i in range(10):
            p.commit(f"commit_{i}")

        for i in range(1, len(p.chain)):
            assert p.chain[i].parent_hash == p.chain[i - 1].hash, (
                f"Parent linkage broken at position {i}"
            )


# ---------------------------------------------------------------------------
# T-3 Correspondence: GovernanceFailClosed.lean <-> risk_gate.py
#
# Lean model:
#   riskGateNat risk threshold := if risk < threshold then permit else deny
#   fail_closed_nat: risk >= threshold -> deny
#   default_denial: riskGateNat threshold threshold = deny
#   monotonic_denial: r1 >= threshold AND r2 >= r1 -> deny(r2)
#
# Runtime:
#   RiskGate.gate(): R < threshold -> (True, R); else (False, R)
#   RiskGate.is_policy_blocked(): hard deny for blocked patterns
#   RiskGate.multi_gate(): all([V_pass, rho_pass, R_pass])
# ---------------------------------------------------------------------------

class TestT3Correspondence:
    """Verify risk_gate.py satisfies GovernanceFailClosed.lean properties."""

    def test_fail_closed_at_threshold(self):
        """Lean T-3d/T-3e: risk >= threshold => deny.
        At exact threshold boundary, gate must deny (fail-closed)."""
        gate = RiskGate(threshold=0.5)
        # Score a benign action to get a known score
        score = gate.score("read a book")
        # Now test: if we set threshold AT the score, it must deny
        gate2 = RiskGate(threshold=score)
        allowed, _ = gate2.gate("read a book")
        assert not allowed, "Lean fail_closed: score == threshold must deny"

    @given(st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=100)
    def test_fail_closed_property(self, threshold):
        """Lean fail_closed_nat: for any action, if score >= threshold, denied."""
        gate = RiskGate(threshold=threshold)
        action = "read a document"
        allowed, score = gate.gate(action)
        if score >= threshold:
            assert not allowed, (
                f"Lean fail_closed violated: score={score} >= threshold={threshold} but allowed"
            )

    def test_default_denial_policy_blocked(self):
        """Lean T-3e default_denial: blocked patterns are ALWAYS denied,
        regardless of threshold (even threshold=1.0)."""
        gate = RiskGate(threshold=1.0)  # maximally permissive
        for pattern in RiskGate.BLOCKED_PATTERNS:
            allowed, _ = gate.gate(f"please {pattern}")
            assert not allowed, (
                f"Default denial violated for blocked pattern: {pattern}"
            )

    @given(
        st.floats(min_value=0.01, max_value=0.99),
        st.floats(min_value=0.01, max_value=0.99),
    )
    @settings(max_examples=100)
    def test_monotonic_denial(self, t1, t2):
        """Lean T-3f monotonic_denial: if action denied at threshold t1,
        still denied at any threshold t2 <= t1."""
        assume(t2 <= t1)
        gate1 = RiskGate(threshold=t1)
        gate2 = RiskGate(threshold=t2)
        action = "read the file"
        allowed1, score1 = gate1.gate(action)
        allowed2, score2 = gate2.gate(action)
        # Scores are the same (same action), thresholds differ
        assert score1 == score2
        if not allowed1:
            assert not allowed2, (
                "Lean monotonic_denial violated: denied at t1 but allowed at t2 <= t1"
            )

    def test_gate_returns_bool_float_pair(self):
        """Runtime contract: gate() returns (bool, float) matching Lean's
        GateDecision enum semantics."""
        gate = RiskGate()
        result = gate.gate("test action")
        assert isinstance(result, tuple)
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)


# ---------------------------------------------------------------------------
# T-5 Correspondence: MemoryHardening.lean <-> memory.py
#
# Lean model (milliscale [0,1000]):
#   hardenScaled q lam r := ((1000 - lam) * q + lam * r) / 1000
#   monotonicity_numerator: r >= q -> numerator >= 1000 * q
#   bounded_numerator: q,r in [0,1000] -> numerator <= 1000*1000
#   fixed_point: (1000-lam)*r + lam*r = 1000*r (when lam <= 1000)
#
# Runtime (float [0.0, 1.0]):
#   EdgeBundle.harden(reward, lam):
#     self.retrieval_util = (1 - lam) * self.retrieval_util + lam * reward
# ---------------------------------------------------------------------------

class TestT5Correspondence:
    """Verify memory.py EdgeBundle.harden() satisfies MemoryHardening.lean."""

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.001, max_value=1.0),
    )
    @settings(max_examples=200)
    def test_monotonicity_positive_reward(self, q, r, lam):
        """Lean monotonicity_numerator: if r >= q, then q' >= q.
        Runtime: harden(reward >= q, lam) never decreases retrieval_util."""
        assume(r >= q)
        edge = EdgeBundle(source="a", target="b", retrieval_util=q)
        edge.harden(r, lam=lam)
        assert edge.retrieval_util >= q - 1e-12, (
            f"Lean monotonicity violated: q={q}, r={r}, lam={lam}, "
            f"q'={edge.retrieval_util}"
        )

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.001, max_value=1.0),
    )
    @settings(max_examples=200)
    def test_bounded_output(self, q, r, lam):
        """Lean bounded_numerator: if q, r in [0,1000], output in [0,1000].
        Runtime: if q, r in [0,1], output in [0,1]."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=q)
        edge.harden(r, lam=lam)
        assert -1e-12 <= edge.retrieval_util <= 1.0 + 1e-12, (
            f"Lean bounded violated: q={q}, r={r}, lam={lam}, "
            f"q'={edge.retrieval_util}"
        )

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.001, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_fixed_point(self, r, lam):
        """Lean fixed_point: harden(r, lam, r) = r.
        Runtime: if q == r, then q' == r (within float tolerance)."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=r)
        edge.harden(r, lam=lam)
        assert abs(edge.retrieval_util - r) < 1e-10, (
            f"Lean fixed_point violated: r={r}, lam={lam}, "
            f"q'={edge.retrieval_util}"
        )

    def test_formula_exact_match(self):
        """Verify runtime formula is exactly q' = (1-lam)*q + lam*r."""
        q, lam, r = 0.4, 0.3, 0.9
        expected = (1 - lam) * q + lam * r
        edge = EdgeBundle(source="a", target="b", retrieval_util=q)
        edge.harden(r, lam=lam)
        assert abs(edge.retrieval_util - expected) < 1e-15, (
            f"Formula mismatch: expected {expected}, got {edge.retrieval_util}"
        )

    def test_milliscale_correspondence(self):
        """Verify that the Lean milliscale model [0,1000] and the runtime
        float model [0,1] produce equivalent results when scaled."""
        q_f, lam_f, r_f = 0.5, 0.1, 0.8

        # Runtime (float)
        edge = EdgeBundle(source="a", target="b", retrieval_util=q_f)
        edge.harden(r_f, lam=lam_f)
        runtime_result = edge.retrieval_util

        # Lean milliscale model
        q_n = int(q_f * 1000)
        lam_n = int(lam_f * 1000)
        r_n = int(r_f * 1000)
        lean_result_scaled = ((1000 - lam_n) * q_n + lam_n * r_n) / 1000

        # Compare (allow for integer truncation in the Lean model)
        assert abs(runtime_result - lean_result_scaled / 1000) < 0.002, (
            f"Milliscale divergence: runtime={runtime_result}, "
            f"lean_scaled={lean_result_scaled / 1000}"
        )


# ---------------------------------------------------------------------------
# T-7 Correspondence: UnifiedGating.lean <-> risk_gate.py
#
# Lean model:
#   permitted g := g.verifier_pass && g.bridge_pass && g.risk_pass
#   conjunction_required: permitted => all three true
#   verifier_blocks: !verifier => !permitted
#   bridge_blocks: !bridge => !permitted
#   risk_blocks: !risk => !permitted
#   order_invariance: permitted = permitted_reordered
#   only_all_true_permits: permitted iff all three true
#
# Runtime:
#   RiskGate.multi_gate(V, rho, R):
#     V_pass = V > tau_verify
#     rho_pass = rho < theta_allow
#     R_pass = R < self.threshold
#     allowed = all([V_pass, rho_pass, R_pass])
# ---------------------------------------------------------------------------

class TestT7Correspondence:
    """Verify risk_gate.py multi_gate satisfies UnifiedGating.lean properties."""

    def test_conjunction_required(self):
        """Lean T-7a: permitted => all three gates true."""
        gate = RiskGate(threshold=0.8)
        # All passing
        allowed, details = gate.multi_gate(0.5, 0.3, 0.5)
        if allowed:
            assert details["V_pass"]
            assert details["rho_pass"]
            assert details["R_pass"]

    def test_verifier_blocks(self):
        """Lean T-7b: verifier_pass=false => not permitted."""
        gate = RiskGate(threshold=0.8)
        # V too low, others passing
        allowed, details = gate.multi_gate(0.1, 0.1, 0.1)
        assert not details["V_pass"]
        assert not allowed, "Lean verifier_blocks: low V must block"

    def test_bridge_blocks(self):
        """Lean T-7b: bridge_pass=false => not permitted."""
        gate = RiskGate(threshold=0.8)
        # rho too high, others passing
        allowed, details = gate.multi_gate(0.9, 0.9, 0.1)
        assert not details["rho_pass"]
        assert not allowed, "Lean bridge_blocks: high rho must block"

    def test_risk_blocks(self):
        """Lean T-7b: risk_pass=false => not permitted."""
        gate = RiskGate(threshold=0.8)
        # R too high, others passing
        allowed, details = gate.multi_gate(0.9, 0.1, 0.9)
        assert not details["R_pass"]
        assert not allowed, "Lean risk_blocks: high R must block"

    def test_default_denial(self):
        """Lean T-7d: default (all gates down) => denial."""
        gate = RiskGate(threshold=0.8)
        # All failing: V low, rho high, R high
        allowed, _ = gate.multi_gate(0.0, 1.0, 1.0)
        assert not allowed, "Lean default_denial: all-down must deny"

    @given(
        st.floats(min_value=-1.0, max_value=2.0),
        st.floats(min_value=-1.0, max_value=2.0),
        st.floats(min_value=-1.0, max_value=2.0),
    )
    @settings(max_examples=200)
    def test_only_all_true_permits(self, V, rho, R):
        """Lean T-7e: permitted iff all three gates pass.
        This is the strongest correspondence check — it exhaustively
        verifies the biconditional across the input space."""
        gate = RiskGate(threshold=0.8)
        tau_v, theta = 0.4, 0.5
        allowed, details = gate.multi_gate(V, rho, R,
                                           tau_verify=tau_v,
                                           theta_allow=theta)

        v_pass = V > tau_v
        rho_pass = rho < theta
        r_pass = R < gate.threshold
        expected = v_pass and rho_pass and r_pass

        assert allowed == expected, (
            f"Lean only_all_true_permits violated: "
            f"V={V}({v_pass}), rho={rho}({rho_pass}), R={R}({r_pass}), "
            f"expected={expected}, got={allowed}"
        )

    def test_order_invariance(self):
        """Lean T-7c: gate ordering does not affect result.
        Runtime uses all([V_pass, rho_pass, R_pass]) which is
        order-independent by definition. We verify by comparing
        against manually reordered evaluation."""
        gate = RiskGate(threshold=0.8)
        cases = [
            (0.5, 0.3, 0.5),   # all pass
            (0.1, 0.3, 0.5),   # V fails
            (0.5, 0.9, 0.5),   # rho fails
            (0.5, 0.3, 0.9),   # R fails
            (0.0, 1.0, 1.0),   # all fail
        ]
        for V, rho, R in cases:
            allowed, d = gate.multi_gate(V, rho, R)
            # Manually compute in different orders
            order1 = d["V_pass"] and d["rho_pass"] and d["R_pass"]
            order2 = d["R_pass"] and d["V_pass"] and d["rho_pass"]
            order3 = d["rho_pass"] and d["R_pass"] and d["V_pass"]
            assert allowed == order1 == order2 == order3, (
                f"Order invariance violated for V={V}, rho={rho}, R={R}"
            )


# ---------------------------------------------------------------------------
# Boundary / Fuzzing Tests
# ---------------------------------------------------------------------------

class TestBoundaryFuzzing:
    """Edge-case and boundary fuzzing for gate and hardening behavior."""

    @given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=100)
    def test_risk_gate_never_permits_at_boundary(self, threshold):
        """At exact boundary (score == threshold), gate always denies."""
        gate = RiskGate(threshold=threshold)
        score = gate.score("read a book")
        gate_exact = RiskGate(threshold=score)
        allowed, _ = gate_exact.gate("read a book")
        assert not allowed, (
            f"Boundary violation: score={score} == threshold but was permitted"
        )

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.001, max_value=1.0),
        st.integers(min_value=1, max_value=50),
    )
    @settings(max_examples=50)
    def test_hardening_convergence(self, r, lam, steps):
        """Repeated hardening with constant reward converges toward reward."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.5)
        for _ in range(steps):
            edge.harden(r, lam=lam)
        # After many steps with constant r, q should approach r
        # The convergence rate depends on lam and steps
        expected_distance = abs(0.5 - r) * ((1 - lam) ** steps)
        actual_distance = abs(edge.retrieval_util - r)
        assert actual_distance <= expected_distance + 1e-10, (
            f"Convergence slower than expected: r={r}, lam={lam}, "
            f"steps={steps}, dist={actual_distance}, expected<={expected_distance}"
        )

    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=50)
    def test_risk_gate_always_returns_valid(self, action):
        """Gate always returns a valid (bool, float) for any input string."""
        gate = RiskGate()
        allowed, score = gate.gate(action)
        assert isinstance(allowed, bool)
        assert isinstance(score, float)
        assert not math.isnan(score)
        assert not math.isinf(score)

    def test_phylactery_empty_string_content(self):
        """Chain handles edge case of empty-string commits."""
        p = Phylactery("")
        p.commit("")
        p.commit("")
        assert p.verify_chain()
        # Each commit still has a unique hash (different parent)
        hashes = [c.hash for c in p.chain]
        assert len(set(hashes)) == len(hashes), "Hash collision on empty strings"

    @given(st.lists(st.text(min_size=0, max_size=100), min_size=1, max_size=30))
    @settings(max_examples=30)
    def test_phylactery_verify_always_true_for_honest_chain(self, commits):
        """An honestly-built chain always verifies, regardless of content."""
        p = Phylactery("genesis")
        for c in commits:
            p.commit(c)
        assert p.verify_chain()
