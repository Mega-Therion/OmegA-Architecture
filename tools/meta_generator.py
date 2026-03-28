#!/usr/bin/env python3
"""
OmegA Meta-Generator — Skill Architect Foundational Tool

Generates OmegA-compliant skill scaffolding:
  - SKILL.md (contract + workflow)
  - Implementation stub (.py)
  - Eval test suite stub
  - TSO-aligned task state schema
  - TELEODYNAMICS_TRACE emission

Usage:
    python meta_generator.py --name pub_packager --description "Publication Packager" \
        --layer AEON --domain publication --priority high

Architectural mandates enforced:
  AEGIS  — trust boundary + policy gate
  AEON   — time-indexed execution + TSO
  ADCCL  — adaptive control loops + self-correction
  MYELIN — knowledge graph update + trace emission
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── OmegA Layer Definitions ─────────────────────────────────────────────────
LAYERS = {
    "AEGIS":  {"role": "Governance shell — trust boundary + policy enforcement",
               "cap": "cap.governance.enforce"},
    "AEON":   {"role": "Cognitive OS — orchestration + TSO lifecycle",
               "cap": "cap.orchestration.run"},
    "ADCCL":  {"role": "Anti-drift control loop — claim budgets + self-tagging",
               "cap": "cap.control.adapt"},
    "MYELIN": {"role": "Graph memory — path hardening + retrieval",
               "cap": "cap.memory.write"},
}

DOMAIN_CAPS = {
    "publication":   ["cap.fs.read", "cap.fs.write", "cap.network.github"],
    "security":      ["cap.fs.read", "cap.audit.scan"],
    "memory":        ["cap.memory.read", "cap.memory.write", "cap.db.neon"],
    "orchestration": ["cap.orchestration.run", "cap.mesh.broadcast"],
    "ingest":        ["cap.fs.read", "cap.db.neon.write"],
    "evaluation":    ["cap.fs.read", "cap.exec.python"],
    "default":       ["cap.fs.read"],
}

# ─── TSO Template ─────────────────────────────────────────────────────────────
def build_tso(name: str, objective: str, domain: str, priority: str) -> dict:
    urgency_map = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}
    return {
        "task_id": f"skill.{name}.{int(time.time())}",
        "objective": objective,
        "constraints": [
            "No secrets in logs or output",
            "All file paths must be absolute",
            "Emit TELEODYNAMICS_TRACE on completion",
            "Log to ~/NEXUS/ERGON.md on success",
        ],
        "success_criteria": [
            f"{name} executes without error",
            "Output artifact is present and non-empty",
            "TELEODYNAMICS_TRACE emitted with phase_state=VERIFY",
        ],
        "declared_unknowns": [],
        "urgency": priority if priority in urgency_map else "normal",
        "intent_priority_score": urgency_map.get(priority, 0.7),
        "goal_valence_vector": {
            "truth": 1.0, "speed": 0.5, "safety": 0.9,
            "continuity": 0.8, "operator_preference": 0.8
        },
        "authority_shrink_level": 0.1,
        "canon_anchor_weight": 0.85,
        "predicted_failure_modes": ["missing_dependency", "permission_denied", "output_empty"],
        "phase_state": "OBSERVE",
    }

# ─── SKILL.md Template ────────────────────────────────────────────────────────
SKILL_MD_TEMPLATE = """\
---
name: {name}
description: {description}
version: "1.0.0"
layer: {layer}
domain: {domain}
priority: {priority}
aegis_policy: strict
generated_by: meta_generator.py
generated_at: {timestamp}
---

# {title}

> **Layer:** {layer} ({layer_role})
> **AEGIS Policy:** `strict` — requires explicit permission for writes/network/exec

## Purpose

{description}

## Skill Contract

### Inputs
{inputs}

### Permissions Required
{permissions}

### Execution Steps (Observable)
1. **OBSERVE** — Load context, verify dependencies, emit trace
2. **THINK** — Validate inputs against constraints, build execution plan
3. **ACT** — Execute primary logic with error capture
4. **VERIFY** — Check output artifacts against success_criteria
5. **REMEMBER** — Emit TELEODYNAMICS_TRACE, log to ERGON.md

### Output Artifacts
{outputs}

