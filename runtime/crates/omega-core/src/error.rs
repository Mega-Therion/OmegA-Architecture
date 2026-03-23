/// Top-level error enum that unifies all subsystem errors.
#[derive(Debug, thiserror::Error)]
pub enum OmegaError {
    #[error("provider error: {0}")]
    Provider(#[from] ProviderError),

    #[error("auth error: {0}")]
    Auth(#[from] AuthError),

    #[error("memory error: {0}")]
    Memory(#[from] MemoryError),

    #[error("config error: {0}")]
    Config(#[from] ConfigError),

    #[error("routing failed after all providers exhausted")]
    RoutingExhausted,
}

#[derive(Debug, thiserror::Error)]
pub enum ProviderError {
    #[error("rate limited (429)")]
    RateLimited,

    #[error("quota exceeded (402)")]
    QuotaExceeded,

    #[error("invalid provider request ({status}): {body}")]
    InvalidRequest { status: u16, body: String },

    #[error("provider unavailable: {status}")]
    Unavailable { status: u16 },

    #[error("request failed: {0}")]
    Request(#[from] reqwest::Error),

    #[error("response parse error: {0}")]
    Parse(String),
}

impl ProviderError {
    /// Returns true if we should try the next provider in the failover chain.
    pub fn is_retriable(&self) -> bool {
        matches!(
            self,
            ProviderError::RateLimited
                | ProviderError::QuotaExceeded
                | ProviderError::Unavailable { .. }
        )
    }
}

#[derive(Debug, thiserror::Error)]
pub enum AuthError {
    #[error("missing authorization header")]
    Missing,
    #[error("invalid bearer token")]
    Invalid,
}

#[derive(Debug, thiserror::Error)]
pub enum ConfigError {
    #[error("missing required env var: {0}")]
    MissingVar(String),
    #[error("invalid value for {key}: {reason}")]
    InvalidValue { key: String, reason: String },
}

#[derive(Debug, thiserror::Error)]
pub enum MemoryError {
    #[error("write failed: {0}")]
    Write(String),
    #[error("read failed: {0}")]
    Read(String),
    #[error("search failed: {0}")]
    Search(String),
    #[error("not found: {0}")]
    NotFound(String),
    #[error("connection failed: {0}")]
    Connection(String),
    #[error("migration failed: {0}")]
    Migration(String),
}

#[derive(Debug, thiserror::Error)]
pub enum AgentError {
    #[error("dispatch failed: {0}")]
    Dispatch(String),
    #[error("timeout")]
    Timeout,
    #[error("agent not found: {0}")]
    NotFound(String),
}

#[derive(Debug, thiserror::Error)]
pub enum RouterError {
    #[error("provider error: {0}")]
    Provider(#[from] ProviderError),
    #[error("all providers exhausted; last error: {last:?}")]
    Exhausted { last: Option<ProviderError> },
}
