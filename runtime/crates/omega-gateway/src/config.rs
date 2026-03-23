use figment::{
    providers::{Env, Serialized},
    Figment,
};
use serde::{Deserialize, Serialize};

/// Gateway configuration. All fields map to `OMEGA_*` environment variables.
/// The Python gateway uses pydantic-settings with env_prefix="OMEGA_", which
/// strips the prefix. Here we read vars as-is (already OMEGA_-prefixed) via
/// figment Env::raw() and match field names to the full env var name lowercased.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GatewayConfig {
    /// Runtime profile. Env: OMEGA_RUNTIME_PROFILE
    /// "smoke-test" strips the system down to the cheapest useful path for
    /// compilation and basic health checks.
    #[serde(default = "default_runtime_profile")]
    pub omega_runtime_profile: String,

    // ---- Auth ----------------------------------------------------------------
    /// Bearer token clients must supply. Env: OMEGA_API_BEARER_TOKEN
    /// Empty string = permissive mode (auth skipped). Default: "".
    #[serde(default)]
    pub omega_api_bearer_token: String,

    // ---- OpenAI / cloud ------------------------------------------------------
    /// OpenAI API key. Env: OMEGA_OPENAI_API_KEY
    #[serde(default)]
    pub omega_openai_api_key: String,
    /// OpenAI base URL. Env: OMEGA_OPENAI_BASE_URL
    #[serde(default = "default_openai_base_url")]
    pub omega_openai_base_url: String,
    /// Default model (OpenAI). Env: OMEGA_MODEL
    #[serde(default = "default_model")]
    pub omega_model: String,

    // ---- Local / Ollama ------------------------------------------------------
    /// Ollama base URL. Env: OMEGA_LOCAL_BASE_URL
    #[serde(default = "default_local_base_url")]
    pub omega_local_base_url: String,
    /// Ollama model name. Env: OMEGA_LOCAL_MODEL
    #[serde(default = "default_local_model")]
    pub omega_local_model: String,
    /// Codex CLI binary path. Env: OMEGA_CODEX_CLI_PATH
    #[serde(default = "default_codex_cli_path")]
    pub omega_codex_cli_path: String,
    /// Optional Codex CLI model override. Env: OMEGA_CODEX_CLI_MODEL
    #[serde(default)]
    pub omega_codex_cli_model: String,
    /// Claude CLI binary path. Env: OMEGA_CLAUDE_CLI_PATH
    #[serde(default = "default_claude_cli_path")]
    pub omega_claude_cli_path: String,
    /// Optional Claude CLI model override. Env: OMEGA_CLAUDE_CLI_MODEL
    #[serde(default)]
    pub omega_claude_cli_model: String,
    /// Gemini CLI binary path. Env: OMEGA_GEMINI_CLI_PATH
    #[serde(default = "default_gemini_cli_path")]
    pub omega_gemini_cli_path: String,
    /// Optional Gemini CLI model override. Env: OMEGA_GEMINI_CLI_MODEL
    #[serde(default)]
    pub omega_gemini_cli_model: String,
    /// HOME passed to CLI-backed providers. Env: OMEGA_CLI_HOME_DIR
    #[serde(default = "default_cli_home_dir")]
    pub omega_cli_home_dir: String,
    /// Timeout for CLI-backed providers. Env: OMEGA_CLI_TIMEOUT_SECS
    #[serde(default = "default_cli_timeout")]
    pub omega_cli_timeout_secs: u64,
    /// Allow background autonomy loops. Env: OMEGA_ENABLE_BACKGROUND_TASKS
    #[serde(default)]
    pub omega_enable_background_tasks: bool,
    /// Allow federated gAIng memory. Env: OMEGA_ENABLE_FEDERATED_MEMORY
    #[serde(default)]
    pub omega_enable_federated_memory: bool,

    // ---- Anthropic -----------------------------------------------------------
    /// Anthropic API key. Env: OMEGA_ANTHROPIC_API_KEY
    #[serde(default)]
    pub omega_anthropic_api_key: String,
    /// Anthropic model. Env: OMEGA_ANTHROPIC_MODEL
    #[serde(default = "default_anthropic_model")]
    pub omega_anthropic_model: String,
    /// Anthropic base URL (override). Env: OMEGA_ANTHROPIC_BASE_URL
    #[serde(default = "default_anthropic_base_url")]
    pub omega_anthropic_base_url: String,

    // ---- Google / Gemini -----------------------------------------------------
    /// Gemini API key. Env: OMEGA_GEMINI_API_KEY
    #[serde(default)]
    pub omega_gemini_api_key: String,
    /// Gemini model. Env: OMEGA_GEMINI_MODEL
    #[serde(default = "default_gemini_model")]
    pub omega_gemini_model: String,
    /// Gemini base URL (override). Env: OMEGA_GEMINI_BASE_URL
    #[serde(default = "default_gemini_base_url")]
    pub omega_gemini_base_url: String,

    // ---- Perplexity ----------------------------------------------------------
    /// Perplexity API key. Env: OMEGA_PERPLEXITY_API_KEY
    #[serde(default)]
    pub omega_perplexity_api_key: String,
    /// Perplexity model. Env: OMEGA_PERPLEXITY_MODEL
    #[serde(default = "default_perplexity_model")]
    pub omega_perplexity_model: String,
    /// Perplexity base URL. Env: OMEGA_PERPLEXITY_BASE_URL
    #[serde(default = "default_perplexity_base_url")]
    pub omega_perplexity_base_url: String,

    // ---- DeepSeek ------------------------------------------------------------
    /// DeepSeek API key. Env: OMEGA_DEEPSEEK_API_KEY
    #[serde(default)]
    pub omega_deepseek_api_key: String,
    /// DeepSeek base URL. Env: OMEGA_DEEPSEEK_BASE_URL
    #[serde(default = "default_deepseek_base_url")]
    pub omega_deepseek_base_url: String,
    /// DeepSeek model. Env: OMEGA_DEEPSEEK_MODEL
    #[serde(default = "default_deepseek_model")]
    pub omega_deepseek_model: String,

    // ---- xAI / Grok ----------------------------------------------------------
    /// xAI API key. Env: OMEGA_XAI_API_KEY
    #[serde(default)]
    pub omega_xai_api_key: String,
    /// xAI base URL. Env: OMEGA_XAI_BASE_URL
    #[serde(default = "default_xai_base_url")]
    pub omega_xai_base_url: String,
    /// xAI model. Env: OMEGA_XAI_MODEL
    #[serde(default = "default_xai_model")]
    pub omega_xai_model: String,

    // ---- Infrastructure ------------------------------------------------------
    /// Database URL. Env: OMEGA_DB_URL
    #[serde(default)]
    pub omega_db_url: String,
    /// Log level. Env: OMEGA_LOG_LEVEL
    #[serde(default = "default_log_level")]
    pub omega_log_level: String,
    /// Brain base URL (proxy target). Env: OMEGA_BRAIN_BASE_URL
    #[serde(default = "default_brain_base_url")]
    pub omega_brain_base_url: String,
    /// Bridge base URL. Env: OMEGA_BRIDGE_BASE_URL
    /// Defaults to brain_base_url with :8080 → :8000 substitution if not set.
    pub omega_bridge_base_url: Option<String>,
    /// Internal service token. Env: OMEGA_INTERNAL_TOKEN
    #[serde(default)]
    pub omega_internal_token: String,

    // ---- Server --------------------------------------------------------------
    /// HTTP port to listen on. Env: OMEGA_PORT
    #[serde(default = "default_port")]
    pub omega_port: u16,
    /// Request timeout in seconds. Env: OMEGA_TIMEOUT_SECS
    #[serde(default = "default_timeout")]
    pub omega_timeout_secs: u64,
    /// Path to a dynamic system prompt file. Env: OMEGA_SYSTEM_PROMPT_PATH
    #[serde(default = "default_system_prompt_path")]
    pub omega_system_prompt_path: String,
    /// Path to identity.yaml. Env: OMEGA_IDENTITY_YAML_PATH
    #[serde(default = "default_identity_yaml_path")]
    pub omega_identity_yaml_path: String,
    /// Separate SQLite DB for the trace store (avoids migration table conflicts
    /// when memory and trace migrators share the same DB). Env: OMEGA_TRACE_DB_URL
    /// Defaults to in-memory SQLite so it never conflicts with memory.db.
    #[serde(default = "default_trace_db_url")]
    pub omega_trace_db_url: String,
}