### Rollback Behavior
- On failure: emit `TELEODYNAMICS_TRACE` with `actual_failure_mode` set
- Partial writes: clean up incomplete artifacts before exit
- Log failure reason to ERGON.md

## Teleodynamic Trace Schema

```python
TeleodynamicSignal(
    trace_id="skill.{name}.<timestamp>",
    phase_state="VERIFY",                    # or "REPAIR" on failure
    phase_transition_id="act->verify",
    resonance_amplitude=0.75,
    shear_index=0.1,                         # < 0.5 = healthy
    canon_anchor_weight=0.85,
    structural_integrity_score=0.90,
    intent_priority_score={priority_score},
    authority_shrink_level=0.1,
    predicted_failure_modes={predicted_failures},
    actual_failure_mode=None,               # set on failure
)
```

## Self-Correction Loop

```
for attempt in range(MAX_RETRIES):
    result = execute()
    if validate(result):
        emit_trace(phase="VERIFY")
        break
    else:
        emit_trace(phase="REPAIR")
        adjust_strategy(result.error)
```

## TSO

```json
{tso_json}
```

## Usage

```bash
# From OmegA-Architecture root:
python3 tools/{name}.py {usage_args}

# Or via omegactl:
python3 omegactl.py {name} {usage_args}
```
"""

# ─── Implementation Stub Template ────────────────────────────────────────────
IMPL_TEMPLATE = '''\
#!/usr/bin/env python3
"""
{title}
{description}

Generated by: meta_generator.py — OmegA Skill Architect
Layer: {layer} | Domain: {domain} | Policy: strict
AEGIS-compliant: Yes | ADCCL self-correction: Yes | MYELIN trace: Yes
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

# Ensure omega module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from omega.teleodynamics import TeleodynamicSignal
    TELE_AVAILABLE = True
except ImportError:
    TELE_AVAILABLE = False


# ─── AEGIS Policy Gate ────────────────────────────────────────────────────────
ALLOWED_CAPABILITIES = {permissions_list}

def aegis_check(required_cap: str) -> bool:
    """Enforce AEGIS capability gate before any privileged operation."""
    if required_cap not in ALLOWED_CAPABILITIES:
        raise PermissionError(f"AEGIS BLOCK: capability {{required_cap}} not in allowlist")
    return True


# ─── TSO ──────────────────────────────────────────────────────────────────────
TASK_STATE = {{
    "task_id": f"skill.{name}.{{int(time.time())}}",
    "objective": "{description}",
    "phase_state": "OBSERVE",
    "predicted_failure_modes": {predicted_failures},
    "authority_shrink_level": 0.1,
}}


# ─── Teleodynamic Trace Emitter ───────────────────────────────────────────────
def emit_trace(phase: str, shear: float = 0.1, failure_mode: Optional[str] = None):
    if not TELE_AVAILABLE:
        print(f"TELEODYNAMICS_TRACE: phase={{phase}} shear={{shear}} failure={{failure_mode}}")
        return
    signal = TeleodynamicSignal(
        trace_id=TASK_STATE["task_id"],
        phase_state=phase,
        phase_transition_id=f"{{TASK_STATE['phase_state']}}->{{phase}}",
        resonance_amplitude=0.75,
        shear_index=shear,
        canon_anchor_weight=0.85,
        structural_integrity_score=0.9 if failure_mode is None else 0.5,
        intent_priority_score={priority_score},
        authority_shrink_level=TASK_STATE["authority_shrink_level"],
        predicted_failure_modes=TASK_STATE["predicted_failure_modes"],
        actual_failure_mode=failure_mode,
    )
    print(f"TELEODYNAMICS_TRACE: {{json.dumps(signal.to_json(), indent=2)}}")
    TASK_STATE["phase_state"] = phase


# ─── ERGON Logger ────────────────────────────────────────────────────────────
def log_ergon(message: str):
    ergon_path = Path.home() / "NEXUS" / "ERGON.md"
    if ergon_path.exists():
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        with open(ergon_path, "a") as f:
            f.write(f"\\n[{{timestamp}}] [CLAUDE] {{message}}\\n")


# ─── ADCCL Control Loop ───────────────────────────────────────────────────────
MAX_RETRIES = 3

