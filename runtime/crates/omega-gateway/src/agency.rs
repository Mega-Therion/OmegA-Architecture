use std::sync::Arc;
use std::time::Duration;
use tokio::time;

use crate::state::AppState;
use omega_core::provider::{ChatRequest, TaskStateEnvelope};

/// Spawns a background task for Proactive Agency.
///
/// It periodically scans memory for tasks or objectives that haven't been
/// addressed and autonomously initiates agentic workflows to complete them.
pub fn spawn_agency_task(state: Arc<AppState>, interval: Duration) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        // Initial delay
        time::sleep(Duration::from_secs(60)).await;

        let mut ticker = time::interval(interval);

        loop {
            ticker.tick().await;

            tracing::info!("🤖 Proactive Agency: Scanning for pending autonomous objectives...");

            // 1. Search for pending tasks (using "task" or "todo" tags)
            let tasks = match state.memory_store.search("task", 3).await {
                Ok(m) => m,
                Err(e) => {
                    tracing::error!(error = %e, "Proactive Agency failed to search tasks");
                    continue;
                }
            };

            for task in tasks {
                // If the task is high importance and not explicitly marked done
                if task.importance >= 0.7 && !task.content.to_lowercase().contains("done") {
                    tracing::info!(task_id = ?task.id, "🎯 Proactive Agency: Addressing autonomous objective: {}", task.content);

                    // 2. Initiate a chat request to "work" on the task
                    let prompt = format!(
                        "You are an autonomous agent. Your current objective is: {}\n\
                        Review your recent memories and context, then perform the necessary actions or provide a status update.\n\
                        If completed, mark it as DONE in your reply.",
                        task.content
                    );

                    let req = ChatRequest {
                        user: prompt,
                        system: Some("You are OmegA in a proactive execution state.".to_string()),
                        mode: "codex".to_string(), // pin autonomous execution to Codex CLI
                        namespace: "default".to_string(),
                        use_memory: true,
                        use_collectivebrain: Some(false),
                        temperature: 0.2,
                        max_tokens: Some(1024),
                        images: None,
                        agent_id: Some("system:agency".to_string()),
                        task_state: Some(TaskStateEnvelope {
                            task_id: task.id.as_ref().map(|id| id.to_string()),
                            objective: format!("Advance or resolve autonomous objective: {}", task.content),
                            constraints: vec![
                                "Preserve OmegA identity continuity.".to_string(),
                                "Prefer reversible or observational actions when uncertainty is high.".to_string(),
                            ],
                            success_criteria: vec![
                                "Provide a concrete status update or execute the next safe step.".to_string(),
                                "Mark the objective as DONE only if it is actually completed.".to_string(),
                            ],
                            declared_unknowns: vec![],
                            urgency: Some(if task.importance >= 0.9 { "high" } else { "normal" }.to_string()),
                            intent_priority_score: Some(task.importance as f64),
                            authority_shrink_level: Some(if task.importance >= 0.9 { 0.18 } else { 0.12 }),
                            canon_anchor_weight: Some(0.82),
                            predicted_failure_modes: vec!["RETRIEVAL".to_string()],
                        }),
                    };

                    match state.router.route(&req).await {
                        Ok(response) => {
                            tracing::info!(
                                "✅ Proactive Agency: Task execution completed. Reply: {}",
                                response.reply.chars().take(50).collect::<String>()
                            );

                            // If it's done, we could update memory here to mark it done.
                            // For now, the reply is logged.
                        }
                        Err(e) => {
                            tracing::error!(error = %e, "Proactive Agency failed to execute task");
                        }
                    }

                    // Break after one task to avoid runaway execution
                    break;
                }
            }
        }
    })
}