// ---- Default value functions ------------------------------------------------

fn default_openai_base_url() -> String {
    "https://api.openai.com/v1".to_string()
}
fn default_runtime_profile() -> String {
    "smoke-test".to_string()
}
fn default_model() -> String {
    "gpt-4o-mini".to_string()
}
fn default_local_base_url() -> String {
    "http://localhost:11434/v1".to_string()
}
fn default_local_model() -> String {
    "llama3.2:3b".to_string()
}
fn default_codex_cli_path() -> String {
    "/home/mega/.nvm/versions/node/v22.22.0/bin/codex".to_string()
}
fn default_claude_cli_path() -> String {
    "/home/mega/.local/bin/claude".to_string()
}
fn default_gemini_cli_path() -> String {
    "/home/mega/.nvm/versions/node/v22.22.0/bin/gemini".to_string()
}
fn default_cli_home_dir() -> String {
    "/home/mega".to_string()
}
fn default_cli_timeout() -> u64 {
    120
}
fn default_anthropic_model() -> String {
    "claude-3-5-haiku-20241022".to_string()
}
fn default_anthropic_base_url() -> String {
    "https://api.anthropic.com".to_string()
}
fn default_gemini_model() -> String {
    "gemini-2.5-flash-lite".to_string()
}
fn default_gemini_base_url() -> String {
    "https://generativelanguage.googleapis.com".to_string()
}
fn default_perplexity_model() -> String {
    "llama-3-sonar-large-32k-online".to_string()
}
fn default_perplexity_base_url() -> String {
    "https://api.perplexity.ai".to_string()
}
fn default_deepseek_base_url() -> String {
    "https://api.deepseek.com".to_string()
}
fn default_deepseek_model() -> String {
    "deepseek-chat".to_string()
}
fn default_xai_base_url() -> String {
    "https://api.x.ai/v1".to_string()
}
fn default_xai_model() -> String {
    "grok-beta".to_string()
}
fn default_brain_base_url() -> String {
    "http://localhost:8080".to_string()
}
fn default_log_level() -> String {
    "INFO".to_string()
}
fn default_port() -> u16 {
    8787
}
fn default_timeout() -> u64 {
    30
}
fn default_system_prompt_path() -> String {
    "/var/lib/omega/SYSTEM_PROMPT.md".to_string()
}
fn default_identity_yaml_path() -> String {
    "/home/mega/.omega/identity.yaml".to_string()
}
fn default_trace_db_url() -> String {
    "sqlite::memory:".to_string()
}

