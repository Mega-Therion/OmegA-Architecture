"""Diagnostic utility for Teleodynamic signals."""
from omega.teleodynamics import TeleodynamicSignal
from tools.repair_protocol import RepairProtocol
from tools.agent_mesh import AgentMesh

class TeleodynamicDiagnostics:
    @staticmethod
    def analyze_signal(trace: TeleodynamicSignal) -> bool:
        """Analyze trace for failure modes or high shear."""
        if trace.actual_failure_mode is not None:
            return True # Trigger repair
        if trace.shear_index > 0.5:
            return True # Trigger repair
        return False

    @staticmethod
    def run_repair(trace: TeleodynamicSignal, agent_context: list = None):
        """Repair logic for high-stress signals with Dynamic Context Purging and Mesh Propagation."""
        print(f"TeleodynamicDiagnostics: Repairing trace {trace.trace_id}...")
        
        # Phase 1: Dynamic Context Purging
        if agent_context is not None and trace.shear_index > 0.5:
            print(f"Purging high-shear context fragments (Shear Index: {trace.shear_index})")
            original_len = len(agent_context)
            if original_len > 1: # Keep at least the initial shell
                agent_context[:] = agent_context[:-1]
                print(f"Purged {original_len - len(agent_context)} fragments. Remaining: {len(agent_context)}")

        # Phase 2: Spec-to-Code Audit for Repair Strategy
        repair_strategy = RepairProtocol.propose_repair(trace)
        print(f"Repair Strategy: {repair_strategy['action']}")
        
        # Mesh Propagation
        AgentMesh.broadcast_repair(repair_strategy)
        
        # Transition to REPAIR state
        trace.phase_state = "REPAIR"
        trace.actual_failure_mode = None
        trace.shear_index = 0.1
        print("TeleodynamicDiagnostics: Repair phase complete.")
