# Tiered Memory (Supabase + Neon)

This gateway supports tiered memory routing across short-term (Supabase) and long-term (Neon) Postgres stores. It also supports reinforcement-based promotion: memories referenced repeatedly get their importance boosted and can be promoted to higher tiers automatically.

## Tiers

Priority order (search):
- s1 (hot/short-term)
- s2
- s3
- n1 (long-term)
- n2 (archive)

Aliases:
- hot/short/short-term/ram => s1
- warm/fresh => s2
- staging => s3
- cold/long/long-term => n1
- archive/immutable/vault => n2

## Enable Tiered Routing

Set the tiered URLs and enable routing:

```
OMEGA_ENABLE_TIERED_MEMORY=true
OMEGA_MEMORY_S1_URL=postgresql://...
OMEGA_MEMORY_S2_URL=postgresql://...
OMEGA_MEMORY_S3_URL=postgresql://...
OMEGA_MEMORY_N1_URL=postgresql://...
OMEGA_MEMORY_N2_URL=postgresql://...
```

Notes:
- If `OMEGA_MEMORY_S1_URL` is empty, `OMEGA_DB_URL` is used for s1.
- Empty tier URLs are simply skipped.
- Writes include the `tier` column when present; older schemas without `tier` still work (tier writes are ignored).

## Reinforcement-Based Promotion

When enabled, the gateway boosts the importance of memory hits returned during chat. If the boosted importance crosses a tier threshold, the entry is written with the higher tier label.

```
OMEGA_MEMORY_REINFORCE_ENABLED=true
OMEGA_MEMORY_REINFORCE_DELTA=0.05
OMEGA_MEMORY_REINFORCE_MAX=1.0
OMEGA_MEMORY_TIER_S2_THRESHOLD=0.6
OMEGA_MEMORY_TIER_S3_THRESHOLD=0.75
OMEGA_MEMORY_TIER_N1_THRESHOLD=0.9
OMEGA_MEMORY_TIER_N2_THRESHOLD=0.97
```

Behavior:
- Only applies on memory hits during `/chat` when `use_memory` is true.
- Reinforcement is best-effort and runs async so it does not block responses.
- Higher tiers win. If the entry is already at a higher tier than the target, it is left unchanged.

## Schema

The tiered path expects a `tier` column on `omega_memory_entries` (text). The write path tolerates older schemas by skipping the tier column when it does not exist.

Example migration:

```
ALTER TABLE omega_memory_entries ADD COLUMN IF NOT EXISTS tier text;
```