impl GatewayConfig {
    pub fn load() -> anyhow::Result<Self> {
        let config: GatewayConfig = Figment::new()
            .merge(Serialized::defaults(GatewayConfig::default_values()))
            // Read all env vars as-is; OMEGA_ prefix already in var names.
            .merge(Env::raw())
            .extract()?;
        Ok(config)
    }

    fn default_values() -> Self {
        GatewayConfig {
            omega_runtime_profile: default_runtime_profile(),
            omega_api_bearer_token: String::new(),
            omega_openai_api_key: String::new(),
            omega_openai_base_url: default_openai_base_url(),
            omega_model: default_model(),
            omega_local_base_url: default_local_base_url(),
            omega_local_model: default_local_model(),
            omega_codex_cli_path: default_codex_cli_path(),
            omega_codex_cli_model: String::new(),
            omega_claude_cli_path: default_claude_cli_path(),
            omega_claude_cli_model: String::new(),
            omega_gemini_cli_path: default_gemini_cli_path(),
            omega_gemini_cli_model: String::new(),
            omega_cli_home_dir: default_cli_home_dir(),
            omega_cli_timeout_secs: default_cli_timeout(),
            omega_enable_background_tasks: false,
            omega_enable_federated_memory: false,
            omega_anthropic_api_key: String::new(),
            omega_anthropic_model: default_anthropic_model(),
            omega_anthropic_base_url: default_anthropic_base_url(),
            omega_gemini_api_key: String::new(),
            omega_gemini_model: default_gemini_model(),
            omega_gemini_base_url: default_gemini_base_url(),
            omega_perplexity_api_key: String::new(),
            omega_perplexity_model: default_perplexity_model(),
            omega_perplexity_base_url: default_perplexity_base_url(),
            omega_deepseek_api_key: String::new(),
            omega_deepseek_base_url: default_deepseek_base_url(),
            omega_deepseek_model: default_deepseek_model(),
            omega_xai_api_key: String::new(),
            omega_xai_base_url: default_xai_base_url(),
            omega_xai_model: default_xai_model(),
            omega_db_url: String::new(),
            omega_log_level: default_log_level(),
            omega_brain_base_url: default_brain_base_url(),
            omega_bridge_base_url: None,
            omega_internal_token: String::new(),
            omega_port: default_port(),
            omega_timeout_secs: default_timeout(),
            omega_system_prompt_path: default_system_prompt_path(),
            omega_identity_yaml_path: default_identity_yaml_path(),
            omega_trace_db_url: default_trace_db_url(),
        }
    }

