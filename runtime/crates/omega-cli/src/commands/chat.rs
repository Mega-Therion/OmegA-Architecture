use std::path::PathBuf;

use crate::client::GatewayClient;

pub async fn run(_client: &GatewayClient, workspace: Option<PathBuf>) -> anyhow::Result<()> {
    if let Some(ws) = workspace {
        println!(
            "Interactive chat (workspace: {}) — not yet implemented.",
            ws.display()
        );
    } else {
        println!("Interactive chat — not yet implemented (Phase 2).");
    }
    Ok(())
}
