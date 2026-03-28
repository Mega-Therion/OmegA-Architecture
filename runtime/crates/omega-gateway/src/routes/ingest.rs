//! POST /api/v1/memory/ingest — chunk text or file content into memory entries.
//!
//! Ported from `core/crates/nexus-memory/src/main.rs` (Ingest subcommand).
//! Text is split at blank lines (paragraph chunks); chunks longer than
//! MAX_CHUNK_CHARS are sub-split at sentence boundaries (`. `, `? `, `! `).

use axum::{extract::State, http::StatusCode, response::IntoResponse, Json};
use omega_core::memory::{MemoryDomain, MemoryEntry, MemoryWriteResult};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::Arc;

use crate::state::AppState;

const MAX_CHUNK_CHARS: usize = 1200;

// ---------------------------------------------------------------------------
// Request / Response types
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
pub struct IngestRequest {
    /// Raw text to ingest. Required if `path` is not set.
    pub content: Option<String>,
    /// File path to read. Optional — alternative to `content`.
    pub path: Option<String>,
    /// Label stored as `entry.source`. Default: "ingest".
    #[serde(default = "default_source")]
    pub source: String,
    /// Memory namespace. Default: "default".
    #[serde(default = "default_namespace")]
    pub namespace: String,
    /// Memory domain. Default: Operational.
    #[serde(default)]
    pub domain: MemoryDomain,
}

fn default_source() -> String {
    "ingest".to_string()
}

fn default_namespace() -> String {
    "default".to_string()
}

#[derive(Debug, Serialize)]
pub struct IngestResponse {
    pub ingested: usize,
    pub chunks: usize,
}

// ---------------------------------------------------------------------------
// Chunking logic (ported from nexus-memory)
// ---------------------------------------------------------------------------

/// Split text into chunks at paragraph boundaries (blank lines).
/// Sub-splits chunks that exceed MAX_CHUNK_CHARS at sentence endings.
pub fn chunk_text(text: &str) -> Vec<String> {
    let mut chunks: Vec<String> = Vec::new();

    for para in text.split("\n\n") {
        let para = para.trim();
        if para.is_empty() {
            continue;
        }
        if para.len() <= MAX_CHUNK_CHARS {
            chunks.push(para.to_string());
        } else {
            // Sub-split at sentence boundaries (`. `, `? `, `! `).
            let mut current = String::new();
            for sentence in para.split_inclusive(|c| c == '.' || c == '?' || c == '!') {
                if current.len() + sentence.len() > MAX_CHUNK_CHARS && !current.is_empty() {
                    chunks.push(current.trim().to_string());
                    current = String::new();
                }
                current.push_str(sentence);
            }
            let remainder = current.trim().to_string();
            if !remainder.is_empty() {
                chunks.push(remainder);
            }
        }
    }

    chunks
}

// ---------------------------------------------------------------------------
// Handler
// ---------------------------------------------------------------------------

/// POST /api/v1/memory/ingest — ingest text or a file into memory as chunks.
pub async fn ingest_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<IngestRequest>,
) -> impl IntoResponse {
    // Resolve content: explicit text or file read.
    let text = if let Some(content) = req.content {
        content
    } else if let Some(ref path) = req.path {
        match std::fs::read_to_string(path) {
            Ok(c) => c,
            Err(e) => {
                return (
                    StatusCode::BAD_REQUEST,
                    Json(json!({
                        "detail": format!("cannot read file '{}': {}", path, e)
                    })),
                )
                    .into_response();
            }
        }
    } else {
        return (
            StatusCode::BAD_REQUEST,
            Json(json!({"detail": "either 'content' or 'path' is required"})),
        )
            .into_response();
    };

    let chunks = chunk_text(&text);
    let total = chunks.len();
    let mut written = 0usize;

    for chunk in chunks {
        let entry = MemoryEntry {
            id: None,
            content: chunk,
            source: req.source.clone(),
            importance: 0.7,
            created_at: None,
            namespace: req.namespace.clone(),
            tags: vec![],
            domain: req.domain.clone(),
            confidence: 1.0,
            version: 1,
            superseded_by: None,
            key: None,
            raw_artifact: req.path.clone(),
            tier: None,
            retrieval_count: 0,
            last_retrieved_at: None,
        };

        match state.memory_store.write(entry).await {
            Ok(MemoryWriteResult::Written(_)) | Ok(MemoryWriteResult::Contradiction { .. }) => {
                written += 1;
            }
            Err(e) => {
                tracing::warn!(error = %e, "ingest: failed to write chunk");
            }
        }
    }

    tracing::info!(chunks = total, written, source = %req.source, "ingest complete");

    (
        StatusCode::OK,
        Json(json!({
            "ingested": written,
            "chunks": total,
        })),
    )
        .into_response()
}
