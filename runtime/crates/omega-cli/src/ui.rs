use comfy_table::{presets::UTF8_FULL, Cell, Color, ContentArrangement, Row, Table};
use owo_colors::OwoColorize;

use crate::config::CliConfig;

pub fn print_banner(cfg: &CliConfig) {
    let mut table = Table::new();
    table.load_preset(UTF8_FULL);
    table.set_content_arrangement(ContentArrangement::DynamicFullWidth);
    table.set_header(vec![
        Cell::new("OmegA").fg(Color::Magenta),
        Cell::new("Sovereign. Persistent. Self-Knowing.").fg(Color::Yellow),
    ]);
    table.add_row(Row::from(vec![
        Cell::new("Gateway").fg(Color::Cyan),
        Cell::new(cfg.gateway.url.clone()).fg(Color::White),
    ]));
    table.add_row(Row::from(vec![
        Cell::new("Mode").fg(Color::Cyan),
        Cell::new(cfg.defaults.mode.clone()).fg(Color::White),
    ]));
    table.add_row(Row::from(vec![
        Cell::new("Auth").fg(Color::Cyan),
        Cell::new(if cfg.gateway.token.is_empty() {
            "linked without token"
        } else {
            "linked"
        })
        .fg(Color::Green),
    ]));
    table.add_row(Row::from(vec![
        Cell::new("Surface").fg(Color::Cyan),
        Cell::new(
            "ask · briefing · inspect · pulse · providers · history · chat · forward · gains · warp · config",
        )
            .fg(Color::White),
    ]));
    println!("{}", "Ω OmegA".bright_magenta().bold());
    println!("{}", "Sovereign. Persistent. Self-Knowing.".bright_yellow());
    println!("{table}");
}

pub fn print_section(title: &str) {
    println!();
    println!("{}", title.bright_magenta().bold());
}

pub fn print_kv_table(title: &str, rows: &[(impl AsRef<str>, impl AsRef<str>)]) {
    let mut table = Table::new();
    table.load_preset(UTF8_FULL);
    table.set_content_arrangement(ContentArrangement::DynamicFullWidth);
    table.set_header(vec![
        Cell::new(title).fg(Color::Magenta),
        Cell::new("Value").fg(Color::Yellow),
    ]);

    for (key, value) in rows {
        table.add_row(Row::from(vec![
            Cell::new(key.as_ref()).fg(Color::Cyan),
            Cell::new(value.as_ref()).fg(Color::White),
        ]));
    }

    println!("{table}");
}

pub fn print_bullets(title: &str, items: &[String]) {
    println!();
    println!("{}", title.bright_magenta().bold());
    for item in items {
        println!("  {}", format!("• {}", item).bright_white());
    }
}
