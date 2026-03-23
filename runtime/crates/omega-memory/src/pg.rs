//! Postgres + pgvector-backed [`MemoryStore`] implementation.
//!
//! Uses `sqlx` with the `postgres` feature.  The schema is managed externally
//! in the Supabase dashboard (see `docs/SUPABASE_SCHEMA.sql` or the SQL block
//! in `GEMINI_WEEK4_REPORT.md`).  No auto-migration: Supabase handles DDL.
//!
//! # Vector search
//!
//! When an embedder is attached (via `PgMemoryStore::with_embedder`), `search()`
//! uses the pgvector `<=>` cosine-distance operator:
//!
//! ```sql
//! ORDER BY embedding <=> $1::vector LIMIT $2
//! ```
//!
//! Without an embedder the store falls back to `ILIKE '%query%'` ordered by
//! `importance DESC` — identical semantics to `SqliteMemoryStore`.

use async_trait::async_trait;
use chrono::Utc;
use sqlx::{PgPool, Row};
use uuid::Uuid;

use omega_core::{
    economy::{EconomyError, NeuroCreditStore, Transaction, TransactionType, Wallet},
    memory::{MemoryEntry, MemoryId, MemoryStore, MemoryWriteResult},
    MemoryError,
};

use crate::error::MemoryStoreError;

// ---------------------------------------------------------------------------
// Optional fastembed integration
// ---------------------------------------------------------------------------

/// Opaque wrapper around a fastembed `TextEmbedding` model.
///
/// We hold it as a `Box<dyn EmbedText>` so that `PgMemoryStore` does not
/// directly depend on the fastembed crate at the call site — callers that want
/// embeddings pull fastembed in and construct one, callers that don't just
/// leave the field `None`.
pub trait EmbedText: Send + Sync {
    /// Produce a 384-dimensional embedding for `text`.
    ///
    /// Returns `None` on any internal error so the store can fall back
    /// gracefully instead of hard-failing.
    fn embed(&self, text: &str) -> Option<Vec<f32>>;
}

// ---------------------------------------------------------------------------
// PgMemoryStore
// ---------------------------------------------------------------------------

/// Postgres + pgvector-backed memory store.
///
/// Construct with [`PgMemoryStore::new`].  Optionally attach an embedder via
/// [`PgMemoryStore::with_embedder`] to enable semantic vector search.
///
/// The schema (`omega_memory_entries` table, `vector(384)` column, IVFFlat
/// index) must be present in the target database before first use.  See the
/// SQL block in `GEMINI_WEEK4_REPORT.md` for the DDL.
pub struct PgMemoryStore {
    pool: PgPool,
    /// None when fastembed is unavailable or not configured.
    embedder: Option<Box<dyn EmbedText>>,
}

impl PgMemoryStore {
    /// Open a connection pool to the Postgres instance at `db_url`.
    ///
    /// `db_url` must be a libpq-style connection string, e.g.:
    /// ```text
    /// postgresql://postgres:[password]@db.tssfdlodjgtedsssfpfc.supabase.co:5432/postgres
    /// ```
    pub async fn new(db_url: &str) -> Result<Self, MemoryStoreError> {
        let pool = PgPool::connect(db_url).await?;
        tracing::info!("PgMemoryStore connected to Postgres");
        Ok(Self {
            pool,
            embedder: None,
        })
    }

    /// Attach a text embedder.  When set, `write()` will persist embeddings
    /// and `search()` will use cosine similarity instead of ILIKE.
    pub fn with_embedder(mut self, embedder: Box<dyn EmbedText>) -> Self {
        self.embedder = Some(embedder);
        self
    }

    /// Serialise an `f32` slice as a pgvector literal: `[x,y,z,...]`.
    fn vec_literal(v: &[f32]) -> String {
        let inner: Vec<String> = v.iter().map(|f| f.to_string()).collect();
        format!("[{}]", inner.join(","))
    }

