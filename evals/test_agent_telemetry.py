"""Test integration of Teleodynamic telemetry in OmegaAgent."""
import time

from omega.agent import OmegaAgent
from omega.memory import MemoryGraph
from omega.telemetry import TelemetryCollector, TelemetryEventType


def test_telemetry_presence(monkeypatch):
    agent = OmegaAgent()
    monkeypatch.setattr(agent, "_generate", lambda *args, **kwargs: "A grounded response.")

    result = agent.run("Hello", model="llama3.2:3b")

    assert result.response == "A grounded response."
    assert result.self_tag.tso_hash
    assert result.self_tag.outcome in {"verified", "uncertain", "rejected"}
    assert result.elapsed_ms > 0
    assert agent.self_tags[-1].tso_hash == result.self_tag.tso_hash
    assert agent.state_vector["G_t_mem"]["nodes"] == 1

def test_memory_retrieval_telemetry():
    memory = MemoryGraph()
    node = memory.add_node("n1", "retrieval test")
    assert node.retrieval_count == 0
    assert node.last_retrieved_at is None

    first = memory.retrieve("n1")
    assert first is not None
    assert first.retrieval_count == 1
    first_retrieved_at = first.last_retrieved_at
    assert first_retrieved_at is not None
    time.sleep(0.01)

    second = memory.retrieve("n1")
    assert second is not None
    assert second.retrieval_count == 2
    assert second.last_retrieved_at is not None
    assert second.last_retrieved_at >= first_retrieved_at


def test_retrieval_hit_telemetry_event():
    collector = TelemetryCollector()
    event = collector.emit(
        TelemetryEventType.RETRIEVAL_HIT,
        run_id="run_1",
        data={"node_id": "n1", "retrieval_count": 1},
    )

    assert event.event_type == TelemetryEventType.RETRIEVAL_HIT
    summary = collector.summarize(run_id="run_1")
    assert summary["event_type_counts"]["retrieval_hit"] == 1

if __name__ == "__main__":
    test_telemetry_presence()
    test_memory_retrieval_telemetry()
