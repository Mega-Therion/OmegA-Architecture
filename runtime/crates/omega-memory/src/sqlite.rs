//! SQLite-backed [`MemoryStore`] implementation.
//!
//! Uses `sqlx` with the `sqlite` feature.  All queries are prepared and
//! type-safe.  The schema is applied via an embedded migration (see
//! `migrations/0001_initial.sql`).
//!
//! # Semantic Search (feature: `semantic-search`)
//!
//! When compiled with `--features semantic-search`, `write()` computes a 384-dim
//! embedding via `fastembed` (all-MiniLM-L6-v2) and stores it in the `embedding`
//! BLOB column.  `search()` then uses cosine similarity to rank results.
//!
//! Rows without an embedding (inserted before the feature was enabled, or when
//! the feature is disabled) are included via a LIKE-based fallback so that no
//! data is silently excluded.
//!
//! When the crate is built *without* the `semantic-search` feature, all behaviour
//! is identical to the Week 2 implementation (LIKE keyword search only).

use async_trait::async_trait;
use chrono::Utc;
use sqlx::{migrate::Migrator, Row, SqlitePool};
use std::path::Path;
use std::time::Duration;
use uuid::Uuid;

use omega_core::{
    economy::{EconomyError, NeuroCreditStore, Transaction, TransactionType, Wallet},
    memory::{MemoryDomain, MemoryEntry, MemoryId, MemoryStore, MemoryWriteResult},
    MemoryError,
};

use crate::error::MemoryStoreError;

// Embed migrations from the crate's migrations/ directory at compile time.
static MIGRATOR: Migrator = sqlx::migrate!();

// ---------------------------------------------------------------------------
// f32 ↔ bytes helpers (little-endian packed)
// ---------------------------------------------------------------------------

fn embed_to_bytes(v: &[f32]) -> Vec<u8> {
    v.iter().flat_map(|f| f.to_le_bytes()).collect()
}

fn bytes_to_embed(b: &[u8]) -> Vec<f32> {
    b.chunks_exact(4)
        .map(|c| f32::from_le_bytes(c.try_into().unwrap()))
        .collect()
}

// ---------------------------------------------------------------------------
// Cosine similarity
// ---------------------------------------------------------------------------

/// Compute cosine similarity between two equal-length vectors.
/// Returns 0.0 if either vector has zero norm (avoids division by zero).
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    dot / (norm_a * norm_b)
}

// ---------------------------------------------------------------------------
// Store struct
// ---------------------------------------------------------------------------

/// SQLite-backed memory store.
///
/// Construct with [`SqliteMemoryStore::new`], then call [`SqliteMemoryStore::migrate`]
/// before first use so the schema is guaranteed to exist.
pub struct SqliteMemoryStore {
    pool: SqlitePool,
    /// Embedding model — only present when `semantic-search` feature is active.
    #[cfg(feature = "semantic-search")]
    embedder: std::sync::Arc<fastembed::TextEmbedding>,
}

impl SqliteMemoryStore {
    /// Open (or create) the SQLite database at `db_url`.
    ///
    /// `db_url` must be a valid SQLite connection string accepted by `sqlx`,
    /// e.g. `"sqlite:///home/mega/.omega/memory.db"` or `"sqlite::memory:"`.
    pub async fn new(db_url: &str) -> Result<Self, MemoryStoreError> {
        // Ensure the parent directory exists when the URL points to a file.
        if let Some(path_str) = db_url.strip_prefix("sqlite://") {
            let path_str = path_str.trim_start_matches('/');
            if !path_str.is_empty() && path_str != ":memory:" {
                let abs = if db_url.starts_with("sqlite:///") {
                    format!("/{path_str}")
                } else {
                    path_str.to_string()
                };
                if let Some(parent) = Path::new(&abs).parent() {
                    if !parent.as_os_str().is_empty() {
                        std::fs::create_dir_all(parent).ok();
                    }
                }
            }
        }

        let pool = SqlitePool::connect(db_url).await?;

        // Initialise the embedding model when the feature is enabled.
        #[cfg(feature = "semantic-search")]
        let embedder = {
            use fastembed::{EmbeddingModel, InitOptions, TextEmbedding};
            let model = TextEmbedding::try_new(InitOptions::new(EmbeddingModel::AllMiniLML6V2))
                .map_err(|e| MemoryStoreError::Embedding(e.to_string()))?;
            std::sync::Arc::new(model)
        };

        Ok(Self {
            pool,
            #[cfg(feature = "semantic-search")]
            embedder,
        })
    }

