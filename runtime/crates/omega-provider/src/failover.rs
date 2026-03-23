use std::sync::Arc;
use std::time::{Duration, Instant};

use dashmap::DashMap;
use futures::stream::Stream;
use omega_core::{
    error::RouterError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider},
    router::Router,
};
use std::pin::Pin;

use crate::council::OmegaCouncilRouter;

/// Per-provider cooldown durations after a retriable failure.
const COOLDOWN_RATE_LIMITED: Duration = Duration::from_secs(300); // 429 → 5 min
const COOLDOWN_QUOTA: Duration = Duration::from_secs(1800); // 402 → 30 min
const COOLDOWN_UNAVAILABLE: Duration = Duration::from_secs(90); // 5xx / transient unavailable → 90 s
/// How many times to retry a single provider with backoff before marking it failed.
const MAX_RETRIES: u32 = 0;
const RETRY_DELAY: Duration = Duration::from_millis(250);

/// Tries each provider in order, falling back on retriable errors.
/// Default chain: codex → gemini-cli → openai → local → gemini → claude-cli → anthropic → perplexity → deepseek → xai
///
/// Mode routing rules:
/// - "omega" / "cloud"          → council synthesis (if set), else full failover chain
/// - "codex"                    → Codex CLI provider, with chain fallback on retriable error
/// - "claude-cli"               → Claude CLI provider, with chain fallback on retriable error
/// - "gemini-cli"               → Gemini CLI provider, with chain fallback on retriable error
/// - "openai"                   → OpenAiProvider, with chain fallback on retriable error
/// - "local"                    → only LocalProvider, no failover
/// - "anthropic" / "claude"     → AnthropicProvider, with chain fallback on retriable error
/// - "google" / "gemini"        → GeminiProvider, with chain fallback on retriable error
/// - "perplexity"               → PerplexityProvider, with chain fallback on retriable error
/// - "deepseek"                 → DeepSeekProvider, with chain fallback on retriable error
/// - "xai" / "grok"             → XaiProvider, with chain fallback on retriable error
pub struct FailoverRouter {
    chain: Vec<Arc<dyn LlmProvider>>,
    council_router: Option<Arc<OmegaCouncilRouter>>,
    /// Tracks when each provider was last marked as failing.
    /// Key = provider name, Value = (failed_at, cooldown_duration)
    cooldowns: Arc<DashMap<String, (Instant, Duration)>>,
}

impl FailoverRouter {
    pub fn new(chain: Vec<Arc<dyn LlmProvider>>) -> Self {
        Self {
            chain,
            council_router: None,
            cooldowns: Arc::new(DashMap::new()),
        }
    }

    pub fn with_council(mut self, council: Arc<OmegaCouncilRouter>) -> Self {
        self.council_router = Some(council);
        self
    }

    /// True if this provider is currently in a cooldown window.
    fn is_cooling_down(&self, name: &str) -> bool {
        if let Some(entry) = self.cooldowns.get(name) {
            let (failed_at, duration) = *entry;
            if failed_at.elapsed() < duration {
                return true;
            }
            // Cooldown expired — remove it
            drop(entry);
            self.cooldowns.remove(name);
        }
        false
    }

    /// Record a provider failure and set its cooldown.
    fn record_failure(&self, name: &str, err: &omega_core::error::ProviderError) {
        use omega_core::error::ProviderError;
        let duration = match err {
            ProviderError::RateLimited => COOLDOWN_RATE_LIMITED,
            ProviderError::QuotaExceeded => COOLDOWN_QUOTA,
            ProviderError::Unavailable { .. } => COOLDOWN_UNAVAILABLE,
            _ => COOLDOWN_UNAVAILABLE,
        };
        tracing::warn!(
            provider = name,
            cooldown_s = duration.as_secs(),
            "Provider marked as cooling down"
        );
        self.cooldowns
            .insert(name.to_string(), (Instant::now(), duration));
    }

    fn should_continue_chain(err: &omega_core::error::ProviderError) -> bool {
        err.is_retriable() || matches!(err, omega_core::error::ProviderError::InvalidRequest { .. })
    }

    /// Try a single provider with one retry on transient network errors.
    async fn try_provider(
        &self,
        provider: &Arc<dyn LlmProvider>,
        req: &ChatRequest,
    ) -> Result<ChatResponse, omega_core::error::ProviderError> {
        for attempt in 0..=MAX_RETRIES {
            match provider.complete(req).await {
                Ok(resp) => return Ok(resp),
                Err(e) if e.is_retriable() => {
                    if attempt < MAX_RETRIES {
                        tracing::debug!(
                            provider = provider.name(),
                            attempt,
                            "Transient error, retrying after backoff"
                        );
                        tokio::time::sleep(RETRY_DELAY).await;
                        continue;
                    }
                    return Err(e);
                }
                Err(e) => return Err(e),
            }
        }
        unreachable!()
    }

