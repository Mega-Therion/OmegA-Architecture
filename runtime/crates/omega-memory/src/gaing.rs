//! Read-only [`MemoryStore`] adapter that queries the gAIng Supabase project's
//! `memories` table via the REST API.
//!
//! This store is **secondary / read-only**.  Writes, reads-by-id, and deletes
//! are no-ops.  Only `search()` is implemented and it falls back gracefully if
//! the gAIng project is unreachable.
//!
//! # Schema (gAIng `memories` table)
//!
//! ```sql
//! id          uuid primary key
//! owner_id    text
//! user_id     text
//! content     text
//! tags        text[]
//! created_at  timestamptz
//! ```

use async_trait::async_trait;
use reqwest::Client;
use serde::Deserialize;

use omega_core::{
    memory::{MemoryEntry, MemoryId, MemoryStore, MemoryWriteResult},
    MemoryError,
};

// ---------------------------------------------------------------------------
// Row type — maps the gAIng `memories` REST response
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct GaingMemoryRow {
    id: String,
    content: String,
    #[serde(default)]
    tags: Option<serde_json::Value>,
    created_at: Option<String>,
}

impl From<GaingMemoryRow> for MemoryEntry {
    fn from(row: GaingMemoryRow) -> Self {
        MemoryEntry {
            id: Some(MemoryId::new(row.id)),
            content: row.content,
            source: "gaing".to_string(),
            importance: 0.5,
            created_at: row.created_at,
            namespace: "gaing".to_string(),
            tags: match row.tags {
                Some(serde_json::Value::Array(arr)) => arr
                    .into_iter()
                    .filter_map(|v| v.as_str().map(|s| s.to_string()))
                    .collect(),
                _ => vec![],
            },
            domain: Default::default(),
            confidence: 0.8,
            version: 1,
            superseded_by: None,
            key: None,
            raw_artifact: None,
            tier: None,
        }
    }
}

// ---------------------------------------------------------------------------
// GaingRestMemoryStore
// ---------------------------------------------------------------------------

/// Read-only memory store backed by the gAIng Supabase project REST API.
pub struct GaingRestMemoryStore {
    client: Client,
    base_url: String,
    /// Supabase service-role JWT.
    api_key: String,
}

impl GaingRestMemoryStore {
    /// Construct a new store.
    ///
    /// `base_url` should be the Supabase project URL, e.g.
    /// `https://sgvitxezqrjgjmduoool.supabase.co`.
    pub fn new(base_url: impl Into<String>, api_key: impl Into<String>) -> Self {
        let client = Client::builder()
            .timeout(std::time::Duration::from_secs(8))
            .build()
            .expect("reqwest client build should not fail");
        Self {
            client,
            base_url: base_url.into().trim_end_matches('/').to_string(),
            api_key: api_key.into(),
        }
    }
}

// ---------------------------------------------------------------------------
// MemoryStore impl (read-only — write/read/delete are deliberate no-ops)
// ---------------------------------------------------------------------------

#[async_trait]
impl MemoryStore for GaingRestMemoryStore {
    /// No-op. gAIng is a read-only secondary source.
    async fn write(&self, entry: MemoryEntry) -> Result<MemoryWriteResult, MemoryError> {
        Ok(MemoryWriteResult::Written(entry.id.unwrap_or_else(|| {
            MemoryId::new(uuid::Uuid::new_v4().to_string())
        })))
    }

    /// Always returns `None`. Use `search()` for gAIng lookups.
    async fn read(&self, _id: &MemoryId) -> Result<Option<MemoryEntry>, MemoryError> {
        Ok(None)
    }

    /// No-op.
    async fn delete(&self, _id: &MemoryId) -> Result<bool, MemoryError> {
        Ok(false)
    }

    /// Full-text search against the gAIng `memories` table using ILIKE.
    ///
    /// Falls back to an empty result on any network or parse error so the
    /// federated store degrades gracefully rather than failing the whole
    /// chat request.
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let url = format!("{}/rest/v1/memories", self.base_url);
        let ilike_pattern = format!("*{}*", query);

        let result = self
            .client
            .get(&url)
            .header("apikey", &self.api_key)
            .header("Authorization", format!("Bearer {}", self.api_key))
            .query(&[
                ("select", "id,content,tags,created_at"),
                ("content", &format!("ilike.{}", ilike_pattern)),
                ("limit", &limit.to_string()),
                ("order", "created_at.desc"),
            ])
            .send()
            .await;

        match result {
            Err(e) => {
                tracing::warn!(error = %e, "gAIng memory search failed (network)");
                Ok(vec![])
            }
            Ok(resp) if !resp.status().is_success() => {
                tracing::warn!(status = %resp.status(), "gAIng memory search returned error");
                Ok(vec![])
            }
            Ok(resp) => match resp.json::<Vec<GaingMemoryRow>>().await {
                Err(e) => {
                    tracing::warn!(error = %e, "gAIng memory search parse error");
                    Ok(vec![])
                }
                Ok(rows) => {
                    let entries = rows.into_iter().map(MemoryEntry::from).collect();
                    Ok(entries)
                }
            },
        }
    }

    async fn get_random(&self, _limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        Ok(vec![])
    }
}
