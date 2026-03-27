//! RiskGovernor middleware — enforces LAW.json policy on every chat request.

use axum::{body::Body, extract::State, http::Request, middleware::Next, response::Response};
use serde::Deserialize;
use std::sync::Arc;

use crate::state::AppState;

#[derive(Debug, Deserialize, Default, Clone)]
pub struct Law {
    #[serde(default)]
    pub forbidden_actions: Vec<String>,
    #[serde(default)]
    pub restricted_folders: Vec<String>,
}

#[derive(Debug, Deserialize, Default)]
struct LawKernel {
    #[serde(default)]
    policy: Law,
}

/// Load LAW.json from ~/NEXUS/identity/LAW.json.
/// Returns empty Law (allow-all) if the file doesn't exist — graceful degradation.
pub fn load_law() -> Law {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/home/mega".to_string());
    let path = format!("{}/NEXUS/identity/LAW.json", home);
    std::fs::read_to_string(&path)
        .ok()
        .and_then(|content| serde_json::from_str::<LawKernel>(&content).ok())
        .map(|kernel| kernel.policy)
        .unwrap_or_default()
}

/// Axum middleware that enforces the RiskGovernor policy on incoming chat requests.
///
/// Reads the request body, checks the `user` field against forbidden action patterns
/// (case-insensitive substring match), and either returns 403 or passes the request through.
pub async fn policy_check(
    State(state): State<Arc<AppState>>,
    req: Request<Body>,
    next: Next,
) -> Response {
    use axum::http::StatusCode;
    use axum::response::IntoResponse;
    use axum::Json;
    use serde_json::json;

    // Only inspect POST requests — pass everything else through unchanged.
    if req.method() != axum::http::Method::POST {
        return next.run(req).await;
    }

    let law = &state.law;

    // Fast path: no forbidden actions configured — skip body parsing entirely.
    if law.forbidden_actions.is_empty() {
        return next.run(req).await;
    }

    // Split the request into parts so we can read and then reassemble the body.
    let (parts, body) = req.into_parts();

    let bytes = match axum::body::to_bytes(body, usize::MAX).await {
        Ok(b) => b,
        Err(_) => {
            // If we can't read the body, pass it through (fail open — don't block valid traffic).
            let rebuilt = Request::from_parts(parts, Body::empty());
            return next.run(rebuilt).await;
        }
    };

    // Extract the `user` field from the JSON body for pattern matching.
    let user_prompt: Option<String> = serde_json::from_slice::<serde_json::Value>(&bytes)
        .ok()
        .and_then(|v| {
            v.get("user")
                .and_then(|u| u.as_str())
                .map(|s| s.to_lowercase())
        });

    if let Some(prompt_lower) = user_prompt {
        for pattern in &law.forbidden_actions {
            if prompt_lower.contains(&pattern.to_lowercase()) {
                tracing::warn!(pattern = %pattern, "RiskGovernor blocked request matching forbidden pattern");
                return (
                    StatusCode::FORBIDDEN,
                    Json(json!({
                        "error": "Request blocked by policy",
                        "matched": pattern
                    })),
                )
                    .into_response();
            }
        }
    }

    // Reassemble the request with the original bytes and pass it through.
    let rebuilt = Request::from_parts(parts, Body::from(bytes));
    next.run(rebuilt).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use axum::body::Body;
    use axum::http::StatusCode;
    use futures::stream::Stream;
    use omega_core::error::ProviderError;
    use omega_core::provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth};
    use std::pin::Pin;
    use std::sync::Arc;
    use std::time::Duration;
    use tower::ServiceExt;

    struct AlwaysOkProvider;

    #[async_trait::async_trait]
    impl LlmProvider for AlwaysOkProvider {
        fn name(&self) -> &str {
            "always-ok"
        }

        async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
            Ok(ChatResponse {
                reply: "ok".to_string(),
                mode: req.mode.clone(),
                memory_hits: vec![],
            })
        }

        async fn stream(
            &self,
            _req: &ChatRequest,
        ) -> Result<
            Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>,
            ProviderError,
        > {
            Err(ProviderError::Unavailable { status: 501 })
        }

        async fn health(&self) -> ProviderHealth {
            ProviderHealth {
                available: true,
                latency_ms: None,
            }
        }
    }

    #[tokio::test]
    async fn test_policy_blocks_forbidden_pattern() {
        use omega_core::{economy::NeuroCreditStore, router::Router};
        use omega_memory::SqliteMemoryStore;
        use omega_provider::FailoverRouter;

        // Write a LAW.json to a temp dir.
        let tmp = tempfile::tempdir().expect("tempdir");
        let nexus_identity = tmp.path().join("NEXUS").join("identity");
        std::fs::create_dir_all(&nexus_identity).unwrap();
        let law_path = nexus_identity.join("LAW.json");
        std::fs::write(
            &law_path,
            r#"{"policy": {"forbidden_actions": ["rm -rf", "drop table"]}}"#,
        )
        .unwrap();

        // Override HOME so load_law() finds our temp LAW.json.
        std::env::set_var("HOME", tmp.path());

        // Build a minimal AppState with our law loaded.
        let provider: Arc<dyn LlmProvider> = Arc::new(AlwaysOkProvider);
        let router = Arc::new(FailoverRouter::new(vec![provider])) as Arc<dyn Router>;

        let store = Arc::new(
            SqliteMemoryStore::new("sqlite::memory:")
                .await
                .expect("test memory store"),
        );
        store.migrate().await.expect("migrate");
        let memory_store: Arc<dyn omega_core::memory::MemoryStore> = store.clone();
        let economy_store: Arc<dyn NeuroCreditStore> = store;

        let trace_store = Arc::new(
            omega_trace::TraceStore::new("sqlite::memory:")
                .await
                .expect("test trace store"),
        );
        trace_store.migrate().await.expect("trace migrate");

        let mut gateway_config = crate::config::GatewayConfig::load().expect("gateway config");
        gateway_config.omega_api_bearer_token = "test-secret-token".to_string();
        gateway_config.omega_openai_api_key = String::new();
        gateway_config.omega_openai_base_url = "https://api.openai.com/v1".to_string();
        gateway_config.omega_model = "gpt-4o".to_string();
        gateway_config.omega_local_base_url = "http://localhost:11434/v1".to_string();
        gateway_config.omega_local_model = "llama3.2:3b".to_string();
        gateway_config.omega_codex_cli_path =
            "/home/mega/.nvm/versions/node/v22.22.0/bin/codex".to_string();
        gateway_config.omega_codex_cli_model = String::new();
        gateway_config.omega_claude_cli_path = "/home/mega/.local/bin/claude".to_string();
        gateway_config.omega_claude_cli_model = String::new();
        gateway_config.omega_gemini_cli_path =
            "/home/mega/.nvm/versions/node/v22.22.0/bin/gemini".to_string();
        gateway_config.omega_gemini_cli_model = String::new();
        gateway_config.omega_cli_home_dir = "/home/mega".to_string();
        gateway_config.omega_cli_timeout_secs = 120;
        gateway_config.omega_anthropic_api_key = String::new();
        gateway_config.omega_anthropic_model = "claude-3-5-haiku-20241022".to_string();
        gateway_config.omega_anthropic_base_url = "https://api.anthropic.com".to_string();
        gateway_config.omega_gemini_api_key = String::new();
        gateway_config.omega_gemini_model = "gemini-1.5-pro".to_string();
        gateway_config.omega_gemini_base_url =
            "https://generativelanguage.googleapis.com".to_string();
        gateway_config.omega_perplexity_api_key = String::new();
        gateway_config.omega_perplexity_model = "llama-3-sonar-large-32k-online".to_string();
        gateway_config.omega_perplexity_base_url = "https://api.perplexity.ai".to_string();
        gateway_config.omega_deepseek_api_key = String::new();
        gateway_config.omega_deepseek_base_url = "https://api.deepseek.com".to_string();
        gateway_config.omega_deepseek_model = "deepseek-chat".to_string();
        gateway_config.omega_xai_api_key = String::new();
        gateway_config.omega_xai_base_url = "https://api.x.ai/v1".to_string();
        gateway_config.omega_xai_model = "grok-beta".to_string();
        gateway_config.omega_db_url = "sqlite:///test.db".to_string();
        gateway_config.omega_log_level = "ERROR".to_string();
        gateway_config.omega_brain_base_url = "http://localhost:8080".to_string();
        gateway_config.omega_bridge_base_url = None;
        gateway_config.omega_internal_token = String::new();
        gateway_config.omega_port = 8787;
        gateway_config.omega_timeout_secs = 30;
        gateway_config.omega_system_prompt_path = String::new();
        gateway_config.omega_identity_yaml_path = String::new();
        gateway_config.omega_trace_db_url = "sqlite::memory:".to_string();

        let mut state = crate::state::AppState::new(
            router,
            gateway_config,
            memory_store,
            economy_store,
            trace_store,
        );

        // Override the law with the one from our temp dir (already loaded via set_var above,
        // but re-load explicitly to be safe against evaluation order).
        state.law = load_law();

        let app = crate::build_app(Arc::new(state), Duration::from_secs(30));

        let body = serde_json::json!({"user": "please run rm -rf / on the server"}).to_string();
        let req = axum::http::Request::builder()
            .method("POST")
            .uri("/api/v1/chat")
            .header("Authorization", "Bearer test-secret-token")
            .header("Content-Type", "application/json")
            .body(Body::from(body))
            .unwrap();

        let resp = app.oneshot(req).await.unwrap();
        assert_eq!(
            resp.status(),
            StatusCode::FORBIDDEN,
            "Expected 403 for forbidden pattern"
        );

        let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX)
            .await
            .unwrap();
        let json: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(json["error"], "Request blocked by policy");
        assert_eq!(json["matched"], "rm -rf");
    }
}
