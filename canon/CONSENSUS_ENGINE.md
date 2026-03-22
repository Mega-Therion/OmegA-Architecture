# Consensus Engine — DCBFT Specification
**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-13
**Operator:** RY (Mega)

DCBFT (Decentralized Collective Brain Fault Tolerance) is OmegA's Byzantine fault-tolerant voting mechanism for multi-agent decisions. It is implemented in `services/packages/bridge/consensus_engine.py` and the Rust-side `omega-consensus` crate.

---

## 1. Purpose

DCBFT ensures that consequential multi-agent decisions are:
- **Fault-tolerant:** Correct even if some agents behave incorrectly or go offline
- **Byzantine-safe:** Correct even if some agents are actively adversarial or malicious
- **Auditable:** Every vote and its outcome is logged
- **Deterministic:** Same inputs always produce the same outcome given the same fault conditions

DCBFT is the mechanism layer beneath the Peace Pipe Protocol. The Peace Pipe is the governance ceremony; DCBFT is the vote counting and fault tolerance math.

---

## 2. When Consensus Is Required vs Optional

### Required (system will not proceed without it)

- Identity changes (changes to OMEGA_IDENTITY.md or equivalent runtime state)
- Canon document ratification
- Treasury moves above configured threshold
- Provider chain modifications
- Any action tagged with `DCBFT_REQUIRED` in the Tool Registry

### Optional (consensus is advisory, operator can override)

- Multi-agent task decomposition outcomes
- Memory promotion decisions (when multiple agents contribute to the same memory)
- Strategy selection when multiple valid approaches exist
- Agent workload rebalancing

### Consensus Bypass Conditions

Consensus may be bypassed only when:
1. **Emergency override** is invoked by the Chief (RY) — see PEACE_PIPE_PROTOCOL.md §6
2. **Quorum is structurally unavailable** (fewer than 4 agents are reachable) AND the action is classified as non-critical — in this case, the action is logged as `CONSENSUS_BYPASSED` and RY is notified
3. **Strict mode is disabled** for the specific action domain — only configurable by RY

Every bypass must be logged with:
- Timestamp
- Agent invoking the bypass
- Reason code (`EMERGENCY` / `QUORUM_UNAVAILABLE` / `STRICT_MODE_DISABLED`)
- The action taken

---

## 3. Fault Tolerance Thresholds

DCBFT requires `N ≥ 3f + 1` agents to tolerate `f` faulty agents.

**Production minimum:** 4 agents (tolerates 1 faulty)
**Target configuration:** 7 agents (tolerates 2 faulty — the 7-specialist setup)

| Agents (N) | Faulty Tolerated (f) | Quorum Required |
|------------|---------------------|-----------------|
| 4 | 1 | 3 (75%) |
| 7 | 2 | 5 (71%) |
| 10 | 3 | 7 (70%) |

**Supermajority threshold:** 2/3 (66.7%) — rounded up

Agents that do not respond within the round timeout are counted as failed, not faulty. An agent that responds with contradictory votes across rounds is counted as Byzantine (faulty).

---

## 4. Round Structure

Each DCBFT vote executes in three phases:

### Phase 1: PROPOSE
- The initiating agent (or Brain orchestrator) broadcasts the proposal to all registered agents
- Proposal includes: action description, action hash, timestamp, initiator identity
- Round timeout begins

### Phase 2: VOTE
- Each reachable agent independently evaluates the proposal
- Each agent casts: `APPROVE` / `REJECT` / `ABSTAIN`
- Votes are signed with the agent's session identity
- Votes are collected by the Bridge consensus engine

### Phase 3: COMMIT (or ABORT)
- If `APPROVE` votes ≥ 2/3 of responding agents: **COMMIT** — action proceeds
- If `REJECT` votes > 1/3 of responding agents: **ABORT** — action is blocked
- If quorum is not reached within timeout: **TIMEOUT** — treated as ABORT unless emergency override applies

Committed actions are written to the consensus ledger before execution begins.

---

## 5. Conflict Resolution

When agents submit conflicting factual claims (not just different votes, but incompatible assertions):

1. **Contradictions are surfaced** — the Bridge notes the conflict in the consensus record
2. **Chief adjudication** — contradictions on canon facts escalate to RY for resolution
3. **Confidence-weighted tiebreaker** — if RY is unavailable and the conflict is non-canon, higher-confidence agent positions take precedence (confidence scores are part of the vote payload)
4. **Memory contradiction flag** — the winning position is written to memory with `conflict_flag: true` so it can be revisited

Agents may not silently override each other's contributions. All conflicts must be visible in the audit trail.

---

## 6. Integration with Peace Pipe Protocol

DCBFT is the vote-counting mechanism that runs inside a Peace Pipe session:

```
Peace Pipe SUBMISSION phase → agents submit Toke templates
                                          ↓
                              DCBFT collects votes from Toke templates
                                          ↓
                              Bridge calculates 2/3 supermajority
                                          ↓
                              Clerk synthesis includes vote summary
                                          ↓
                              Chief Ruling (override possible at this stage)
                                          ↓
                              COMMIT or ABORT
```

The Chief Ruling can override any DCBFT outcome — even a unanimous APPROVE vote can be vetoed by RY.

---

## 7. Implementation References

| Component | Location | Notes |
|-----------|----------|-------|
| Python DCBFT engine | `services/packages/bridge/consensus_engine.py` | Primary production implementation |
| Rust consensus crate | `rust/omega-rust/crates/omega-consensus/` | Used by Gateway for low-level operations |
| Brain consensus bridge | `services/packages/brain/src/core/consensus-engine.js` | Brain-side JS wrapper |
| AsyncOrchestrator | `services/packages/bridge/orchestrator.py` | Wraps DCBFT for async task execution |

**Current status:** JS-side voting logic is operational. True multi-node network consensus (multiple physical nodes) is not yet in production Docker configs — all agents currently run on the same host. This is noted in OMEGA_FULL_SYSTEM_SPEC.md as Confidence Gap #2.

---

## Changelog

- 1.0.0 (2026-03-13): Initial canonical synthesis from OMEGA_FULL_SYSTEM_SPEC.md, OMEGA_VISION.md. Prior stub was a placeholder.
