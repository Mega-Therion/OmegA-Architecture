#!/usr/bin/env python3
"""Polyglot runtime validator for OmegA.

This script is the repository's cross-language validation spine:
Rust builds the runtime, TypeScript builds the MCP/web layers,
Python orchestrates the checks, and R computes the aggregate summary.
"""

from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parent.parent
R_SCRIPT = ROOT / "runtime" / "r" / "omega_sovereign_stats.R"


@dataclass
class StepResult:
    step: str
    status: str
    command: str
    cwd: str
    duration_ms: float
    returncode: int
    stdout_tail: str = ""
    stderr_tail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "step": self.step,
            "status": self.status,
            "command": self.command,
            "cwd": self.cwd,
            "duration_ms": round(self.duration_ms, 2),
            "returncode": self.returncode,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }


def tail(text: str, limit: int = 12) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    return "\n".join(lines[-limit:])


def run_command(step: str, command: Sequence[str], cwd: Path, env: dict[str, str] | None = None) -> StepResult:
    start = time.perf_counter()
    proc = subprocess.run(
        list(command),
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    status = "pass" if proc.returncode == 0 else "fail"
    return StepResult(
        step=step,
        status=status,
        command=" ".join(command),
        cwd=str(cwd),
        duration_ms=elapsed_ms,
        returncode=proc.returncode,
        stdout_tail=tail(proc.stdout),
        stderr_tail=tail(proc.stderr),
    )


def compile_python_sources() -> StepResult:
    start = time.perf_counter()
    candidates = [
        ROOT / "omega",
        ROOT / "tools",
        ROOT / "evals",
        ROOT / "voice" / "omega_voice.py",
        ROOT / "runtime" / "voice" / "voice_service.py",
    ]
    all_ok = True
    for path in candidates:
        if not path.exists():
            continue
        if path.is_dir():
            ok = compileall.compile_dir(
                str(path),
                quiet=1,
                force=True,
                maxlevels=10,
                rx=re.compile(r"/(?:__pycache__|node_modules|dist|build|\.venv|venv)/"),
            )
        else:
            ok = compileall.compile_file(str(path), quiet=1, force=True)
        all_ok = all_ok and ok
    elapsed_ms = (time.perf_counter() - start) * 1000
    return StepResult(
        step="python_compile",
        status="pass" if all_ok else "fail",
        command="python3 -m compileall omega tools evals voice/omega_voice.py runtime/voice/voice_service.py",
        cwd=str(ROOT),
        duration_ms=elapsed_ms,
        returncode=0 if all_ok else 1,
    )


def build_csv(steps: Iterable[StepResult]) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="omega-polyglot-"))
    csv_path = temp_dir / "step_results.csv"
    lines = ["step,status,latency_ms"]
    for step in steps:
        lines.append(f"{step.step},{step.status},{step.duration_ms:.2f}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path


def parse_r_summary(csv_path: Path) -> dict[str, object]:
    if not R_SCRIPT.exists():
        return {
            "available": False,
            "error": f"R script missing: {R_SCRIPT}",
        }

    if shutil.which("Rscript") is None:
        return {
            "available": False,
            "error": "Rscript is not installed or not on PATH",
        }

    proc = subprocess.run(
        ["Rscript", str(R_SCRIPT), str(csv_path)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            "available": True,
            "ok": False,
            "error": tail(proc.stderr or proc.stdout),
            "returncode": proc.returncode,
        }

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {
            "available": True,
            "ok": False,
            "error": f"Failed to parse R output as JSON: {exc}",
            "stdout_tail": tail(proc.stdout),
        }

    payload["available"] = True
    payload["ok"] = True
    return payload


def check_gateway(url: str | None) -> dict[str, object]:
    if not url:
        return {"available": False, "skipped": True, "reason": "No gateway URL supplied"}

    health_url = url.rstrip("/") + "/health"
    try:
        import urllib.request

        start = time.perf_counter()
        with urllib.request.urlopen(health_url, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
            elapsed_ms = (time.perf_counter() - start) * 1000
            return {
                "available": True,
                "ok": response.status == 200,
                "status_code": response.status,
                "duration_ms": round(elapsed_ms, 2),
                "body": body[:500],
            }
    except Exception as exc:  # pragma: no cover - network and env dependent
        return {
            "available": True,
            "ok": False,
            "error": str(exc),
        }


def validate_polyglot(
    repo_root: Path = ROOT,
    build: bool = True,
    test: bool = False,
    gateway_url: str | None = None,
) -> dict[str, object]:
    steps: list[StepResult] = []

    if build:
        steps.append(run_command("rust_build", ["cargo", "build", "--workspace"], repo_root / "runtime"))
        steps.append(run_command("mcp_build", ["npm", "run", "build"], repo_root / "mcp"))
        steps.append(run_command("web_build", ["npm", "run", "build"], repo_root / "web"))
    if test:
        steps.append(run_command("rust_test", ["cargo", "test", "--workspace"], repo_root / "runtime"))

    steps.append(compile_python_sources())

    csv_path = build_csv(steps)
    r_summary = parse_r_summary(csv_path)
    gateway = check_gateway(gateway_url or os.environ.get("OMEGA_GATEWAY_URL"))

    required_steps = {"python_compile"}
    if build:
        required_steps.update({"rust_build", "mcp_build", "web_build"})
    if test:
        required_steps.add("rust_test")

    step_lookup = {step.step: step for step in steps}
    build_ok = all(step_lookup.get(name, StepResult(name, "fail", "", "", 0, 1)).status == "pass" for name in required_steps)
    r_ok = bool(r_summary.get("ok"))
    gateway_ok = bool(gateway.get("ok")) if gateway.get("available") else True

    report = {
        "repo_root": str(repo_root),
        "build": build,
        "test": test,
        "steps": [step.to_dict() for step in steps],
        "r_summary": r_summary,
        "gateway": gateway,
        "overall_ok": build_ok and r_ok and gateway_ok,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the OmegA polyglot runtime.")
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    parser.add_argument("--build", action="store_true", default=False, help="Run build steps.")
    parser.add_argument("--test", action="store_true", default=False, help="Run Rust tests as part of validation.")
    parser.add_argument("--gateway-url", default=None, help="Optional gateway URL to probe after validation.")
    parser.add_argument("--write-report", default=None, help="Optional path to write the JSON report.")
    args = parser.parse_args()

    report = validate_polyglot(
        repo_root=Path(args.repo_root).resolve(),
        build=args.build,
        test=args.test,
        gateway_url=args.gateway_url,
    )

    output = json.dumps(report, indent=None if args.json else 2, sort_keys=True)
    print(output)

    if args.write_report:
        Path(args.write_report).write_text(output + "\n", encoding="utf-8")

    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
