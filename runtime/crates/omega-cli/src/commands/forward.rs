use crate::client::GatewayClient;
use crate::{config::CliConfig, ui};

pub async fn run(
    client: &GatewayClient,
    prompt: Vec<String>,
    mode: &str,
    cfg: &CliConfig,
) -> anyhow::Result<()> {
    if prompt.is_empty() {
        anyhow::bail!("prompt cannot be empty");
    }
    ui::print_banner(cfg);
    ui::print_section("Forward");
    let text = prompt.join(" ");
    let response = client.chat(&text, mode).await?;
    println!("{response}");
    Ok(())
}
