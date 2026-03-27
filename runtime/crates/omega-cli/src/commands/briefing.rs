use crate::client::GatewayClient;
use crate::{config::CliConfig, ui};

pub async fn run(client: &GatewayClient, mode: &str, cfg: &CliConfig) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Briefing");
    let response = client
        .chat("Give me an activity briefing summary.", mode)
        .await?;
    println!("{response}");
    Ok(())
}
