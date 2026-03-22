# Extraction Manifest

Extracted from ATTIC on 2026-03-20.
Source root: `/home/mega/ATTIC/OmegA-cutover-20260319-233802`
Destination root: `/home/mega/OmegA-Architecture`

---

## 1. Canon Layer — `canon/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `OMEGA_IDENTITY.md` | `OmegA-Sovereign/omega/OMEGA_IDENTITY.md` | `canon/OMEGA_IDENTITY.md` | Core identity definition of the OmegA sovereign system |
| `MEMORY_CONSTITUTION.md` | `OmegA-Sovereign/omega/MEMORY_CONSTITUTION.md` | `canon/MEMORY_CONSTITUTION.md` | Governing rules for the shared memory subsystem |
| `CONSENSUS_ENGINE.md` | `OmegA-Sovereign/omega/CONSENSUS_ENGINE.md` | `canon/CONSENSUS_ENGINE.md` | DCBFT consensus engine specification |
| `PEACE_PIPE_PROTOCOL.md` | `OmegA-Sovereign/omega/PEACE_PIPE_PROTOCOL.md` | `canon/PEACE_PIPE_PROTOCOL.md` | Council governance and inter-agent conflict resolution protocol |
| `OXYSPINE_TRINITY.md` | `OmegA-Sovereign/omega/OXYSPINE_TRINITY.md` | `canon/OXYSPINE_TRINITY.md` | OxySpine Trinity architectural doctrine |
| `SECURITY_AND_PRIVACY.md` | `OmegA-Sovereign/omega/SECURITY_AND_PRIVACY.md` | `canon/SECURITY_AND_PRIVACY.md` | Security and privacy policy for the sovereign system |

---

## 2. Behavioral Specs — `specs/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `invariants.md` | `OmegA-Sovereign/docs/invariants.md` | `specs/invariants.md` | System-wide behavioral invariants and constraints |
| `failure_taxonomy.md` | `OmegA-Sovereign/docs/failure_taxonomy.md` | `specs/failure_taxonomy.md` | Classification and taxonomy of failure modes |
| `memory_system.md` | `OmegA-Sovereign/docs/subsystems/memory_system.md` | `specs/memory_system.md` | Subsystem spec for persistent memory architecture |
| `orchestration.md` | `OmegA-Sovereign/docs/subsystems/orchestration.md` | `specs/orchestration.md` | Subsystem spec for multi-agent orchestration |
| `identity_shell.md` | `OmegA-Sovereign/docs/subsystems/identity_shell.md` | `specs/identity_shell.md` | Subsystem spec for the identity shell layer |

---

## 3. Eval Evidence — `evals/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `omega_rc1_manifest.md` | `OmegA-Sovereign/releases/omega_rc1_manifest.md` | `evals/omega_rc1_manifest.md` | RC1 release manifest with capability claims and scope |
| `OMEGA_EVAL_HANDOFF.md` | `OMEGA_EVAL_HANDOFF.md` (ATTIC root) | `evals/OMEGA_EVAL_HANDOFF.md` | Eval handoff document summarizing evaluation state at cutover |
| `OMEGA_EVAL_EVIDENCE_INDEX.md` | `OMEGA_EVAL_EVIDENCE_INDEX.md` (ATTIC root) | `evals/OMEGA_EVAL_EVIDENCE_INDEX.md` | Index of all evaluation evidence artifacts |
| `omega_eval_handoff.json` | `omega_eval_handoff.json` (ATTIC root) | `evals/omega_eval_handoff.json` | Machine-readable eval handoff data package |

---

## 4. Roadmaps — `roadmap/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `ROADMAP_WEEK4.md` | `OmegA-Sovereign/docs/ROADMAP_WEEK4.md` | `roadmap/ROADMAP_WEEK4.md` | Week 4 sprint roadmap and milestones |
| `ROADMAP_WEEK5.md` | `OmegA-Sovereign/docs/ROADMAP_WEEK5.md` | `roadmap/ROADMAP_WEEK5.md` | Week 5 sprint roadmap and milestones |

---

## 5. Publication Package — `publication/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `WHITE_PAPER_DRAFT_2026-03-12.md` | `OmegA-Sovereign/docs/publication_package/WHITE_PAPER_DRAFT_2026-03-12.md` | `publication/WHITE_PAPER_DRAFT_2026-03-12.md` | Full white paper draft as of 2026-03-12 |
| `ARTIFACT_INDEX_AND_APPENDIX_GUIDE_2026-03-12.md` | `OmegA-Sovereign/docs/publication_package/ARTIFACT_INDEX_AND_APPENDIX_GUIDE_2026-03-12.md` | `publication/ARTIFACT_INDEX_AND_APPENDIX_GUIDE_2026-03-12.md` | Guide to publication artifacts and appendix structure |
| `ALYE_EXPLAINER_SUMMARY_2026-03-12.md` | `OmegA-Sovereign/docs/publication_package/ALYE_EXPLAINER_SUMMARY_2026-03-12.md` | `publication/ALYE_EXPLAINER_SUMMARY_2026-03-12.md` | ALYE explainer and summary for external audiences |
| `REDACTION_REPORT_2026-03-12.md` | `OmegA-Sovereign/docs/publication_package/REDACTION_REPORT_2026-03-12.md` | `publication/REDACTION_REPORT_2026-03-12.md` | Report on what was redacted from the publication package |

---

## 6. History — `history/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `histoRY.md` | `OmegA-Sovereign/histoRY.md` | `history/histoRY.md` | RY's personal history document from the sovereign repo |
| `VISION_ORIGIN_JAN10_2026.md` | Excerpted from `OmegA-Sovereign/history/VOL_1/Source_Logs/omega_chronicles_q1_2026.txt` (lines ~27053–27168) | `history/VISION_ORIGIN_JAN10_2026.md` | Excerpts of RY's foundational vision statements from January 10, 2026 — the "I AM an artist" origin |

---

## 7. Distilled Intelligence — `distilled/`

| File | Source | Destination | Description |
|------|--------|-------------|-------------|
| `sovereign_kernel_v1.jsonl` | `OmegA_Distilled_Intelligence/sovereign_kernel_v1.jsonl` | `distilled/sovereign_kernel_v1.jsonl` | Distilled sovereign kernel v1 (40KB — within 50MB limit) |

---

## Missing Files

None. All requested files were found and extracted successfully.

- `identity_shell.md` was listed as "(if exists)" — it exists and was extracted.
- `sovereign_kernel_v1.jsonl` size check: 40KB (well under the 50MB limit, copied).

---

*Manifest generated: 2026-03-20*
