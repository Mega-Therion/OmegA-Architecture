use axum::{extract::State, http::StatusCode, response::IntoResponse, Json};
use serde_json::json;
use std::sync::Arc;
use std::time::Duration;

use crate::state::AppState;

/// GET / — root info endpoint (no auth required).
/// Python contract: {"service": "OMEGA Gateway", "version": "0.1", "status": "operational"}
pub async fn root_handler() -> impl IntoResponse {
    (
        StatusCode::OK,
        Json(json!({
            "service": "OMEGA Gateway",
            "version": "0.1",
            "status": "operational"
        })),
    )
}

/// GET /health and GET /api/v1/health — quick liveness check (no auth required).
/// Python contract: {"ok": true, "service": "Gateway", "version": "0.1"}
pub async fn health_handler() -> impl IntoResponse {
    (
        StatusCode::OK,
        Json(json!({
            "ok": true,
            "service": "Gateway",
            "version": "0.1"
        })),
    )
}

/// GET /healthz — minimal liveness check (no auth required).
/// Python contract: {"ok": true}
pub async fn healthz_handler() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({"ok": true})))
}

/// GET /ready — readiness probe.
pub async fn ready_handler() -> impl IntoResponse {
    (StatusCode::OK, Json(json!({"status": "ready"})))
}

/// GET /health/deep — deep health check, probes Brain and Bridge.
/// Python contract:
/// {"ok": bool, "services": {"gateway": "ok", "brain": "ok"|"error:<N>"|"unreachable:<msg>", "bridge": ...}}
pub async fn deep_health_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let brain_url = format!(
        "{}/health",
        state.config.omega_brain_base_url.trim_end_matches('/')
    );
    let bridge_url = format!(
        "{}/health",
        state.config.bridge_base_url().trim_end_matches('/')
    );

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
        .unwrap_or_default();

    let brain_status = probe_service(&client, &brain_url).await;
    let bridge_status = probe_service(&client, &bridge_url).await;

    let all_ok = brain_status == "ok" && bridge_status == "ok";
    let state = if all_ok {
        "AR137 NAOMI"
    } else {
        "AR137 DEGRADED"
    };

    (
        StatusCode::OK,
        Json(json!({
            "ok": all_ok,
            "state": state,
            "services": {
                "gateway": "AR137 NAOMI",
                "brain": brain_status,
                "bridge": bridge_status
            }
        })),
    )
}

/// Probe a service's health URL. Returns "ok", "error:<status>", or "unreachable:<msg>".
async fn probe_service(client: &reqwest::Client, url: &str) -> String {
    match client.get(url).send().await {
        Ok(resp) => {
            if resp.status().as_u16() == 200 {
                "ok".to_string()
            } else {
                format!("error:{}", resp.status().as_u16())
            }
        }
        Err(e) => {
            let msg = e.to_string();
            // Truncate to 50 chars matching Python behavior: f"unreachable:{str(e)[:50]}"
            let truncated = &msg[..msg.len().min(50)];
            format!("unreachable:{}", truncated)
        }
    }
}

/// GET /api/v1/status — config status (auth required).
/// Python contract: {"model": str, "base_url": str, "db": "sqlite"|"pgvector", "auth": bool}
pub async fn status_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let cfg = &state.config;
    (
        StatusCode::OK,
        Json(json!({
            "model": cfg.omega_model,
            "base_url": cfg.omega_openai_base_url,
            "db": cfg.db_type(),
            "auth": cfg.auth_enabled()
        })),
    )
}
