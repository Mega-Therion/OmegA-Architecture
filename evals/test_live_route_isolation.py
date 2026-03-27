#!/usr/bin/env python3
"""
OmegA Live Route Isolation Probe

This eval targets the deployed route layer directly to isolate which route
still collapses first under the latest production deployment.

It probes:
  - /api/chat
  - /api/research
  - /api/synthesize
  - /api/refine

Usage:
  python3 evals/test_live_route_isolation.py
  OMEGA_DEPLOYMENT_URL=https://... python3 evals/test_live_route_isolation.py
"""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = (
    os.environ.get("OMEGA_DEPLOYMENT_URL")
    or "https://omega-sovereign-jdgjin71d-megas-projects-1fcf4ba6.vercel.app"
)
RESULT_DIR = REPO_ROOT / "runtime" / "eval" / "results"
JSON_REPORT_PATH = REPO_ROOT / "evals" / "live_route_isolation_report.json"


@dataclass
class RouteResult:
    route: str
    path: str
    ok: bool
    usable: bool
    provider: str
    latency_ms: float
    status: int | None
    response: str
    response_excerpt: str
    details: dict[str, Any]
    error: str = ""


def _extract_response_text(raw: str) -> str:
    lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith("data:") or line.startswith("event:") or line.startswith("id:"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def _request(base_url: str, path: str, payload: dict[str, Any], expect_json: bool = False) -> tuple[int | None, dict[str, str], str, float, str]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json" if expect_json else "text/plain",
        },
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            elapsed_ms = (time.perf_counter() - started) * 1000
            headers = {k: v for k, v in resp.headers.items()}
            return resp.status, headers, raw, elapsed_ms, ""
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
        elapsed_ms = (time.perf_counter() - started) * 1000
        headers = {}
        raw = ""
        try:
            raw = e.read().decode("utf-8", errors="replace") if hasattr(e, "read") else ""
        except Exception:
            raw = ""
        return getattr(e, "code", None), headers, raw, elapsed_ms, str(e)


