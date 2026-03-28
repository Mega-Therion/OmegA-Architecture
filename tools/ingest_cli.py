#!/usr/bin/env python3
"""
OmegA Ingest CLI — canonical ingestion entry point.

Usage:
    python tools/ingest_cli.py file <path> [--title TITLE]
    python tools/ingest_cli.py text "<content>" [--uri URI] [--title TITLE]
    python tools/ingest_cli.py url <url> [--title TITLE]
    python tools/ingest_cli.py status
    python tools/ingest_cli.py retry
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.ingest import IngestPlane, IngestJob, IngestSource, build_checkpoint


def _parse_metadata(metadata_raw: str | None) -> dict:
    if not metadata_raw:
        return {}
    try:
        return json.loads(metadata_raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid --metadata JSON: {exc}") from exc


def _parse_format(fmt_raw: str | None) -> DocFormat:
    if not fmt_raw:
        return DocFormat.PLAINTEXT
    try:
        return DocFormat(fmt_raw)
    except ValueError as exc:
        raise SystemExit(f"Invalid --format (use: plaintext, markdown, json, code)") from exc


def _write_checkpoint(path: str | None, job: IngestJob, result) -> None:
    if not path:
        return
    entry = build_checkpoint(job, result).to_dict()
    Path(path).write_text(json.dumps(entry, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="OmegA canonical ingest CLI")
    parser.add_argument(
        "--journal",
        default="data/ingest_journal",
        help="Directory for ingest_journal.jsonl",
    )
    parser.add_argument(
        "--checkpoint",
        help="Optional path to write the last checkpoint JSON",
    )
    parser.add_argument(
        "--metadata",
        help="Optional JSON metadata string",
    )

    subparsers = parser.add_subparsers(dest="command")

    file_parser = subparsers.add_parser("file", help="Ingest a local file")
    file_parser.add_argument("path")
    file_parser.add_argument("--title", default="")

    text_parser = subparsers.add_parser("text", help="Ingest raw text")
    text_parser.add_argument("content")
    text_parser.add_argument("--uri", default="")
    text_parser.add_argument("--title", default="")
    text_parser.add_argument("--format", default="plaintext")

    url_parser = subparsers.add_parser("url", help="Ingest from URL")
    url_parser.add_argument("url")
    url_parser.add_argument("--title", default="")

    subparsers.add_parser("status", help="Show ingest status")
    subparsers.add_parser("retry", help="Retry failed ingests")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    store = DocumentStore()
    plane = IngestPlane(store, journal_path=args.journal)
    metadata = _parse_metadata(args.metadata)

    if args.command == "status":
        failed = plane.failed_jobs()
        print(f"Store: {store.doc_count} docs, {store.chunk_count} chunks")
        print(f"Failed jobs: {len(failed)}")
        for f in failed:
            print(f"  [{f.job_id[:8]}] {f.source_id} — {f.error}")
        return 0

    if args.command == "retry":
        results = plane.retry_failed()
        print(json.dumps([r.to_dict() for r in results], indent=2))
        return 0 if all(r.ok for r in results) else 1

    if args.command == "file":
        p = Path(args.path)
        job = IngestJob(
            source_type=IngestSource.FILE,
            source_uri=str(p.resolve()),
            title=args.title or p.name,
            metadata=metadata,
        )
        result = plane.ingest(job)
        _write_checkpoint(args.checkpoint, job, result)
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.ok else 1

    if args.command == "text":
        job = IngestJob(
            source_type=IngestSource.TEXT,
            source_uri=args.uri or f"text://{uuid.uuid4().hex[:8]}",
            content=args.content,
            title=args.title,
            format=_parse_format(args.format),
            metadata=metadata,
        )
        result = plane.ingest(job)
        _write_checkpoint(args.checkpoint, job, result)
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.ok else 1

    if args.command == "url":
        job = IngestJob(
            source_type=IngestSource.URL,
            source_uri=args.url,
            title=args.title,
            metadata=metadata,
        )
        result = plane.ingest(job)
        _write_checkpoint(args.checkpoint, job, result)
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.ok else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
