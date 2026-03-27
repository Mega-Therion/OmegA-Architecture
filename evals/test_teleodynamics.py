"""Tests for Teleodynamic Observability."""
from omega.teleodynamics import TeleodynamicSignal

def test_signal_serialization():
    signal = TeleodynamicSignal(
        trace_id="test_001",
        phase_state="ACT",
        phase_transition_id="pt_001",
        resonance_amplitude=0.5,
        shear_index=0.1,
        canon_anchor_weight=0.9,
        structural_integrity_score=0.95,
        intent_priority_score=0.8,
        authority_shrink_level=0.1,
        predicted_failure_modes=["RETRIEVAL"]
    )
    
    data = signal.to_json()
    assert data["trace_id"] == "test_001"
    assert "actual_failure_mode" not in data
    print("Success: Signal serialization verified.")

if __name__ == "__main__":
    test_signal_serialization()