    /// Deserialise a pgvector text representation back to `Vec<f32>`.
    /// Returns `None` on parse failure.
    fn parse_vec_literal(s: &str) -> Option<Vec<f32>> {
        // pgvector returns "[x,y,z,...]"
        let trimmed = s.trim_matches(|c| c == '[' || c == ']');
        trimmed
            .split(',')
            .map(|tok| tok.trim().parse::<f32>().ok())
            .collect()
    }
}

// ---------------------------------------------------------------------------
// MemoryStore impl
// ---------------------------------------------------------------------------

#[async_trait]
impl MemoryStore for PgMemoryStore {
    /// Persist a [`MemoryEntry`] with `INSERT … ON CONFLICT DO UPDATE`.
    ///
    /// If `entry.id` is `None` a new UUID v4 is assigned.  When an embedder
    /// is configured the embedding is computed and stored alongside the text.
    async fn write(&self, entry: MemoryEntry) -> Result<MemoryWriteResult, MemoryError> {
        let id_str = entry
            .id
            .as_ref()
            .map(|m| m.0.clone())
            .unwrap_or_else(|| Uuid::new_v4().to_string());

        // Define contradiction threshold
        let threshold = std::env::var("OMEGA_MEMORY_CONTRADICTION_THRESHOLD")
            .ok()
            .and_then(|v| v.parse::<f32>().ok())
            .unwrap_or(0.85);

        let created_at = entry.created_at.unwrap_or_else(|| Utc::now().to_rfc3339());

        // Compute embedding if an embedder is attached.
        let embedding: Option<String> = self
            .embedder
            .as_ref()
            .and_then(|e| e.embed(&entry.content))
            .map(|v| Self::vec_literal(&v));

        let mut contradiction_found = false;
        let mut conflicting_ids = Vec::new();
        let mut conflicting_contents = Vec::new();
        let mut max_similarity = 0.0_f32;

        if let Some(ref emb_literal) = embedding {
            // Check for contradictions before writing
            let check_sql = format!(
                r#"
                SELECT id, content, (1 - (embedding <=> '{}'::vector)) as similarity
                FROM omega_memory_entries
                WHERE namespace = $1 AND id != $2 AND embedding IS NOT NULL
                ORDER BY similarity DESC
                LIMIT 5
                "#,
                emb_literal
            );

            if let Ok(rows) = sqlx::query(&check_sql)
                .bind(&entry.namespace)
                .bind(&id_str)
                .fetch_all(&self.pool)
                .await
            {
                for row in rows {
                    let sim: f32 = row.try_get::<f64, _>("similarity").unwrap_or(0.0) as f32;
                    if sim > threshold {
                        contradiction_found = true;
                        conflicting_ids.push(MemoryId::new(
                            row.try_get::<String, _>("id").unwrap_or_default(),
                        ));
                        conflicting_contents
                            .push(row.try_get::<String, _>("content").unwrap_or_default());
                        if sim > max_similarity {
                            max_similarity = sim;
                        }
                    }
                }
            }

            // Write with embedding
            let sql = format!(
                r#"
                INSERT INTO omega_memory_entries
                    (id, content, source, importance, created_at, namespace, embedding,
                     domain, confidence, version, superseded_by, key, raw_artifact)
                VALUES ($1, $2, $3, $4, $5, $6, '{}'::vector, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    content       = EXCLUDED.content,
                    source        = EXCLUDED.source,
                    importance    = EXCLUDED.importance,
                    created_at    = EXCLUDED.created_at,
                    namespace     = EXCLUDED.namespace,
                    embedding     = EXCLUDED.embedding,
                    domain        = EXCLUDED.domain,
                    confidence    = EXCLUDED.confidence,
                    version       = EXCLUDED.version,
                    superseded_by = EXCLUDED.superseded_by,
                    key           = EXCLUDED.key,
                    raw_artifact  = EXCLUDED.raw_artifact
                "#,
                emb_literal
            );

            let domain_str = serde_json::to_string(&entry.domain)
                .unwrap_or_default()
                .trim_matches('"')
                .to_string();

            sqlx::query(&sql)
                .bind(&id_str)
                .bind(&entry.content)
                .bind(&entry.source)
                .bind(entry.importance)
                .bind(&created_at)
                .bind(&entry.namespace)
                .bind(&domain_str)
                .bind(entry.confidence as f64)
                .bind(entry.version as i64)
                .bind(&entry.superseded_by)
                .bind(&entry.key)
                .bind(&entry.raw_artifact)
                .execute(&self.pool)
                .await
                .map_err(MemoryStoreError::Sqlx)?;
        } else {
            // Write without embedding
            sqlx::query(
                r#"
                INSERT INTO omega_memory_entries
                    (id, content, source, importance, created_at, namespace,
                     domain, confidence, version, superseded_by, key, raw_artifact)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    content       = EXCLUDED.content,
                    source        = EXCLUDED.source,
                    importance    = EXCLUDED.importance,
                    created_at    = EXCLUDED.created_at,
                    namespace     = EXCLUDED.namespace,
                    domain        = EXCLUDED.domain,
                    confidence    = EXCLUDED.confidence,
                    version       = EXCLUDED.version,
                    superseded_by = EXCLUDED.superseded_by,
                    key           = EXCLUDED.key,
                    raw_artifact  = EXCLUDED.raw_artifact
                "#,
            )
            .bind(&id_str)
            .bind(&entry.content)
            .bind(&entry.source)
            .bind(entry.importance)
            .bind(&created_at)
            .bind(&entry.namespace)
            .bind(
                serde_json::to_string(&entry.domain)
                    .unwrap_or_default()
                    .trim_matches('"'),
            )
            .bind(entry.confidence as f64)
            .bind(entry.version as i64)
            .bind(&entry.superseded_by)
            .bind(&entry.key)
            .bind(&entry.raw_artifact)
            .execute(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;
        }

        tracing::debug!(id = %id_str, namespace = %entry.namespace, contradiction = %contradiction_found, "pg memory entry written");

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
    /// Returns `None` if the entry does not exist.
    async fn read(&self, id: &MemoryId) -> Result<Option<MemoryEntry>, MemoryError> {
        let row = sqlx::query(
            "SELECT id, content, source, importance, created_at, namespace \
             FROM omega_memory_entries WHERE id = $1",
        )
        .bind(&id.0)
        .fetch_optional(&self.pool)
        .await
        .map_err(MemoryStoreError::Sqlx)?;

        match row {
            None => Ok(None),
            Some(r) => Ok(Some(MemoryEntry {
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
                domain: {
                    let domain_str: String = r
                        .try_get("domain")
                        .unwrap_or_else(|_| "operational".to_string());
                    serde_json::from_str(&format!("\"{}\"", domain_str)).unwrap_or_default()
                },
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
            })),
        }
    }

    /// Delete a single entry by its [`MemoryId`].
    /// Returns `true` if the row existed and was removed.
    async fn delete(&self, id: &MemoryId) -> Result<bool, MemoryError> {
        let result = sqlx::query("DELETE FROM omega_memory_entries WHERE id = $1")
            .bind(&id.0)
            .execute(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?;

        let deleted = result.rows_affected() > 0;
        if deleted {
            tracing::debug!(id = %id.0, "pg memory entry deleted");
        }
        Ok(deleted)
    }

    /// Search for entries matching `query`.
    ///
    /// - **With embedder** — computes a query embedding and uses pgvector
    ///   cosine distance (`<=>`) to return the `limit` nearest neighbours,
    ///   ordered closest-first.
    /// - **Without embedder** — falls back to `ILIKE '%query%'` ordered by
    ///   `importance DESC` (same semantics as `SqliteMemoryStore`).
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let limit_i64 = limit as i64;

        let rows = if let Some(emb) = self.embedder.as_ref().and_then(|e| e.embed(query)) {
            // Vector similarity search.
            let vec_literal = Self::vec_literal(&emb);
            let sql = format!(
                r#"
                SELECT id, content, source, importance, created_at, namespace,
                       domain, confidence, version, superseded_by, key, raw_artifact
                FROM omega_memory_entries
                ORDER BY embedding <=> '{}'::vector
                LIMIT $1
                "#,
                vec_literal
            );
            sqlx::query(&sql)
                .bind(limit_i64)
                .fetch_all(&self.pool)
                .await
                .map_err(MemoryStoreError::Sqlx)?
        } else {
            // Keyword fallback.
            let pattern = format!("%{}%", query);
            sqlx::query(
                r#"
                SELECT id, content, source, importance, created_at, namespace,
                       domain, confidence, version, superseded_by, key, raw_artifact
                FROM omega_memory_entries
                WHERE content ILIKE $1
                ORDER BY importance DESC
                LIMIT $2
                "#,
            )
            .bind(&pattern)
            .bind(limit_i64)
            .fetch_all(&self.pool)
            .await
            .map_err(MemoryStoreError::Sqlx)?
        };

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
                domain: {
                    let domain_str: String = r
                        .try_get("domain")
                        .unwrap_or_else(|_| "operational".to_string());
                    serde_json::from_str(&format!("\"{}\"", domain_str)).unwrap_or_default()
                },
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
            })
            .collect();

        Ok(entries)
    }

    async fn get_random(&self, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError> {
        let limit_i64 = limit as i64;
        let rows = sqlx::query(
            "SELECT id, content, source, importance, created_at, namespace, \
             domain, confidence, version, superseded_by, key, raw_artifact \
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
                domain: {
                    let domain_str: String = r
                        .try_get("domain")
                        .unwrap_or_else(|_| "operational".to_string());
                    serde_json::from_str(&format!("\"{}\"", domain_str)).unwrap_or_default()
                },
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
            })
            .collect();

        Ok(entries)
    }
}

#[async_trait]
impl NeuroCreditStore for PgMemoryStore {
    async fn init_wallet(
        &self,
        agent_id: &str,
        start_balance: f32,
    ) -> Result<Wallet, EconomyError> {
        // Attempt to create if not exists
        let now = Utc::now().to_rfc3339();

        // Supabase might fail if table missing.
        sqlx::query(
            "INSERT INTO agent_wallets (agent_id, balance, total_earned, total_spent, is_bankrupt, updated_at) \
             VALUES ($1, $2, $3, $4, $5, $6) ON CONFLICT (agent_id) DO NOTHING"
        )
        .bind(agent_id)
        .bind(start_balance as f64)
        .bind(0.0_f64)
        .bind(0.0_f64)
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
                balance: r.try_get::<f64, _>("balance").unwrap_or(0.0) as f32,
                total_earned: r.try_get::<f64, _>("total_earned").unwrap_or(0.0) as f32,
                total_spent: r.try_get::<f64, _>("total_spent").unwrap_or(0.0) as f32,
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
                "UPDATE agent_wallets SET is_bankrupt = true, balance = 0 WHERE agent_id = $1",
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
        .bind(new_balance as f64)
        .bind(earned_delta as f64)
        .bind(spent_delta as f64)
        .bind(&now)
        .bind(agent_id)
        .execute(&self.pool)
        .await
        .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

        // Log to financial_ledger — transaction_type as string
        let tx_type_str = serde_json::to_string(&tx_type)
            .unwrap_or_default()
            .trim_matches('"')
            .to_string();

        let row = sqlx::query(
            "INSERT INTO financial_ledger (agent_id, amount, transaction_type, description, balance_after, created_at) \
             VALUES ($1, $2, $3, $4, $5, $6) RETURNING id"
        )
        .bind(agent_id)
        .bind(amount as f64)
        .bind(&tx_type_str)
        .bind(description)
        .bind(new_balance as f64)
        .bind(&now)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| EconomyError::DatabaseError(e.to_string()))?;

        // Supabase might use bigint for id
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