    /// Apply all pending migrations.  Safe to call on every startup — sqlx
    /// tracks which migrations have already run and is idempotent.
    pub async fn migrate(&self) -> Result<(), MemoryStoreError> {
        MIGRATOR.run(&self.pool).await?;
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Internal embedding helper
    // -----------------------------------------------------------------------

    /// Compute a single embedding vector for `text`.
    /// Returns `None` when the `semantic-search` feature is disabled.
    #[allow(unused_variables)]
    fn compute_embedding(&self, text: &str) -> Option<Vec<f32>> {
        #[cfg(feature = "semantic-search")]
        {
            match self.embedder.embed(vec![text.to_string()], None) {
                Ok(mut vecs) if !vecs.is_empty() => Some(vecs.remove(0)),
                Ok(_) => None,
                Err(e) => {
                    tracing::warn!(error = %e, "embedding failed — falling back to keyword search");
                    None
                }
            }
        }
        #[cfg(not(feature = "semantic-search"))]
        {
            None
        }
    }

    // -----------------------------------------------------------------------
    // Importance decay background task
    // -----------------------------------------------------------------------

    /// Spawn a background Tokio task that applies importance decay every `interval`.
    ///
    /// Each tick multiplies every row's importance by `decay_factor`.
    /// Rows whose importance falls below `min_importance` are deleted.
    ///
    /// The returned `JoinHandle` should be kept alive for the lifetime of the
    /// process (typically assigned to a `_decay_handle` in `main`).
    pub fn spawn_decay_task(
        &self,
        interval: Duration,
        decay_factor: f64,
        min_importance: f64,
    ) -> tokio::task::JoinHandle<()> {
        let pool = self.pool.clone();
        tokio::spawn(async move {
            let mut ticker = tokio::time::interval(interval);
            loop {
                ticker.tick().await;

                // Apply multiplicative decay to all rows.
                let _ = sqlx::query("UPDATE memory_entries SET importance = importance * ?1")
                    .bind(decay_factor)
                    .execute(&pool)
                    .await;

                // Prune rows below the minimum threshold.
                let pruned = sqlx::query("DELETE FROM memory_entries WHERE importance < ?1")
                    .bind(min_importance)
                    .execute(&pool)
                    .await
                    .map(|r| r.rows_affected())
                    .unwrap_or(0);

                if pruned > 0 {
                    tracing::info!(pruned, "importance decay pruned low-importance entries");
                }
            }
        })
    }
}

// ---------------------------------------------------------------------------
// MemoryStore trait impl
// ---------------------------------------------------------------------------

#[async_trait]
impl MemoryStore for SqliteMemoryStore {
    /// Persist a [`MemoryEntry`].
    ///
    /// If `entry.id` is `None` a new UUID v4 is generated.
    /// When the `semantic-search` feature is enabled, an embedding is computed
    /// and stored alongside the content.
    async fn write(&self, entry: MemoryEntry) -> Result<MemoryWriteResult, MemoryError> {
        let id_str = entry
            .id
            .as_ref()
            .map(|m| m.0.clone())
            .unwrap_or_else(|| Uuid::new_v4().to_string());

        let threshold = std::env::var("OMEGA_MEMORY_CONTRADICTION_THRESHOLD")
            .ok()
            .and_then(|v| v.parse::<f32>().ok())
            .unwrap_or(0.85);

        let created_at = entry.created_at.unwrap_or_else(|| Utc::now().to_rfc3339());

        // Compute embedding (None when feature disabled or on error).
        let embedding_bytes: Option<Vec<u8>> = self
            .compute_embedding(&entry.content)
            .map(|v| embed_to_bytes(&v));

        let mut contradiction_found = false;
        let mut conflicting_ids: Vec<MemoryId> = Vec::new();
        let mut conflicting_contents: Vec<String> = Vec::new();
        let mut max_similarity = 0.0_f32;

        #[cfg(feature = "semantic-search")]
        if let Some(ref e_bytes) = embedding_bytes {
            // Check for contradictions
            let rows = sqlx::query(
                r#"
                SELECT id, content, embedding
                FROM memory_entries
                WHERE namespace = ?1 AND id != ?2 AND embedding IS NOT NULL
                "#,
            )
            .bind(&entry.namespace)
            .bind(&id_str)
            .fetch_all(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;

            let query_emb = bytes_to_embed(e_bytes);

            let mut scored: Vec<(f32, String, String)> = rows
                .iter()
                .filter_map(|r| {
                    let blob: Vec<u8> = r.try_get("embedding").ok()?;
                    let entry_emb = bytes_to_embed(&blob);
                    let sim = cosine_similarity(&query_emb, &entry_emb);
                    if sim > threshold {
                        Some((
                            sim,
                            r.try_get("id").unwrap_or_default(),
                            r.try_get("content").unwrap_or_default(),
                        ))
                    } else {
                        None
                    }
                })
                .collect();

            scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

            for (sim, row_id, content) in scored.into_iter().take(5) {
                contradiction_found = true;
                conflicting_ids.push(MemoryId::new(row_id));
                conflicting_contents.push(content);
                if sim > max_similarity {
                    max_similarity = sim;
                }
            }
        }

        // Key-based supersession: if entry.key is Some and an active entry with
        // that key already exists, mark it as superseded by the new id and derive
        // the new version number from the old one.
        let mut new_version = entry.version;
        if let Some(ref key_val) = entry.key {
            let existing = sqlx::query(
                r#"
                SELECT id, version FROM memory_entries
                WHERE namespace = ?1 AND key = ?2 AND superseded_by IS NULL
                LIMIT 1
                "#,
            )
            .bind(&entry.namespace)
            .bind(key_val)
            .fetch_optional(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;

            if let Some(row) = existing {
                let old_id: String = row.try_get("id").unwrap_or_default();
                let old_version: i64 = row.try_get("version").unwrap_or(1);
                new_version = (old_version as u32).saturating_add(1);

                sqlx::query("UPDATE memory_entries SET superseded_by = ?1 WHERE id = ?2")
                    .bind(&id_str)
                    .bind(&old_id)
                    .execute(&self.pool)
                    .await
                    .map_err(MemoryStoreError::Sqlx)?;
            }
        }

        let domain_str = serde_json::to_string(&entry.domain)
            .unwrap_or_default()
            .trim_matches('"')
            .to_string();

        sqlx::query(
            r#"
            INSERT INTO memory_entries
                (id, content, source, importance, created_at, namespace, embedding,
                 domain, confidence, version, superseded_by, key, raw_artifact, tier)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14)
            ON CONFLICT(id) DO UPDATE SET
                content       = excluded.content,
                source        = excluded.source,
                importance    = excluded.importance,
                created_at    = excluded.created_at,
                namespace     = excluded.namespace,
                embedding     = excluded.embedding,
                domain        = excluded.domain,
                confidence    = excluded.confidence,
                version       = excluded.version,
                superseded_by = excluded.superseded_by,
                key           = excluded.key,
                raw_artifact  = excluded.raw_artifact,
                tier          = excluded.tier
            "#,
        )
        .bind(&id_str)
        .bind(&entry.content)
        .bind(&entry.source)
        .bind(entry.importance)
        .bind(&created_at)
        .bind(&entry.namespace)
        .bind(embedding_bytes.as_deref())
        .bind(&domain_str)
        .bind(entry.confidence)
        .bind(new_version as i64)
        .bind(&entry.superseded_by)
        .bind(&entry.key)
        .bind(&entry.raw_artifact)
        .bind(&entry.tier)
        .execute(&self.pool)
        .await
        .map_err(MemoryStoreError::Sqlx)?;

        tracing::debug!(id = %id_str, namespace = %entry.namespace, contradiction = %contradiction_found, "memory entry written");

        if contradiction_found {
            Ok(MemoryWriteResult::Contradiction {
                new_id: MemoryId::new(id_str),
                conflicting_ids,
                conflicting_contents,
                similarity: max_similarity,
            })
        } else {
            Ok(MemoryWriteResult::Written(MemoryId::new(id_str)))
        }
    }

    /// Retrieve a single entry by its [`MemoryId`].
    async fn read(&self, id: &MemoryId) -> Result<Option<MemoryEntry>, MemoryError> {
        let row = sqlx::query(
            "SELECT id, content, source, importance, created_at, namespace, \
             domain, confidence, version, superseded_by, key, raw_artifact, tier \
             FROM memory_entries WHERE id = ?1",
        )
        .bind(&id.0)
        .fetch_optional(&self.pool)
        .await
        .map_err(MemoryStoreError::Sqlx)?;

        match row {
            None => Ok(None),
            Some(r) => Ok(Some(row_to_entry(&r))),
        }
    }

    /// Delete a single entry by its [`MemoryId`].
    async fn delete(&self, id: &MemoryId) -> Result<bool, MemoryError> {
        let result = sqlx::query("DELETE FROM memory_entries WHERE id = ?1")
            .bind(&id.0)
            .execute(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;

        let deleted = result.rows_affected() > 0;
        if deleted {
            tracing::debug!(id = %id.0, "memory entry deleted");
        }
        Ok(deleted)
    }

    /// Search memory entries.
    ///
    /// When `semantic-search` is enabled and a query embedding can be computed:
    /// - Fetches all rows that have stored embeddings and ranks by cosine similarity.
    /// - Also includes rows without embeddings via LIKE fallback (deduped by id).
    /// - Returns top `limit` results sorted by similarity DESC.
    ///
    /// When `semantic-search` is disabled (or embedding fails):
    /// - Falls back to `content LIKE '%query%'` ordered by importance DESC.
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let query_embedding = self.compute_embedding(query);

        if let Some(ref q_emb) = query_embedding {
            // --- Semantic path: fetch rows with embeddings, rank by cosine sim ---
            let rows = sqlx::query(
                r#"
                SELECT id, content, source, importance, created_at, namespace, embedding,
                       domain, confidence, version, superseded_by, key, raw_artifact, tier
                FROM memory_entries
                WHERE embedding IS NOT NULL
                "#,
            )
            .fetch_all(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;

            let mut scored: Vec<(f32, MemoryEntry)> = rows
                .iter()
                .filter_map(|r| {
                    let blob: Vec<u8> = r.try_get("embedding").ok()?;
                    let entry_emb = bytes_to_embed(&blob);
                    let sim = cosine_similarity(q_emb, &entry_emb);
                    Some((sim, row_to_entry(r)))
                })
                .collect();

            // Sort descending by similarity.
            scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));

            // Collect ids of entries already ranked.
            let ranked_ids: std::collections::HashSet<String> = scored
                .iter()
                .filter_map(|(_, e)| e.id.as_ref().map(|i| i.0.clone()))
                .collect();

            // LIKE fallback for rows that have no embedding.
            let pattern = format!("%{}%", query);
            let fallback_rows = sqlx::query(
                r#"
                SELECT id, content, source, importance, created_at, namespace,
                       domain, confidence, version, superseded_by, key, raw_artifact, tier
                FROM memory_entries
                WHERE embedding IS NULL AND content LIKE ?1
                ORDER BY importance DESC
                "#,
            )
            .bind(&pattern)
            .fetch_all(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;

            // Merge: semantic results first, then fallback (that aren't already included).
            let mut results: Vec<MemoryEntry> = scored
                .into_iter()
                .map(|(_, e)| e)
                .chain(fallback_rows.iter().map(row_to_entry).filter(|e| {
                    e.id.as_ref()
                        .map(|i| !ranked_ids.contains(&i.0))
                        .unwrap_or(true)
                }))
                .take(limit)
                .collect();

            results.truncate(limit);
            return Ok(results);
        }

        // --- Keyword fallback (no embedding available) ---
        let pattern = format!("%{}%", query);
        let limit_i64 = limit as i64;

        let rows = sqlx::query(
            r#"
            SELECT id, content, source, importance, created_at, namespace,
                   domain, confidence, version, superseded_by, key, raw_artifact, tier
            FROM memory_entries
            WHERE content LIKE ?1
            ORDER BY importance DESC
            LIMIT ?2
            "#,
        )
        .bind(&pattern)
        .bind(limit_i64)
        .fetch_all(&self.pool)
        .await
        .map_err(MemoryStoreError::Sqlx)?;

        Ok(rows.iter().map(row_to_entry).collect())
    }

    /// Fetch random memories (used for background Dream State reflection).
    async fn get_random(&self, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let limit_i64 = limit as i64;
        let rows = sqlx::query(
            "SELECT id, content, source, importance, created_at, namespace \
             FROM omega_memory_entries ORDER BY RANDOM() LIMIT $1",
        )
        .bind(limit_i64)
        .fetch_all(&self.pool)
        .await
        .map_err(MemoryStoreError::Sqlx)?;

        let entries = rows
            .into_iter()
            .map(|r| MemoryEntry {
                id: Some(MemoryId::new(
                    r.try_get::<String, _>("id").unwrap_or_default(),
                )),
                content: r.try_get("content").unwrap_or_default(),
                source: r
                    .try_get::<String, _>("source")
                    .unwrap_or_else(|_| "chat".to_string()),
                importance: r.try_get::<f64, _>("importance").unwrap_or(0.5),
                created_at: r.try_get::<Option<String>, _>("created_at").unwrap_or(None),
                namespace: r
                    .try_get::<String, _>("namespace")
                    .unwrap_or_else(|_| "default".to_string()),
                tags: vec![],
                domain: Default::default(),
                confidence: 1.0,
                version: 1,
                superseded_by: None,
                key: None,
                raw_artifact: None,
                tier: None,
            })
            .collect();

        Ok(entries)
    }
}

#[async_trait]
impl NeuroCreditStore for SqliteMemoryStore {
    async fn init_wallet(
        &self,
        agent_id: &str,
        start_balance: f32,
    ) -> Result<Wallet, EconomyError> {
        let existing = self.get_wallet(agent_id).await;
        if existing.is_ok() {
            return existing;
        }

        let now = Utc::now().to_rfc3339();

        sqlx::query(
            "INSERT INTO agent_wallets (agent_id, balance, total_earned, total_spent, is_bankrupt, updated_at) \
             VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (agent_id) DO NOTHING"
        )
        .bind(agent_id)
        .bind(start_balance)
        .bind(0.0)
        .bind(0.0)
        .bind(false)
        .bind(&now)
        .execute(&self.pool)
        .await
        .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

        self.get_wallet(agent_id).await
    }

