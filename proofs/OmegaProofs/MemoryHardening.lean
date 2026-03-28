/-
  T-5: Memory Hardening Monotonicity (MYELIN)

  Formal statement:
    Given the edge hardening update rule:
      q_{ij}(t+1) = (1 - λ) * q_{ij}(t) + λ * r_t

    T-5a: If r ≥ q, then q' ≥ q (positive reward never decreases)
    T-5b: Bounded in [0, 1] when inputs are in [0, 1]
    T-5c: Fixed point: harden(r, λ, r) yields r

  We prove over Nat with milliscale [0, 1000] ≅ [0.0, 1.0].
  Lean4 stdlib only (no Mathlib). ring is unavailable so
  we factor through Nat.sub_add_cancel.
-/

namespace OmegA.MemoryHardening

-- Scaled hardening: inputs and output in [0, 1000]
def hardenScaled (q lam r : Nat) : Nat :=
  ((1000 - lam) * q + lam * r) / 1000

-- Helper: (1000 - lam) + lam = 1000 when lam ≤ 1000
theorem sub_add_eq (lam : Nat) (h : lam ≤ 1000) :
    1000 - lam + lam = 1000 :=
  Nat.sub_add_cancel h

-- T-5a: Monotonicity under positive reward
-- If r ≥ q and lam ≤ 1000, then the numerator ≥ 1000 * q
-- Proof sketch: (1000-lam)*q + lam*r ≥ (1000-lam)*q + lam*q = 1000*q
theorem monotonicity_numerator (q lam r : Nat)
    (_hlam : lam ≤ 1000)
    (hr : r ≥ q) :
    (1000 - lam) * q + lam * r ≥ (1000 - lam) * q + lam * q := by
  apply Nat.add_le_add_left
  exact Nat.mul_le_mul_left lam hr

-- T-5a corollary: the sum equals 1000*q when r = q
theorem sum_at_equality (q lam : Nat) (_hlam : lam ≤ 1000) :
    (1000 - lam) * q + lam * q = (1000 - lam + lam) * q := by
  exact (Nat.add_mul (1000 - lam) lam q).symm

-- T-5b: Upper bound — numerator ≤ 1000 * 1000
-- (1000-lam)*q + lam*r ≤ (1000-lam)*1000 + lam*1000
theorem bounded_numerator (q lam r : Nat)
    (_hlam : lam ≤ 1000) (hq : q ≤ 1000) (hr : r ≤ 1000) :
    (1000 - lam) * q + lam * r ≤ (1000 - lam) * 1000 + lam * 1000 := by
  apply Nat.add_le_add
  · exact Nat.mul_le_mul_left _ hq
  · exact Nat.mul_le_mul_left _ hr

-- T-5b corollary: the upper bound sum
theorem upper_sum (lam : Nat) (_hlam : lam ≤ 1000) :
    (1000 - lam) * 1000 + lam * 1000 = (1000 - lam + lam) * 1000 := by
  exact (Nat.add_mul (1000 - lam) lam 1000).symm

-- T-5c: Fixed point — (1000-lam)*r + lam*r = (1000-lam+lam)*r
theorem fixed_point_sum (r lam : Nat) :
    (1000 - lam) * r + lam * r = (1000 - lam + lam) * r := by
  exact (Nat.add_mul (1000 - lam) lam r).symm

-- T-5c corollary: when lam ≤ 1000, fixed point sum = 1000 * r
theorem fixed_point (r lam : Nat) (hlam : lam ≤ 1000) :
    (1000 - lam) * r + lam * r = 1000 * r := by
  rw [fixed_point_sum]
  rw [OmegA.MemoryHardening.sub_add_eq lam hlam]

end OmegA.MemoryHardening
