"""Repair Protocol for OmegA Teleodynamic failures."""
from omega.teleodynamics import TeleodynamicSignal
from tools.spec_auditor import scan_files
from pathlib import Path

class RepairProtocol:
    # Map failure modes/high-shear triggers to architectural specs
    SPEC_MAPPING = {
        "RISK_GATED": "AEGIS_CORE",
        "RETRIEVAL": "MYELIN_FETCH",
        "DRIFT": "ADCCL_VERIFY",
        "PHASE_ERROR": "AEON_TSO"
    }

    @staticmethod
    def propose_repair(trace: TeleodynamicSignal, root_dir: str = "/home/mega/OmegA-Architecture") -> dict:
        """Analyze failure and find relevant spec locations to repair."""
        trigger = trace.actual_failure_mode or ("HIGH_SHEAR" if trace.shear_index > 0.5 else "UNKNOWN")
        spec_id = RepairProtocol.SPEC_MAPPING.get(trigger, "OMEGA_GENERAL")
        
        print(f"RepairProtocol: Trigger={trigger} -> Spec={spec_id}")
        
        # Scan for the spec in the codebase
        specs, _ = scan_files(root_dir)
        
        relevant_files = []
        if spec_id in specs:
            relevant_files = specs[spec_id]["locations"]
        
        repair_strategy = {
            "trace_id": trace.trace_id,
            "trigger": trigger,
            "spec_id": spec_id,
            "target_files": relevant_files,
            "action": f"Re-verify {spec_id} compliance in {len(relevant_files)} files."
        }
        
        return repair_strategy
