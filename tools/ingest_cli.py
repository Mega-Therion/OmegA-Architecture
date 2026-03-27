#!/usr/bin/env python3
"""
OmegA Ingest CLI — Manual ingestion tool.

Usage:
    python tools/ingest_cli.py file <path> [--title TITLE]
    python tools/ingest_cli.py text "<content>" [--uri URI] [--title TITLE]
    python tools/ingest_cli.py url <url> [--title TITLE]
    python tools/ingest_cli.py status
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.docstore import DocumentStore
from omega.ingest import IngestPlane


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    store = DocumentStore()
    journal = Path("data/ingest_journal")
    plane = IngestPlane(store, journal_path=str(journal))

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    title = ""
    uri = ""
    i = 0
    positional = []
    while i < len(rest):
        if rest[i] == "--title" and i + 1 < len(rest):
            title = rest[i + 1]
            i += 2
        elif rest[i] == "--uri" and i + 1 < len(rest):
            uri = rest[i + 1]
            i += 2
        else:
            positional.append(rest[i])
            i += 1

    if cmd == "file":
        if not positional:
            print("Usage: ingest_cli.py file <path>")
            return
        result = plane.ingest_file(positional[0], title=title)

    elif cmd == "text":
        if not positional:
            print("Usage: ingest_cli.py text \"<content>\"")
            return
        result = plane.ingest_text(positional[0], source_uri=uri, title=title)

    elif cmd == "url":
        if not positional:
            print("Usage: ingest_cli.py url <url>")
            return
        result = plane.ingest_url(positional[0], title=title)

    elif cmd == "status":
        failed = plane.failed_jobs()
        print(f"Store: {store.doc_count} docs, {store.chunk_count} chunks")
        print(f"Failed jobs: {len(failed)}")
        for f in failed:
            print(f"  [{f.job_id[:8]}] {f.source_id} — {f.error}")
        return

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return

    print(json.dumps(result.to_dict(), indent=2))
    sys.exit(0 if result.ok else 1)


if __name__ == "__main__":
    main()
