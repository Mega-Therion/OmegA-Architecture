use crate::client::GatewayClient;
use futures_util::StreamExt;
use indicatif::{ProgressBar, ProgressStyle};
use owo_colors::OwoColorize;
use std::io::{self, Write};

pub async fn run(client: &GatewayClient, prompt: Vec<String>, mode: &str) -> anyhow::Result<()> {
    if prompt.is_empty() {
        anyhow::bail!("prompt cannot be empty");
    }
    let text = prompt.join(" ");

    // Create a branded spinner
    let pb = ProgressBar::new_spinner();
    pb.set_style(
        ProgressStyle::with_template("{spinner:.magenta} {msg}")
            .unwrap()
            .tick_chars("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"),
    );
    pb.set_message(format!("{} is thinking...", "Ω".bright_purple().bold()));
    pb.enable_steady_tick(std::time::Duration::from_millis(80));

    let mut stream = client.stream(&text, mode).await?;
    pb.finish_and_clear();

    print!("{} ", "Ω".bright_purple().bold());
    io::stdout().flush()?;

    let mut full_response = String::new();
    while let Some(chunk_result) = stream.next().await {
        match chunk_result {
            Ok(chunk) => {
                print!("{}", chunk);
                io::stdout().flush()?;
                full_response.push_str(&chunk);
            }
            Err(e) => {
                eprintln!("\n{}: {}", "Error".red().bold(), e);
                break;
            }
        }
    }
    println!();

    Ok(())
}
