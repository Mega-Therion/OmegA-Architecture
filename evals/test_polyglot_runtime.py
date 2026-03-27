"""Polyglot runtime validation tests.

These tests cover the Python → R reporting bridge and the lightweight
validation report assembly used by the TypeScript MCP tool and verify script.
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import polyglot_runtime as pr  # noqa: E402


def test_r_summary_round_trip(tmp_path):
    if shutil.which("Rscript") is None:
        pytest.skip("Rscript not available")

    csv_path = tmp_path / "steps.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["step", "status", "latency_ms"])
        writer.writeheader()
        writer.writerow({"step": "rust_build", "status": "pass", "latency_ms": "12.5"})
        writer.writerow({"step": "mcp_build", "status": "fail", "latency_ms": "20.0"})
        writer.writerow({"step": "python_compile", "status": "skip", "latency_ms": "4.5"})

    summary = pr.parse_r_summary(csv_path)

    assert summary["available"] is True
    assert summary["ok"] is True
    assert summary["total_steps"] == 3
    assert summary["passed_steps"] == 1
    assert summary["failed_steps"] == 1
    assert summary["skipped_steps"] == 1
    assert summary["status_counts"]["pass"] == 1
    assert summary["status_counts"]["fail"] == 1
    assert summary["status_counts"]["skip"] == 1


def test_polyglot_validation_report_shape():
    report = pr.validate_polyglot(build=False, test=False)

    assert "steps" in report
    assert "r_summary" in report
    assert "gateway" in report
    assert isinstance(report["overall_ok"], bool)
    assert report["r_summary"]["available"] is True
    assert report["steps"]