def run_with_correction(fn, *args, **kwargs):
    """ADCCL: run fn with up to MAX_RETRIES self-correction attempts."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            emit_trace("ACT", shear=0.1 + attempt * 0.1)
            result = fn(*args, **kwargs)
            emit_trace("VERIFY")
            return result
        except Exception as e:
            last_error = e
            emit_trace("REPAIR", shear=0.5 + attempt * 0.15, failure_mode=type(e).__name__)
            if attempt < MAX_RETRIES - 1:
                print(f"Attempt {{attempt+1}} failed: {{e}} — retrying...")
    raise RuntimeError(f"All {{MAX_RETRIES}} attempts failed. Last error: {{last_error}}")


# ─── Core Implementation ──────────────────────────────────────────────────────
def main_logic(args: argparse.Namespace) -> dict:
    """
    TODO: Implement {title} logic here.

    Contract:
    - Inputs: {inputs_inline}
    - Outputs: {outputs_inline}
    - Must call aegis_check() before any write or network operation
    - Must return dict with 'success', 'artifacts', and 'message' keys
    """
    emit_trace("OBSERVE")
    emit_trace("THINK")

    # Example: aegis_check("cap.fs.write") before writing any file

    # TODO: Replace with real implementation
    result = {{
        "success": False,
        "artifacts": [],
        "message": "Not yet implemented — Skill Architect stub",
    }}

    return result


# ─── Entry Point ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="{description}")
    {argparse_args}
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args()

    print(f"[{name}] Starting — AEGIS policy: strict")
    emit_trace("OBSERVE")

    try:
        result = run_with_correction(main_logic, args)
        if result["success"]:
            log_ergon(f"{title}: completed. Artifacts: {{result[\'artifacts\']}}")
            print(f"[{name}] Done. {{result[\'message\']}}")
            sys.exit(0)
        else:
            print(f"[{name}] Failed: {{result[\'message\']}}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        emit_trace("REPAIR", shear=0.8, failure_mode=str(e))
        log_ergon(f"{title}: FAILED — {{e}}")
        print(f"[{name}] Fatal: {{e}}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
'''

# ─── Eval Stub Template ───────────────────────────────────────────────────────
EVAL_TEMPLATE = '''\
"""
Eval suite for {title}
Generated by meta_generator.py
Covers: execution, AEGIS gate, ADCCL retry, MYELIN trace emission
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.{name} import main_logic, aegis_check, emit_trace

class TestAEGIS:
    def test_capability_gate_blocks_unknown(self):
        with pytest.raises(PermissionError):
            aegis_check("cap.unknown.operation")

    def test_capability_gate_allows_permitted(self):
        # Update with actual permitted cap
        # assert aegis_check("cap.fs.read") is True
        pass

class Test{title_class}:
    def test_main_logic_returns_required_keys(self, tmp_path):
        class Args:
            dry_run = True
        result = main_logic(Args())
        assert "success" in result
        assert "artifacts" in result
        assert "message" in result

    def test_emit_trace_does_not_raise(self):
        emit_trace("OBSERVE")
        emit_trace("VERIFY")
        emit_trace("REPAIR", failure_mode="TestError")

class TestADCCL:
    def test_retry_on_transient_failure(self):
        """Verify ADCCL loop retries before raising."""
        from tools.{name} import run_with_correction
        call_count = [0]
        def flaky():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("transient")
            return {{"success": True, "artifacts": [], "message": "ok"}}
        result = run_with_correction(flaky)
        assert result["success"] is True
        assert call_count[0] == 2
