"""
MYELIN Document Store — Canonical source truth layer.

Stores full source documents with provenance, SHA-256 hashing, versioning,
and structured chunk/section extraction. No document is ever deleted —
superseded versions are archived with a lineage pointer.

Architecture: MYELIN Phase 3
"""

import hashlib
import json
import re
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator


class DocFormat(str, Enum):
    MARKDOWN = "markdown"
    PLAINTEXT = "plaintext"
    JSON = "json"
    CODE = "code"


@dataclass
class DocumentChunk:
    """A single chunk extracted from a document."""
    chunk_id: str
    doc_id: str
    content: str
    section: str = ""
    chunk_index: int = 0
    char_start: int = 0
    char_end: int = 0
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "char_start": self.char_start,
            "char_end": self.char_end,
        }


@dataclass
class DocumentRecord:
    """A canonical source document with full provenance."""
    doc_id: str
    content: str
    source_uri: str
    doc_hash: str                          # SHA-256 of content
    format: DocFormat = DocFormat.PLAINTEXT
    title: str = ""
    version: int = 1
    parent_doc_id: str | None = None       # lineage pointer for superseded docs
    ingested_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    chunks: list[DocumentChunk] = field(default_factory=list)

    @classmethod
    def from_content(
        cls,
        content: str,
        source_uri: str,
        format: DocFormat = DocFormat.PLAINTEXT,
        title: str = "",
        metadata: dict | None = None,
    ) -> "DocumentRecord":
        doc_id = str(uuid.uuid4())
        doc_hash = hashlib.sha256(content.encode()).hexdigest()
        doc = cls(
            doc_id=doc_id,
            content=content,
            source_uri=source_uri,
            doc_hash=doc_hash,
            format=format,
            title=title or source_uri,
            metadata=metadata or {},
        )
        doc.chunks = list(_extract_chunks(doc))
        return doc

    def to_provenance(self) -> dict:
        """Return a minimal provenance record (no full content)."""
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "source_uri": self.source_uri,
            "doc_hash": self.doc_hash,
            "format": self.format.value,
            "version": self.version,
            "parent_doc_id": self.parent_doc_id,
            "ingested_at": self.ingested_at,
            "chunk_count": len(self.chunks),
            "metadata": self.metadata,
        }


def _extract_chunks(
    doc: DocumentRecord,
    chunk_size: int = 512,
    overlap: int = 64,
) -> Iterator[DocumentChunk]:
    """Extract overlapping chunks with section labels."""
    content = doc.content
    sections = _split_sections(content, doc.format)

    chunk_index = 0
    for section_title, section_text in sections:
        pos = 0
        while pos < len(section_text):
            end = min(pos + chunk_size, len(section_text))
            chunk_text = section_text[pos:end].strip()
            if chunk_text:
                chunk_id = f"{doc.doc_id[:8]}_{chunk_index:04d}"
                yield DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc.doc_id,
                    content=chunk_text,
                    section=section_title,
                    chunk_index=chunk_index,
                    char_start=pos,
                    char_end=end,
                )
                chunk_index += 1
            pos += chunk_size - overlap


def _split_sections(content: str, fmt: DocFormat) -> list[tuple[str, str]]:
    """Split content into (section_title, section_text) pairs."""
    if fmt == DocFormat.MARKDOWN:
        return _split_markdown_sections(content)
    # Plaintext: treat as single section
    return [("", content)]


def _split_markdown_sections(content: str) -> list[tuple[str, str]]:
    """Split markdown by headings (## level)."""
    pattern = re.compile(r'^(#{1,3}\s+.+)$', re.MULTILINE)
    sections: list[tuple[str, str]] = []
    matches = list(pattern.finditer(content))

    if not matches:
        return [("", content)]

    # Content before first heading
    preamble = content[:matches[0].start()].strip()
    if preamble:
        sections.append(("", preamble))

    for i, match in enumerate(matches):
        title = match.group(0).lstrip('#').strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text = content[start:end].strip()
        if text:
            sections.append((title, text))

    return sections or [("", content)]


