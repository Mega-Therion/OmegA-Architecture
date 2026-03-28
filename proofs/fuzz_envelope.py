"""
OmegA Fuzz Harness — RunEnvelope and EnvelopeClock

Fuzzes missing fields, malformed identity kernels, invalid versions,
and identityless envelopes. Verifies is_complete() and has_identity()
correctly reject bad inputs and that EnvelopeClock.next() is strictly
monotonic.

Run: python3 -m pytest proofs/fuzz_envelope.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omega.envelope import RunEnvelope, EnvelopeClock


# ---------------------------------------------------------------------------
# Fuzz: Missing required fields
# ---------------------------------------------------------------------------

class TestFuzzMissingFields:
    """Setting each required field to None individually must make
    is_complete() return False."""

    REQUIRED_FIELDS = [
        "identity_kernel", "goal_contract", "version", "governance_policy",
        "memory_snapshot", "tool_manifest", "audit_config",
    ]

    @pytest.mark.parametrize("field_name", REQUIRED_FIELDS)
    def test_missing_field_rejects(self, field_name):
        """is_complete() must return False when any required field is None."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="test goal",
        )
        assert env.is_complete(), "Baseline envelope should be complete"
        setattr(env, field_name, None)
        assert not env.is_complete(), (
            f"is_complete() should reject envelope with {field_name}=None"
        )


# ---------------------------------------------------------------------------
# Fuzz: Malformed identity_kernel
# ---------------------------------------------------------------------------

class TestFuzzMalformedIdentityKernel:
    """Fuzz identity_kernel with empty dict, missing 'name', and non-dict."""

    def test_empty_dict_kernel(self):
        """Empty dict kernel: has_identity() must return False."""
        env = RunEnvelope(identity_kernel={}, goal_contract="test")
        assert not env.has_identity()

    def test_missing_name_kernel(self):
        """Dict without 'name' key: has_identity() must return False."""
        env = RunEnvelope(
            identity_kernel={"doctrine": "be good"},
            goal_contract="test",
        )
        assert not env.has_identity()

    @given(st.one_of(
        st.none(),
        st.integers(),
        st.text(),
        st.lists(st.integers()),
        st.booleans(),
    ))
    @settings(max_examples=100)
    def test_non_dict_kernel(self, kernel):
        """Non-dict identity_kernel: has_identity() must return False or
        is_complete() must still function without crash."""
        env = RunEnvelope(identity_kernel=kernel, goal_contract="test")
        # Must not crash
        result = env.has_identity()
        if not isinstance(kernel, dict) or not kernel:
            assert not result, (
                f"has_identity() should reject non-dict kernel: {kernel!r}"
            )

    def test_name_is_empty_string(self):
        """Kernel with name='' should be rejected by has_identity()."""
        env = RunEnvelope(
            identity_kernel={"name": ""},
            goal_contract="test",
        )
        assert not env.has_identity()

    def test_name_is_none(self):
        """Kernel with name=None should be rejected by has_identity()."""
        env = RunEnvelope(
            identity_kernel={"name": None},
            goal_contract="test",
        )
        assert not env.has_identity()


# ---------------------------------------------------------------------------
# Fuzz: Invalid version numbers
# ---------------------------------------------------------------------------

class TestFuzzInvalidVersion:
    """Fuzz version field with 0, -1, None, float, and string."""

    @given(st.one_of(
        st.just(0),
        st.just(-1),
        st.none(),
        st.floats(allow_nan=True, allow_infinity=True),
        st.text(),
    ))
    @settings(max_examples=100)
    def test_invalid_version_rejects(self, version):
        """is_complete() must return False for invalid version values."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="test",
            version=version,
        )
        # Valid only if version is a positive int
        if isinstance(version, int) and not isinstance(version, bool) and version > 0:
            assert env.is_complete()
        else:
            assert not env.is_complete(), (
                f"is_complete() should reject version={version!r}"
            )

    def test_version_zero(self):
        """Version 0 must be rejected."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="test",
            version=0,
        )
        assert not env.is_complete()

    def test_version_negative(self):
        """Negative version must be rejected."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="test",
            version=-1,
        )
        assert not env.is_complete()

    def test_version_float(self):
        """Float version must be rejected."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="test",
            version=1.5,
        )
        assert not env.is_complete()

    def test_version_string(self):
        """String version must be rejected."""
        env = RunEnvelope(
            identity_kernel={"name": "OmegA"},
            goal_contract="test",
            version="1",
        )
        assert not env.is_complete()


# ---------------------------------------------------------------------------
# Fuzz: Identityless envelopes
# ---------------------------------------------------------------------------

class TestFuzzIdentitylessEnvelope:
    """Envelopes with no identity should report correctly."""

    @given(st.one_of(
        st.just({}),
        st.just(None),
        st.just({"doctrine": "none"}),
        st.just({"name": ""}),
        st.just({"name": None}),
    ))
    @settings(max_examples=100)
    def test_identityless_envelopes(self, kernel):
        """has_identity() must return False for all identityless kernels."""
        env = RunEnvelope(
            identity_kernel=kernel,
            goal_contract="test",
        )
        assert not env.has_identity(), (
            f"has_identity() should be False for kernel={kernel!r}"
        )


# ---------------------------------------------------------------------------
# Fuzz: EnvelopeClock monotonicity
# ---------------------------------------------------------------------------

class TestFuzzEnvelopeClock:
    """EnvelopeClock.next() must always be strictly monotonic."""

    @given(st.integers(min_value=1, max_value=500))
    @settings(max_examples=100)
    def test_clock_strictly_monotonic(self, n):
        """n consecutive calls to next() must produce strictly increasing values."""
        clock = EnvelopeClock()
        prev = clock.next()
        for _ in range(n - 1):
            curr = clock.next()
            assert curr > prev, (
                f"Clock not strictly monotonic: {curr} <= {prev}"
            )
            prev = curr

    def test_clock_starts_at_one(self):
        """First call to next() must return 1."""
        clock = EnvelopeClock()
        assert clock.next() == 1

    def test_clock_no_gaps(self):
        """Sequential calls produce consecutive integers."""
        clock = EnvelopeClock()
        for expected in range(1, 101):
            assert clock.next() == expected

    def test_multiple_clocks_independent(self):
        """Two clocks advance independently."""
        c1 = EnvelopeClock()
        c2 = EnvelopeClock()
        c1.next()
        c1.next()
        assert c2.next() == 1, "Clocks must be independent"
