# Peace Pipe Protocol
**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-13
**Operator:** RY (Mega)

The Peace Pipe Protocol is a formal governance ceremony for consequential system decisions. It is implemented as strict turn-taking, locks, and artifacts — not merely a ritual. The metaphor is a talking circle; the implementation is a state machine enforced server-side by the Bridge.

---

## 1. What the Peace Pipe Protocol Is

A structured council process that must be completed before any of the following are canonized:
- Changes to OmegA's identity or core doctrine
- Modifications to LAW.json policies
- Changes to memory constitution rules
- Major architectural changes affecting service contracts
- Treasury or economic policy changes
- Any action that OMEGA_VISION.md designates as requiring "Council Resolution"

The protocol ensures that consequential changes have:
1. A deliberation record (transcript)
2. Multiple agent perspectives (docket)
3. A Chief Ruling (RY's final decision)
4. A Phylactery update (canon version bump)
5. An enforcement test (proof the change is implemented)

A change is canonical ONLY if it produces all five artifacts.

---

## 2. When the Protocol Triggers

### Mandatory Triggers (cannot be bypassed)

| Trigger | Risk Level | Description |
|---------|-----------|-------------|
| Identity update | CRITICAL | Any change to OMEGA_IDENTITY.md or soul.rs canonical() |
| LAW.json modification | CRITICAL | Adding/removing forbidden actions, restricted folders, or authority levels |
| Memory Constitution change | HIGH | Write trigger rules, purge rules, provenance schema |
| Provider removal from failover | HIGH | Removing a provider from the active chain |
| Service contract change | HIGH | Port changes, health endpoint changes, shared schema changes |
| Canon document creation | MEDIUM | Creating a new canonical sub-document |

### Optional (Recommended) Triggers

- Architectural changes that affect two or more services
- New external integrations (Telegram, Alexa, n8n, etc.)
- Changes to Neuro-Credit economy rules
- Adding a new agent to the gAIng collective

### Risk Thresholds from LAW.json

- Unsupervised action limit: 5 consecutive actions without operator review
- Beyond this threshold, escalate to council or request explicit operator confirmation

---

## 3. Council Composition

### Standing Members

| Role | Agent | Authority |
|------|-------|-----------|
| Chief | RY (Mega) | Final authority. Veto power. Speaks last. |
| Clerk | Safa (or designated synthesizer) | Synthesizes all positions before Chief speaks. Does not vote. |
| Architect | Claude | Analytical review, safety validation, architectural critique |
| Strategist | Gemini | Strategic perspective, risk assessment, alternatives |
| Builder | Codex | Implementation feasibility, technical constraints |
| Scout | Grok | Real-time context, external signals |

### Quorum Requirement

- Minimum 3 agents must have spoken before Clerk synthesis
- Chief cannot speak before Clerk synthesis is complete
- A missing agent's position can be noted as ABSTAIN; council can proceed with remaining members

---

## 4. Voting Mechanics

### Turn Structure (Toke Template)

Each agent submits a structured statement containing:
1. **Position:** Their stance on the proposed change (APPROVE / REJECT / AMEND / ABSTAIN)
2. **Reasoning:** Evidence and argument for their position
3. **Failure Modes:** What breaks if this change is adopted
4. **Safeguards:** How to prevent or recover from those failures
5. **Vote + Confidence:** Vote and a confidence percentage (0-100%)

### Session State Machine

```
OPEN → PIPE_GRANTED → SUBMISSION (per agent) → SYNTHESIS (Clerk) → CHIEF_RULING → CLOSE
```

- OPEN: Council session initiated, topic stated, docket created
- PIPE_GRANTED: One agent at a time holds the pipe and may speak
- SUBMISSION: All agents submit their Toke template
- SYNTHESIS: Clerk summarizes all positions without adding their own judgment
- CHIEF_RULING: RY makes the final decision (APPROVE / REJECT / AMEND + conditions)
- CLOSE: Artifacts generated, session closed

### Locks Enforced by Bridge

- Only the pipe holder may submit a statement
- No agent may speak twice in the same lap
- Chief cannot rule before Clerk synthesis
- State transitions are one-way; sessions cannot be rewound
- Session artifacts are generated at CLOSE and are immutable

---

## 5. Veto Rights

**RY (Chief) holds absolute veto.** No consensus outcome, however unanimous, overrides a Chief veto.

When RY vetoes:
- The proposed change is rejected
- The veto reason is recorded in the session transcript
- A new council session can be opened later with revised proposal

**Agent rejection** (REJECT vote) does not constitute a veto — it counts as input for Chief deliberation only.

---

## 6. Emergency Override Procedures

In operational emergencies (service down, security breach, data loss imminent), the Chief may:
1. Issue a **Emergency Ruling** without full council session
2. The ruling takes immediate effect
3. A post-hoc council session must be opened within 24 hours to ratify or reverse the emergency ruling
4. Emergency rulings without ratification expire after 72 hours and the system reverts

Emergency rulings must be logged to:
- `~/NEXUS/ERGON.md` with tag `[EMERGENCY_RULING]`
- The Bridge audit trail with reason field populated

Non-emergency situations may not use emergency override. "Urgency" does not qualify unless the system is at risk of active harm.

---

## 7. Audit Trail Requirements

Every council session generates three artifacts:

**1. Transcript (`transcript_[session_id].md`)**
- Full verbatim record of all agent submissions
- Timestamps and agent identifiers
- Immutable once session is closed

**2. Docket (`docket_[session_id].md`)**
- Summary of the proposed change
- Agent vote tallies
- Clerk synthesis
- Chief Ruling text

**3. Resolution (`resolution_[session_id].md`)**
- The canonical change instruction (if APPROVE)
- Version bump specification
- Enforcement test requirement
- Target documents to update

All artifacts are stored in the Bridge consensus archive and referenced in the Phylactery version history.

---

## Changelog

- 1.0.0 (2026-03-13): Initial canonical synthesis from OMEGA_VISION.md, LAW.json. Prior stubs were empty placeholders.
