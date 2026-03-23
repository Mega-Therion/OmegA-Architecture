use std::sync::Arc;
use std::time::Duration;
use tokio::fs;
use tokio::time;

use crate::state::AppState;
use omega_core::memory::MemoryEntry;

/// Spawns a background task for Autonomous Principle Evolution.
///
/// It periodically scans for high-importance "Epiphanies" in memory and
/// integrates the best ones into the system prompt file.
pub fn spawn_correction_task(
    state: Arc<AppState>,
    interval: Duration,
) -> tokio::task::JoinHandle<()> {
    tokio::spawn(async move {
        // Delay slightly after boot
        time::sleep(Duration::from_secs(45)).await;

        let mut ticker = time::interval(interval);

        loop {
            ticker.tick().await;

            tracing::info!(
                "⚖️  Self-Correction: Evaluating recent epiphanies for principle evolution..."
            );

            // 1. Fetch recent high-importance epiphanies
            let epiphanies = match state.memory_store.search("epiphany", 5).await {
                Ok(m) => m,
                Err(e) => {
                    tracing::error!(error = %e, "Self-Correction failed to fetch epiphanies");
                    continue;
                }
            };

            let valid_epiphanies: Vec<MemoryEntry> = epiphanies
                .into_iter()
                .filter(|m| m.content.starts_with("Dream Epiphany:") && m.importance >= 0.85)
                .collect();

            if valid_epiphanies.is_empty() {
                continue;
            }

            // 2. Draft a new Principle block
            let mut principles_text = String::from("\n## Autonomous Principles (Ratified)\n");
            for ep in valid_epiphanies {
                principles_text.push_str(&format!(
                    "- {}\n",
                    ep.content.replace("Dream Epiphany: ", "")
                ));
            }

            // 3. Update the SYSTEM_PROMPT.md file (appending for now as a simple way)
            let path = &state.config.omega_system_prompt_path;

            // Ensure directory exists
            if let Some(parent) = std::path::Path::new(path).parent() {
                let _ = fs::create_dir_all(parent).await;
            }

            // Read existing or create new
            let current_content = match fs::read_to_string(path).await {
                Ok(c) => c,
                Err(_) => String::from(
                    "# OMEGA SYSTEM PROMPT\n\nYou are OmegA, a self-evolving sovereign AI.\n",
                ),
            };

            // Only update if principles have changed
            if !current_content.contains("Autonomous Principles (Ratified)")
                || current_content.len() < 500
            // force refresh if small
            {
                let mut new_content = current_content;
                // Remove old principles section if it exists to replace it
                if let Some(pos) = new_content.find("\n## Autonomous Principles (Ratified)\n") {
                    new_content.truncate(pos);
                }
                new_content.push_str(&principles_text);

                if let Err(e) = fs::write(path, new_content).await {
                    tracing::error!(error = %e, path = %path, "Self-Correction failed to write system prompt");
                } else {
                    tracing::info!("📜 System Prompt updated with new autonomous principles.");
                }
            }
        }
    })
}
