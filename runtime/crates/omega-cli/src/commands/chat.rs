use std::path::PathBuf;

use crate::client::GatewayClient;
use crate::{
    cli::ConfigAction,
    config::{history_path, CliConfig},
    ui,
};
use owo_colors::OwoColorize;
use rustyline::{error::ReadlineError, DefaultEditor};

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
        "Type a message and press Enter. Use /help, /status, /inspect, /providers, /briefing, /pulse, /gains, or /exit."
            .bright_white()
    );
    println!(
        "{}",
        "Multiline input: end a line with `\\` to continue onto the next line.".bright_white()
    );

    let mut editor = DefaultEditor::new()?;
    if let Some(path) = history_path() {
        if path.exists() {
            let _ = editor.load_history(&path);
        }
    }

    let mut session_mode = mode.to_string();
    let mut input_buffer = String::new();
    let mut prompt = prompt_for(&session_mode, false);

    loop {
        let line = match editor.readline(&prompt) {
            Ok(line) => line,
            Err(ReadlineError::Interrupted) => {
                input_buffer.clear();
                prompt = prompt_for(&session_mode, false);
                println!();
                continue;
            }
            Err(ReadlineError::Eof) => {
                println!();
                break;
            }
            Err(err) => return Err(err.into()),
        };

        let trimmed = line.trim_end();
        if input_buffer.is_empty() && trimmed.is_empty() {
            continue;
        }

        if trimmed.ends_with('\\') {
            let part = trimmed.trim_end_matches('\\').trim_end();
            if !part.is_empty() {
                if !input_buffer.is_empty() {
                    input_buffer.push('\n');
                }
                input_buffer.push_str(part);
            }
            prompt = prompt_for(&session_mode, true);
            continue;
        }

        if !input_buffer.is_empty() {
            input_buffer.push('\n');
        }
        input_buffer.push_str(&line);

        let message = input_buffer.trim();
        if message.is_empty() {
            input_buffer.clear();
            prompt = prompt_for(&session_mode, false);
            continue;
        }

        let _ = editor.add_history_entry(message);
        match handle_command(message, client, cfg, &mut session_mode).await? {
            ChatCommandResult::Handled => {
                input_buffer.clear();
                prompt = prompt_for(&session_mode, false);
                continue;
            }
            ChatCommandResult::Exit => {
                break;
            }
            ChatCommandResult::PassThrough => {
                crate::commands::ask::run(client, vec![message.to_string()], &session_mode).await?;
            }
        }

        input_buffer.clear();
        prompt = prompt_for(&session_mode, false);
    }

    if let Some(path) = history_path() {
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        let _ = editor.save_history(&path);
    }

    Ok(())
}

fn prompt_for(mode: &str, multiline: bool) -> String {
    if multiline {
        format!("omega:{mode}...> ")
    } else {
        format!("omega:{mode}> ")
    }
}

async fn handle_command(
    message: &str,
    client: &GatewayClient,
    cfg: &CliConfig,
    session_mode: &mut String,
) -> anyhow::Result<ChatCommandResult> {
    if !message.starts_with('/') {
        return Ok(ChatCommandResult::PassThrough);
    }

    let parts = message.split_whitespace().collect::<Vec<_>>();
    let Some(command) = parts.first().copied() else {
        return Ok(ChatCommandResult::Handled);
    };

    match command {
        "/exit" | "/quit" => {
            println!("bye");
            return Ok(ChatCommandResult::Exit);
        }
        "/help" => {
            ui::print_section("Chat shortcuts");
            ui::print_bullets(
                "Available commands",
                &[
                    "/help - show shortcuts".to_string(),
                    "/status - show live gateway status".to_string(),
                    "/inspect - show a full local + live diagnostics panel".to_string(),
                    "/providers - list linked providers".to_string(),
                    "/doctor - verify the configured gateway link".to_string(),
                    "/briefing - run the briefing summary".to_string(),
                    "/pulse - show the health panel".to_string(),
                    "/gains - show accomplishments".to_string(),
                    "/mode [name] - view or change the session mode".to_string(),
                    "/config show - inspect local CLI settings".to_string(),
                    "/config doctor - verify the configured gateway link".to_string(),
                    "/config link <url> [token=...] [mode=...] [temperature=...] [timeout_secs=...]"
                        .to_string(),
                    "/exit - leave chat".to_string(),
                ],
            );
        }
        "/status" | "/pulse" => {
            crate::commands::pulse::run(client, cfg).await?;
        }
        "/inspect" => {
            crate::commands::inspect::run(client, cfg).await?;
        }
        "/providers" => {
            crate::commands::providers::run(client, cfg).await?;
        }
        "/doctor" => {
            crate::commands::config::run(ConfigAction::Doctor, cfg, client).await?;
        }
        "/briefing" => {
            crate::commands::briefing::run(client, session_mode, cfg).await?;
        }
        "/gains" => {
            crate::commands::gains::run(client, session_mode, cfg).await?;
        }
        "/mode" => {
            if let Some(mode) = parts.get(1) {
                *session_mode = (*mode).to_string();
                println!(
                    "{}",
                    format!("Session mode set to `{}`", session_mode).bright_green()
                );
            } else {
                println!(
                    "{}",
                    format!("Session mode: `{}`", session_mode).bright_cyan()
                );
            }
        }
        "/config" => {
            handle_config_command(&parts, client, cfg).await?;
        }
        other => {
            println!(
                "{}",
                format!("Unknown shortcut `{other}`. Try /help or type a normal message.")
                    .bright_red()
            );
        }
    }

    Ok(ChatCommandResult::Handled)
}

enum ChatCommandResult {
    Handled,
    PassThrough,
    Exit,
}

async fn handle_config_command(
    parts: &[&str],
    client: &GatewayClient,
    cfg: &CliConfig,
) -> anyhow::Result<()> {
    match parts.get(1).copied() {
        None | Some("show") => {
            crate::commands::config::run(ConfigAction::Show, cfg, client).await?;
        }
        Some("doctor") => {
            crate::commands::config::run(ConfigAction::Doctor, cfg, client).await?;
        }
        Some("link") => {
            let Some(gateway_url) = parts.get(2).copied() else {
                println!(
                    "{}",
                    "Usage: /config link <gateway_url> [token=...] [mode=...] [temperature=...] [timeout_secs=...]"
                        .bright_yellow()
                );
                return Ok(());
            };

            let mut token = None;
            let mut mode = None;
            let mut temperature = None;
            let mut timeout_secs = None;

            for arg in &parts[3..] {
                if let Some((key, value)) = arg.split_once('=') {
                    match key {
                        "token" => token = Some(value.to_string()),
                        "mode" => mode = Some(value.to_string()),
                        "temperature" => temperature = value.parse::<f32>().ok(),
                        "timeout" | "timeout_secs" => timeout_secs = value.parse::<u64>().ok(),
                        _ => {}
                    }
                }
            }

            crate::commands::config::run(
                ConfigAction::Link {
                    gateway_url: gateway_url.to_string(),
                    token,
                    mode,
                    temperature,
                    timeout_secs,
                },
                cfg,
                client,
            )
            .await?;
        }
        Some(other) => {
            println!(
                "{}",
                format!(
                    "Unknown config subcommand `{other}`. Try /config show, /config doctor, or /config link."
                )
                .bright_red()
            );
        }
    }

    Ok(())
}
