"""
OmegA Fuzz Harness — ClaimBudget and DriftController

Fuzzes support/evidence combinations, grounding_ratio bounds,
DriftController.verify() with random strings, V score bounds,
and drift_penalty with random tuples.

Run: python3 -m pytest proofs/fuzz_drift.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from omega.drift import (
    ClaimBudget, SupportStatus, Claim, GoalContract, DriftController,
)


# ---------------------------------------------------------------------------
# Fuzz: Support/evidence combinations exhaustively
# ---------------------------------------------------------------------------

class TestFuzzClaimBudgetValidity:
    """Exhaustive fuzzing of support/evidence combinations."""

    SUPPORT_VALUES = [
        SupportStatus.SUPPORTED,
        SupportStatus.COMPUTED,
        SupportStatus.HYPOTHETICAL,
        SupportStatus.UNKNOWN,
    ]

    @pytest.mark.parametrize("support", SUPPORT_VALUES)
    def test_supported_without_evidence_invalid(self, support):
        """SUPPORTED without evidence must make is_valid() False.
        Other statuses without evidence are allowed."""
        budget = ClaimBudget()
        budget.add("test claim", support, evidence=None)
        if support == SupportStatus.SUPPORTED:
            assert not budget.is_valid(), (
                "SUPPORTED claim without evidence must be invalid"
            )
        else:
            assert budget.is_valid(), (
                f"{support.value} claim without evidence should be valid"
            )

    @pytest.mark.parametrize("support", SUPPORT_VALUES)
    def test_all_statuses_with_evidence_valid(self, support):
        """Any status with evidence provided is valid."""
        budget = ClaimBudget()
        budget.add("test claim", support, evidence="some evidence")
        assert budget.is_valid()

    @given(st.lists(
        st.tuples(
            st.sampled_from([
                SupportStatus.SUPPORTED,
                SupportStatus.COMPUTED,
                SupportStatus.HYPOTHETICAL,
                SupportStatus.UNKNOWN,
            ]),
            st.one_of(st.none(), st.text(min_size=1, max_size=50)),
        ),
        min_size=1, max_size=20,
    ))
    @settings(max_examples=100)
    def test_supported_without_evidence_always_invalid(self, claims):
        """Any budget containing a SUPPORTED claim without evidence is invalid."""
        budget = ClaimBudget()
        has_unsupported = False
        for support, evidence in claims:
            budget.add("claim", support, evidence=evidence)
            if support == SupportStatus.SUPPORTED and evidence is None:
                has_unsupported = True

        if has_unsupported:
            assert not budget.is_valid(), (
                "Budget with SUPPORTED+no-evidence claim must be invalid"
            )

    def test_empty_budget_is_valid(self):
        """Empty budget has no SUPPORTED claims, so is_valid() is True."""
        budget = ClaimBudget()
        assert budget.is_valid()

    def test_multiple_supported_all_need_evidence(self):
        """All SUPPORTED claims need evidence; one missing makes it invalid."""
        budget = ClaimBudget()
        budget.add("claim1", SupportStatus.SUPPORTED, evidence="proof1")
        budget.add("claim2", SupportStatus.SUPPORTED, evidence=None)
        budget.add("claim3", SupportStatus.COMPUTED, evidence=None)
        assert not budget.is_valid()


# ---------------------------------------------------------------------------
# Fuzz: grounding_ratio always in [0.0, 1.0]
# ---------------------------------------------------------------------------

class TestFuzzGroundingRatio:
    """grounding_ratio must always be in [0.0, 1.0]."""

    @given(st.lists(
        st.tuples(
            st.sampled_from([
                SupportStatus.SUPPORTED,
                SupportStatus.COMPUTED,
                SupportStatus.HYPOTHETICAL,
                SupportStatus.UNKNOWN,
            ]),
            st.one_of(st.none(), st.text(min_size=1, max_size=20)),
        ),
        min_size=0, max_size=30,
    ))
    @settings(max_examples=100)
    def test_grounding_ratio_bounded(self, claims):
        """grounding_ratio is always in [0.0, 1.0]."""
        budget = ClaimBudget()
        for support, evidence in claims:
            budget.add("claim", support, evidence=evidence)
        ratio = budget.grounding_ratio()
        assert 0.0 <= ratio <= 1.0, (
            f"grounding_ratio={ratio} out of [0,1]"
        )

    def test_grounding_ratio_empty(self):
        """Empty budget has grounding_ratio 0.0."""
        budget = ClaimBudget()
        assert budget.grounding_ratio() == 0.0

    def test_grounding_ratio_all_supported(self):
        """All SUPPORTED claims give grounding_ratio 1.0."""
        budget = ClaimBudget()
        for i in range(5):
            budget.add(f"claim_{i}", SupportStatus.SUPPORTED, evidence="proof")
        assert budget.grounding_ratio() == 1.0

    def test_grounding_ratio_all_hypothetical(self):
        """All HYPOTHETICAL claims give grounding_ratio 0.0."""
        budget = ClaimBudget()
        for i in range(5):
            budget.add(f"claim_{i}", SupportStatus.HYPOTHETICAL)
        assert budget.grounding_ratio() == 0.0

    def test_grounding_ratio_mixed(self):
        """Mixed claims: ratio equals grounded / total."""
        budget = ClaimBudget()
        budget.add("s1", SupportStatus.SUPPORTED, evidence="e")
        budget.add("c1", SupportStatus.COMPUTED, evidence="e")
        budget.add("h1", SupportStatus.HYPOTHETICAL)
        budget.add("u1", SupportStatus.UNKNOWN)
        assert budget.grounding_ratio() == 0.5  # 2/4


# ---------------------------------------------------------------------------
# Fuzz: DriftController.verify() with random strings
# ---------------------------------------------------------------------------

class TestFuzzDriftVerify:
    """verify() must always return a dict with V in [0.0, 1.0]."""

    @given(st.text(min_size=0, max_size=500))
    @settings(max_examples=100)
    def test_verify_random_strings(self, response):
        """V score is always in [0.0, 1.0] for any input string."""
        goal = GoalContract(task="test the system")
        dc = DriftController(goal)
        result = dc.verify(response)
        assert isinstance(result, dict)
        assert "V" in result
        assert 0.0 <= result["V"] <= 1.0, (
            f"V={result['V']} out of [0,1] for response={response!r}"
        )
        assert "passed" in result
        assert isinstance(result["passed"], bool)

    @given(
        st.text(min_size=1, max_size=100),
        st.text(min_size=0, max_size=300),
    )
    @settings(max_examples=100)
    def test_verify_random_goal_and_response(self, task, response):
        """V is bounded for any goal/response combination."""
        goal = GoalContract(task=task)
        dc = DriftController(goal)
        result = dc.verify(response)
        assert 0.0 <= result["V"] <= 1.0

    def test_verify_empty_response(self):
        """Empty response must not crash and V stays bounded."""
        goal = GoalContract(task="do something")
        dc = DriftController(goal)
        result = dc.verify("")
        assert 0.0 <= result["V"] <= 1.0

    def test_verify_all_certainty_words(self):
        """Response full of certainty words: V stays bounded."""
        goal = GoalContract(task="test")
        dc = DriftController(goal)
        response = " ".join(["definitely", "certainly", "absolutely"] * 20)
        result = dc.verify(response)
        assert 0.0 <= result["V"] <= 1.0

    def test_verify_all_hedge_words(self):
        """Response full of hedge words: V stays bounded."""
        goal = GoalContract(task="test")
        dc = DriftController(goal)
        response = " ".join(["perhaps", "maybe", "possibly"] * 20)
        result = dc.verify(response)
        assert 0.0 <= result["V"] <= 1.0


# ---------------------------------------------------------------------------
# Fuzz: V score always in [0.0, 1.0]
# ---------------------------------------------------------------------------

class TestFuzzVScoreBounded:
    """V score must always be clamped to [0.0, 1.0] regardless of alpha/beta."""

    @given(
        st.text(min_size=1, max_size=200),
        st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_v_bounded_with_extreme_alpha_beta(self, response, alpha, beta):
        """V stays in [0,1] even with extreme alpha and beta."""
        goal = GoalContract(task="important task")
        dc = DriftController(goal)
        result = dc.verify(response, alpha=alpha, beta=beta)
        assert 0.0 <= result["V"] <= 1.0, (
            f"V={result['V']} out of bounds with alpha={alpha}, beta={beta}"
        )


# ---------------------------------------------------------------------------
# Fuzz: drift_penalty with random tuples
# ---------------------------------------------------------------------------

class TestFuzzDriftPenalty:
    """drift_penalty must handle arbitrary (d_s, d_c, g_t) tuples."""

    @given(st.lists(
        st.tuples(
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),
        ),
        min_size=0, max_size=50,
    ))
    @settings(max_examples=100)
    def test_drift_penalty_no_crash(self, tokens):
        """drift_penalty must not crash on arbitrary tuples."""
        goal = GoalContract(task="test")
        dc = DriftController(goal)
        J = dc.drift_penalty(tokens)
        assert isinstance(J, (int, float))

    def test_drift_penalty_empty_tokens(self):
        """Empty token list gives penalty 0."""
        goal = GoalContract(task="test")
        dc = DriftController(goal)
        assert dc.drift_penalty([]) == 0.0

    @given(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_drift_penalty_single_token(self, ds, dc_val, gt):
        """Single token penalty equals w_s*ds + w_c*dc + w_g*gt."""
        goal = GoalContract(task="test")
        ctrl = DriftController(goal, w_s=0.3, w_c=0.4, w_g=0.3)
        J = ctrl.drift_penalty([(ds, dc_val, gt)])
        expected = 0.3 * ds + 0.4 * dc_val + 0.3 * gt
        assert abs(J - expected) < 1e-10, (
            f"drift_penalty mismatch: got {J}, expected {expected}"
        )

    @given(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_drift_penalty_nonneg_for_nonneg_inputs(self, ds, dc_val, gt):
        """Non-negative inputs with non-negative weights give non-negative J."""
        goal = GoalContract(task="test")
        ctrl = DriftController(goal)
        J = ctrl.drift_penalty([(ds, dc_val, gt)])
        assert J >= -1e-12, f"J={J} negative for non-negative inputs"

    def test_drift_penalty_weights_respected(self):
        """Verify that custom weights are applied correctly."""
        goal = GoalContract(task="test")
        dc1 = DriftController(goal, w_s=1.0, w_c=0.0, w_g=0.0)
        dc2 = DriftController(goal, w_s=0.0, w_c=1.0, w_g=0.0)
        dc3 = DriftController(goal, w_s=0.0, w_c=0.0, w_g=1.0)

        tokens = [(0.5, 0.3, 0.7)]
        assert abs(dc1.drift_penalty(tokens) - 0.5) < 1e-10
        assert abs(dc2.drift_penalty(tokens) - 0.3) < 1e-10
        assert abs(dc3.drift_penalty(tokens) - 0.7) < 1e-10
