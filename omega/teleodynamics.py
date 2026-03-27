"""Teleodynamic Observability Layer."""
from dataclasses import dataclass, field
from typing import List, Optional
import time

@dataclass
class TeleodynamicSignal:
    trace_id: str
    phase_state: str
    phase_transition_id: str
    resonance_amplitude: float
    shear_index: float
    canon_anchor_weight: float
    structural_integrity_score: float
    intent_priority_score: float
    authority_shrink_level: float
    predicted_failure_modes: List[str]
    actual_failure_mode: Optional[str] = None
    promotion_decay_ratio: Optional[float] = None
    
    # Phase 3: Wormhole-DA Integration
    da_reachability: float = 1.0 # 0.0 to 1.0 (1.0 = full connectivity)
    da_consensus_delay: float = 0.0 # ms delay in data availability layer
    
    timestamp: float = field(default_factory=time.time)

    def to_json(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}
