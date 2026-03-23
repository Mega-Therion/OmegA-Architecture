use std::path::PathBuf;

use clap::{Parser, Subcommand};
use clap_complete::Shell;

#[derive(Parser)]
#[command(name = "omega", about = "Ω sovereign CLI", version)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Command>,
}

#[derive(Subcommand)]
pub enum Command {
    /// Route to best available agent
    Ask {
        #[arg(trailing_var_arg = true)]
        prompt: Vec<String>,
        #[arg(long, default_value = "omega")]
        mode: String,
    },
    /// Route directly to Claude
    AskClaude {
        #[arg(trailing_var_arg = true)]
        prompt: Vec<String>,
    },
    /// Route directly to Gemini
    AskGemini {
        #[arg(trailing_var_arg = true)]
        prompt: Vec<String>,
    },
    /// Activity summary
    Briefing,
    /// CPU/RAM vitals
    Pulse,
    /// Interactive multi-agent chat
    Chat {
        #[arg(short, long)]
        workspace: Option<PathBuf>,
    },
    /// Forward task to another agent
    Forward {
        #[arg(trailing_var_arg = true)]
        prompt: Vec<String>,
    },
    /// Show collective accomplishments
    Gains,
    /// Performance mode control
    Warp {
        #[command(subcommand)]
        action: WarpAction,
    },
    /// Generate shell completion scripts
    Completions {
        #[arg(value_enum)]
        shell: Shell,
    },
}

#[derive(Subcommand)]
pub enum WarpAction {
    /// Enable performance mode (stop non-essential services)
    Engage,
    /// Restore services
    Disengage,
}
