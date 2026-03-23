//! [`FederatedMemoryStore`] — wraps a primary and a secondary [`MemoryStore`]
//! so OmegA can search both the sovereign Supabase project and the gAIng project
//! in a single call.
//!
//! # Write policy
//! All writes, reads-by-id, and deletes are **delegated to the primary only**.
//! The secondary (gAIng) is never mutated by the gateway.
//!
//! # Search policy
//! Both stores are queried **in parallel** via `tokio::join!`.  Results are
//! merged, deduplicated by content hash (first 64 chars), and truncated to
//! the requested `limit`.  Primary results always appear first in the merged
//! list so sovereign memory takes precedence when there are ties.

use std::sync::Arc;

use async_trait::async_trait;
use std::collections::HashSet;

use omega_core::{
    memory::{MemoryEntry, MemoryId, MemoryStore, MemoryWriteResult},
    MemoryError,
};

/// Federated memory store: primary for writes, both for reads/search.
pub struct FederatedMemoryStore {
    primary: Arc<dyn MemoryStore>,
    secondary: Arc<dyn MemoryStore>,
}

impl FederatedMemoryStore {
    pub fn new(primary: Arc<dyn MemoryStore>, secondary: Arc<dyn MemoryStore>) -> Self {
        Self { primary, secondary }
    }
}

#[async_trait]
impl MemoryStore for FederatedMemoryStore {
    /// Delegates to primary only.
    async fn write(&self, entry: MemoryEntry) -> Result<MemoryWriteResult, MemoryError> {
        self.primary.write(entry).await
    }

    /// Checks primary, then secondary.
    async fn read(&self, id: &MemoryId) -> Result<Option<MemoryEntry>, MemoryError> {
        if let Some(entry) = self.primary.read(id).await? {
            return Ok(Some(entry));
        }
        self.secondary.read(id).await
    }

    /// Delegates to primary only.
    async fn delete(&self, id: &MemoryId) -> Result<bool, MemoryError> {
        self.primary.delete(id).await
    }

    /// Searches both stores in parallel, merges, deduplicates, returns up to `limit`.
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let (primary_res, secondary_res) = tokio::join!(
            self.primary.search(query, limit),
            self.secondary.search(query, limit),
        );

        let mut seen: HashSet<String> = HashSet::new();
        let mut merged: Vec<MemoryEntry> = Vec::with_capacity(limit * 2);

        // Primary results first — sovereign memory takes precedence.
        let primary_hits = primary_res.unwrap_or_default();
        for entry in primary_hits {
            let key = entry.content.chars().take(64).collect::<String>();
            if seen.insert(key) {
                merged.push(entry);
            }
        }

        // Secondary (gAIng) results fill remaining slots.
        let secondary_hits = secondary_res.unwrap_or_default();
        for entry in secondary_hits {
            if merged.len() >= limit {
                break;
            }
            let key = entry.content.chars().take(64).collect::<String>();
            if seen.insert(key) {
                merged.push(entry);
            }
        }

        Ok(merged)
    }

    async fn get_random(&self, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        self.primary.get_random(limit).await
    }
}
