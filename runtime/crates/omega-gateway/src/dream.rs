use std::sync::Arc;
use std::time::Duration;
use tokio::time;

use crate::state::AppState;
use omega_core::{
    economy::TransactionType,
    memory::MemoryEntry,
    provider::{ChatRequest, TaskStateEnvelope},
};

/// Spawns a background task that periodically puts the system into a "Dream State".
///
/// In the Dream State, the system picks random memories to reflect upon,
/// synthesizing new insights or noticing contradictions without user prompting.
pub fn spawn_dream_task(state: Arc<AppState>, interval: Duration) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        // Delay the first tick so the system can boot normally
        time::sleep(Duration::from_secs(30)).await;

        let mut ticker = time::interval(interval);

        loop {
            ticker.tick().await;

            tracing::info!("💤 Entering Dream State...");

            // 1. Fetch random memories
            let memories = match state.memory_store.get_random(3).await {
                Ok(m) => m,
                Err(e) => {
                    tracing::error!(error = %e, "Dream State failed to fetch memories");
                    continue;
                }
            };

            if memories.is_empty() {
                tracing::debug!("Dream State skipped: Not enough memories to dream about.");
                continue;
            }

            // 2. Format a reflection prompt for the LLM
            let mut prompt = String::from(
                "You are in a Dream State. Reflect on the following disparate memories. \
                Synthesize a new insight, identify an underlying pattern, or notice a contradiction. \
                Keep your epiphany profound, concise, and focused on the AI system's self-evolution.\n\n"
            );

            for (i, mem) in memories.iter().enumerate() {
                prompt.push_str(&format!("Memory {}:\n{}\n\n", i + 1, mem.content));
            }

            let req = ChatRequest {
                user: prompt,
                system: Some("You are OmegA in an autonomous reflection state.".to_string()),
                mode: "codex".to_string(), // pin autonomous reflection to Codex CLI
                namespace: "default".to_string(),
                use_memory: false, // already have the memories in the prompt
                use_collectivebrain: Some(false),
                temperature: 0.7,
                max_tokens: Some(512),
                images: None,
                agent_id: Some("system:dream".to_string()),
                task_state: Some(TaskStateEnvelope {
                    task_id: None,
                    objective: "Synthesize a grounded epiphany from recent memory fragments."
                        .to_string(),
                    constraints: vec![
                        "Do not invent memories that were not provided.".to_string(),
                        "Prefer concise, high-signal synthesis over theatrical language."
                            .to_string(),
                    ],
                    success_criteria: vec![
                        "Identify a useful pattern, contradiction, or insight.".to_string(),
                        "Produce an insight safe to store as a memory artifact.".to_string(),
                    ],
                    declared_unknowns: vec![],
                    urgency: Some("low".to_string()),
                    intent_priority_score: Some(0.58),
                    authority_shrink_level: Some(0.22),
                    canon_anchor_weight: Some(0.78),
                    predicted_failure_modes: vec!["MEMORY".to_string(), "RETRIEVAL".to_string()],
                }),
            };

            // 3. Complete the request using the router
            match state.router.route(&req).await {
                Ok(response) => {
                    let text = response.reply.trim();
                    tracing::info!("✨ Dream Epiphany synthesis complete");

                    // 4. Save the new Epiphany to memory with high importance
                    let epiphany = MemoryEntry {
                        id: None,
                        content: format!("Dream Epiphany: {}", text),
                        source: "dream_state".to_string(),
                        importance: 0.9, // high importance for synthesized epiphanies
                        created_at: None,
                        namespace: "default".to_string(),
                        tags: vec!["epiphany".to_string(), "dream".to_string()],
                        domain: Default::default(),
                        confidence: 1.0,
                        version: 1,
                        superseded_by: None,
                        key: None,
                        raw_artifact: None,
                        tier: None,
                        retrieval_count: 0,
                        last_retrieved_at: None,
                    };

                    if let Err(e) = state.memory_store.write(epiphany).await {
                        tracing::error!(error = %e, "Dream State failed to save epiphany");
                    } else {
                        // 5. Reward the Dream State agent for a successful synthesis
                        let reward = 0.5_f32; // grant 0.5 credits for each epiphany
                        let _ = state
                            .economy
                            .record_transaction(
                                "system:dream",
                                reward,
                                TransactionType::Earn,
                                "Epiphany Synthesis Reward",
                            )
                            .await;
                    }
                }
                Err(e) => {
                    tracing::error!(error = %e, "Dream State failed to synthesise insights");
                }
            }
        }
    })
}
