use std::{fs, path::Path};

use crate::{
    client::GatewayClient,
    config::{history_path, CliConfig},
    ui,
};
use owo_colors::OwoColorize;

pub async fn run(
    client: &GatewayClient,
    cfg: &CliConfig,
    search: Option<&str>,
    replay: Option<&str>,
    limit: usize,
    mode: &str,
) -> anyhow::Result<()> {
    ui::print_banner(cfg);
    ui::print_section("History");

    let entries = load_entries()?;
    if entries.is_empty() {
        println!("{}", "No saved chat history found yet.".bright_yellow());
        return Ok(());
    }

    let mut filtered = if let Some(query) = search {
        let needle = query.to_lowercase();
        entries
            .iter()
            .rev()
            .filter(|entry| entry.to_lowercase().contains(&needle))
            .cloned()
            .collect::<Vec<_>>()
    } else {
        entries.iter().rev().cloned().collect::<Vec<_>>()
    };

    if let Some(target) = replay {
        let entry = select_replay_target(&filtered, target)?;
        println!(
            "{}",
            format!("Replaying history entry: {}", preview(&entry)).bright_green()
        );
        crate::commands::ask::run(client, vec![entry], mode).await?;
        return Ok(());
    }

    filtered.truncate(limit);
    print_entries(&filtered);
    Ok(())
}

fn load_entries() -> anyhow::Result<Vec<String>> {
    let Some(path) = history_path() else {
        return Ok(Vec::new());
    };

    if !Path::new(&path).exists() {
        return Ok(Vec::new());
    }

    let content = fs::read_to_string(path)?;
    let entries = content
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    Ok(entries)
}

fn print_entries(entries: &[String]) {
    if entries.is_empty() {
        println!("{}", "No matching history entries found.".bright_yellow());
        return;
    }

    ui::print_bullets(
        "Recent prompts",
        &entries
            .iter()
            .enumerate()
            .map(|(idx, entry)| format!("{:>2}. {}", idx + 1, preview(entry)))
            .collect::<Vec<_>>(),
    );
}

fn preview(entry: &str) -> String {
    let mut single_line = entry.replace('\n', " ").replace('\r', " ");
    if single_line.len() > 96 {
        single_line.truncate(93);
        single_line.push_str("...");
    }
    single_line
}

fn select_replay_target(entries: &[String], target: &str) -> anyhow::Result<String> {
    if let Ok(index) = target.parse::<usize>() {
        if index == 0 || index > entries.len() {
            anyhow::bail!(
                "history index out of range: {} (available entries: 1..={})",
                index,
                entries.len()
            );
        }
        return Ok(entries[index - 1].clone());
    }

    let needle = target.to_lowercase();
    entries
        .iter()
        .find(|entry| entry.to_lowercase().contains(&needle))
        .cloned()
        .ok_or_else(|| anyhow::anyhow!("no history entry matched `{target}`"))
}
