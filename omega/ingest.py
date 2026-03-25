"""
MYELIN Ingestion Plane — Structured source ingestion with provenance and journaling.

Supports: files, raw text blobs, URLs.
Every ingest produces a structured IngestResult with provenance, hash, lineage.
Failed ingests are tracked and recoverable.

Architecture: MYELIN Phase 4
"""

import hashlib
import json
import time
import uuid
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from omega.docstore import DocumentStore, DocumentRecord, DocFormat


class IngestSource(str, Enum):
    FILE = "file"
    TEXT = "text"
    URL = "url"


class IngestStatus(str, Enum):
    SUCCESS = "success"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    UPDATED = "updated"


@dataclass
class IngestJob:
    """A structured ingest request."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_type: IngestSource = IngestSource.TEXT
    source_uri: str = ""
    content: str | None = None
    title: str = ""
    format: DocFormat = DocFormat.PLAINTEXT
    metadata: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "source_type": self.source_type.value,
            "source_uri": self.source_uri,
            "title": self.title,
            "format": self.format.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "has_content": self.content is not None,
        }


@dataclass
class IngestResult:
    """Result of an ingest operation."""
    job_id: str
    status: IngestStatus
    doc_id: str | None = None
    source_id: str = ""
    content_hash: str = ""
    version: int = 1
    parent_doc_id: str | None = None
    error: str = ""
    elapsed_ms: float = 0.0
    provenance: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "doc_id": self.doc_id,
            "source_id": self.source_id,
            "content_hash": self.content_hash,
            "version": self.version,
            "parent_doc_id": self.parent_doc_id,
            "error": self.error,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "provenance": self.provenance,
        }

    @property
    def ok(self) -> bool:
        return self.status in (IngestStatus.SUCCESS, IngestStatus.DUPLICATE, IngestStatus.UPDATED)


class IngestPlane:
    """
    Structured ingestion engine over the canonical DocumentStore.
    Journals all operations. Failed ingests are tracked for recovery.
    """

    def __init__(self, store: DocumentStore, journal_path: str | None = None):
        self.store = store
        self._journal_path = Path(journal_path) if journal_path else None
        self._failed: list[IngestResult] = []

    def ingest(self, job: IngestJob) -> IngestResult:
        """Execute an ingest job. Dispatches by source_type."""
        start = time.time()
        try:
            if job.source_type == IngestSource.FILE:
                return self._ingest_file(job, start)
            elif job.source_type == IngestSource.URL:
                return self._ingest_url(job, start)
            elif job.source_type == IngestSource.TEXT:
                return self._ingest_text(job, start)
            else:
                return self._fail(job, f"Unknown source type: {job.source_type}", start)
        except Exception as e:
            return self._fail(job, str(e), start)

    def ingest_file(self, path: str, title: str = "", metadata: dict | None = None) -> IngestResult:
        """Convenience: ingest a local file."""
        p = Path(path)
        job = IngestJob(
            source_type=IngestSource.FILE,
            source_uri=str(p.resolve()),
            title=title or p.name,
            metadata=metadata or {},
        )
        return self.ingest(job)

    def ingest_text(self, content: str, source_uri: str = "", title: str = "",
                    fmt: DocFormat = DocFormat.PLAINTEXT, metadata: dict | None = None) -> IngestResult:
        """Convenience: ingest raw text."""
        job = IngestJob(
            source_type=IngestSource.TEXT,
            source_uri=source_uri or f"text://{uuid.uuid4().hex[:8]}",
            content=content,
            title=title,
            format=fmt,
            metadata=metadata or {},
        )
        return self.ingest(job)

    def ingest_url(self, url: str, title: str = "", metadata: dict | None = None) -> IngestResult:
        """Convenience: ingest from URL."""
        job = IngestJob(
            source_type=IngestSource.URL,
            source_uri=url,
            title=title,
            metadata=metadata or {},
        )
        return self.ingest(job)

    def reingest(self, source_uri: str, content: str | None = None,
                 title: str = "", metadata: dict | None = None) -> IngestResult:
        """Re-ingest a source with updated content. Creates version lineage."""
        if content is None:
            # Try to re-fetch if URL
            if source_uri.startswith("http://") or source_uri.startswith("https://"):
                return self.ingest_url(source_uri, title=title, metadata=metadata)
            elif Path(source_uri).exists():
                return self.ingest_file(source_uri, title=title, metadata=metadata)
            else:
                return IngestResult(
                    job_id=str(uuid.uuid4()),
                    status=IngestStatus.FAILED,
                    error="Cannot re-ingest: no content provided and source not fetchable",
                )
        return self.ingest_text(content, source_uri=source_uri, title=title, metadata=metadata)

    def failed_jobs(self) -> list[IngestResult]:
        return list(self._failed)

    def retry_failed(self) -> list[IngestResult]:
        """Retry all failed jobs. Returns new results."""
        results = []
        remaining_failed = []
        for failed in self._failed:
            # Re-create a job from the failed result's provenance
            job = IngestJob(
                source_type=IngestSource(failed.provenance.get("source_type", "text")),
                source_uri=failed.source_id,
                title=failed.provenance.get("title", ""),
                metadata=failed.provenance.get("metadata", {}),
            )
            result = self.ingest(job)
            results.append(result)
            if not result.ok:
                remaining_failed.append(result)
        self._failed = remaining_failed
        return results

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _ingest_text(self, job: IngestJob, start: float) -> IngestResult:
        if not job.content:
            return self._fail(job, "No content provided for text ingest", start)

        content_hash = hashlib.sha256(job.content.encode()).hexdigest()
        existed = self.store.get_by_hash(content_hash) is not None
        doc = self.store.ingest(
            content=job.content,
            source_uri=job.source_uri,
            format=job.format,
            title=job.title,
            metadata=job.metadata,
        )
        return self._success(job, doc, start, existed_before=existed)

    def _ingest_file(self, job: IngestJob, start: float) -> IngestResult:
        p = Path(job.source_uri)
        if not p.exists():
            return self._fail(job, f"File not found: {p}", start)
        if not p.is_file():
            return self._fail(job, f"Not a file: {p}", start)

        content = p.read_text(encoding="utf-8", errors="replace")
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        existed = self.store.get_by_hash(content_hash) is not None
        doc = self.store.ingest_file(p, metadata=job.metadata)
        return self._success(job, doc, start, existed_before=existed)

    def _ingest_url(self, job: IngestJob, start: float) -> IngestResult:
        try:
            req = urllib.request.Request(job.source_uri, headers={"User-Agent": "OmegA-Ingest/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return self._fail(job, f"URL fetch failed: {e}", start)

        fmt = DocFormat.PLAINTEXT
        if job.source_uri.endswith(".md"):
            fmt = DocFormat.MARKDOWN
        elif job.source_uri.endswith(".json"):
            fmt = DocFormat.JSON

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        existed = self.store.get_by_hash(content_hash) is not None
        doc = self.store.ingest(
            content=content,
            source_uri=job.source_uri,
            format=job.format or fmt,
            title=job.title or job.source_uri,
            metadata=job.metadata,
        )
        return self._success(job, doc, start, existed_before=existed)

    def _success(self, job: IngestJob, doc: DocumentRecord, start: float,
                  existed_before: bool = False) -> IngestResult:
        content_hash = doc.doc_hash
        if existed_before:
            status = IngestStatus.DUPLICATE
        elif doc.version > 1:
            status = IngestStatus.UPDATED
        else:
            status = IngestStatus.SUCCESS

        result = IngestResult(
            job_id=job.job_id,
            status=status,
            doc_id=doc.doc_id,
            source_id=job.source_uri,
            content_hash=content_hash,
            version=doc.version,
            parent_doc_id=doc.parent_doc_id,
            elapsed_ms=(time.time() - start) * 1000,
            provenance=doc.to_provenance(),
        )
        self._journal(result, job)
        return result

    def _fail(self, job: IngestJob, error: str, start: float) -> IngestResult:
        result = IngestResult(
            job_id=job.job_id,
            status=IngestStatus.FAILED,
            source_id=job.source_uri,
            error=error,
            elapsed_ms=(time.time() - start) * 1000,
            provenance={
                "source_type": job.source_type.value,
                "title": job.title,
                "metadata": job.metadata,
            },
        )
        self._failed.append(result)
        self._journal(result, job)
        return result

    def _journal(self, result: IngestResult, job: IngestJob) -> None:
        if not self._journal_path:
            return
        self._journal_path.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": time.time(),
            "job": job.to_dict(),
            "result": result.to_dict(),
        }
        journal_file = self._journal_path / "ingest_journal.jsonl"
        with journal_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
