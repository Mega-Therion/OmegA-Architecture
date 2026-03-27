use crate::{
    cli::ConfigAction,
    client::GatewayClient,
    config::{config_path, history_path, CliConfig},
    ui,
};

pub async fn run(
    action: ConfigAction,
    cfg: &CliConfig,
    client: &GatewayClient,
) -> anyhow::Result<()> {
    match action {
        ConfigAction::Show => show(cfg),
        ConfigAction::Link {
            gateway_url,
            token,
            mode,
            temperature,
            timeout_secs,
        } => link(gateway_url, token, mode, temperature, timeout_secs, cfg).await,
        ConfigAction::Doctor => doctor(client, cfg).await,
    }
}

fn show(cfg: &CliConfig) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Config");

    let path = config_path()
        .map(|p| p.display().to_string())
        .unwrap_or_else(|| "~/.omega/config.toml".to_string());

    ui::print_kv_table(
        "Resolved configuration",
        &[
            ("config_path", path),
            (
                "history_path",
                history_path()
                    .map(|p| p.display().to_string())
                    .unwrap_or_else(|| "~/.omega/chat.history".to_string()),
            ),
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

    Ok(())
}

async fn link(
    gateway_url: String,
    token: Option<String>,
    mode: Option<String>,
    temperature: Option<f32>,
    timeout_secs: Option<u64>,
    current: &CliConfig,
) -> anyhow::Result<()> {
    let mut next = current.clone();
    next.gateway.url = gateway_url;
    next.gateway.token = token.unwrap_or_default();

    if let Some(mode) = mode {
        next.defaults.mode = mode;
    }
    if let Some(temperature) = temperature {
        next.defaults.temperature = temperature;
    }
    if let Some(timeout_secs) = timeout_secs {
        next.defaults.timeout_secs = timeout_secs;
    }

    let saved_path = next.save()?;
    ui::print_banner(&next);
    ui::print_section("Link");
    ui::print_kv_table(
        "Saved configuration",
        &[
            ("config_path", saved_path.display().to_string()),
            ("gateway_url", next.gateway.url.clone()),
            (
                "gateway_token",
                if next.gateway.token.is_empty() {
                    "not set".to_string()
                } else {
                    "set".to_string()
                },
            ),
            ("mode", next.defaults.mode.clone()),
        ],
    );

    let linked_client = GatewayClient::new(next.gateway.url.clone(), next.gateway.token.clone());
    match linked_client.health().await {
        Ok(health) => {
            ui::print_kv_table(
                "Live gateway",
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
        Err(err) => {
            println!("Gateway link saved, but the live health check failed: {err}");
        }
    }

    Ok(())
}

async fn doctor(client: &GatewayClient, cfg: &CliConfig) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Doctor");

    let health = client.health().await;
    let status = client.status().await.ok();

    match health {
        Ok(health) => {
            ui::print_kv_table(
                "Link health",
                &[
                    ("service", health.service),
                    ("version", health.version),
                    (
                        "health",
                        if health.ok { "ok" } else { "degraded" }.to_string(),
                    ),
                    ("gateway_url", cfg.gateway.url.clone()),
                ],
            );
        }
        Err(err) => {
            println!("Gateway health check failed: {err}");
        }
    }

    if let Some(status) = status {
        ui::print_kv_table(
            "Resolved status",
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

    Ok(())
}
