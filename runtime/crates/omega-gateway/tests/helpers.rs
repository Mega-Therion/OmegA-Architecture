// Shared test helpers for omega-gateway integration tests.
#![allow(dead_code)]

use axum::{body::Body, http::Request};
use futures::stream::Stream;
use omega_core::error::ProviderError;
use omega_core::provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth};
use omega_gateway::{build_app, config::GatewayConfig, state::AppState};
use omega_trace::TraceStore;
use std::pin::Pin;
use std::sync::{Arc, Mutex};
use std::time::Duration;

// ---- Mock providers ---------------------------------------------------------

/// A mock provider that always returns a fixed reply.
pub struct MockProvider {
    pub name: &'static str,
    pub reply: String,
}

impl MockProvider {
    pub fn new(name: &'static str, reply: impl Into<String>) -> Self {
        Self {
            name,
            reply: reply.into(),
        }
    }
}

#[async_trait::async_trait]
impl LlmProvider for MockProvider {
    fn name(&self) -> &str {
        self.name
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        Ok(ChatResponse {
            reply: self.reply.clone(),
            mode: req.mode.clone(),
            memory_hits: vec![],
        })
    }

    async fn stream(
        &self,
        _req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>, ProviderError>
    {
        Err(ProviderError::Unavailable { status: 501 })
    }

    async fn health(&self) -> ProviderHealth {
        ProviderHealth {
            available: true,
            latency_ms: None,
        }
    }
}

/// A mock provider that always returns a retriable error (RateLimited).
pub struct FailingProvider {
    pub name: &'static str,
}

impl FailingProvider {
    pub fn rate_limited(name: &'static str) -> Self {
        Self { name }
    }
}

#[async_trait::async_trait]
impl LlmProvider for FailingProvider {
    fn name(&self) -> &str {
        self.name
    }

    async fn complete(&self, _req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        Err(ProviderError::RateLimited)
    }

    async fn stream(
        &self,
        _req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>, ProviderError>
    {
        Err(ProviderError::Unavailable { status: 501 })
    }

    async fn health(&self) -> ProviderHealth {
        ProviderHealth {
            available: false,
            latency_ms: None,
        }
    }
}

// ---- Config helpers ---------------------------------------------------------

/// Build a test config with a known token and all provider keys empty.
pub fn test_config() -> GatewayConfig {
    let mut cfg = GatewayConfig::load().expect("gateway config");
    cfg.omega_api_bearer_token = "test-secret-token".to_string();
    cfg.omega_openai_api_key = String::new();
    cfg.omega_openai_base_url = "https://api.openai.com/v1".to_string();
    cfg.omega_model = "gpt-4o".to_string();
    cfg.omega_local_base_url = "http://localhost:11434/v1".to_string();
    cfg.omega_local_model = "llama3.2:3b".to_string();
    cfg.omega_codex_cli_path = "/home/mega/.nvm/versions/node/v22.22.0/bin/codex".to_string();
    cfg.omega_codex_cli_model = String::new();
    cfg.omega_claude_cli_path = "/home/mega/.local/bin/claude".to_string();
    cfg.omega_claude_cli_model = String::new();
    cfg.omega_gemini_cli_path = "/home/mega/.nvm/versions/node/v22.22.0/bin/gemini".to_string();
    cfg.omega_gemini_cli_model = String::new();
    cfg.omega_cli_home_dir = "/home/mega".to_string();
    cfg.omega_cli_timeout_secs = 120;
    cfg.omega_anthropic_api_key = String::new();
    cfg.omega_anthropic_model = "claude-3-5-haiku-20241022".to_string();
    cfg.omega_anthropic_base_url = "https://api.anthropic.com".to_string();
    cfg.omega_gemini_api_key = String::new();
    cfg.omega_gemini_model = "gemini-1.5-pro".to_string();
    cfg.omega_gemini_base_url = "https://generativelanguage.googleapis.com".to_string();
    cfg.omega_perplexity_api_key = String::new();
    cfg.omega_perplexity_model = "llama-3-sonar-large-32k-online".to_string();
    cfg.omega_perplexity_base_url = "https://api.perplexity.ai".to_string();
    cfg.omega_deepseek_api_key = String::new();
    cfg.omega_deepseek_base_url = "https://api.deepseek.com".to_string();
    cfg.omega_deepseek_model = "deepseek-chat".to_string();
    cfg.omega_xai_api_key = String::new();
    cfg.omega_xai_base_url = "https://api.x.ai/v1".to_string();
    cfg.omega_xai_model = "grok-beta".to_string();
    cfg.omega_db_url = "sqlite:///test.db".to_string();
    cfg.omega_log_level = "ERROR".to_string();
    cfg.omega_brain_base_url = "http://localhost:8080".to_string();
    cfg.omega_bridge_base_url = None;
    cfg.omega_internal_token = String::new();
    cfg.omega_port = 8787;
    cfg.omega_timeout_secs = 30;
    cfg.omega_system_prompt_path = String::new();
    cfg.omega_identity_yaml_path = String::new();
    cfg.omega_trace_db_url = "sqlite::memory:".to_string();
    cfg
}

/// Build a test config with auth disabled (empty token).
pub fn test_config_no_auth() -> GatewayConfig {
    let mut cfg = test_config();
    cfg.omega_api_bearer_token = String::new();
    cfg
}

/// A mock provider that records every `complete()` call.
/// Used to verify synthesis prompt content in council tests.
pub struct RecordingProvider {
    pub name: &'static str,
    pub reply: String,
    pub calls: Arc<Mutex<Vec<String>>>,
}

impl RecordingProvider {
    pub fn new(name: &'static str, reply: impl Into<String>) -> (Self, Arc<Mutex<Vec<String>>>) {
        let calls = Arc::new(Mutex::new(Vec::new()));
        let provider = Self {
            name,
            reply: reply.into(),
            calls: Arc::clone(&calls),
        };
        (provider, calls)
    }
}

#[async_trait::async_trait]
impl LlmProvider for RecordingProvider {
    fn name(&self) -> &str {
        self.name
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        self.calls.lock().unwrap().push(req.user.clone());
        Ok(ChatResponse {
            reply: self.reply.clone(),
            mode: req.mode.clone(),
            memory_hits: vec![],
        })
    }

