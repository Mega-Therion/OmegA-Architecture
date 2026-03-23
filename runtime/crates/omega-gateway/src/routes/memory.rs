/// Memory endpoints — persistent SQLite-backed implementation.
/// Replaces the Phase 1 wire-compatible stubs with real storage via
/// `omega_memory::SqliteMemoryStore`.
use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use omega_core::memory::{MemoryEntry, MemoryId, MemoryWriteResult};
use serde::Deserialize;
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct UpsertRequest {
    #[serde(default = "default_namespace")]
    pub namespace: String,
    pub id: Option<String>,
    pub content: String,
    /// Importance score [0.0, 1.0]. Default: 0.5.
    #[serde(default = "default_importance")]
    pub importance: f64,
    /// Source label (e.g. "chat", "agent"). Default: "chat".
    #[serde(default = "default_source")]
    pub source: String,
    #[serde(default)]
    pub meta: serde_json::Value,
}

#[derive(Debug, Deserialize)]
pub struct QueryRequest {
    #[serde(default = "default_namespace")]
    pub namespace: String,
    pub query: String,
    #[serde(default = "default_k")]
    pub k: u32,
}

fn default_namespace() -> String {
    String::new()
}

fn default_k() -> u32 {
    8
}

fn default_importance() -> f64 {
    0.5
}

fn default_source() -> String {
    "chat".to_string()
}

#[derive(Debug, Deserialize)]
pub struct ConsolidateRequest {
    #[serde(default = "default_namespace")]
    pub namespace: String,
    #[serde(default = "default_min_cluster_size")]
    pub min_cluster_size: usize,
    /// How many nearest neighbours to fetch per seed entry.
    #[serde(default = "default_neighbour_k")]
    pub neighbour_k: usize,
    /// Safety cap on how many entries to consider in a single request.
    #[serde(default = "default_fetch_limit")]
    pub fetch_limit: usize,
    /// If true, deletes original entries after writing the consolidated summary.
    #[serde(default)]
    pub delete_originals: bool,
}

fn default_min_cluster_size() -> usize {
    3
}

fn default_neighbour_k() -> usize {
    32
}

fn default_fetch_limit() -> usize {
    1000
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        return s.to_string();
    }
    let mut out = s.chars().take(max.saturating_sub(1)).collect::<String>();
    out.push('…');
    out
}

