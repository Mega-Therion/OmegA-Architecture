"""Test integration of Teleodynamic telemetry in OmegaAgent."""
from omega.agent import OmegaAgent

def test_telemetry_presence():
    agent = OmegaAgent()
    # Using a simple task that won't trigger the risk gate
    result = agent.run("Hello", model="llama3.2:3b")
    
    trace = result.teleodynamic_trace
    print(f"Trace ID: {trace.trace_id}")
    print(f"Final Phase: {trace.phase_state}")
    
    assert trace.trace_id.startswith("req_")
    assert trace.phase_state == "REMEMBER"
    print("Success: Telemetry integrated and present.")

if __name__ == "__main__":
    test_telemetry_presence()
