"""
OmegA Fuzz Harness — Phylactery Corruption Detection

Fuzzes content tampering, parent_hash tampering, hash tampering,
commit reordering, and duplicate hash injection. Asserts that
verify_chain() returns False for ALL corrupted chains.

Run: python3 -m pytest proofs/fuzz_phylactery.py -v
"""

import sys
import os
import copy
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from omega.phylactery import Phylactery, PhylacteryCommit


def _build_chain(n: int = 5) -> Phylactery:
    """Build an honest chain with n commits after genesis."""
    p = Phylactery("genesis doctrine")
    for i in range(n):
        p.commit(f"commit_{i}")
    assert p.verify_chain(), "Honest chain must verify before corruption"
    return p


# ---------------------------------------------------------------------------
# Fuzz: Content tampering at random positions
# ---------------------------------------------------------------------------

class TestFuzzContentTampering:
    """Modifying content at any position must break verification."""

    @given(
        st.integers(min_value=0, max_value=9),
        st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=100)
    def test_content_tamper_at_random_position(self, pos, evil_content):
        """Tampering content at a random position breaks the chain."""
        p = _build_chain(10)
        idx = pos % len(p.chain)
        original = p.chain[idx].content
        assume(evil_content != original)
        p.chain[idx].content = evil_content
        assert not p.verify_chain(), (
            f"Content tamper at position {idx} not detected"
        )

    def test_content_tamper_every_position(self):
        """Exhaustively tamper each position."""
        for pos in range(6):
            p = _build_chain(5)
            p.chain[pos].content = "EVIL"
            assert not p.verify_chain(), (
                f"Content tamper at position {pos} not detected"
            )


# ---------------------------------------------------------------------------
# Fuzz: Parent hash tampering
# ---------------------------------------------------------------------------

class TestFuzzParentHashTampering:
    """Corrupting parent_hash in various ways must break verification."""

    @given(st.integers(min_value=1, max_value=9))
    @settings(max_examples=100)
    def test_parent_hash_swap(self, pos):
        """Swap parent_hash with a wrong commit's hash."""
        p = _build_chain(10)
        idx = pos % (len(p.chain) - 1) + 1  # skip genesis
        # Point parent to genesis instead of actual parent
        p.chain[idx].parent_hash = p.chain[0].hash
        assert not p.verify_chain(), (
            f"Parent hash swap at position {idx} not detected"
        )

    @given(st.text(min_size=1, max_size=64))
    @settings(max_examples=100)
    def test_parent_hash_corrupt(self, garbage):
        """Replace parent_hash with random garbage."""
        p = _build_chain(5)
        p.chain[2].parent_hash = garbage
        assert not p.verify_chain(), "Corrupted parent_hash not detected"

    def test_parent_hash_empty(self):
        """Set non-genesis parent_hash to empty string."""
        p = _build_chain(5)
        p.chain[3].parent_hash = ""
        assert not p.verify_chain(), "Empty parent_hash at pos 3 not detected"

    def test_genesis_parent_hash_nonempty(self):
        """Set genesis parent_hash to non-empty; must break chain."""
        p = _build_chain(3)
        p.chain[0].parent_hash = "not_empty"
        assert not p.verify_chain(), (
            "Non-empty genesis parent_hash not detected"
        )


# ---------------------------------------------------------------------------
# Fuzz: Hash tampering (modify stored hash)
# ---------------------------------------------------------------------------

class TestFuzzHashTampering:
    """Modifying the stored hash of any commit must break verification."""

    @given(
        st.integers(min_value=0, max_value=9),
        st.text(min_size=1, max_size=64),
    )
    @settings(max_examples=100)
    def test_hash_tamper_random(self, pos, fake_hash):
        """Replacing stored hash at any position breaks the chain."""
        p = _build_chain(10)
        idx = pos % len(p.chain)
        original = p.chain[idx].hash
        assume(fake_hash != original)
        p.chain[idx].hash = fake_hash
        assert not p.verify_chain(), (
            f"Hash tamper at position {idx} not detected"
        )

    def test_hash_tamper_single_char(self):
        """Flip a single character in a hash."""
        p = _build_chain(5)
        h = p.chain[2].hash
        flipped = h[:-1] + ("0" if h[-1] != "0" else "1")
        p.chain[2].hash = flipped
        assert not p.verify_chain(), "Single-char hash flip not detected"


# ---------------------------------------------------------------------------
# Fuzz: Commit reordering (swap two adjacent commits)
# ---------------------------------------------------------------------------

class TestFuzzCommitReordering:
    """Swapping two adjacent commits must break verification."""

    @given(st.integers(min_value=0, max_value=8))
    @settings(max_examples=100)
    def test_swap_adjacent_commits(self, pos):
        """Swapping two adjacent commits breaks the chain."""
        p = _build_chain(10)
        idx = pos % (len(p.chain) - 1)
        p.chain[idx], p.chain[idx + 1] = p.chain[idx + 1], p.chain[idx]
        assert not p.verify_chain(), (
            f"Swap at positions {idx},{idx + 1} not detected"
        )

    def test_swap_genesis_and_first(self):
        """Swapping genesis and first commit must break chain."""
        p = _build_chain(3)
        p.chain[0], p.chain[1] = p.chain[1], p.chain[0]
        assert not p.verify_chain()


# ---------------------------------------------------------------------------
# Fuzz: Duplicate hash injection
# ---------------------------------------------------------------------------

class TestFuzzDuplicateHash:
    """Injecting a commit with a duplicated hash must break verification."""

    def test_duplicate_hash_injection(self):
        """Duplicate an existing commit's hash in a new commit."""
        p = _build_chain(5)
        # Create a fake commit with same hash as commit[2]
        stolen_hash = p.chain[2].hash
        fake = PhylacteryCommit(
            content="injected",
            parent_hash=p.chain[-1].hash,
        )
        fake.hash = stolen_hash  # overwrite computed hash
        p.chain.append(fake)
        assert not p.verify_chain(), "Duplicate hash injection not detected"

    @given(st.integers(min_value=0, max_value=4))
    @settings(max_examples=100)
    def test_clone_commit_at_end(self, pos):
        """Appending a clone of an existing commit breaks the chain."""
        p = _build_chain(5)
        idx = pos % len(p.chain)
        clone = copy.deepcopy(p.chain[idx])
        p.chain.append(clone)
        assert not p.verify_chain(), (
            f"Cloned commit from position {idx} appended but not detected"
        )


# ---------------------------------------------------------------------------
# Fuzz: Honest chains always verify
# ---------------------------------------------------------------------------

class TestHonestChainAlwaysVerifies:
    """Sanity: honestly built chains must always verify."""

    @given(st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=20))
    @settings(max_examples=100)
    def test_honest_chain_verifies(self, commits):
        """Any honestly built chain verifies, regardless of content."""
        p = Phylactery("genesis")
        for c in commits:
            p.commit(c)
        assert p.verify_chain()
