use crate::{client::GatewayClient, config::CliConfig, ui};

pub async fn run(client: &GatewayClient, cfg: &CliConfig) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Providers");

    let providers = client.providers().await?;
    let items = providers
        .providers
        .into_iter()
        .map(|p| {
            format!(
                "{} — {}",
                p.name,
                if p.enabled { "enabled" } else { "disabled" }
            )
        })
        .collect::<Vec<_>>();

    ui::print_bullets("Linked providers", &items);
    Ok(())
}