    async fn get_wallet(&self, agent_id: &str) -> Result<Wallet, EconomyError> {
        let row = sqlx::query(
            "SELECT agent_id, balance, total_earned, total_spent, is_bankrupt, updated_at \
             FROM agent_wallets WHERE agent_id = $1",
        )
        .bind(agent_id)
        .fetch_optional(&self.pool)
        .await
        .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

        match row {
            Some(r) => Ok(Wallet {
                agent_id: r.try_get("agent_id").unwrap_or_default(),
                balance: r.try_get("balance").unwrap_or(0.0),
                total_earned: r.try_get("total_earned").unwrap_or(0.0),
                total_spent: r.try_get("total_spent").unwrap_or(0.0),
                is_bankrupt: r.try_get("is_bankrupt").unwrap_or(false),
                updated_at: r.try_get::<String, _>("updated_at").unwrap_or_default(),
            }),
            None => Err(EconomyError::WalletNotFound(agent_id.to_string())),
        }
    }

    async fn record_transaction(
        &self,
        agent_id: &str,
        amount: f32,
        tx_type: TransactionType,
        description: &str,
    ) -> Result<Transaction, EconomyError> {
        let wallet = self.get_wallet(agent_id).await?;

        let is_debit = matches!(tx_type, TransactionType::Spend | TransactionType::Fine);
        let new_balance = if is_debit {
            wallet.balance - amount
        } else {
            wallet.balance + amount
        };

        if new_balance < 0.0 {
            // Mark bankrupt
            sqlx::query(
                "UPDATE agent_wallets SET is_bankrupt = 1, balance = 0 WHERE agent_id = $1",
            )
            .bind(agent_id)
            .execute(&self.pool)
            .await
            .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

            return Err(EconomyError::InsufficientBalance {
                need: amount,
                have: wallet.balance,
            });
        }

        let now = Utc::now().to_rfc3339();

        // Update wallet balance
        let earned_delta = if is_debit { 0.0 } else { amount };
        let spent_delta = if is_debit { amount } else { 0.0 };

        sqlx::query(
            "UPDATE agent_wallets SET \
             balance = $1, \
             total_earned = total_earned + $2, \
             total_spent = total_spent + $3, \
             updated_at = $4 \
             WHERE agent_id = $5",
        )
        .bind(new_balance)
        .bind(earned_delta)
        .bind(spent_delta)
        .bind(&now)
        .bind(agent_id)
        .execute(&self.pool)
        .await
        .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

        // Log to financial_ledger
        let tx_type_str = serde_json::to_string(&tx_type)
            .unwrap_or_default()
            .trim_matches('"')
            .to_string();

        let row = sqlx::query(
            "INSERT INTO financial_ledger (agent_id, amount, transaction_type, description, balance_after, created_at) \
             VALUES ($1, $2, $3, $4, $5, $6) RETURNING id"
        )
        .bind(agent_id)
        .bind(amount)
        .bind(&tx_type_str)
        .bind(description)
        .bind(new_balance)
        .bind(&now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

        let tx_id: i64 = row.try_get("id").unwrap_or(0);

        Ok(Transaction {
            id: Some(tx_id as u64),
            agent_id: agent_id.to_string(),
            amount,
            transaction_type: tx_type,
            description: description.to_string(),
            balance_after: new_balance,
            created_at: now,
        })
    }
}

// ---------------------------------------------------------------------------
// Row mapping helper
// ---------------------------------------------------------------------------

fn row_to_entry(r: &sqlx::sqlite::SqliteRow) -> MemoryEntry {
    // Parse the domain string back into the enum; fall back to Operational on any error.
    let domain_str: String = r
        .try_get::<String, _>("domain")
        .unwrap_or_else(|_| "operational".to_string());
    let domain: MemoryDomain =
        serde_json::from_str(&format!("\"{domain_str}\"")).unwrap_or_default();

    MemoryEntry {
        id: Some(MemoryId::new(
            r.try_get::<String, _>("id").unwrap_or_default(),
        )),
        content: r.try_get("content").unwrap_or_default(),
        source: r
            .try_get::<String, _>("source")
            .unwrap_or_else(|_| "chat".to_string()),
        importance: r.try_get::<f64, _>("importance").unwrap_or(0.5),
        created_at: r.try_get::<Option<String>, _>("created_at").unwrap_or(None),
        namespace: r
            .try_get::<String, _>("namespace")
            .unwrap_or_else(|_| "default".to_string()),
        tags: vec![],
        domain,
        confidence: r.try_get::<f64, _>("confidence").unwrap_or(1.0) as f32,
        version: r.try_get::<i64, _>("version").unwrap_or(1) as u32,
        superseded_by: r
            .try_get::<Option<String>, _>("superseded_by")
            .unwrap_or(None),
        key: r.try_get::<Option<String>, _>("key").unwrap_or(None),
        raw_artifact: r
            .try_get::<Option<String>, _>("raw_artifact")
            .unwrap_or(None),
        tier: r.try_get::<Option<String>, _>("tier").unwrap_or(None),
    }
}

#[cfg(test)]
mod tests {
    use super::SqliteMemoryStore;
    use omega_core::memory::MemoryStore;

    #[tokio::test]
    async fn search_includes_rows_with_null_embedding() {
        let store = SqliteMemoryStore::new("sqlite::memory:").await.unwrap();
        store.migrate().await.unwrap();

        // Insert a legacy row with NULL embedding (simulates rows created before
        // the Week 4 migration/feature).
        sqlx::query(
            r#"
            INSERT INTO memory_entries (id, content, source, importance, created_at, namespace, embedding)
            VALUES (?1, ?2, ?3, ?4, ?5, ?6, NULL)
            "#,
        )
        .bind("legacy-row")
        .bind("legacy keyword hit")
        .bind("test")
        .bind(0.5_f64)
        .bind("2026-01-01T00:00:00Z")
        .bind("default")
        .execute(&store.pool)
        .await
        .unwrap();

        let hits = store.search("keyword", 10).await.unwrap();
        assert!(
            hits.iter()
                .any(|e| e.id.as_ref().is_some_and(|i| i.0 == "legacy-row")),
            "expected legacy row to be returned by LIKE fallback"
        );
    }
}
