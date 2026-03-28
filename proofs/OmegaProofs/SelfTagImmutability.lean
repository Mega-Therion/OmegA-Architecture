/-
  T-9: Self-Tag Immutability

  Formal statement:
    The self-tag log S_t is append-only. For all t1 < t2,
    S_t1 is a prefix of S_t2. No entry can be modified or
    deleted after creation.

  We model the self-tag log as a List with an append operation
  and prove structural properties: prefix preservation,
  genesis immutability, historical entry immutability,
  length monotonicity, and multi-append prefix stability.
-/

namespace OmegA.SelfTagImmutability

-- The append-only operation: add one entry to the end of the chain
def append_entry (chain : List α) (entry : α) : List α :=
  chain ++ [entry]

-- Prefix relation: l₁ is a prefix of l₂ iff ∃ t, l₂ = l₁ ++ t
def IsPrefix (l₁ l₂ : List α) : Prop :=
  ∃ t, l₂ = l₁ ++ t

/-
  T-9a: Prefix preserved under append.
  For any chain and entry, chain is a prefix of (append_entry chain entry).
-/
theorem prefix_preserved (chain : List α) (entry : α) :
    IsPrefix chain (append_entry chain entry) :=
  ⟨[entry], rfl⟩

/-
  T-9b: Genesis immutable.
  The first element of the chain is unchanged after appending.
-/
theorem append_entry_ne_nil (chain : List α) (entry : α) :
    append_entry chain entry ≠ [] := by
  unfold append_entry
  simp

theorem genesis_immutable (chain : List α) (entry : α) (h : chain ≠ []) :
    (append_entry chain entry).head (append_entry_ne_nil chain entry) =
    chain.head h := by
  unfold append_entry
  cases chain with
  | nil => exact absurd rfl h
  | cons x xs => simp

/-
  T-9c: Historical entries unchanged (core immutability theorem).
  For all i < chain.length, the i-th element of the appended chain
  equals the i-th element of the original chain.
-/
theorem historical_entries_unchanged (chain : List α) (entry : α)
    (i : Nat) (hi : i < chain.length) :
    (append_entry chain entry)[i]'(by
      unfold append_entry
      simp [List.length_append]
      omega) =
    chain[i] := by
  unfold append_entry
  simp [List.getElem_append_left hi]

/-
  T-9d: Length monotonic.
  Appending an entry strictly increases the chain length.
-/
theorem length_monotonic (chain : List α) (entry : α) :
    (append_entry chain entry).length > chain.length := by
  unfold append_entry
  simp [List.length_append]

/-
  T-9e: Multi-append prefix.
  After applying n appends via a sequence of entries, the original
  chain is still a prefix of the result. Proved by induction.
-/
def multi_append (chain : List α) (entries : List α) : List α :=
  chain ++ entries

theorem multi_append_prefix (chain : List α) (entries : List α) :
    IsPrefix chain (multi_append chain entries) :=
  ⟨entries, rfl⟩

-- Stronger form: induction over individual appends
def append_n (chain : List α) (f : Nat → α) : Nat → List α
  | 0     => chain
  | n + 1 => append_entry (append_n chain f n) (f n)

theorem multi_append_prefix_inductive (chain : List α) (f : Nat → α) (n : Nat) :
    IsPrefix chain (append_n chain f n) := by
  induction n with
  | zero =>
    exact ⟨[], by simp [append_n]⟩
  | succ k ih =>
    obtain ⟨t, ht⟩ := ih
    exact ⟨t ++ [f k], by simp [append_n, append_entry, ht, List.append_assoc]⟩

/-
  T-9f: Monotonic length under iterated appends.
  After n appends, the length equals original + n.
-/
theorem append_n_length (chain : List α) (f : Nat → α) (n : Nat) :
    (append_n chain f n).length = chain.length + n := by
  induction n with
  | zero => simp [append_n]
  | succ k ih =>
    simp [append_n, append_entry, List.length_append, ih]
    omega

/-
  T-9g: Transitivity of prefix.
  If chain₁ is a prefix of chain₂ and chain₂ is a prefix of chain₃,
  then chain₁ is a prefix of chain₃.
-/
theorem prefix_trans {l₁ l₂ l₃ : List α}
    (h₁ : IsPrefix l₁ l₂) (h₂ : IsPrefix l₂ l₃) :
    IsPrefix l₁ l₃ := by
  obtain ⟨t₁, ht₁⟩ := h₁
  obtain ⟨t₂, ht₂⟩ := h₂
  exact ⟨t₁ ++ t₂, by rw [ht₂, ht₁, List.append_assoc]⟩

/-
  T-9h: For all t1 < t2, S_t1 is a prefix of S_t2.
  This is the top-level immutability statement: the log at any
  earlier time is a prefix of the log at any later time.
-/
theorem log_prefix_at_earlier_time (chain : List α) (f : Nat → α)
    (t1 t2 : Nat) (hlt : t1 ≤ t2) :
    IsPrefix (append_n chain f t1) (append_n chain f t2) := by
  induction t2 with
  | zero =>
    have : t1 = 0 := Nat.eq_zero_of_le_zero hlt
    subst this
    exact ⟨[], by simp [append_n]⟩
  | succ k ih =>
    cases Nat.eq_or_lt_of_le hlt with
    | inl heq =>
      subst heq
      exact ⟨[], by simp⟩
    | inr hlt' =>
      have hle : t1 ≤ k := Nat.lt_succ_iff.mp hlt'
      have := ih hle
      exact prefix_trans this (prefix_preserved (append_n chain f k) (f k))

end OmegA.SelfTagImmutability