/// POST /api/v1/memory/upsert
/// Python contract response: {"id": str}
pub async fn upsert_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<UpsertRequest>,
) -> impl IntoResponse {
    let entry = MemoryEntry {
        id: req.id.map(MemoryId::new),
        content: req.content,
        source: req.source,
        importance: req.importance.clamp(0.0, 1.0),
        created_at: None,
        namespace: req.namespace.clone(),
        tags: vec![],
        domain: Default::default(),
        confidence: 1.0,
        version: 1,
        superseded_by: None,
        key: None,
        raw_artifact: None,
        tier: None,
    };

    match state.memory_store.write(entry).await {
        Ok(MemoryWriteResult::Written(id)) => {
            tracing::debug!(namespace = %req.namespace, id = %id, "memory upserted");
            (StatusCode::OK, Json(json!({"id": id.0}))).into_response()
        }
        Ok(MemoryWriteResult::Contradiction {
            new_id,
            conflicting_ids,
            conflicting_contents,
            similarity,
        }) => {
            tracing::debug!(namespace = %req.namespace, id = %new_id, "memory upserted with contradiction");
            let conf_ids: Vec<String> = conflicting_ids.into_iter().map(|id| id.0).collect();
            (
                StatusCode::OK,
                Json(json!({
                    "id": new_id.0,
                    "contradiction": {
                        "conflicting_ids": conf_ids,
                        "conflicting_contents": conflicting_contents,
                        "similarity": similarity
                    }
                })),
            )
                .into_response()
        }
        Err(e) => {
            tracing::error!(error = %e, "memory upsert failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response()
        }
    }
}

/// POST /api/v1/memory/query
/// Python contract response: {"hits": [...]}
pub async fn query_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<QueryRequest>,
) -> impl IntoResponse {
    let limit = req.k as usize;
    let search_limit = (limit.saturating_mul(4)).max(limit);

    match state.memory_store.search(&req.query, search_limit).await {
        Ok(entries) => {
            let hits: Vec<serde_json::Value> = entries
                .into_iter()
                .filter(|e| req.namespace.is_empty() || e.namespace == req.namespace)
                .take(limit)
                .map(|e| serde_json::to_value(e).unwrap_or_default())
                .collect();
            tracing::debug!(namespace = %req.namespace, k = req.k, hits = hits.len(), "memory queried");
            (StatusCode::OK, Json(json!({"hits": hits}))).into_response()
        }
        Err(e) => {
            tracing::error!(error = %e, "memory query failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response()
        }
    }
}

/// GET /api/v1/memory/:id — retrieve a memory entry by ID.
/// Returns 200 + entry JSON, or 404 if not found.
pub async fn get_by_id_handler(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    let memory_id = MemoryId::new(id);

    match state.memory_store.read(&memory_id).await {
        Ok(Some(entry)) => {
            tracing::debug!(id = %memory_id, "memory entry retrieved");
            (
                StatusCode::OK,
                Json(serde_json::to_value(entry).unwrap_or_default()),
            )
                .into_response()
        }
        Ok(None) => {
            tracing::debug!(id = %memory_id, "memory entry not found");
            (
                StatusCode::NOT_FOUND,
                Json(json!({"detail": format!("memory entry '{}' not found", memory_id)})),
            )
                .into_response()
        }
        Err(e) => {
            tracing::error!(error = %e, "memory read failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response()
        }
    }
}

/// DELETE /api/v1/memory/:id — delete a memory entry by ID.
/// Returns 204 on success, 404 if not found.
pub async fn delete_by_id_handler(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    let memory_id = MemoryId::new(id);

    match state.memory_store.delete(&memory_id).await {
        Ok(true) => {
            tracing::debug!(id = %memory_id, "memory entry deleted");
            StatusCode::NO_CONTENT.into_response()
        }
        Ok(false) => {
            tracing::debug!(id = %memory_id, "memory entry not found for delete");
            (
                StatusCode::NOT_FOUND,
                Json(json!({"detail": format!("memory entry '{}' not found", memory_id)})),
            )
                .into_response()
        }
        Err(e) => {
            tracing::error!(error = %e, "memory delete failed");
            (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response()
        }
    }
}

/// POST /api/v1/memory/consolidate — greedy in-process consolidation.
///
/// This is a Week 4 MVP:
/// - Fetches up to `fetch_limit` entries (via `search("")`) and filters by namespace.
/// - For each seed entry, pulls `neighbour_k` neighbours via `search(seed.content)`.
/// - If a cluster meets `min_cluster_size`, writes a consolidated summary entry.
/// - Optionally deletes original entries when `delete_originals=true`.
pub async fn consolidate_handler(
    State(state): State<Arc<AppState>>,
    req: Option<Json<ConsolidateRequest>>,
) -> impl IntoResponse {
    // Backward-compatible behaviour: older clients/tests POST an empty body and
    // expect the Week 4 stub response shape.
    if req.is_none() {
        return (
            StatusCode::OK,
            Json(json!({
                "status": "ok",
                "consolidated": 0,
                "message": "consolidation not yet implemented — Week 4 (send JSON body to enable MVP)"
            })),
        )
            .into_response();
    }

    let req = req.map(|j| j.0).unwrap_or(ConsolidateRequest {
        namespace: default_namespace(),
        min_cluster_size: default_min_cluster_size(),
        neighbour_k: default_neighbour_k(),
        fetch_limit: default_fetch_limit(),
        delete_originals: false,
    });
    let namespace = req.namespace.clone();

    let all = match state.memory_store.search("", req.fetch_limit).await {
        Ok(entries) => entries
            .into_iter()
            .filter(|e| e.namespace == namespace)
            .collect::<Vec<_>>(),
        Err(e) => {
            tracing::error!(error = %e, "memory consolidate fetch failed");
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response();
        }
    };

    let mut visited: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut created: Vec<String> = Vec::new();
    let mut deleted_count: u64 = 0;
    let mut consolidated_clusters: u64 = 0;

    for seed in all.iter() {
        let Some(seed_id) = seed.id.as_ref().map(|i| i.0.clone()) else {
            continue;
        };
        if visited.contains(&seed_id) {
            continue;
        }

        // Pull neighbours via store search (semantic when enabled, keyword otherwise).
        let neighbours = match state
            .memory_store
            .search(&seed.content, req.neighbour_k)
            .await
        {
            Ok(entries) => entries
                .into_iter()
                .filter(|e| e.namespace == namespace)
                .collect::<Vec<_>>(),
            Err(e) => {
                tracing::warn!(error = %e, "memory consolidate neighbour search failed");
                tokio::time::sleep(Duration::from_millis(5)).await;
                continue;
            }
        };

        let mut cluster: Vec<MemoryEntry> = Vec::new();
        let mut cluster_ids: Vec<String> = Vec::new();

        for e in neighbours.into_iter().chain(std::iter::once(seed.clone())) {
            let Some(id) = e.id.as_ref().map(|i| i.0.clone()) else {
                continue;
            };
            if visited.insert(id.clone()) {
                cluster_ids.push(id);
                cluster.push(e);
            }
        }

        if cluster.len() < req.min_cluster_size {
            continue;
        }

        consolidated_clusters += 1;

        // Build a simple summary. (Week 5+: LLM synthesis + archival metadata.)
        cluster.sort_by(|a, b| {
            b.importance
                .partial_cmp(&a.importance)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        let mut summary_lines: Vec<String> = Vec::new();
        summary_lines.push(format!(
            "Consolidated memory cluster ({} entries):",
            cluster.len()
        ));
        for e in cluster.iter().take(24) {
            summary_lines.push(format!(
                "- {}",
                truncate(&e.content.replace('\n', " "), 180)
            ));
        }

        let new_importance = cluster.iter().map(|e| e.importance).fold(0.0_f64, f64::max);

        let consolidated_entry = MemoryEntry {
            id: None,
            content: summary_lines.join("\n"),
            source: "consolidation".to_string(),
            importance: new_importance,
            created_at: None,
            namespace: namespace.clone(),
            tags: vec![],
            domain: Default::default(),
            confidence: 1.0,
            version: 1,
            superseded_by: None,
            key: None,
            raw_artifact: None,
            tier: None,
        };

        let consolidated_id = match state.memory_store.write(consolidated_entry).await {
            Ok(MemoryWriteResult::Written(id))
            | Ok(MemoryWriteResult::Contradiction { new_id: id, .. }) => id.0,
            Err(e) => {
                tracing::error!(error = %e, "memory consolidate write failed");
                continue;
            }
        };
        created.push(consolidated_id);

        if req.delete_originals {
            for id in cluster_ids {
                match state.memory_store.delete(&MemoryId::new(id)).await {
                    Ok(true) => deleted_count += 1,
                    Ok(false) => {}
                    Err(e) => tracing::warn!(error = %e, "memory consolidate delete failed"),
                }
            }
        }
    }

    (
        StatusCode::OK,
        Json(json!({
            "status": "ok",
            "namespace": namespace,
            "clusters": consolidated_clusters,
            "created": created,
            "deleted": deleted_count,
            "delete_originals": req.delete_originals
        })),
    )
        .into_response()
}
