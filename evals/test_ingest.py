"""Tests for Ticket 4: Ingestion Plane."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.ingest import IngestPlane, IngestJob, IngestSource, IngestStatus


def test_ingest_text():
    """Text blob ingest produces structured result with provenance."""
    store = DocumentStore()
    plane = IngestPlane(store)
    result = plane.ingest_text(
        "OmegA is a four-layer AI architecture.",
        source_uri="test://omega",
        title="OmegA Summary",
    )
    assert result.ok
    assert result.status == IngestStatus.SUCCESS
    assert result.doc_id is not None
    assert result.content_hash != ""
    assert result.version == 1
    assert result.provenance.get("doc_id") == result.doc_id
    print("[PASS] test_ingest_text")


def test_ingest_file():
    """File ingest works for a real file."""
    store = DocumentStore()
    plane = IngestPlane(store)
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as f:
        f.write("# Test Document\n\nThis is test content.")
        f.flush()
        result = plane.ingest_file(f.name, title="Test Doc")
    assert result.ok
    assert result.content_hash != ""
    # Verify doc is in store
    doc = store.get_doc(result.doc_id)
    assert doc is not None
    assert "Test Document" in doc.content
    print("[PASS] test_ingest_file")


def test_ingest_duplicate():
    """Duplicate content returns existing doc (idempotent)."""
    store = DocumentStore()
    plane = IngestPlane(store)
    r1 = plane.ingest_text("Same content", source_uri="test://a")
    r2 = plane.ingest_text("Same content", source_uri="test://b")
    assert r1.doc_id == r2.doc_id
    assert store.doc_count == 1
    print("[PASS] test_ingest_duplicate")


def test_ingest_version_lineage():
    """Updated content for same URI creates version lineage."""
    store = DocumentStore()
    plane = IngestPlane(store)
    r1 = plane.ingest_text("Version 1", source_uri="test://doc")
    r2 = plane.ingest_text("Version 2", source_uri="test://doc")
    assert r2.version == 2
    assert r2.parent_doc_id == r1.doc_id
    print("[PASS] test_ingest_version_lineage")


def test_ingest_failed_tracking():
    """Failed ingests are tracked and recoverable."""
    store = DocumentStore()
    plane = IngestPlane(store)
    result = plane.ingest_file("/nonexistent/path.txt")
    assert result.status == IngestStatus.FAILED
    assert result.error != ""
    failed = plane.failed_jobs()
    assert len(failed) == 1
    assert failed[0].job_id == result.job_id
    print("[PASS] test_ingest_failed_tracking")


def test_ingest_empty_text_fails():
    """Empty text ingest fails gracefully."""
    store = DocumentStore()
    plane = IngestPlane(store)
    job = IngestJob(source_type=IngestSource.TEXT, source_uri="test://empty", content=None)
    result = plane.ingest(job)
    assert result.status == IngestStatus.FAILED
    print("[PASS] test_ingest_empty_text_fails")


def test_ingest_job_serialization():
    """IngestJob and IngestResult serialize to dict."""
    store = DocumentStore()
    plane = IngestPlane(store)
    result = plane.ingest_text("test", source_uri="test://ser")
    d = result.to_dict()
    assert "job_id" in d
    assert "status" in d
    assert "content_hash" in d
    print("[PASS] test_ingest_job_serialization")


def test_ingest_journaling():
    """Journal file is written when journal_path is set."""
    store = DocumentStore()
    with tempfile.TemporaryDirectory() as tmpdir:
        plane = IngestPlane(store, journal_path=tmpdir)
        plane.ingest_text("journal test", source_uri="test://journal")
        journal_file = Path(tmpdir) / "ingest_journal.jsonl"
        assert journal_file.exists()
        lines = journal_file.read_text().strip().split("\n")
        assert len(lines) == 1
    print("[PASS] test_ingest_journaling")


if __name__ == "__main__":
    test_ingest_text()
    test_ingest_file()
    test_ingest_duplicate()
    test_ingest_version_lineage()
    test_ingest_failed_tracking()
    test_ingest_empty_text_fails()
    test_ingest_job_serialization()
    test_ingest_journaling()
    print("\n  All ingestion tests passed.")
