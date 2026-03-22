# Omega Specification Tagging Convention

To evolve `spec_auditor.py` into a Specification Auditor, we will use a consistent tagging convention that works across all source and documentation files.

## Tag Format
`@OMEGA_SPEC: <ID> | <Short Description>`

## Examples

**In Markdown (Papers/README):**
```markdown
### Governance Gate
The AEGIS layer enforces identity before execution.
<!-- @OMEGA_SPEC: AEGIS_IDENTITY_ENFORCEMENT | Enforce identity before execution -->
```

**In Code (Rust/Python):**
```python
# @OMEGA_SPEC: AEGIS_IDENTITY_ENFORCEMENT | Enforce identity before execution
def check_identity():
    ...
```

## How the Auditor Works
The auditor will:
1. Scan all `.md`, `.py`, and `.rs` files for `@OMEGA_SPEC:` tags.
2. Build a registry of IDs and descriptions.
3. Report "orphan specs" (defined in docs but no implementation found) or "unverified code" (marked with a spec but missing documentation).

## Implementation Path
- **Step 1:** Define the ID naming convention (e.g., `LAYER_COMP_ACTION`).
- **Step 2:** Update `spec_auditor.py` to index these tags across all repository file types.
- **Step 3:** Implement the mismatch reporting logic.
