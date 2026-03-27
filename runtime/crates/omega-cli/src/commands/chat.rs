use std::path::PathBuf;

use crate::client::GatewayClient;
use crate::{config::CliConfig, ui};
use owo_colors::OwoColorize;
use tokio::io::{self, AsyncBufReadExt, AsyncWriteExt};

pub async fn run(
    client: &GatewayClient,
    workspace: Option<PathBuf>,
    mode: &str,
    cfg: &CliConfig,
) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("Interactive chat");

    if let Some(ws) = workspace {
        println!("{}", format!("Workspace: {}", ws.display()).bright_cyan());
    }

    println!(
        "{}",
        "Type a message and press Enter. Use /briefing, /pulse, /gains, or /exit.".bright_white()
    );

    let mut stdin = io::BufReader::new(io::stdin()).lines();
    let mut stdout = io::stdout();
    loop {
        stdout.write_all(b"\nomega> ").await?;
        stdout.flush().await?;

        let Some(line) = stdin.next_line().await? else {
            println!();
            break;
        };

        let text = line.trim();
        if text.is_empty() {
            continue;
        }
        if matches!(text, "/exit" | "/quit") {
            println!("bye");
            break;
        }
        if text == "/pulse" {
            crate::commands::pulse::run(client, cfg).await?;
            continue;
        }
        if text == "/briefing" {
            crate::commands::briefing::run(client, mode, cfg).await?;
            continue;
        }
        if text == "/gains" {
            crate::commands::gains::run(client, mode, cfg).await?;
            continue;
        }

        crate::commands::ask::run(client, vec![text.to_string()], mode).await?;
    }

    Ok(())
}
