mod cli;
mod client;
mod commands;
mod config;
mod ui;

use clap::Parser;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use cli::{Cli, Command};
use client::GatewayClient;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("warn")))
        .with(tracing_subscriber::fmt::layer().with_writer(std::io::stderr))
        .init();

    let cfg = config::CliConfig::load().unwrap_or_default();
    let cli = Cli::parse();

    let gateway_client = GatewayClient::new(cfg.gateway.url.clone(), cfg.gateway.token.clone());

    match cli.command {
        None => {
            ui::print_banner(&cfg);
        }
        Some(Command::Ask { prompt, mode }) => {
            commands::ask::run(&gateway_client, prompt, &mode).await?;
        }
        Some(Command::AskClaude { prompt }) => {
            commands::ask::run(&gateway_client, prompt, "claude").await?;
        }
        Some(Command::AskGemini { prompt }) => {
            commands::ask::run(&gateway_client, prompt, "gemini").await?;
        }
        Some(Command::Briefing) => {
            commands::briefing::run(&gateway_client, &cfg.defaults.mode, &cfg).await?;
        }
        Some(Command::Inspect) => {
            commands::inspect::run(&gateway_client, &cfg).await?;
        }
        Some(Command::Pulse) => {
            commands::pulse::run(&gateway_client, &cfg).await?;
        }
        Some(Command::Providers) => {
            commands::providers::run(&gateway_client, &cfg).await?;
        }
        Some(Command::Chat { workspace }) => {
            commands::chat::run(&gateway_client, workspace, &cfg.defaults.mode, &cfg).await?;
        }
        Some(Command::Forward { prompt }) => {
            commands::forward::run(&gateway_client, prompt, &cfg.defaults.mode, &cfg).await?;
        }
        Some(Command::Gains) => {
            commands::gains::run(&gateway_client, &cfg.defaults.mode, &cfg).await?;
        }
        Some(Command::Warp { action }) => {
            commands::warp::run(action, &cfg).await?;
        }
        Some(Command::Completions { shell }) => {
            commands::completions::run(shell)?;
        }
        Some(Command::Config { action }) => {
            commands::config::run(action, &cfg, &gateway_client).await?;
        }
    }

    Ok(())
}
