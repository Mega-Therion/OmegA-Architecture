use std::sync::Arc;

use dashmap::DashMap;
use omega_consensus::DCBFTEngine;
use omega_core::{
    economy::NeuroCreditStore, memory::MemoryStore, provider::LlmProvider, router::Router,
};
use omega_identity::soul::IdentityProfile;
use omega_trace::TraceStore;
use serde::{Deserialize, Serialize};

use crate::config::GatewayConfig;
use crate::middleware::policy::Law;

/// Opaque identifier for an in-flight or recent request (idempotency key).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct RequestId(pub String);

/// A logged record for idempotency / audit.
#[derive(Debug, Clone)]
pub struct RequestRecord {
    pub id: RequestId,
    pub prompt: String,
    pub provider_used: Option<String>,
}

/// Shared application state injected into every Axum handler.
pub struct AppState {
    pub router: Arc<dyn Router>,
    pub config: GatewayConfig,
    /// Persistent memory store (SQLite-backed).
    pub memory_store: Arc<dyn MemoryStore>,
    /// Economy store for Neuro-Credits.
    pub economy: Arc<dyn NeuroCreditStore>,
    /// In-memory idempotency map keyed by request id.
    pub request_log: DashMap<RequestId, RequestRecord>,
    /// Provider used for SSE streaming (LocalProvider / Ollama).
    /// None if no streaming-capable provider is configured.
    pub stream_provider: Option<Arc<dyn LlmProvider>>,
    /// DCBFT consensus engine for agentic voting.
    pub consensus: Arc<DCBFTEngine>,
    /// Canonical sovereign identity — injected as system prompt on every chat request.
    pub identity: IdentityProfile,
    /// Pre-rendered identity kernel text (render_text() result cached at startup).
    /// Avoids allocating a new multi-KB String on every chat request.
    pub identity_text: String,
    /// Cached RiskGovernor policy loaded from LAW.json at startup.
    pub law: Law,
    /// Append-only trace store for agent lifecycle events.
    pub trace: Arc<TraceStore>,
}

impl AppState {
    pub fn new(
        router: Arc<dyn Router>,
        config: GatewayConfig,
        memory_store: Arc<dyn MemoryStore>,
        economy: Arc<dyn NeuroCreditStore>,
        trace: Arc<TraceStore>,
    ) -> Self {
        let identity_yaml_path = config.omega_identity_yaml_path.clone();
        let identity = IdentityProfile::load_or_default(&identity_yaml_path);
        let identity_text = identity.render_text();
        Self {
            router,
            config,
            memory_store,
            economy,
            request_log: DashMap::new(),
            stream_provider: None,
            consensus: Arc::new(DCBFTEngine::new(1)),
            identity,
            identity_text,
            law: crate::middleware::policy::load_law(),
            trace,
        }
    }

    /// Attach a streaming-capable provider (typically LocalProvider).
    pub fn with_stream_provider(mut self, provider: Arc<dyn LlmProvider>) -> Self {
        self.stream_provider = Some(provider);
        self
    }
}
