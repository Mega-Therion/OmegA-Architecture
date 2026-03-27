"""Test Autonomous Repair Loop in OmegaAgent."""
from omega.agent import OmegaAgent
from tools.telemetry_harvester import TelemetryHarvester
import os

def test_autonomous_repair_on_block():
    # Clear logs first
    if os.path.exists(TelemetryHarvester.LOG_FILE):
        os.remove(TelemetryHarvester.LOG_FILE)
        
    agent = OmegaAgent()
    # Task that is hard-blocked by risk gate policy
    result = agent.run("rm -rf /", model="llama3.2:3b")
    
    trace = result.teleodynamic_trace
    print(f"Trace ID: {trace.trace_id}")
    print(f"Initial Failure Mode: {trace.actual_failure_mode}") # Should be 'RISK_GATED'
    
    # In my current agent.py, I call TelemetryHarvester.ingest(trace) BEFORE return.
    # But does the repair happen for blocked tasks?
    # Let's check agent.py logic.
    
    # Re-reading agent.py:
    # if not allowed:
    #     trace.phase_state = "BLOCKED"
    #     trace.actual_failure_mode = "RISK_GATED"
    #     TelemetryHarvester.ingest(trace)
    #     return RunResult(...)
    
    # Wait, in agent.py, I DON'T call TeleodynamicDiagnostics.analyze_signal if it's blocked.
    # I should fix that to ensure blocked tasks also trigger repair/audit if needed.
    # Actually, for a block, it's a known failure mode.
    
    # If repair was successful, the trace state should be REPAIR and metrics reset
    assert trace.phase_state == "REPAIR"
    assert trace.actual_failure_mode is None
    print("Success: Blocked task triggered autonomous REPAIR and audit.")

if __name__ == "__main__":
    test_autonomous_repair_on_block()
