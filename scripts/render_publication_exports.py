#!/usr/bin/env python3
"""Render export-ready publication markdown files to PDF bundles.

This script converts the publication export front pages into PDF artifacts using
Google Chrome headless. The source markdown remains canonical; the rendered PDFs
are emitted into output/publication/.
"""

from __future__ import annotations

import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path

import markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "publication" / "exports"
OUTPUT_DIR = REPO_ROOT / "output" / "publication"
HTML_DIR = OUTPUT_DIR / "html"

TRACKS: dict[str, dict[str, str]] = {
    "public": {
        "source": "PUBLIC_RELEASE_EXPORT.md",
        "pdf": "public-release-bundle.pdf",
        "title": "OmegA Public Release Export",
    },
    "private-review": {
        "source": "PRIVATE_REVIEW_EXPORT.md",
        "pdf": "private-review-bundle.pdf",
        "title": "OmegA Private Review Export",
    },
    "master-synthesis": {
        "source": "OMEGA_MASTER_ONE_PAGER.md",
        "pdf": "omega-master-synthesis-one-pager.pdf",
        "title": "OmegA Master Synthesis One-Pager",
    },
}


CSS = """
:root {
  color-scheme: light;
}
html, body {
  margin: 0;
  padding: 0;
  font-family: Inter, Arial, Helvetica, sans-serif;
  color: #111827;
  background: #ffffff;
}
.page {
  max-width: 900px;
  margin: 0 auto;
  padding: 56px 64px 72px;
}
h1, h2, h3, h4 {
  line-height: 1.2;
  margin: 0 0 0.6em 0;
}
h1 {
  font-size: 30px;
  letter-spacing: -0.02em;
}
h2 {
  font-size: 22px;
  margin-top: 1.25em;
}
h3 {
  font-size: 18px;
  margin-top: 1.1em;
}
p, li {
  font-size: 12.5px;
  line-height: 1.65;
}
pre, code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
}
pre {
  padding: 12px 14px;
  background: #f3f4f6;
  border-radius: 10px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
blockquote {
  border-left: 3px solid #d1d5db;
  margin: 16px 0;
  padding: 0 0 0 16px;
  color: #374151;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}
th, td {
  border: 1px solid #d1d5db;
  padding: 8px 10px;
  vertical-align: top;
  font-size: 12px;
}
th {
  background: #f9fafb;
  text-align: left;
}
.front-matter {
  font-size: 11px;
  color: #6b7280;
  margin-bottom: 28px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e5e7eb;
}
.title-page {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 28px 28px 22px;
  margin-bottom: 28px;
  background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
}
.smallcaps {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 10px;
  color: #6b7280;
}
@media print {
  .page {
    padding: 36px 40px 48px;
  }
}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render OmegA export-ready publication markdown files to PDF."
    )
    parser.add_argument(
        "--track",
        choices=TRACKS.keys(),
        help="Render a single track. Use --all to render every track.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Render all publication export tracks.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Directory for generated PDFs (default: output/publication).",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="Keep the generated HTML files alongside the PDFs.",
    )
    return parser.parse_args()


def chrome_path() -> str:
    for candidate in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        found = shutil.which(candidate)
        if found:
            return found
    raise SystemExit("No Chromium/Chrome executable found on PATH.")


def render_markdown(md_text: str, title: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=["extra", "tables", "fenced_code", "sane_lists", "toc"],
        output_format="html5",
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="page">
    <div class="title-page">
      <div class="smallcaps">OmegA Sovereign Publication Export</div>
      <h1>{html.escape(title)}</h1>
      <div class="front-matter">Generated from canonical source markdown in the OmegA publication corpus.</div>
    </div>
    {body}
  </div>
</body>
</html>
"""


def run_chrome(html_file: Path, pdf_file: Path) -> None:
    chrome = chrome_path()
    cmd = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--hide-scrollbars",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={pdf_file}",
        html_file.as_uri(),
    ]
    subprocess.run(cmd, check=True)


def render_track(track: str, output_dir: Path, keep_html: bool) -> Path:
    info = TRACKS[track]
    source_path = EXPORT_DIR / info["source"]
    if not source_path.exists():
        raise SystemExit(f"Missing source export file: {source_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    HTML_DIR.mkdir(parents=True, exist_ok=True)

    markdown_text = source_path.read_text(encoding="utf-8")
    html_text = render_markdown(markdown_text, info["title"])

    html_path = HTML_DIR / f"{Path(info['pdf']).stem}.html"
    pdf_path = output_dir / info["pdf"]
    html_path.write_text(html_text, encoding="utf-8")
    run_chrome(html_path, pdf_path)

    if not keep_html:
        html_path.unlink(missing_ok=True)

    return pdf_path


def main() -> int:
    args = parse_args()
    requested_tracks: list[str]
    if args.all:
        requested_tracks = list(TRACKS.keys())
    elif args.track:
        requested_tracks = [args.track]
    else:
        requested_tracks = ["public"]

    output_dir = Path(args.output_dir)
    generated: list[Path] = []
    for track in requested_tracks:
        generated.append(render_track(track, output_dir, args.keep_html))

    for path in generated:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
