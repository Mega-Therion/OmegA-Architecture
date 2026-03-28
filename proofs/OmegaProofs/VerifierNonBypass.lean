/-
  T-6: Verifier Non-Bypass

  Formal statement:
    The unified 3-gate composition requires all three gates to pass.
    The verifier (V) cannot be silently bypassed. Specifically:

      multi_gate(V, rho, R) == True
        iff (V > tau_verify) AND (rho < theta_allow) AND (R < tau_consent)

    If V <= tau_verify, the action is blocked regardless of rho and R values.

  Key insight: T-7 proves conjunction properties over Bool gates.
  T-6 focuses on the SPECIFIC claim that the verifier gate cannot be
  bypassed — no combination of other gate values can compensate for
  verifier failure. We prove symmetric non-bypass for all three gates.

  We prove:
    1. verifier_failure_blocks — verifier_pass=false => blocked, regardless of others
    2. verifier_necessary — permitted=true => verifier_pass=true (extraction)
    3. no_compensation — exhaustive: for all b r, verifier_pass=false => blocked
    4. bridge_necessary — permitted=true => bridge_pass=true
    5. risk_necessary — permitted=true => risk_pass=true
-/

namespace OmegA.VerifierNonBypass

-- Reuse the same GateResult shape as UnifiedGating (compatible definition)
structure GateResult where
  verifier_pass : Bool    -- V_t > tau_verify (ADCCL)
  bridge_pass : Bool      -- rho(A) < theta_allow (AEON)
  risk_pass : Bool        -- R(a) < tau_consent (AEGIS)
  deriving Repr, DecidableEq

-- The unified gate: pure conjunction (identical to T-7 definition)
def permitted (g : GateResult) : Bool :=
  g.verifier_pass && g.bridge_pass && g.risk_pass

-- ═══════════════════════════════════════════════════════════════════════
-- T-6a: Verifier failure blocks — if verifier_pass = false, permitted = false
--        regardless of bridge_pass and risk_pass values.
-- ═══════════════════════════════════════════════════════════════════════

theorem verifier_failure_blocks (g : GateResult) (h : g.verifier_pass = false) :
    permitted g = false := by
  unfold permitted; simp [h]

-- ═══════════════════════════════════════════════════════════════════════
-- T-6b: Verifier necessary — permitted = true implies verifier_pass = true.
--        This is the extraction direction: if you got through, verifier passed.
-- ═══════════════════════════════════════════════════════════════════════

theorem verifier_necessary (g : GateResult) (h : permitted g = true) :
    g.verifier_pass = true := by
  unfold permitted at h
  simp [Bool.and_eq_true] at h
  exact h.1.1

-- ═══════════════════════════════════════════════════════════════════════
-- T-6c: No compensation — for ALL values of bridge_pass and risk_pass,
--        if verifier_pass = false then permitted = false.
--        This is the core non-bypass claim: no other gate combination
--        can compensate for verifier failure.
-- ═══════════════════════════════════════════════════════════════════════

theorem no_compensation (b r : Bool) :
    permitted ⟨false, b, r⟩ = false := by
  unfold permitted; simp

-- Explicit enumeration for emphasis: all four cases
theorem no_compensation_ff : permitted ⟨false, false, false⟩ = false := by native_decide
theorem no_compensation_ft : permitted ⟨false, false, true⟩  = false := by native_decide
theorem no_compensation_tf : permitted ⟨false, true, false⟩  = false := by native_decide
theorem no_compensation_tt : permitted ⟨false, true, true⟩   = false := by native_decide

-- ═══════════════════════════════════════════════════════════════════════
-- T-6d: Bridge necessary — symmetric non-bypass for the bridge gate.
--        permitted = true implies bridge_pass = true.
-- ═══════════════════════════════════════════════════════════════════════

theorem bridge_failure_blocks (g : GateResult) (h : g.bridge_pass = false) :
    permitted g = false := by
  unfold permitted; simp [h]
  cases g.verifier_pass <;> simp

theorem bridge_necessary (g : GateResult) (h : permitted g = true) :
    g.bridge_pass = true := by
  unfold permitted at h
  simp [Bool.and_eq_true] at h
  exact h.1.2

theorem no_compensation_bridge (v r : Bool) :
    permitted ⟨v, false, r⟩ = false := by
  unfold permitted; cases v <;> simp

-- ═══════════════════════════════════════════════════════════════════════
-- T-6e: Risk necessary — symmetric non-bypass for the risk gate.
--        permitted = true implies risk_pass = true.
-- ═══════════════════════════════════════════════════════════════════════

theorem risk_failure_blocks (g : GateResult) (h : g.risk_pass = false) :
    permitted g = false := by
  unfold permitted; simp [h]
  cases g.verifier_pass <;> cases g.bridge_pass <;> simp

theorem risk_necessary (g : GateResult) (h : permitted g = true) :
    g.risk_pass = true := by
  unfold permitted at h
  simp [Bool.and_eq_true] at h
  exact h.2

theorem no_compensation_risk (v b : Bool) :
    permitted ⟨v, b, false⟩ = false := by
  unfold permitted; cases v <;> cases b <;> simp

-- ═══════════════════════════════════════════════════════════════════════
-- T-6f: Universal non-bypass — ANY single gate failure is fatal.
--        Unified statement: for each gate index, failure blocks.
-- ═══════════════════════════════════════════════════════════════════════

theorem universal_non_bypass (g : GateResult) :
    (g.verifier_pass = false ∨ g.bridge_pass = false ∨ g.risk_pass = false) →
    permitted g = false := by
  intro h
  unfold permitted
  cases h with
  | inl hv => simp [hv]
  | inr h =>
    cases h with
    | inl hb => cases g.verifier_pass <;> simp [hb]
    | inr hr => cases g.verifier_pass <;> cases g.bridge_pass <;> simp [hr]

-- ═══════════════════════════════════════════════════════════════════════
-- T-6g: Completeness — permitted = true iff ALL gates pass.
--        (Mirrors T-7e but within the VerifierNonBypass namespace.)
-- ═══════════════════════════════════════════════════════════════════════

theorem all_gates_required (g : GateResult) :
    permitted g = true ↔
    g.verifier_pass = true ∧ g.bridge_pass = true ∧ g.risk_pass = true := by
  constructor
  · intro h
    exact ⟨verifier_necessary g h, bridge_necessary g h, risk_necessary g h⟩
  · intro ⟨hv, hb, hr⟩
    unfold permitted; simp [hv, hb, hr]

end OmegA.VerifierNonBypass
