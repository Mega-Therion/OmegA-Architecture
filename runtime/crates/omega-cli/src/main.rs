mod cli;
mod client;
mod commands;
mod config;

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
            // Default: show status / help.
            println!("Ω Sovereign CLI — run `omega --help` for commands.");
            println!("Gateway: {}", cfg.gateway.url);
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
            commands::briefing::run(&gateway_client).await?;
        }
        Some(Command::Pulse) => {
            commands::pulse::run().await?;
        }
        Some(Command::Chat { workspace }) => {
            commands::chat::run(&gateway_client, workspace).await?;
        }
        Some(Command::Forward { prompt }) => {
            commands::forward::run(&gateway_client, prompt).await?;
        }
        Some(Command::Gains) => {
            commands::gains::run(&gateway_client).await?;
        }
        Some(Command::Warp { action }) => {
            commands::warp::run(action).await?;
        }
        Some(Command::Completions { shell }) => {
            commands::completions::run(shell)?;
        }
    }

    Ok(())
}