    /// Run the full failover chain, skipping providers in cooldown.
    /// On first pass if all providers are cooling down, waits for the shortest
    /// remaining cooldown and tries once more (non-recursive).
    async fn run_chain(&self, req: &ChatRequest, mode: &str) -> Result<ChatResponse, RouterError> {
        for pass in 0..2u8 {
            let mut last_err: Option<omega_core::error::ProviderError> = None;
            let mut all_cooling = true;

            for provider in &self.chain {
                if self.is_cooling_down(provider.name()) {
                    tracing::debug!(provider = provider.name(), "Skipping: in cooldown");
                    continue;
                }
                all_cooling = false;

                match self.try_provider(provider, req).await {
                    Ok(mut resp) => {
                        resp.mode = mode.to_string();
                        return Ok(resp);
                    }
                    Err(e) if Self::should_continue_chain(&e) => {
                        if e.is_retriable() {
                            tracing::warn!(
                                provider = provider.name(),
                                error = %e,
                                "Retriable failure — cooling down, trying next provider"
                            );
                            self.record_failure(provider.name(), &e);
                        } else {
                            tracing::warn!(
                                provider = provider.name(),
                                error = %e,
                                "Provider rejected request — trying next provider in auto chain"
                            );
                        }
                        last_err = Some(e);
                        continue;
                    }
                    Err(e) => return Err(RouterError::Provider(e)),
                }
            }

            if all_cooling && pass == 0 {
                // All providers are temporarily rate-limited — wait for the shortest
                // remaining cooldown window, clear, and make one final attempt.
                tracing::warn!("All providers in cooldown — waiting for shortest window");
                let soonest = self
                    .cooldowns
                    .iter()
                    .map(|e| {
                        let (failed_at, duration) = *e.value();
                        duration.saturating_sub(failed_at.elapsed())
                    })
                    .min()
                    .unwrap_or(Duration::from_secs(5));
                tokio::time::sleep(soonest.min(Duration::from_secs(30))).await;
                self.cooldowns.clear();
                continue; // second pass
            }

            return Err(RouterError::Exhausted { last: last_err });
        }

        Err(RouterError::Exhausted { last: None })
    }
}

/// How a mode resolves to providers in the chain.
enum ModeTarget {
    /// Match providers whose name equals one of the given strings.
    Exact(Vec<&'static str>),
    /// Match all providers whose name starts with the given prefix.
    /// Used for gemini-cli where each model has a unique name like "gemini-cli:model".
    Prefix(&'static str),
    /// No matches — return unknown-mode response.
    Unknown,
}

/// Resolve mode → how to select providers from the chain.
/// Returns None for auto/full-chain modes (omega/cloud).
fn resolve_mode(mode: &str) -> Option<ModeTarget> {
    match mode.to_lowercase().as_str() {
        // Full failover chain
        "omega" | "cloud" => None,
        // Gemini CLI: match all gemini-cli:* slots (7-model fallthrough)
        "gemini-cli" => Some(ModeTarget::Prefix("gemini-cli")),
        "codex" => Some(ModeTarget::Exact(vec!["codex"])),
        "claude-cli" => Some(ModeTarget::Exact(vec!["claude-cli"])),
        "openai" => Some(ModeTarget::Exact(vec!["openai"])),
        "local" => Some(ModeTarget::Exact(vec!["local"])),
        "anthropic" | "claude" => Some(ModeTarget::Exact(vec!["anthropic"])),
        "google" | "gemini" => Some(ModeTarget::Exact(vec!["gemini"])),
        "perplexity" => Some(ModeTarget::Exact(vec!["perplexity"])),
        "deepseek" => Some(ModeTarget::Exact(vec!["deepseek"])),
        "xai" | "grok" => Some(ModeTarget::Exact(vec!["xai"])),
        _ => Some(ModeTarget::Unknown),
    }
}

fn providers_for_target<'a>(
    chain: &'a [Arc<dyn LlmProvider>],
    target: &ModeTarget,
) -> Vec<&'a Arc<dyn LlmProvider>> {
    match target {
        ModeTarget::Exact(names) => chain.iter().filter(|p| names.contains(&p.name())).collect(),
        ModeTarget::Prefix(prefix) => chain
            .iter()
            .filter(|p| p.name().starts_with(prefix))
            .collect(),
        ModeTarget::Unknown => vec![],
    }
}