    /// Returns the effective Bridge base URL.
    /// Uses OMEGA_BRIDGE_BASE_URL if set, otherwise derives from brain URL.
    pub fn bridge_base_url(&self) -> String {
        self.omega_bridge_base_url
            .clone()
            .filter(|s| !s.is_empty())
            .unwrap_or_else(|| self.omega_brain_base_url.replace(":8080", ":8000"))
    }

    /// Returns true when authentication is enabled (token is non-empty).
    pub fn auth_enabled(&self) -> bool {
        !self.omega_api_bearer_token.is_empty()
    }

    pub fn is_smoke_test_profile(&self) -> bool {
        matches!(
            self.omega_runtime_profile
                .trim()
                .to_ascii_lowercase()
                .as_str(),
            "" | "smoke" | "smoke-test" | "compile" | "compile-only"
        )
    }

    pub fn effective_cli_home_dir(&self) -> String {
        if self.is_smoke_test_profile() {
            "/home/mega/.omega/cli-smoke".to_string()
        } else if self.omega_cli_home_dir.trim().is_empty() {
            default_cli_home_dir()
        } else {
            self.omega_cli_home_dir.clone()
        }
    }

    pub fn effective_codex_cli_model(&self) -> String {
        if self.is_smoke_test_profile() || self.omega_codex_cli_model.trim().is_empty() {
            "gpt-5.1-codex-mini".to_string()
        } else {
            self.omega_codex_cli_model.clone()
        }
    }

    pub fn effective_claude_cli_model(&self) -> String {
        if self.is_smoke_test_profile() || self.omega_claude_cli_model.trim().is_empty() {
            "claude-3-5-haiku-20241022".to_string()
        } else {
            self.omega_claude_cli_model.clone()
        }
    }

    pub fn effective_gemini_cli_model(&self) -> String {
        if self.is_smoke_test_profile() || self.omega_gemini_cli_model.trim().is_empty() {
            "gemini-2.5-flash-lite".to_string()
        } else {
            self.omega_gemini_cli_model.clone()
        }
    }

    pub fn background_tasks_enabled(&self) -> bool {
        !self.is_smoke_test_profile() && self.omega_enable_background_tasks
    }

    pub fn federated_memory_enabled(&self) -> bool {
        !self.is_smoke_test_profile() && self.omega_enable_federated_memory
    }

    /// Returns the effective SQLite DB URL.
    ///
    /// Uses `OMEGA_DB_URL` if set and non-empty; otherwise falls back to
    /// `sqlite:///home/mega/.omega/memory.db` so the gateway has a sensible
    /// default without explicit configuration.
    pub fn omega_db_url_or_default(&self) -> String {
        if self.omega_db_url.is_empty() {
            "sqlite:///home/mega/.omega/memory.db".to_string()
        } else {
            self.omega_db_url.clone()
        }
    }

    /// Returns "sqlite" or "pgvector" based on the db URL.
    pub fn db_type(&self) -> &str {
        if self.omega_db_url.contains("sqlite") {
            "sqlite"
        } else {
            "pgvector"
        }
    }
}