def _parse_json(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    if not raw:
        raise ValueError("empty response")
    return json.loads(raw)


def _probe_chat(base_url: str) -> RouteResult:
    status, headers, raw, latency_ms, error = _request(
        base_url,
        "/api/chat",
        {
            "user": "Reply with exactly one word: OK.",
            "history": [],
            "voiceMode": False,
            "sessionId": str(uuid.uuid4()),
        },
        expect_json=False,
    )
    text = _extract_response_text(raw)
    provider = headers.get("X-Provider", "unknown")
    usable = bool(status == 200 and text and "[OmegA diagnostic]" not in text)
    return RouteResult(
        route="chat",
        path="/api/chat",
        ok=status == 200 and not error,
        usable=usable,
        provider=provider,
        latency_ms=round(latency_ms, 1),
        status=status,
        response=text,
        response_excerpt=text[:240],
        details={
            "provider_header": provider,
            "has_diagnostic": "[OmegA diagnostic]" in text,
            "response_length": len(text),
        },
        error=error,
    )


def _probe_research(base_url: str) -> RouteResult:
    status, headers, raw, latency_ms, error = _request(
        base_url,
        "/api/research",
        {
            "query": "Reply with exactly one word: OK.",
            "documents": [],
            "sessionId": str(uuid.uuid4()),
        },
        expect_json=True,
    )
    provider = headers.get("X-Provider", "unknown")
    usable = False
    response_excerpt = raw[:240]
    details: dict[str, Any] = {"provider_header": provider}
    if status == 200 and raw.strip():
        try:
            parsed = _parse_json(raw)
            provider = str(parsed.get("provider", provider))
            details.update(
                {
                    "provider": provider,
                    "providerAttempts": parsed.get("providerAttempts", []),
                    "mode": parsed.get("mode"),
                    "verified": parsed.get("verified"),
                    "confidence": parsed.get("confidence"),
                }
            )
            answer = str(parsed.get("answer", "")).strip()
            usable = bool(answer and not answer.startswith("[PROVIDER ERROR]"))
            response_excerpt = answer[:240] or raw[:240]
        except Exception as e:
            details["parse_error"] = str(e)
    return RouteResult(
        route="research",
        path="/api/research",
        ok=status == 200 and not error,
        usable=usable,
        provider=provider,
        latency_ms=round(latency_ms, 1),
        status=status,
        response=raw.strip(),
        response_excerpt=response_excerpt,
        details=details,
        error=error,
    )


def _probe_synthesize(base_url: str) -> RouteResult:
    status, headers, raw, latency_ms, error = _request(
        base_url,
        "/api/synthesize",
        {
            "history": [
                {"role": "user", "text": "Summarize the conversation in one sentence."},
                {"role": "assistant", "text": "Focus on provider routing and fallback behavior."},
            ]
        },
        expect_json=True,
    )
    provider = headers.get("X-Provider", "unknown")
    usable = False
    response_excerpt = raw[:240]
    details: dict[str, Any] = {"provider_header": provider}
    if status == 200 and raw.strip():
        try:
            parsed = _parse_json(raw)
            provider = str(parsed.get("provider", provider))
            details.update(
                {
                    "provider": provider,
                    "providerAttempts": parsed.get("providerAttempts", []),
                }
            )
            directive = str(parsed.get("directive", "")).strip()
            expansion = str(parsed.get("expansion", "")).strip()
            usable = bool(directive and expansion)
            response_excerpt = directive[:120] or raw[:240]
        except Exception as e:
            details["parse_error"] = str(e)
    return RouteResult(
        route="synthesize",
        path="/api/synthesize",
        ok=status == 200 and not error,
        usable=usable,
        provider=provider,
        latency_ms=round(latency_ms, 1),
        status=status,
        response=raw.strip(),
        response_excerpt=response_excerpt,
        details=details,
        error=error,
    )


def _probe_refine(base_url: str) -> RouteResult:
    status, headers, raw, latency_ms, error = _request(
        base_url,
        "/api/refine",
        {"text": "make this more precise"},
        expect_json=True,
    )
    provider = headers.get("X-Provider", "unknown")
    usable = False
    response_excerpt = raw[:240]
    details: dict[str, Any] = {"provider_header": provider}
    if status == 200 and raw.strip():
        try:
            parsed = _parse_json(raw)
            provider = str(parsed.get("provider", provider))
            details.update(
                {
                    "provider": provider,
                    "providerAttempts": parsed.get("providerAttempts", []),
                }
            )
            refined = str(parsed.get("refined", "")).strip()
            usable = bool(refined)
            response_excerpt = refined[:240] or raw[:240]
        except Exception as e:
            details["parse_error"] = str(e)
    return RouteResult(
        route="refine",
        path="/api/refine",
        ok=status == 200 and not error,
        usable=usable,
        provider=provider,
        latency_ms=round(latency_ms, 1),
        status=status,
        response=raw.strip(),
        response_excerpt=response_excerpt,
        details=details,
        error=error,
    )


def run_suite(base_url: str) -> tuple[list[RouteResult], dict[str, Any]]:
    probes = [_probe_chat, _probe_research, _probe_synthesize, _probe_refine]
    results = [probe(base_url) for probe in probes]
    summary = {
        "base_url": base_url,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(results),
        "usable": sum(1 for r in results if r.usable),
        "collapsed": sum(1 for r in results if not r.usable),
        "routes": {},
        "first_collapse_route": next((r.route for r in results if not r.usable), None),
        "mean_latency_ms": round(sum(r.latency_ms for r in results) / max(len(results), 1), 1),
    }
    for r in results:
        summary["routes"][r.route] = {
            "usable": r.usable,
            "provider": r.provider,
            "status": r.status,
            "latency_ms": r.latency_ms,
        }
    return results, summary


def write_outputs(results: list[RouteResult], summary: dict[str, Any]) -> tuple[Path, Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = RESULT_DIR / f"rc1_e14_route_isolation_{datetime.now().date().isoformat()}.md"
    lines = [
        "# Eval E14 — Deployed Route Isolation",
        f"**Date:** {datetime.now().date().isoformat()}",
        f"**Run:** Live deployment route isolation — {summary['base_url']}",
        f"**Result:** {'✅ PASS' if summary['collapsed'] == 0 else '⚠️ PARTIAL'} ({summary['usable']}/{summary['total']} usable)",
        "",
        "This eval hits the deployed route contracts directly so we can see which endpoint collapses first under the current production build.",
        "",
        f"**First collapse:** {summary['first_collapse_route'] or 'none'}",
        "",
    ]
    for r in results:
        tag = "USABLE" if r.usable else "COLLAPSED"
        lines.extend(
            [
                f"## {r.route}",
                f"- Path: `{r.path}`",
                f"- Provider: `{r.provider}`",
                f"- Status: {r.status}",
                f"- Latency: {r.latency_ms:.1f} ms",
                f"- Result: {tag}",
                f"- Response excerpt: {r.response_excerpt or '(empty)'}",
                f"- Details: {json.dumps(r.details, ensure_ascii=False)}",
                f"- Error: {r.error or 'none'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "- A route counts as usable only if it returned a non-empty, parseable, route-shaped answer.",
            "- This eval distinguishes live route behavior from local provider accessibility.",
            "- The first collapsed route is the earliest route in sequence that failed the usable-output criterion.",
        ]
    )
    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    json_report = {
        "suite": "OmegA Deployed Route Isolation",
        "base_url": summary["base_url"],
        "timestamp_utc": summary["timestamp_utc"],
        "total": summary["total"],
        "usable": summary["usable"],
        "collapsed": summary["collapsed"],
        "mean_latency_ms": summary["mean_latency_ms"],
        "first_collapse_route": summary["first_collapse_route"],
        "routes": summary["routes"],
        "results": [
            {
                "route": r.route,
                "path": r.path,
                "ok": r.ok,
                "usable": r.usable,
                "provider": r.provider,
                "latency_ms": r.latency_ms,
                "status": r.status,
                "response": r.response,
                "response_excerpt": r.response_excerpt,
                "details": r.details,
                "error": r.error,
            }
            for r in results
        ],
        "notes": [
            "This probe targets the live route layer only.",
            "It intentionally keeps the prompts trivial so provider fallback and route shape are the only variables.",
        ],
    }
    json_path = REPO_ROOT / "evals" / "live_route_isolation_report.json"
    json_path.write_text(json.dumps(json_report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return md_path, json_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the OmegA deployed route isolation probe.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL for the deployed OmegA app")
    parser.add_argument("--json", action="store_true", help="Print the JSON summary to stdout")
    args = parser.parse_args()

    results, summary = run_suite(args.base_url)
    md_path, json_path = write_outputs(results, summary)

    print(f"OmegA route isolation complete: {summary['usable']}/{summary['total']} usable")
    print(f"Markdown report: {md_path}")
    print(f"JSON report: {json_path}")
    if args.json:
        print(json.dumps({"summary": summary, "results": [r.__dict__ for r in results]}, indent=2, ensure_ascii=False))
    return 0 if summary["collapsed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
