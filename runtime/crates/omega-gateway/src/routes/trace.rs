//! Trace inspection routes.
//!
//! GET  /api/v1/trace              — last 50 events
//! GET  /api/v1/trace/task/:id     — events for a specific task

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde_json::json;
use std::sync::Arc;

use crate::state::AppState;

/// GET /api/v1/trace — returns the 50 most recent trace events.
pub async fn list_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    match state.trace.recent(50).await {
        Ok(events) => (StatusCode::OK, Json(json!({ "events": events }))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "detail": e.to_string() })),
        )
            .into_response(),
    }
}

/// GET /api/v1/trace/task/:task_id — returns all events for the given task.
pub async fn by_task_handler(
    State(state): State<Arc<AppState>>,
    Path(task_id): Path<String>,
) -> impl IntoResponse {
    match state.trace.by_task(&task_id).await {
        Ok(events) => (StatusCode::OK, Json(json!({ "events": events }))).into_response(),
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(json!({ "detail": e.to_string() })),
        )
            .into_response(),
    }
}