#[async_trait::async_trait]
impl Router for FailoverRouter {
    async fn route(&self, req: &ChatRequest) -> Result<ChatResponse, RouterError> {
        let mode = req.mode.as_str();

        // Council synthesis for omega/cloud modes
        if mode == "omega" || mode == "cloud" {
            if let Some(council) = &self.council_router {
                match council.route(req).await {
                    Ok(resp) => return Ok(resp),
                    Err(e) => {
                        tracing::warn!(error = %e, "Council failed — falling back to chain");
                        // Fall through to chain below
                    }
                }
            }
        }

        let target = resolve_mode(mode);

        match target {
            Some(ModeTarget::Unknown) => Ok(ChatResponse {
                reply: format!("OMEGA_GATEWAY: Unknown AI Mode '{}'.", mode),
                mode: mode.to_string(),
                memory_hits: vec![],
            }),

            // Direct / prefix mode: walk matching providers in chain order,
            // falling back to the full chain on retriable error.
            Some(ref t) => {
                let matching = providers_for_target(&self.chain, t);

                if matching.is_empty() {
                    return Ok(ChatResponse {
                        reply: format!(
                            "OMEGA_GATEWAY: No provider configured for mode '{}'.",
                            mode
                        ),
                        mode: mode.to_string(),
                        memory_hits: vec![],
                    });
                }

                // Try each matching provider in order (handles gemini model fallthrough).
                for provider in &matching {
                    if self.is_cooling_down(provider.name()) {
                        tracing::debug!(
                            provider = provider.name(),
                            "Skipping matching provider: in cooldown"
                        );
                        continue;
                    }

                    match self.try_provider(provider, req).await {
                        Ok(mut resp) => {
                            resp.mode = mode.to_string();
                            return Ok(resp);
                        }
                        Err(e) if Self::should_continue_chain(&e) => {
                            if e.is_retriable() {
                                tracing::warn!(
                                    provider = provider.name(),
                                    error = %e,
                                    "Retriable failure — trying next matching provider"
                                );
                                self.record_failure(provider.name(), &e);
                            } else {
                                tracing::warn!(
                                    provider = provider.name(),
                                    error = %e,
                                    "Provider rejected — trying next matching provider"
                                );
                            }
                            continue;
                        }
                        Err(e) => return Err(RouterError::Provider(e)),
                    }
                }

                // For explicit modes, fail closed instead of cascading into unrelated providers.
                tracing::warn!(mode, "All matching providers failed for explicit mode");
                Err(RouterError::Exhausted { last: None })
            }

            // Auto/omega mode → full failover chain with circuit breaker
            None => self.run_chain(req, mode).await,
        }
    }

    async fn stream(
        &self,
        req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, RouterError>> + Send>>, RouterError>
    {
        let mode = req.mode.as_str();

        if mode == "omega" || mode == "cloud" {
            if let Some(council) = &self.council_router {
                if let Ok(stream) = council.stream(req).await {
                    return Ok(stream);
                }
                tracing::warn!("Council stream failed — falling back to chain");
            }
        }

        let target = resolve_mode(mode);

        match target {
            Some(ModeTarget::Unknown) => {
                let chunks: Vec<Result<ChatChunk, RouterError>> = vec![
                    Ok(ChatChunk {
                        delta: format!("OMEGA_GATEWAY: Unknown AI Mode '{}'.", mode),
                        done: false,
                    }),
                    Ok(ChatChunk {
                        delta: String::new(),
                        done: true,
                    }),
                ];
                Ok(Box::pin(futures::stream::iter(chunks)))
            }

            Some(ref t) => {
                let matching = providers_for_target(&self.chain, t);

                if matching.is_empty() {
                    let chunks: Vec<Result<ChatChunk, RouterError>> = vec![
                        Ok(ChatChunk {
                            delta: format!(
                                "OMEGA_GATEWAY: No provider configured for mode '{}'.",
                                mode
                            ),
                            done: false,
                        }),
                        Ok(ChatChunk {
                            delta: String::new(),
                            done: true,
                        }),
                    ];
                    return Ok(Box::pin(futures::stream::iter(chunks)));
                }

                // Walk matching providers in order; fall back to full chain if all fail.
                for provider in &matching {
                    if self.is_cooling_down(provider.name()) {
                        continue;
                    }
                    match provider.stream(req).await {
                        Ok(stream) => {
                            use futures::stream::StreamExt;
                            return Ok(Box::pin(
                                stream.map(|res| res.map_err(RouterError::Provider)),
                            ));
                        }
                        Err(e) if e.is_retriable() => {
                            self.record_failure(provider.name(), &e);
                            continue;
                        }
                        Err(e) => return Err(RouterError::Provider(e)),
                    }
                }

                Err(RouterError::Exhausted { last: None })
            }

            None => {
                let mut last_err: Option<omega_core::error::ProviderError> = None;
                for provider in &self.chain {
                    if self.is_cooling_down(provider.name()) {
                        continue;
                    }
                    match provider.stream(req).await {
                        Ok(stream) => {
                            use futures::stream::StreamExt;
                            return Ok(Box::pin(
                                stream.map(|res| res.map_err(RouterError::Provider)),
                            ));
                        }
                        Err(e) if Self::should_continue_chain(&e) => {
                            if e.is_retriable() {
                                self.record_failure(provider.name(), &e);
                            } else {
                                tracing::warn!(
                                    provider = provider.name(),
                                    error = %e,
                                    "Provider rejected stream request — trying next provider in auto chain"
                                );
                            }
                            last_err = Some(e);
                        }
                        Err(e) => return Err(RouterError::Provider(e)),
                    }
                }
                Err(RouterError::Exhausted { last: last_err })
            }
        }
    }
}
