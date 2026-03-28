#!/usr/bin/env python3
"""Cross-session identity persistence regression test."""

from __future__ import annotations

import tempfile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.agent import OmegaAgent


def test_cross_session_identity_persistence():
    with tempfile.TemporaryDirectory() as td:
        phylactery_path = Path(td) / "phylactery.json"

        agent_one = OmegaAgent(phylactery_path=str(phylactery_path))
        original_head = agent_one.phylactery.head
        agent_one.phylactery.commit("The sovereign identity must persist across sessions.")
        agent_one.persist_identity()

        assert phylactery_path.exists()
        persisted_head = agent_one.phylactery.head
        assert persisted_head != original_head

        agent_two = OmegaAgent(phylactery_path=str(phylactery_path))
        assert agent_two.phylactery.head == persisted_head
        assert agent_two.phylactery.doctrine == agent_one.phylactery.doctrine
        assert agent_two.phylactery.verify_chain() is True
        assert agent_two.state_vector["Phi_t"] == persisted_head
        assert len(agent_two.phylactery) == len(agent_one.phylactery)

        print("[PASS] cross-session identity persistence")


if __name__ == "__main__":
    test_cross_session_identity_persistence()
