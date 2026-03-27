use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;

use omega_core::{economy::NeuroCreditStore, memory::MemoryStore};
use omega_memory::{
    FederatedMemoryStore, GaingRestMemoryStore, PgMemoryStore, SqliteMemoryStore,
    TieredMemoryConfig, TieredMemoryStore,
};
use omega_provider::{
    anthropic::AnthropicProvider,
    cli::{CliKind, CliProvider},
    deepseek::DeepSeekProvider,
    failover::FailoverRouter,
    gemini::GeminiProvider,
    local::LocalProvider,
    openai::OpenAiProvider,
    perplexity::PerplexityProvider,
    xai::XaiProvider,
};
use omega_trace::TraceStore;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter};

use omega_gateway::{
    agency::spawn_agency_task, build_app, config::GatewayConfig, correction::spawn_correction_task,
    dream::spawn_dream_task, state::AppState,
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialise structured logging.
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load config from env.
    let cfg = GatewayConfig::load()?;
    tracing::info!(
        port = cfg.omega_port,
        runtime_profile = %cfg.omega_runtime_profile,
        "omega-gateway starting"
    );
    omega_gateway::livekit::log_livekit_status(&cfg);
    if !cfg.omega_anthropic_api_key.is_empty() {
        tracing::info!(
            model = %cfg.omega_anthropic_model,
            base_url = %cfg.omega_anthropic_base_url,
            "Anthropic provider configured"
        );
    }
    tracing::info!(
        system_prompt_path = %cfg.omega_system_prompt_path,
        "Dynamic system prompt target configured"
    );
    tracing::info!(
        local_base_url = %cfg.omega_local_base_url,
        local_model = %cfg.omega_local_model,
        "Local Ollama provider configured"
    );
    let cli_home = cfg.effective_cli_home_dir();
    let codex_model = cfg.effective_codex_cli_model();
    let claude_model = cfg.effective_claude_cli_model();
    let gemini_cli_model = cfg.effective_gemini_cli_model();
    tracing::info!(
        cli_home = %cli_home,
        codex_cli = %cfg.omega_codex_cli_path,
        codex_model = %codex_model,
        claude_cli = %cfg.omega_claude_cli_path,
        claude_model = %claude_model,
        gemini_cli = %cfg.omega_gemini_cli_path,
        gemini_model = %gemini_cli_model,
        smoke_test = cfg.is_smoke_test_profile(),
        "CLI-backed providers configured"
    );

    async fn build_memory_store(db_url: &str) -> anyhow::Result<Arc<dyn MemoryStore>> {
        if db_url.starts_with("postgres://") || db_url.starts_with("postgresql://") {
            let store = Arc::new(
                PgMemoryStore::new(db_url)
                    .await
                    .map_err(|e| anyhow::anyhow!("pg memory store init failed: {e}"))?,
            );
            Ok(store)
        } else {
            let store = Arc::new(
                SqliteMemoryStore::new(db_url)
                    .await
                    .map_err(|e| anyhow::anyhow!("sqlite memory store init failed: {e}"))?,
            );
            store
                .migrate()
                .await
                .map_err(|e| anyhow::anyhow!("memory migration failed: {e}"))?;

            // Spawn importance decay — 0.995 decay per hour, prune below 0.01.
            let _decay_handle = store.spawn_decay_task(Duration::from_secs(3600), 0.995, 0.01);

            Ok(store)
        }
    }

    // Initialise the memory and economy stores.
    let db_url = cfg.omega_db_url_or_default();
    tracing::info!(db_url = %db_url, "initialising memory and economy stores");

    let (base_memory_store, economy_store): (Arc<dyn MemoryStore>, Arc<dyn NeuroCreditStore>) =
        if db_url.starts_with("postgres://") || db_url.starts_with("postgresql://") {
            let store = Arc::new(
                PgMemoryStore::new(&db_url)
                    .await
                    .map_err(|e| anyhow::anyhow!("pg memory store init failed: {e}"))?,
            );
            tracing::info!("pg memory store ready");
            (store.clone(), store)
        } else {
            let store = Arc::new(
                SqliteMemoryStore::new(&db_url)
                    .await
                    .map_err(|e| anyhow::anyhow!("sqlite memory store init failed: {e}"))?,
            );
            store
                .migrate()
                .await
                .map_err(|e| anyhow::anyhow!("memory migration failed: {e}"))?;

            // Spawn importance decay — 0.995 decay per hour, prune below 0.01.
            let _decay_handle = store.spawn_decay_task(Duration::from_secs(3600), 0.995, 0.01);

            tracing::info!("sqlite memory store ready");
            (store.clone(), store)
        };

    let mut memory_store: Arc<dyn MemoryStore> = base_memory_store.clone();
    if cfg.tiered_memory_enabled() {
        let s1_url = if cfg.omega_memory_s1_url.trim().is_empty() {
            db_url.clone()
        } else {
            cfg.omega_memory_s1_url.clone()
        };
        let s1_store = if s1_url == db_url {
            base_memory_store.clone()
        } else {
            build_memory_store(&s1_url).await?
        };
        let s2_store = if cfg.omega_memory_s2_url.trim().is_empty() {
            None
        } else {
            Some(build_memory_store(&cfg.omega_memory_s2_url).await?)
        };
        let s3_store = if cfg.omega_memory_s3_url.trim().is_empty() {
            None
        } else {
            Some(build_memory_store(&cfg.omega_memory_s3_url).await?)
        };
        let n1_store = if cfg.omega_memory_n1_url.trim().is_empty() {
            None
        } else {
            Some(build_memory_store(&cfg.omega_memory_n1_url).await?)
        };
        let n2_store = if cfg.omega_memory_n2_url.trim().is_empty() {
            None
        } else {
            Some(build_memory_store(&cfg.omega_memory_n2_url).await?)
        };

        let tiered = TieredMemoryStore::new(TieredMemoryConfig {
            s1: Some(s1_store),
            s2: s2_store,
            s3: s3_store,
            n1: n1_store,
            n2: n2_store,
            promote_threshold: cfg.omega_memory_tier_n1_threshold,
        });
        memory_store = Arc::new(tiered);
        tracing::info!("tiered memory routing enabled");
    }

    // Optionally wrap the memory store in a FederatedMemoryStore that also
    // searches the gAIng Supabase project (secondary, read-only).
    let memory_store: Arc<dyn MemoryStore> = {
        let gaing_url = std::env::var("GAING_SUPABASE_URL").ok();
        let gaing_key = std::env::var("GAING_SUPABASE_SERVICE_ROLE_KEY").ok();
        match (gaing_url, gaing_key) {
            (Some(url), Some(key)) if !url.is_empty() && !key.is_empty() => {
                if cfg.federated_memory_enabled() {
                    tracing::info!(
                        "gAIng secondary memory source enabled — federating with sovereign store"
                    );
                    let secondary = Arc::new(GaingRestMemoryStore::new(url, key));
                    Arc::new(FederatedMemoryStore::new(memory_store, secondary))
                } else {
                    tracing::info!(
                        "gAIng secondary memory configured but disabled by runtime profile"
                    );
                    memory_store
                }
            }
            _ => {
                tracing::info!(
                    "gAIng secondary memory not configured — using sovereign store only"
                );
                memory_store
            }
        }
    };

    // Helper to build a Gemini CLI provider for a specific model.
    let gemini_path = cfg.omega_gemini_cli_path.clone();
    let gemini_home = cli_home.clone();
    let gemini_timeout = cfg.omega_cli_timeout_secs;
    let mk_gemini = move |model: &str| -> Arc<dyn omega_core::provider::LlmProvider> {
        Arc::new(CliProvider::new(
            CliKind::Gemini,
            gemini_path.clone(),
            gemini_home.clone(),
            gemini_timeout,
            Some(model.to_string()),
            vec![],
        ))
    };
    let codex_extra_args = vec![
        "-c".to_string(),
        "model_reasoning_effort=\"low\"".to_string(),
        "-c".to_string(),
        "mcp_servers={}".to_string(),
    ];
    let claude_extra_args = vec![
        "--effort".to_string(),
        "low".to_string(),
        "--strict-mcp-config".to_string(),
        "--tools".to_string(),
        "".to_string(),
        "--disable-slash-commands".to_string(),
        "--no-chrome".to_string(),
        "--no-session-persistence".to_string(),
    ];

    // Provider chain:
    //   headless           → API providers only (OpenAI/Gemini/Anthropic/etc) → Local
    //   smoke-test profile → Codex CLI → Gemini CLI flash-lite → Claude CLI → Local
    //   full profile       → Codex CLI → Gemini CLI fallthrough → OpenAI → Local →
    //                        Gemini API → Claude CLI → Anthropic → Perplexity → DeepSeek → xAI
    let chain: Vec<Arc<dyn omega_core::provider::LlmProvider>> = if cfg.headless_enabled() {
        let mut providers: Vec<Arc<dyn omega_core::provider::LlmProvider>> = Vec::new();
        if !cfg.omega_openai_api_key.trim().is_empty() {
            providers.push(Arc::new(OpenAiProvider::new(
                cfg.omega_openai_api_key.clone(),
                cfg.omega_openai_base_url.clone(),
                cfg.omega_model.clone(),
            )));
        }
        if !cfg.omega_gemini_api_key.trim().is_empty() {
            providers.push(Arc::new(GeminiProvider::new(
                cfg.omega_gemini_api_key.clone(),
                cfg.omega_gemini_base_url.clone(),
                cfg.omega_gemini_model.clone(),
            )));
        }
        if !cfg.omega_anthropic_api_key.trim().is_empty() {
            providers.push(Arc::new(AnthropicProvider::new(
                cfg.omega_anthropic_api_key.clone(),
                cfg.omega_anthropic_base_url.clone(),
                cfg.omega_anthropic_model.clone(),
            )));
        }
        if !cfg.omega_perplexity_api_key.trim().is_empty() {
            providers.push(Arc::new(PerplexityProvider::new(
                cfg.omega_perplexity_api_key.clone(),
                cfg.omega_perplexity_base_url.clone(),
                cfg.omega_perplexity_model.clone(),
            )));
        }
        if !cfg.omega_deepseek_api_key.trim().is_empty() {
            providers.push(Arc::new(DeepSeekProvider::new(
                cfg.omega_deepseek_api_key.clone(),
                cfg.omega_deepseek_base_url.clone(),
                cfg.omega_deepseek_model.clone(),
            )));
        }
        if !cfg.omega_xai_api_key.trim().is_empty() {
            providers.push(Arc::new(XaiProvider::new(
                cfg.omega_xai_api_key.clone(),
                cfg.omega_xai_base_url.clone(),
                cfg.omega_xai_model.clone(),
            )));
        }
        providers.push(Arc::new(LocalProvider::new(
            Some(cfg.omega_local_base_url.clone()),
            Some(cfg.omega_local_model.clone()),
        )));
        providers
    } else if cfg.is_smoke_test_profile() {
        vec![
            Arc::new(CliProvider::new(
                CliKind::Codex,
                cfg.omega_codex_cli_path.clone(),
                cli_home.clone(),
                cfg.omega_cli_timeout_secs,
                Some(codex_model.clone()),
                codex_extra_args,
            )),
            mk_gemini(&gemini_cli_model),
            Arc::new(CliProvider::new(
                CliKind::Claude,
                cfg.omega_claude_cli_path.clone(),
                cli_home.clone(),
                cfg.omega_cli_timeout_secs,
                Some(claude_model.clone()),
                claude_extra_args,
            )),
            Arc::new(LocalProvider::new(
                Some(cfg.omega_local_base_url.clone()),
                Some(cfg.omega_local_model.clone()),
            )),
        ]
    } else {
        vec![
            Arc::new(CliProvider::new(
                CliKind::Codex,
                cfg.omega_codex_cli_path.clone(),
                cli_home.clone(),
                cfg.omega_cli_timeout_secs,
                Some(codex_model.clone()),
                codex_extra_args.clone(),
            )),
            mk_gemini("gemini-2.5-flash"),
            mk_gemini("gemini-2.5-pro"),
            Arc::new(OpenAiProvider::new(
                cfg.omega_openai_api_key.clone(),
                cfg.omega_openai_base_url.clone(),
                cfg.omega_model.clone(),
            )),
            Arc::new(LocalProvider::new(
                Some(cfg.omega_local_base_url.clone()),
                Some(cfg.omega_local_model.clone()),
            )),
            Arc::new(GeminiProvider::new(
                cfg.omega_gemini_api_key.clone(),
                cfg.omega_gemini_base_url.clone(),
                cfg.omega_gemini_model.clone(),
            )),
            Arc::new(CliProvider::new(
                CliKind::Claude,
                cfg.omega_claude_cli_path.clone(),
                cli_home.clone(),
                cfg.omega_cli_timeout_secs,
                Some(claude_model.clone()),
                claude_extra_args,
            )),
            Arc::new(AnthropicProvider::new(
                cfg.omega_anthropic_api_key.clone(),
                cfg.omega_anthropic_base_url.clone(),
                cfg.omega_anthropic_model.clone(),
            )),
            Arc::new(PerplexityProvider::new(
                cfg.omega_perplexity_api_key.clone(),
                cfg.omega_perplexity_base_url.clone(),
                cfg.omega_perplexity_model.clone(),
            )),
            Arc::new(DeepSeekProvider::new(
                cfg.omega_deepseek_api_key.clone(),
                cfg.omega_deepseek_base_url.clone(),
                cfg.omega_deepseek_model.clone(),
            )),
            Arc::new(XaiProvider::new(
                cfg.omega_xai_api_key.clone(),
                cfg.omega_xai_base_url.clone(),
                cfg.omega_xai_model.clone(),
            )),
        ]
    };
    // Build FailoverRouter; attach council synthesis when CLI agents are available.
    let failover_router = FailoverRouter::new(chain);

    // omega/cloud mode uses the same failover chain as all other modes.
    // Identity is enforced by the identity layer (identity.yaml) on every request —
    // the model is the voice, not the identity. No council needed.
    tracing::info!("omega mode → standard failover chain (identity layer handles sovereignty)");

    let failover = Arc::new(failover_router) as Arc<dyn omega_core::router::Router>;

    // Build a LocalProvider for SSE streaming.
    let local_for_stream: Arc<dyn omega_core::provider::LlmProvider> =
        Arc::new(LocalProvider::new(
            Some(cfg.omega_local_base_url.clone()),
            Some(cfg.omega_local_model.clone()),
        ));

    // Initialise the trace store (separate DB to avoid migration table conflicts
    // with the memory store migrator).  Defaults to sqlite::memory: (no persistence
    // needed — traces are append-only diagnostics, not durable state).
    let trace_db_url = cfg.omega_trace_db_url.clone();
    let trace_store = Arc::new(
        TraceStore::new(&trace_db_url)
            .await
            .map_err(|e| anyhow::anyhow!("trace store init failed: {e}"))?,
    );
    trace_store
        .migrate()
        .await
        .map_err(|e| anyhow::anyhow!("trace migration failed: {e}"))?;
    tracing::info!("trace store ready");

    let state = Arc::new(
        AppState::new(
            failover,
            cfg.clone(),
            memory_store,
            economy_store,
            trace_store,
        )
        .with_stream_provider(local_for_stream),
    );
    let timeout = Duration::from_secs(cfg.omega_timeout_secs);

    if cfg.background_tasks_enabled() {
        // Spawn Dream State background task (every 1 hour by default)
        let dream_state_shared = Arc::clone(&state);
        let _dream_handle = spawn_dream_task(dream_state_shared, Duration::from_secs(3600));

        // Spawn Self-Correction background task (every 10 minutes)
        let correction_state_shared = Arc::clone(&state);
        let _correction_handle =
            spawn_correction_task(correction_state_shared, Duration::from_secs(600));

        // Spawn Proactive Agency background task (every 5 minutes)
        let agency_state_shared = Arc::clone(&state);
        let _agency_handle = spawn_agency_task(agency_state_shared, Duration::from_secs(300));
    } else {
        tracing::info!("Background autonomy disabled by runtime profile");
    }

    let app = build_app(state, timeout);

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.omega_port));
    tracing::info!(%addr, "AR137 NAOMI — Ω · אין סוף");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
