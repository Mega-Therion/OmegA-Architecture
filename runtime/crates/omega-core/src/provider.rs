use std::pin::Pin;

use futures::stream::Stream;
use serde::{Deserialize, Serialize};

use crate::error::ProviderError;

/// A single chat request from the user/system.
/// Fields match the Python ChatRequest model exactly for wire compatibility.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatRequest {
    /// The user prompt text (required).
    pub user: String,
    /// Memory namespace (default: "default").
    #[serde(default = "default_namespace")]
    pub namespace: String,
    /// Whether to retrieve memory snippets (default: true).
    #[serde(default = "default_use_memory")]
    pub use_memory: bool,
    /// Whether to run through CollectiveBrain (default: false).
    /// Accepted for wire compatibility; full CollectiveBrain is a TODO.
    #[serde(default)]
    pub use_collectivebrain: Option<bool>,
    /// Sampling temperature [0.0, 2.0] (default: 0.2).
    #[serde(default = "default_temperature")]
    pub temperature: f32,
    /// Optional routing mode (e.g. "omega", "claude", "gemini", ...).
    /// Stored as a raw string to preserve all aliases.
    #[serde(default = "default_mode")]
    pub mode: String,
    /// Optional system prompt override.
    pub system: Option<String>,
    /// Optional max tokens to generate.
    pub max_tokens: Option<u32>,
    /// Optional images for vision models (URLs or base64 data).
    pub images: Option<Vec<String>>,
    /// Optional agent ID for billing/attribution.
    pub agent_id: Option<String>,
    /// Optional task-state envelope carrying structured objective and governance context.
    #[serde(default)]
    pub task_state: Option<TaskStateEnvelope>,
}

/// Lightweight task-state envelope for routing, observability, and governance.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskStateEnvelope {
    pub task_id: Option<String>,
    pub objective: String,
    #[serde(default)]
    pub constraints: Vec<String>,
    #[serde(default)]
    pub success_criteria: Vec<String>,
    #[serde(default)]
    pub declared_unknowns: Vec<String>,
    #[serde(default)]
    pub urgency: Option<String>,
    #[serde(default)]
    pub intent_priority_score: Option<f64>,
    #[serde(default)]
    pub authority_shrink_level: Option<f64>,
    #[serde(default)]
    pub canon_anchor_weight: Option<f64>,
    #[serde(default)]
    pub predicted_failure_modes: Vec<String>,
}

fn default_namespace() -> String {
    "default".to_string()
}

fn default_use_memory() -> bool {
    true
}

fn default_temperature() -> f32 {
    0.2
}

fn default_mode() -> String {
    "omega".to_string()
}

/// A complete (non-streaming) chat response.
/// Fields match the Python ChatResponse model exactly for wire compatibility.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatResponse {
    /// The model-generated text. Key is "reply" matching Python contract.
    pub reply: String,
    /// Which mode/provider produced this response. Key is "mode" matching Python.
    pub mode: String,
    /// Memory hits included in the response (always present, may be empty).
    #[serde(default)]
    pub memory_hits: Vec<serde_json::Value>,
}

/// A single streamed chunk from a provider.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatChunk {
    /// Partial text delta.
    pub delta: String,
    /// True when this is the final chunk.
    pub done: bool,
}

/// Health status reported by a provider.
pub struct ProviderHealth {
    pub available: bool,
    pub latency_ms: Option<u64>,
}

/// Core trait every LLM provider must implement.
#[async_trait::async_trait]
pub trait LlmProvider: Send + Sync {
    fn name(&self) -> &str;

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError>;

    async fn stream(
        &self,
        req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>, ProviderError>;

    async fn health(&self) -> ProviderHealth;
}
