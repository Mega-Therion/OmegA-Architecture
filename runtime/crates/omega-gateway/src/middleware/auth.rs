use axum::{
    body::Body,
    extract::State,
    http::{Request, StatusCode},
    middleware::Next,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use std::sync::Arc;

use crate::state::AppState;

/// Axum middleware that validates `Authorization: Bearer <token>` against
/// the configured `omega_api_bearer_token`.
///
/// Behavior matches the Python gateway exactly:
/// - If OMEGA_API_BEARER_TOKEN is empty/unset → auth is skipped (permissive mode)
/// - If Authorization header is missing or not "Bearer …" → HTTP 401
/// - If token is present but wrong → HTTP 403
/// - If token matches → request passes through
pub async fn bearer_auth(
    State(state): State<Arc<AppState>>,
    req: Request<Body>,
    next: Next,
) -> Response {
    let configured_token = &state.config.omega_api_bearer_token;

    // Permissive mode: if no token is configured, skip auth entirely.
    if configured_token.is_empty() {
        return next.run(req).await;
    }

    // Extract the bearer token from the Authorization header.
    let maybe_token = req
        .headers()
        .get(axum::http::header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .and_then(|v| v.strip_prefix("Bearer "))
        .map(|t| t.trim().to_string());

    match maybe_token {
        None => {
            // Header missing entirely or not in "Bearer <token>" format → 401
            (
                StatusCode::UNAUTHORIZED,
                Json(json!({"detail": "Missing bearer token."})),
            )
                .into_response()
        }
        Some(ref t) if t != configured_token => {
            // Token present but wrong → 403
            (
                StatusCode::FORBIDDEN,
                Json(json!({"detail": "Invalid bearer token."})),
            )
                .into_response()
        }
        Some(_) => {
            // Token matches → pass through
            next.run(req).await
        }
    }
}
