#!/usr/bin/env python3
"""
OmegA Master Evaluation Harness
Iterates through all registered architectural specifications and validates them.
"""
import subprocess
import json
from pathlib import Path

# Mapping of SPEC_IDs to Validation Script/Harness Paths
VALIDATION_MAP = {
    "AEGIS_IDENTITY_ENFORCEMENT": "evals/test_aegis_identity.py",
    "OMEGA_CONFORMANCE_SUITE": "evals/test_conformance.py",
    "OMEGA_CROSS_SESSION_IDENTITY": "evals/test_cross_session_identity.py",
    "OMEGA_MEMORY_UTILITY_GROWTH": "evals/test_memory_utility_growth.py",
    # Live tests require Ollama — run separately:
    #   python3 evals/test_live_ollama.py --model llama3.2:3b
}

def run_suite():
    print("Running Master OmegA Evaluation Suite...")
    repo_root = Path(__file__).resolve().parents[1]
    results = {"OMEGA_SPEC_AUDITOR": "PASS"}
    
    # Get all specs
    subprocess.check_call(["python3", str(repo_root / "tools/spec_auditor.py")], cwd=repo_root)
    
    for spec_id in VALIDATION_MAP:
        harness = repo_root / VALIDATION_MAP[spec_id]
        if harness.exists():
            print(f"Validating [{spec_id}]...")
            try:
                subprocess.check_call(["python3", str(harness)], cwd=repo_root)
                results[spec_id] = "PASS"
            except subprocess.CalledProcessError:
                results[spec_id] = "FAIL"
        else:
            results[spec_id] = "NO_HARNESS_FOUND"
    
    # Generate Summary Report
    report_path = repo_root / "evals" / "final_evaluation_report.json"
    with report_path.open("w") as f:
        json.dump(results, f, indent=2)
    
    print("\n--- Master Evaluation Summary ---")
    for sid, status in results.items():
        print(f"{sid}: {status}")
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    Path("evals").mkdir(exist_ok=True)
    run_suite()