class DocumentStore:
    """
    In-memory canonical document store with hash-dedup and versioning.

    Production deployments should swap the in-memory dict for SQLite or
    Postgres-backed storage using the same interface.
    """

    def __init__(self, persist_path: str | None = None):
        self._docs: dict[str, DocumentRecord] = {}          # doc_id → record
        self._hash_index: dict[str, str] = {}               # doc_hash → doc_id
        self._uri_index: dict[str, list[str]] = {}          # source_uri → [doc_ids]
        self._chunks: dict[str, DocumentChunk] = {}         # chunk_id → chunk
        self._persist_path = Path(persist_path) if persist_path else None

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest(
        self,
        content: str,
        source_uri: str,
        format: DocFormat = DocFormat.PLAINTEXT,
        title: str = "",
        metadata: dict | None = None,
    ) -> DocumentRecord:
        """
        Ingest a document. If an identical hash already exists, returns the
        existing record (idempotent). If the URI has a prior version, links
        the new record to the old one.
        """
        doc_hash = hashlib.sha256(content.encode()).hexdigest()

        # Dedup by hash
        if doc_hash in self._hash_index:
            return self._docs[self._hash_index[doc_hash]]

        doc = DocumentRecord.from_content(
            content=content,
            source_uri=source_uri,
            format=format,
            title=title,
            metadata=metadata,
        )

        # Version lineage
        if source_uri in self._uri_index and self._uri_index[source_uri]:
            prev_id = self._uri_index[source_uri][-1]
            prev = self._docs[prev_id]
            doc.version = prev.version + 1
            doc.parent_doc_id = prev_id

        # Commit
        self._docs[doc.doc_id] = doc
        self._hash_index[doc_hash] = doc.doc_id
        self._uri_index.setdefault(source_uri, []).append(doc.doc_id)
        for chunk in doc.chunks:
            self._chunks[chunk.chunk_id] = chunk

        if self._persist_path:
            self._append_to_journal(doc)

        return doc

    def ingest_file(self, path: str | Path, metadata: dict | None = None) -> DocumentRecord:
        """Ingest a local file."""
        p = Path(path)
        fmt = _infer_format(p)
        content = p.read_text(encoding="utf-8", errors="replace")
        return self.ingest(
            content=content,
            source_uri=str(p.resolve()),
            format=fmt,
            title=p.name,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_doc(self, doc_id: str) -> DocumentRecord | None:
        return self._docs.get(doc_id)

    def get_chunk(self, chunk_id: str) -> DocumentChunk | None:
        return self._chunks.get(chunk_id)

    def get_by_hash(self, doc_hash: str) -> DocumentRecord | None:
        doc_id = self._hash_index.get(doc_hash)
        return self._docs.get(doc_id) if doc_id else None

    def get_by_uri(self, source_uri: str, version: int = -1) -> DocumentRecord | None:
        """Get a document by URI. version=-1 returns the latest."""
        ids = self._uri_index.get(source_uri, [])
        if not ids:
            return None
        target_id = ids[version]
        return self._docs.get(target_id)

    def neighboring_chunks(self, chunk_id: str, window: int = 1) -> list[DocumentChunk]:
        """Return the chunk plus up to `window` neighbors on each side."""
        chunk = self._chunks.get(chunk_id)
        if not chunk:
            return []
        doc = self._docs.get(chunk.doc_id)
        if not doc:
            return [chunk]

        idx = chunk.chunk_index
        lo = max(0, idx - window)
        hi = min(len(doc.chunks) - 1, idx + window)
        return doc.chunks[lo:hi + 1]

    def expand_context(self, chunk_id: str, window: int = 1) -> str:
        """Reconstruct a context string from a chunk and its neighbors."""
        neighbors = self.neighboring_chunks(chunk_id, window)
        return "\n\n".join(c.content for c in neighbors)

    def all_chunks(self) -> list[DocumentChunk]:
        return list(self._chunks.values())

    def all_docs(self) -> list[DocumentRecord]:
        return list(self._docs.values())

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def doc_count(self) -> int:
        return len(self._docs)

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    # ------------------------------------------------------------------
    # Persistence (append-only journal)
    # ------------------------------------------------------------------

    def _append_to_journal(self, doc: DocumentRecord):
        """Append a provenance record to the journal file."""
        if not self._persist_path:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with self._persist_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(doc.to_provenance()) + "\n")


def _infer_format(path: Path) -> DocFormat:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return DocFormat.MARKDOWN
    if suffix in {".json", ".jsonl"}:
        return DocFormat.JSON
    if suffix in {".py", ".rs", ".ts", ".js", ".go", ".c", ".cpp", ".h"}:
        return DocFormat.CODE
    return DocFormat.PLAINTEXT
