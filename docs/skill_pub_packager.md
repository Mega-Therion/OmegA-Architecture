---
name: pub_packager
description: Automates GitHub releases, Zenodo uploads, citation updates, changelogs, and documentation bundles for OmegA papers
version: "1.0.0"
layer: AEON
domain: publication
priority: high
aegis_policy: strict
generated_by: meta_generator.py
generated_at: 2026-03-28T00:29:04.584484
---

# Automates GitHub releases, Zenodo uploads, citation updates, changelogs, and documentation bundles for OmegA papers

> **Layer:** AEON (Cognitive OS — orchestration + TSO lifecycle)
> **AEGIS Policy:** `strict` — requires explicit permission for writes/network/exec

## Purpose

Automates GitHub releases, Zenodo uploads, citation updates, changelogs, and documentation bundles for OmegA papers

## Skill Contract

### Inputs
- `repo_root,target_version,zenodo_token`

### Permissions Required
- `cap.fs.read`
- `cap.fs.write`
- `cap.network.github`

### Execution Steps (Observable)
1. **OBSERVE** — Load context, verify dependencies, emit trace
2. **THINK** — Validate inputs against constraints, build execution plan
3. **ACT** — Execute primary logic with error capture
4. **VERIFY** — Check output artifacts against success_criteria
5. **REMEMBER** — Emit TELEODYNAMICS_TRACE, log to ERGON.md

### Output Artifacts
- `release_bundle.zip,CHANGELOG.md,CITATION.cff`

### Rollback Behavior
- On failure: emit `TELEODYNAMICS_TRACE` with `actual_failure_mode` set
- Partial writes: clean up incomplete artifacts before exit
- Log failure reason to ERGON.md

## Teleodynamic Trace Schema

```python
TeleodynamicSignal(
    trace_id="skill.pub_packager.<timestamp>",
    phase_state="VERIFY",                    # or "REPAIR" on failure
    phase_transition_id="act->verify",
    resonance_amplitude=0.75,
    shear_index=0.1,                         # < 0.5 = healthy
    canon_anchor_weight=0.85,
    structural_integrity_score=0.90,
    intent_priority_score=0.8,
    authority_shrink_level=0.1,
    predicted_failure_modes=['missing_dependency', 'permission_denied', 'output_empty'],
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
{
  "task_id": "skill.pub_packager.1774675744",
  "objective": "Automates GitHub releases, Zenodo uploads, citation updates, changelogs, and documentation bundles for OmegA papers",
  "constraints": [
    "No secrets in logs or output",
    "All file paths must be absolute",
    "Emit TELEODYNAMICS_TRACE on completion",
    "Log to ~/NEXUS/ERGON.md on success"
  ],
  "success_criteria": [
    "pub_packager executes without error",
    "Output artifact is present and non-empty",
    "TELEODYNAMICS_TRACE emitted with phase_state=VERIFY"
  ],
  "declared_unknowns": [],
  "urgency": "high",
  "intent_priority_score": 0.8,
  "goal_valence_vector": {
    "truth": 1.0,
    "speed": 0.5,
    "safety": 0.9,
    "continuity": 0.8,
    "operator_preference": 0.8
  },
  "authority_shrink_level": 0.1,
  "canon_anchor_weight": 0.85,
  "predicted_failure_modes": [
    "missing_dependency",
    "permission_denied",
    "output_empty"
  ],
  "phase_state": "OBSERVE"
}
```

## Usage

```bash
# From OmegA-Architecture root:
python3 tools/pub_packager.py --pub-packager <arg>

# Or via omegactl:
python3 omegactl.py pub_packager --pub-packager <arg>
```
