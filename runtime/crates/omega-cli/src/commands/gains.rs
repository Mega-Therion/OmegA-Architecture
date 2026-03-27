use crate::client::GatewayClient;
use crate::{config::CliConfig, ui};

pub async fn run(client: &GatewayClient, mode: &str, cfg: &CliConfig) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Gains");
    let response = client
        .chat("Show me the collective accomplishments.", mode)
        .await?;
    println!("{response}");
    Ok(())
}
