use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::IntoResponse,
    Json,
};
use serde::Deserialize;
use std::sync::Arc;

use crate::state::AppState;
use omega_consensus::VoteType;

#[derive(Debug, Deserialize)]
pub struct InitiateVoteRequest {
    pub decision_id: Option<String>,
    pub description: String,
    pub required_agents: Vec<String>,
}

#[derive(Debug, Deserialize)]
pub struct CastVoteRequest {
    pub agent_id: String,
    pub vote: VoteType,
    pub justification: Option<String>,
}

/// POST /api/v1/consensus/initiate
pub async fn initiate_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<InitiateVoteRequest>,
) -> impl IntoResponse {
    match state
        .consensus
        .initiate_vote(req.decision_id, req.description, req.required_agents)
        .await
    {
        Ok(decision) => (StatusCode::CREATED, Json(decision)).into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"detail": e.to_string()})),
        )
            .into_response(),
    }
}

/// POST /api/v1/consensus/:id/vote
pub async fn vote_handler(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
    Json(req): Json<CastVoteRequest>,
) -> impl IntoResponse {
    match state
        .consensus
        .cast_vote(&id, &req.agent_id, req.vote, req.justification)
        .await
    {
        Ok(_) => StatusCode::OK.into_response(),
        Err(e) => (
            StatusCode::BAD_REQUEST,
            Json(serde_json::json!({"detail": e.to_string()})),
        )
            .into_response(),
    }
}

/// GET /api/v1/consensus/:id
pub async fn status_handler(
    State(state): State<Arc<AppState>>,
    Path(id): Path<String>,
) -> impl IntoResponse {
    match state.consensus.tally(&id).await {
        Ok(tally) => Json(tally).into_response(),
        Err(e) => (
            StatusCode::NOT_FOUND,
            Json(serde_json::json!({"detail": e.to_string()})),
        )
            .into_response(),
    }
}