'''

# ─── Core Generator ──────────────────────────────────────────────────────────
def generate_skill(args):
    name = args.name.lower().replace("-", "_")
    title = args.description or name.replace("_", " ").title()
    title_class = "".join(w.title() for w in name.split("_"))
    layer = args.layer.upper() if args.layer else "AEON"
    domain = args.domain.lower() if args.domain else "default"
    priority = args.priority.lower() if args.priority else "medium"

    layer_info = LAYERS.get(layer, LAYERS["AEON"])
    permissions = DOMAIN_CAPS.get(domain, DOMAIN_CAPS["default"])
    permissions_list = repr(set(permissions))

    priority_score_map = {"critical": 1.0, "high": 0.8, "medium": 0.6, "low": 0.4}
    priority_score = priority_score_map.get(priority, 0.7)

    tso = build_tso(name, args.description or f"OmegA {title}", domain, priority)
    tso_json = json.dumps(tso, indent=2)

    predicted_failures = str(tso["predicted_failure_modes"])
    inputs_inline = args.inputs or "TBD"
    outputs_inline = args.outputs or "TBD"

    # Format SKILL.md
    skill_md = SKILL_MD_TEMPLATE.format(
        name=name, title=title, description=args.description or f"OmegA {title}",
        layer=layer, layer_role=layer_info["role"], domain=domain, priority=priority,
        timestamp=datetime.now().isoformat(),
        inputs=f"- `{inputs_inline}`" if inputs_inline else "- TBD",
        permissions="\n".join(f"- `{p}`" for p in permissions),
        outputs=f"- `{outputs_inline}`" if outputs_inline else "- TBD",
        priority_score=priority_score, predicted_failures=predicted_failures,
        tso_json=tso_json, usage_args=f"--{name.replace('_','-')} <arg>",
    )

    # Format implementation
    argparse_lines = []
    if inputs_inline and inputs_inline != "TBD":
        for inp in inputs_inline.split(","):
            arg = inp.strip().lstrip("-").strip()
            argparse_lines.append(f'parser.add_argument("--{arg}", help="{arg} input")')
    argparse_args = "\n    ".join(argparse_lines) if argparse_lines else "# TODO: add argparse arguments"

    impl = IMPL_TEMPLATE.format(
        name=name, title=title, description=args.description or f"OmegA {title}",
        layer=layer, domain=domain,
        permissions_list=permissions_list,
        predicted_failures=predicted_failures,
        priority_score=priority_score,
        inputs_inline=inputs_inline, outputs_inline=outputs_inline,
        argparse_args=argparse_args,
    )

    # Format eval
    eval_code = EVAL_TEMPLATE.format(name=name, title=title, title_class=title_class)

    return {
        "name": name, "title": title,
        "skill_md": skill_md,
        "impl": impl,
        "eval": eval_code,
        "tso": tso,
    }


def write_skill(skill: dict, output_root: Path, dry_run: bool = False):
    name = skill["name"]
    files = {
        output_root / "tools" / f"{name}.py": skill["impl"],
        output_root / "evals" / f"test_{name}.py": skill["eval"],
        output_root / "docs" / f"skill_{name}.md": skill["skill_md"],
    }
    results = []
    for path, content in files.items():
        if dry_run:
            print(f"[DRY RUN] Would write: {path} ({len(content)} bytes)")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            print(f"Written: {path}")
        results.append(str(path))
    return results


def main():
    parser = argparse.ArgumentParser(
        description="OmegA Meta-Generator — Skill Architect Foundational Tool"
    )
    parser.add_argument("--name", required=True, help="Skill name (snake_case)")
    parser.add_argument("--description", required=True, help="One-line description")
    parser.add_argument("--layer", default="AEON",
                        choices=["AEGIS", "AEON", "ADCCL", "MYELIN"],
                        help="OmegA architectural layer")
    parser.add_argument("--domain", default="default",
                        choices=list(DOMAIN_CAPS.keys()),
                        help="Skill domain (determines capability allowlist)")
    parser.add_argument("--priority", default="medium",
                        choices=["critical", "high", "medium", "low"],
                        help="Skill priority")
    parser.add_argument("--inputs", help="Comma-separated input parameters")
    parser.add_argument("--outputs", help="Comma-separated output artifacts")
    parser.add_argument("--root", default=".", help="OmegA-Architecture root path")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview files without writing")
    args = parser.parse_args()

    print(f"\n[meta_generator] Architecting skill: {args.name}")
    print(f"  Layer: {args.layer} | Domain: {args.domain} | Priority: {args.priority}")

    skill = generate_skill(args)
    root = Path(args.root).resolve()
    written = write_skill(skill, root, dry_run=args.dry_run)

    print(f"\n[meta_generator] Skill '{skill['name']}' generated:")
    for f in written:
        print(f"  {f}")

    if not args.dry_run:
        print(f"\n[meta_generator] TSO saved. Next step:")
        print(f"  Implement tools/{skill['name']}.py main_logic()")
        print(f"  Then: python3 -m pytest evals/test_{skill['name']}.py -v")

    return skill


if __name__ == "__main__":
    main()
