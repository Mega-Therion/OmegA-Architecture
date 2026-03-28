/-
  T-7: Unified Action Gating (3-Gate Conjunction)

  Formal statement:
    An action a is permitted if and only if ALL three gates pass:
      V_t > τ_verify  ∧  ρ(A) < θ_allow  ∧  R(a) < τ_consent

    This is a pure conjunction — no single gate can be bypassed.

  We prove:
    1. The gate is conjunctive (not disjunctive)
    2. Failure of any single gate blocks the action
    3. Gate ordering does not affect the result
    4. Default state is denial
    5. Only the all-true configuration permits
-/

namespace OmegA.UnifiedGating

-- Gate results
structure GateResult where
  verifier_pass : Bool    -- V_t > τ_verify (ADCCL)
  bridge_pass : Bool      -- ρ(A) < θ_allow (AEON)
  risk_pass : Bool        -- R(a) < τ_consent (AEGIS)
  deriving Repr, DecidableEq

-- The unified gate is a pure conjunction
def permitted (g : GateResult) : Bool :=
  g.verifier_pass && g.bridge_pass && g.risk_pass

-- T-7a: Conjunction — all three must pass
theorem conjunction_required (g : GateResult) :
    permitted g = true →
    g.verifier_pass = true ∧ g.bridge_pass = true ∧ g.risk_pass = true := by
  intro h
  unfold permitted at h
  simp [Bool.and_eq_true] at h
  exact ⟨h.1.1, h.1.2, h.2⟩

-- T-7b: Any single gate failure blocks
theorem verifier_blocks (g : GateResult) (h : g.verifier_pass = false) :
    permitted g = false := by
  unfold permitted; simp [h]

theorem bridge_blocks (g : GateResult) (h : g.bridge_pass = false) :
    permitted g = false := by
  unfold permitted; simp [h]

theorem risk_blocks (g : GateResult) (h : g.risk_pass = false) :
    permitted g = false := by
  unfold permitted; simp [h]

-- T-7c: Gate ordering does not affect the result
def permitted_reordered (g : GateResult) : Bool :=
  g.risk_pass && g.verifier_pass && g.bridge_pass

theorem order_invariance (g : GateResult) :
    permitted g = permitted_reordered g := by
  unfold permitted permitted_reordered
  cases g.verifier_pass <;> cases g.bridge_pass <;> cases g.risk_pass <;> simp

-- T-7d: Default (all gates down) is denial
theorem default_denial : permitted ⟨false, false, false⟩ = false := by
  native_decide

-- T-7e: Only the all-true configuration permits
theorem only_all_true_permits (g : GateResult) :
    permitted g = true ↔ g = ⟨true, true, true⟩ := by
  constructor
  · intro h
    have ⟨hv, hb, hr⟩ := conjunction_required g h
    cases g; simp_all
  · intro h; subst h; native_decide

end OmegA.UnifiedGating
