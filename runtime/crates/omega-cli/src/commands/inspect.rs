use crate::{client::GatewayClient, config::CliConfig, ui};

pub async fn run(client: &GatewayClient, cfg: &CliConfig) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Inspect");

    let health = client.health().await.ok();
    let status = client.status().await.ok();
    let deep = client.deep_health().await.ok();
    let providers = client.providers().await.ok();

    ui::print_kv_table(
        "Local config",
        &[
            ("gateway_url", cfg.gateway.url.clone()),
            (
                "gateway_token",
                if cfg.gateway.token.is_empty() {
                    "not set".to_string()
                } else {
                    "set".to_string()
                },
            ),
            ("mode", cfg.defaults.mode.clone()),
            ("temperature", cfg.defaults.temperature.to_string()),
            ("timeout_secs", cfg.defaults.timeout_secs.to_string()),
        ],
    );

    if let Some(health) = health {
        ui::print_kv_table(
            "Gateway health",
            &[
                ("service", health.service),
                ("version", health.version),
                (
                    "health",
                    if health.ok { "ok" } else { "degraded" }.to_string(),
                ),
            ],
        );
    }

    if let Some(status) = status {
        ui::print_kv_table(
            "Resolved gateway",
            &[
                ("model", status.model),
                ("base_url", status.base_url),
                ("db", status.db),
                (
                    "auth",
                    if status.auth { "enabled" } else { "disabled" }.to_string(),
                ),
            ],
        );
    }

    if let Some(deep) = deep {
        ui::print_kv_table(
            "Deep health",
            &[
                ("state", deep.state),
                ("ok", if deep.ok { "true" } else { "false" }.to_string()),
                ("services", deep.services.to_string()),
            ],
        );
    }

    if let Some(providers) = providers {
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
        ui::print_bullets("Providers", &items);
    }

    Ok(())
}
