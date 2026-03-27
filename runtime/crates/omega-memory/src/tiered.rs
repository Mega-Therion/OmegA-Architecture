//! Tiered memory store — routes reads/writes across short-term (Supabase) and
//! long-term (Neon) Postgres stores.
//!
//! Tiers (priority order):
//!   s1 (hot/short-term) → s2 → s3 → n1 (long-term) → n2 (archive)
//!
//! Write policy:
//!   - Route by entry.tier when set (s1/s2/s3/n1/n2, hot/warm/cold/archive).
//!   - Default to s1 when no tier is provided.
//!   - Optional promotion: if importance >= promote_threshold, also write to n1.

use std::collections::HashSet;
use std::sync::Arc;

use async_trait::async_trait;
use omega_core::memory::{MemoryEntry, MemoryId, MemoryStore, MemoryWriteResult};
use omega_core::MemoryError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TierId {
    S1,
    S2,
    S3,
    N1,
    N2,
}

impl TierId {
    fn as_str(self) -> &'static str {
        match self {
            TierId::S1 => "s1",
            TierId::S2 => "s2",
            TierId::S3 => "s3",
            TierId::N1 => "n1",
            TierId::N2 => "n2",
        }
    }
}

#[derive(Default, Clone)]
pub struct TieredMemoryConfig {
    pub s1: Option<Arc<dyn MemoryStore>>,
    pub s2: Option<Arc<dyn MemoryStore>>,
    pub s3: Option<Arc<dyn MemoryStore>>,
    pub n1: Option<Arc<dyn MemoryStore>>,
    pub n2: Option<Arc<dyn MemoryStore>>,
    pub promote_threshold: f64,
}

/// Tiered memory store with fixed priority order.
pub struct TieredMemoryStore {
    s1: Option<Arc<dyn MemoryStore>>,
    s2: Option<Arc<dyn MemoryStore>>,
    s3: Option<Arc<dyn MemoryStore>>,
    n1: Option<Arc<dyn MemoryStore>>,
    n2: Option<Arc<dyn MemoryStore>>,
    promote_threshold: f64,
}

impl TieredMemoryStore {
    pub fn new(cfg: TieredMemoryConfig) -> Self {
        Self {
            s1: cfg.s1,
            s2: cfg.s2,
            s3: cfg.s3,
            n1: cfg.n1,
            n2: cfg.n2,
            promote_threshold: if cfg.promote_threshold <= 0.0 {
                0.9
            } else {
                cfg.promote_threshold
            },
        }
    }

    fn resolve_tier(&self, tier: Option<&str>) -> TierId {
        let t = tier.unwrap_or("").trim().to_ascii_lowercase();
        match t.as_str() {
            "s1" | "hot" | "short" | "short-term" | "ram" => TierId::S1,
            "s2" | "warm" | "fresh" => TierId::S2,
            "s3" | "staging" => TierId::S3,
            "n1" | "cold" | "long" | "long-term" => TierId::N1,
            "n2" | "archive" | "immutable" | "vault" => TierId::N2,
            _ => TierId::S1,
        }
    }

    fn tier_store(&self, tier: TierId) -> Option<Arc<dyn MemoryStore>> {
        match tier {
            TierId::S1 => self.s1.clone(),
            TierId::S2 => self.s2.clone(),
            TierId::S3 => self.s3.clone(),
            TierId::N1 => self.n1.clone(),
            TierId::N2 => self.n2.clone(),
        }
    }

    fn ordered_stores(&self) -> Vec<Arc<dyn MemoryStore>> {
        [self.s1.clone(), self.s2.clone(), self.s3.clone(), self.n1.clone(), self.n2.clone()]
            .into_iter()
            .flatten()
            .collect()
    }

    fn should_promote(&self, entry: &MemoryEntry, target: TierId) -> bool {
        matches!(target, TierId::S1 | TierId::S2 | TierId::S3)
            && entry.importance >= self.promote_threshold
            && self.n1.is_some()
    }
}

#[async_trait]
impl MemoryStore for TieredMemoryStore {
    async fn write(&self, mut entry: MemoryEntry) -> Result<MemoryWriteResult, MemoryError> {
        let target = self.resolve_tier(entry.tier.as_deref());
        entry.tier = Some(target.as_str().to_string());

        let primary = self
            .tier_store(target)
            .or_else(|| self.s1.clone())
            .or_else(|| self.n1.clone())
            .ok_or_else(|| MemoryError::Write("no memory tiers configured".to_string()))?;

        let result = primary.write(entry.clone()).await?;

        if self.should_promote(&entry, target) {
            if let Some(n1) = self.n1.clone() {
                let mut promoted = entry.clone();
                promoted.tier = Some(TierId::N1.as_str().to_string());
                tokio::spawn(async move {
                    let _ = n1.write(promoted).await;
                });
            }
        }

        Ok(result)
    }

    async fn read(&self, id: &MemoryId) -> Result<Option<MemoryEntry>, MemoryError> {
        for store in self.ordered_stores() {
            if let Some(entry) = store.read(id).await? {
                return Ok(Some(entry));
            }
        }
        Ok(None)
    }

    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let s1 = self.s1.clone();
        let s2 = self.s2.clone();
        let s3 = self.s3.clone();
        let n1 = self.n1.clone();
        let n2 = self.n2.clone();

        let (r1, r2, r3, r4, r5) = tokio::join!(
            async { if let Some(s) = s1 { s.search(query, limit).await.ok() } else { Some(vec![]) } },
            async { if let Some(s) = s2 { s.search(query, limit).await.ok() } else { Some(vec![]) } },
            async { if let Some(s) = s3 { s.search(query, limit).await.ok() } else { Some(vec![]) } },
            async { if let Some(s) = n1 { s.search(query, limit).await.ok() } else { Some(vec![]) } },
            async { if let Some(s) = n2 { s.search(query, limit).await.ok() } else { Some(vec![]) } },
        );

        let mut seen: HashSet<String> = HashSet::new();
        let mut merged: Vec<MemoryEntry> = Vec::with_capacity(limit);
        for bucket in [r1, r2, r3, r4, r5] {
            if merged.len() >= limit {
                break;
            }
            let entries = bucket.unwrap_or_default();
            for entry in entries {
                if merged.len() >= limit {
                    break;
                }
                let key = entry.content.chars().take(64).collect::<String>();
                if seen.insert(key) {
                    merged.push(entry);
                }
            }
        }
        Ok(merged)
    }

    async fn delete(&self, id: &MemoryId) -> Result<bool, MemoryError> {
        let mut deleted_any = false;
        for store in self.ordered_stores() {
            match store.delete(id).await {
                Ok(true) => deleted_any = true,
                Ok(false) => {}
                Err(e) => tracing::warn!(error = %e, "tiered delete failed"),
            }
        }
        Ok(deleted_any)
    }

    async fn get_random(&self, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        for store in self.ordered_stores() {
            let hits = store.get_random(limit).await?;
            if !hits.is_empty() {
                return Ok(hits);
            }
        }
        Ok(vec![])
    }
}

