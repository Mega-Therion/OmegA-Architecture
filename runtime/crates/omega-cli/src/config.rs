use figment::{
    providers::{Env, Format, Serialized, Toml},
    Figment,
};
use serde::{Deserialize, Serialize};
use std::{fs, path::PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GatewaySection {
    #[serde(default = "default_gateway_url")]
    pub url: String,
    #[serde(default)]
    pub token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DefaultsSection {
    #[serde(default = "default_mode")]
    pub mode: String,
    #[serde(default = "default_temperature")]
    pub temperature: f32,
    #[serde(default = "default_timeout")]
    pub timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CliConfig {
    pub gateway: GatewaySection,
    pub defaults: DefaultsSection,
}

fn default_gateway_url() -> String {
    "http://localhost:8787".to_string()
}

fn default_mode() -> String {
    "omega".to_string()
}

fn default_temperature() -> f32 {
    0.4
}

fn default_timeout() -> u64 {
    30
}

impl Default for GatewaySection {
    fn default() -> Self {
        Self {
            url: default_gateway_url(),
            token: String::new(),
        }
    }
}

impl Default for DefaultsSection {
    fn default() -> Self {
        Self {
            mode: default_mode(),
            temperature: default_temperature(),
            timeout_secs: default_timeout(),
        }
    }
}

impl Default for CliConfig {
    fn default() -> Self {
        Self {
            gateway: GatewaySection::default(),
            defaults: DefaultsSection::default(),
        }
    }
}

impl CliConfig {
    pub fn load() -> anyhow::Result<Self> {
        let config_path = config_path();

        let mut fig = Figment::new().merge(Serialized::defaults(CliConfig::default()));

        if let Some(path) = config_path {
            fig = fig.merge(Toml::file(path));
        }

        // Environment overrides: OMEGA_GATEWAY_URL, OMEGA_API_BEARER_TOKEN
        fig = fig.merge(Env::raw().map(|key| match key.as_str() {
            "OMEGA_GATEWAY_URL" => "gateway.url".into(),
            "OMEGA_API_BEARER_TOKEN" => "gateway.token".into(),
            other => other.to_lowercase().replace('_', ".").into(),
        }));

        let config: CliConfig = fig.extract()?;
        Ok(config)
    }

    pub fn save(&self) -> anyhow::Result<PathBuf> {
        let path = config_file_path().ok_or_else(|| anyhow::anyhow!("HOME is not set"))?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }
        let serialized = toml::to_string_pretty(self)?;
        fs::write(&path, serialized)?;
        Ok(path)
    }
}

pub fn config_path() -> Option<PathBuf> {
    let path = config_file_path()?;
    if path.exists() {
        Some(path)
    } else {
        None
    }
}

pub fn history_path() -> Option<PathBuf> {
    let home = std::env::var("HOME").ok()?;
    Some(PathBuf::from(home).join(".omega").join("chat.history"))
}

fn config_file_path() -> Option<PathBuf> {
    let home = std::env::var("HOME").ok()?;
    Some(PathBuf::from(home).join(".omega").join("config.toml"))
}
