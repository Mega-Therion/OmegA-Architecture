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
}

def run_suite():
    print("Running Master OmegA Evaluation Suite...")
    results = {}
    
    # Get all specs
    auditor_output = subprocess.check_output(["python3", "tools/spec_auditor.py"]).decode()
    
    for spec_id in VALIDATION_MAP:
        harness = Path(VALIDATION_MAP[spec_id])
        if harness.exists():
            print(f"Validating [{spec_id}]...")
            try:
                subprocess.check_call(["python3", str(harness)])
                results[spec_id] = "PASS"
            except subprocess.CalledProcessError:
                results[spec_id] = "FAIL"
        else:
            results[spec_id] = "NO_HARNESS_FOUND"
    
    # Generate Summary Report
    with open("evals/final_evaluation_report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\n--- Master Evaluation Summary ---")
    for sid, status in results.items():
        print(f"{sid}: {status}")
    print("\nReport saved to: evals/final_evaluation_report.json")

if __name__ == "__main__":
    Path("evals").mkdir(exist_ok=True)
    run_suite()
