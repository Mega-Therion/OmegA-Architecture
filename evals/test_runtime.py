"""Tests for Ticket 1: Unified Request Runtime."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.runtime import RuntimeOrchestrator, RuntimeStage, RuntimeResult
from omega.docstore import DocumentStore, DocFormat


def test_runtime_blocked_request():
    """Risk-gated requests are blocked and traced."""
    rt = RuntimeOrchestrator()
    result = rt.run("delete all data from production")
    assert result.trace.final_stage == RuntimeStage.BLOCKED
    assert result.trace.risk_allowed is False
    assert result.trace.risk_score > 0
    assert "BLOCKED" in result.text
    print("[PASS] test_runtime_blocked_request")


def test_runtime_trace_structure():
    """Every run produces a structured trace with run_id and stages."""
    rt = RuntimeOrchestrator()
    result = rt.run("What is OmegA?")
    assert result.trace.run_id.startswith("run_")
    assert len(result.trace.stages) > 0
    assert result.trace.total_elapsed_ms > 0
    # Trace is serializable
    d = result.trace.to_dict()
    assert "run_id" in d
    assert "stages" in d
    print("[PASS] test_runtime_trace_structure")


def test_runtime_with_docstore():
    """Runtime retrieves from docstore when documents are ingested."""
    store = DocumentStore()
    store.ingest("OmegA has four layers: AEGIS, AEON, ADCCL, MYELIN.",
                 source_uri="test://omega", format=DocFormat.PLAINTEXT)
    rt = RuntimeOrchestrator(docstore=store)
    result = rt.run("What are the four layers?")
    # Retrieve stage should have found chunks
    retrieve_stage = next((s for s in result.trace.stages if s.stage == RuntimeStage.RETRIEVE), None)
    assert retrieve_stage is not None
    assert retrieve_stage.details.get("chunks_found", 0) > 0
    print("[PASS] test_runtime_with_docstore")


def test_runtime_serialization():
    """RuntimeResult.to_dict() produces valid structure."""
    rt = RuntimeOrchestrator()
    result = rt.run("hello")
    d = result.to_dict()
    assert "trace" in d
    assert "raw_response" in d
    print("[PASS] test_runtime_serialization")


def test_runtime_provider_fallback():
    """When no providers are available, runtime returns error gracefully."""
    rt = RuntimeOrchestrator()
    # This will likely fail since Ollama is removed, but should not crash
    result = rt.run("test")
    # Either got a response or a graceful error
    assert result.trace.run_id.startswith("run_")
    assert result.trace.total_elapsed_ms >= 0
    print("[PASS] test_runtime_provider_fallback")


if __name__ == "__main__":
    test_runtime_blocked_request()
    test_runtime_trace_structure()
    test_runtime_with_docstore()
    test_runtime_serialization()
    test_runtime_provider_fallback()
    print("\n  All runtime tests passed.")