    async fn stream(
        &self,
        _req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>, ProviderError>
    {
        Err(ProviderError::Unavailable { status: 501 })
    }

    async fn health(&self) -> ProviderHealth {
        ProviderHealth {
            available: true,
            latency_ms: None,
        }
    }
}

// ---- App builder ------------------------------------------------------------

/// Build the test app with a given provider chain.
///
/// Uses an in-memory SQLite store so tests are isolated and leave no files on disk.
/// Async because it needs to initialise the SQLite store.
pub async fn build_test_app(
    config: GatewayConfig,
    chain: Vec<Arc<dyn LlmProvider>>,
) -> axum::Router {
    use omega_core::{economy::NeuroCreditStore, router::Router};
    use omega_memory::SqliteMemoryStore;
    use omega_provider::FailoverRouter;

    let router = Arc::new(FailoverRouter::new(chain)) as Arc<dyn Router>;

    let store = Arc::new(
        SqliteMemoryStore::new("sqlite::memory:")
            .await
            .expect("test memory store init failed"),
    );
    store
        .migrate()
        .await
        .expect("test memory store migration failed");
    let memory_store: Arc<dyn omega_core::memory::MemoryStore> = store.clone();
    let economy_store: Arc<dyn NeuroCreditStore> = store;

    let trace = Arc::new(
        TraceStore::new("sqlite::memory:")
            .await
            .expect("test trace store init failed"),
    );
    trace
        .migrate()
        .await
        .expect("test trace store migration failed");

    let state = Arc::new(AppState::new(
        router,
        config,
        memory_store,
        economy_store,
        trace,
    ));
    build_app(state, Duration::from_secs(30))
}

/// Build a test app with an `OmegaCouncilRouter` attached to the FailoverRouter.
///
/// - `anthropic` + `gemini`: council members
/// - `synthesis`: provider used for the synthesis call
/// - `fallback`: chain used when both council members fail (passed as plain chain)
pub async fn build_test_app_with_council(
    config: GatewayConfig,
    anthropic: Arc<dyn LlmProvider>,
    gemini: Arc<dyn LlmProvider>,
    synthesis: Arc<dyn LlmProvider>,
    fallback_chain: Vec<Arc<dyn LlmProvider>>,
) -> axum::Router {
    use omega_core::router::Router;
    use omega_memory::SqliteMemoryStore;
    use omega_provider::{FailoverRouter, OmegaCouncilRouter};

    let fallback: Arc<dyn Router> = Arc::new(FailoverRouter::new(fallback_chain));

    let council = Arc::new(OmegaCouncilRouter {
        anthropic,
        gemini,
        synthesis_provider: synthesis,
        fallback_chain: fallback,
        timeout: Duration::from_secs(25),
    });

    // The outer failover chain sees all providers (direct mode routing), but
    // omega/cloud modes will be intercepted by the council router.
    let router = Arc::new(FailoverRouter::new(vec![]).with_council(council)) as Arc<dyn Router>;

    let store = Arc::new(
        SqliteMemoryStore::new("sqlite::memory:")
            .await
            .expect("test memory store init failed"),
    );
    store
        .migrate()
        .await
        .expect("test memory store migration failed");
    let memory_store: Arc<dyn omega_core::memory::MemoryStore> = store.clone();
    let economy_store: Arc<dyn omega_core::economy::NeuroCreditStore> = store;

    let trace = Arc::new(
        TraceStore::new("sqlite::memory:")
            .await
            .expect("test trace store init failed"),
    );
    trace
        .migrate()
        .await
        .expect("test trace store migration failed");

    let state = Arc::new(AppState::new(
        router,
        config,
        memory_store,
        economy_store,
        trace,
    ));
    build_app(state, Duration::from_secs(30))
}

// ---- Request builders -------------------------------------------------------

/// Build a POST /api/v1/chat request with the test bearer token.
pub fn chat_request(body: &str) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/api/v1/chat")
        .header("Authorization", "Bearer test-secret-token")
        .header("Content-Type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

/// Build a POST /api/v1/chat request with a custom Authorization header value.
pub fn chat_request_with_auth(body: &str, auth: &str) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/api/v1/chat")
        .header("Authorization", auth)
        .header("Content-Type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

/// Build a POST /api/v1/chat request with NO Authorization header.
pub fn chat_request_no_auth(body: &str) -> Request<Body> {
    Request::builder()
        .method("POST")
        .uri("/api/v1/chat")
        .header("Content-Type", "application/json")
        .body(Body::from(body.to_string()))
        .unwrap()
}

// ---- Response helpers -------------------------------------------------------

/// Parse an Axum response body as a JSON Value.
pub async fn parse_body(resp: axum::response::Response) -> serde_json::Value {
    let bytes = axum::body::to_bytes(resp.into_body(), usize::MAX)
        .await
        .unwrap();
    serde_json::from_slice(&bytes).expect("response body must be valid JSON")
}
