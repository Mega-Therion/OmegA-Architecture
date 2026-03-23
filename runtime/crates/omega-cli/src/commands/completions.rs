use clap::CommandFactory;
use clap_complete::{generate, Shell};

use crate::cli::Cli;

pub fn run(shell: Shell) -> anyhow::Result<()> {
    let mut cmd = Cli::command();
    generate(shell, &mut cmd, "omega-cli", &mut std::io::stdout());
    Ok(())
}
