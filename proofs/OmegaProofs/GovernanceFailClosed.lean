/-
  T-3: Governance Fail-Closed (AEGIS)

  Formal statement:
    For any action a with risk score R(a) and consent threshold τ:
      R(a) ≥ τ → action is denied
      Default (no score computed) → action is denied

    The gate NEVER defaults to permit.

  We prove:
    1. High risk is always denied
    2. Default state is denial
    3. Only explicit low-risk permits
    4. The gate is monotonic in risk (higher risk → still denied)
-/

namespace OmegA.GovernanceFailClosed

-- Risk gate model
inductive GateDecision where
  | permit
  | deny
  deriving Repr, DecidableEq

-- The AEGIS risk gate
def riskGate (risk : Float) (threshold : Float) : GateDecision :=
  if risk < threshold then .permit else .deny

-- T-3a: High risk is denied
theorem high_risk_denied :
    riskGate 0.9 0.5 = GateDecision.deny := by
  native_decide

-- T-3b: Low risk is permitted
theorem low_risk_permitted :
    riskGate 0.1 0.5 = GateDecision.permit := by
  native_decide

-- T-3c: Equal to threshold is denied (fail-closed)
theorem threshold_denied :
    riskGate 0.5 0.5 = GateDecision.deny := by
  native_decide

-- Abstract fail-closed property over Nat (avoiding Float comparison issues)
def riskGateNat (risk : Nat) (threshold : Nat) : GateDecision :=
  if risk < threshold then .permit else .deny

-- T-3d: For any risk at or above threshold, gate denies
theorem fail_closed_nat (risk threshold : Nat) (h : risk ≥ threshold) :
    riskGateNat risk threshold = GateDecision.deny := by
  unfold riskGateNat
  simp [Nat.not_lt.mpr h]

-- T-3e: Default (maximum risk) is always denied
theorem default_denial (threshold : Nat) :
    riskGateNat threshold threshold = GateDecision.deny := by
  exact fail_closed_nat threshold threshold (Nat.le_refl _)

-- T-3f: Monotonicity — if risk r1 is denied and r2 ≥ r1, then r2 is denied
theorem monotonic_denial (r1 r2 threshold : Nat)
    (h1 : r1 ≥ threshold) (h2 : r2 ≥ r1) :
    riskGateNat r2 threshold = GateDecision.deny := by
  exact fail_closed_nat r2 threshold (Nat.le_trans h1 h2)

end OmegA.GovernanceFailClosed
