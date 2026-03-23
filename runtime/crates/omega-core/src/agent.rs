use serde::{Deserialize, Serialize};

use crate::error::AgentError;

/// A task dispatched to an agent worker.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentTask {
    pub id: String,
    pub prompt: String,
    pub context: Option<String>,
    pub agent_hint: Option<String>,
}

/// The result returned by an agent worker after completing a task.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResult {
    pub task_id: String,
    pub output: String,
    pub agent: String,
    pub success: bool,
}

/// Trait for any agent that can be dispatched tasks.
#[async_trait::async_trait]
pub trait AgentWorker: Send + Sync {
    fn agent_id(&self) -> &str;
    async fn dispatch(&self, task: AgentTask) -> Result<AgentResult, AgentError>;
}
