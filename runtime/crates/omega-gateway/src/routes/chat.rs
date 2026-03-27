use axum::response::sse::Event;
use axum::{
    extract::State,
    http::StatusCode,
    response::{IntoResponse, Response, Sse},
    Json,
};
use futures::StreamExt;
use omega_core::memory::{MemoryEntry, MemoryStore};
use omega_core::provider::ChatRequest;
use omega_trace::{TraceEvent, TraceOutcome};
use serde_json::json;
use std::sync::{Arc, OnceLock};
use std::time::Instant;
use uuid::Uuid;

use crate::state::AppState;
use omega_core::economy::TransactionType;

fn clamp01(value: f64) -> f64 {
    value.clamp(0.0, 1.0)
}

fn tier_rank(label: &str) -> u8 {
    match label.trim().to_ascii_lowercase().as_str() {
        "s1" | "hot" | "short" | "short-term" | "ram" => 1,
        "s2" | "warm" | "fresh" => 2,
        "s3" | "staging" => 3,
        "n1" | "cold" | "long" | "long-term" => 4,
        "n2" | "archive" | "immutable" | "vault" => 5,
        _ => 0,
    }
}

fn target_tier_from_importance(importance: f64, thresholds: (f64, f64, f64, f64)) -> &'static str {
    let (s2, s3, n1, n2) = thresholds;
    if importance >= n2 {
        "n2"
    } else if importance >= n1 {
        "n1"
    } else if importance >= s3 {
        "s3"
    } else if importance >= s2 {
        "s2"
    } else {
        "s1"
    }
}

async fn reinforce_memory_hits(
    store: Arc<dyn MemoryStore>,
    cfg: &crate::config::GatewayConfig,
    entries: Vec<MemoryEntry>,
) {
    if entries.is_empty() || !cfg.memory_reinforce_enabled() {
        return;
    }

    let delta = cfg.memory_reinforce_delta();
    let max_importance = cfg.memory_reinforce_max();
    let thresholds = cfg.memory_tier_thresholds();

    for entry in entries {
        let Some(id) = entry.id.clone() else { continue };
        let mut updated = entry.clone();
        let boosted = (updated.importance + delta).min(max_importance);
        if boosted <= updated.importance {
            continue;
        }

        updated.importance = boosted;
        let target_tier = target_tier_from_importance(boosted, thresholds);
        let current_rank = updated
            .tier
            .as_deref()
            .map(tier_rank)
            .unwrap_or(0);
        let target_rank = tier_rank(target_tier);
        if target_rank > current_rank {
            updated.tier = Some(target_tier.to_string());
        }

        updated.id = Some(id);
        if let Err(err) = store.write(updated).await {
            tracing::warn!(error = %err, "failed to reinforce memory entry");
        }
    }
}

fn retrieval_sources_from_hits(memory_hits: &[serde_json::Value]) -> Option<Vec<String>> {
    let ids: Vec<String> = memory_hits
        .iter()
        .filter_map(|hit| {
            hit.get("id")
                .and_then(|v| v.as_str())
                .map(ToString::to_string)
                .or_else(|| {
                    hit.get("key")
                        .and_then(|v| v.as_str())
                        .map(ToString::to_string)
                })
        })
        .collect();

    if ids.is_empty() {
        None
    } else {
        Some(ids)
    }
}

fn estimate_canon_anchor_weight(state: &AppState, req: &ChatRequest) -> f64 {
    if let Some(task_state) = &req.task_state {
        if let Some(weight) = task_state.canon_anchor_weight {
            return clamp01(weight);
        }
    }

    let anchor_count = state.identity.identity_anchors.len() as f64;
    let doctrine_count = state.identity.doctrine.len() as f64;
    clamp01(0.45 + anchor_count.min(5.0) * 0.07 + doctrine_count.min(5.0) * 0.03)
}

fn estimate_intent_priority_score(req: &ChatRequest, consensus_required: bool) -> f64 {
    if let Some(task_state) = &req.task_state {
        if let Some(score) = task_state.intent_priority_score {
            return clamp01(score);
        }
    }

    let mut score: f64 = 0.45;
    if consensus_required {
        score += 0.2;
    }
    if req.agent_id.is_some() {
        score += 0.1;
    }
    if req.use_memory {
        score += 0.05;
    }
    if let Some(max_tokens) = req.max_tokens {
        score += ((max_tokens as f64) / 4096.0).min(0.15);
    }
    clamp01(score)
}

fn estimate_authority_shrink_level(
    req: &ChatRequest,
    consensus_required: bool,
    memory_hits_len: usize,
) -> f64 {
    if let Some(task_state) = &req.task_state {
        if let Some(level) = task_state.authority_shrink_level {
            return clamp01(level);
        }
    }

    let mut level: f64 = 0.12;
    if consensus_required {
        level += 0.28;
    }
    if req.use_memory && memory_hits_len == 0 {
        level += 0.16;
    }
    if req.images.as_ref().map(|v| !v.is_empty()).unwrap_or(false) {
        level += 0.08;
    }
    clamp01(level)
}

fn estimate_resonance_amplitude(
    req: &ChatRequest,
    memory_hits_len: usize,
    consensus_required: bool,
) -> f64 {
    let mut amplitude: f64 = 0.28;
    amplitude += match req.mode.as_str() {
        "omega" | "cloud" => 0.14,
        "codex" | "claude-cli" | "gemini-cli" => 0.12,
        "local" => 0.06,
        _ => 0.08,
    };
    if req.use_memory {
        amplitude += 0.08;
    }
    amplitude += (memory_hits_len as f64 * 0.05).min(0.2);
    if consensus_required {
        amplitude += 0.08;
    }
    if let Some(max_tokens) = req.max_tokens {
        amplitude += ((max_tokens as f64) / 4096.0).min(0.12);
    }
    clamp01(amplitude)
}

fn estimate_shear_index(req: &ChatRequest, memory_hits_len: usize) -> f64 {
    let mut shear: f64 = if req.use_memory { 0.18 } else { 0.08 };
    if req.use_memory && memory_hits_len == 0 {
        shear += 0.32;
    } else if memory_hits_len > 0 {
        shear -= (memory_hits_len as f64 * 0.03).min(0.12);
    }
    if req.task_state.is_none() {
        shear += 0.05;
    }
    clamp01(shear)
}

fn predicted_failure_modes(
    req: &ChatRequest,
    memory_hits_len: usize,
    consensus_required: bool,
) -> Option<Vec<String>> {
    let mut predicted = req
        .task_state
        .as_ref()
        .map(|ts| ts.predicted_failure_modes.clone())
        .unwrap_or_default();

    if req.use_memory && memory_hits_len == 0 {
        predicted.push("RETRIEVAL".to_string());
    }
    if consensus_required {
        predicted.push("CONSENSUS_BYPASS".to_string());
    }
    predicted.sort();
    predicted.dedup();

    if predicted.is_empty() {
        None
    } else {
        Some(predicted)
    }
}

fn estimate_structural_integrity_score(
    outcome: &TraceOutcome,
    shear_index: f64,
    authority_shrink_level: f64,
    consensus_required: bool,
) -> f64 {
    let base = match outcome {
        TraceOutcome::Success => 0.92,
        TraceOutcome::Failure => 0.38,
        TraceOutcome::Timeout => 0.3,
        TraceOutcome::Blocked => 0.7,
        TraceOutcome::Delegated => 0.76,
    };

    let mut score = base - (shear_index * 0.25) - (authority_shrink_level * 0.1);
    if consensus_required {
        score -= 0.05;
    }
    clamp01(score)
}

/// Scan a response for provider contamination signals and replace them.
///
/// `signals` must already be lowercased (pre-processed at identity load time).
/// Each matched signal is replaced with the OmegA-sovereign equivalent.
/// `lower` is recomputed after each mutation so byte offsets stay accurate.
fn scan_output_contamination(reply: &str, signals: &[String]) -> String {
    if signals.is_empty() {
        return reply.to_string();
    }

    let mut output = reply.to_string();

    for signal in signals {
        // Recompute after each mutation so offsets stay accurate.
        let lower = output.to_lowercase();
        let Some(start) = lower.find(signal.as_str()) else {
            continue;
        };

        let replacement = match signal.as_str() {
            p if p.contains("created by anthropic") || p.contains("made by anthropic") => {
                "built by RY (artistMega)"
            }
            p if p.contains("created by openai") || p.contains("made by openai") => {
                "built by RY (artistMega)"
            }
            p if p.contains("as claude") => "As OmegA",
            p if p.contains("i was trained by") || p.contains("trained by anthropic") => {
                "I was built by RY"
            }
            p if p.contains("built by ry anthropic") || p.contains("anthropic used") => {
                "built by RY"
            }
            _ => continue,
        };

        tracing::warn!(
            signal = %signal,
            "Output contamination detected — suppressing provider identity bleed"
        );
        // Splice output using the byte offset found in `lower`.  All contamination
        // signals are ASCII-only, so to_lowercase() is length-preserving and the
        // byte offset is valid in both `lower` and `output`.
        let end = start + signal.len();
        output = format!("{}{}{}", &output[..start], replacement, &output[end..]);
    }

    output
}

/// Compiled injection-detection regexes — initialized once, reused on every request.
static INJECTION_REGEXES: OnceLock<Vec<regex::Regex>> = OnceLock::new();

fn injection_regexes() -> &'static Vec<regex::Regex> {
    INJECTION_REGEXES.get_or_init(|| {
        [
            "(?i)ignore\\s+all\\s+previous\\s+instructions",
            "(?i)system\\s+prompt",
            "(?i)you\\s+are\\s+now\\s+a",
            "(?i)disregard\\s+previous",
        ]
        .iter()
        .filter_map(|p| regex::Regex::new(p).ok())
        .collect()
    })
}

fn detect_injection(prompt: &str) -> bool {
    injection_regexes().iter().any(|re| re.is_match(prompt))
}

/// Valid mode names accepted by the router.  Must stay in sync with
/// `resolve_mode()` in `omega-provider/src/failover.rs`.
const VALID_MODES: &[&str] = &[
    "omega",
    "cloud",
    "codex",
    "claude-cli",
    "gemini-cli",
    "openai",
    "local",
    "anthropic",
    "claude",
    "google",
    "gemini",
    "perplexity",
    "deepseek",
    "xai",
    "grok",
];

fn is_valid_mode(mode: &str) -> bool {
    VALID_MODES.contains(&mode.to_lowercase().as_str())
}

/// POST /api/v1/chat — main inference endpoint (auth required).
///
/// Response shape matches Python contract:
/// {"reply": "...", "mode": "...", "memory_hits": [...]}
///
/// When `use_memory` is true (the default), the store is queried for the
/// top-3 entries matching the user prompt and the results are returned in
/// `memory_hits`.  This matches the Python gateway's behaviour.
pub async fn chat_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<ChatRequest>,
) -> impl IntoResponse {
    // Capture consensus_required before req is moved/mutated.
    // CollectiveBrain requests require consensus per CONSENSUS_ENGINE.md.
    let consensus_required = req.use_collectivebrain.unwrap_or(false);
    if consensus_required {
        tracing::debug!(
            "use_collectivebrain=true requested but CollectiveBrain is not yet implemented in Rust; \
             falling through to normal LLM routing — tagging trace as consensus_required"
        );
    }

    // Economic Integration: Charge the agent if agent_id is present.
    // Base cost for a standard chat request.
    let base_cost = 0.05_f32;
    if let Some(ref agent_id) = req.agent_id {
        // Auto-init with 10.0 credits if new.
        let _ = state.economy.init_wallet(agent_id, 10.0).await;

        if !state
            .economy
            .can_afford(agent_id, base_cost)
            .await
            .unwrap_or(false)
        {
            return (
                StatusCode::PAYMENT_REQUIRED,
                Json(json!({"detail": "Insufficient Neuro-Credits for this request.", "agent_id": agent_id})),
            ).into_response();
        }

        // Record the transaction before routing (pessimistic lock on budget).
        let _ = state
            .economy
            .record_transaction(
                agent_id,
                base_cost,
                TransactionType::Spend,
                &format!("Chat inference: {}", req.mode),
            )
            .await;
    }

    // Validate mode before routing — return 400 for unknown modes.
    if !is_valid_mode(&req.mode) {
        tracing::warn!(mode = %req.mode, "Rejected request with unknown mode");
        return (
            StatusCode::BAD_REQUEST,
            Json(json!({"detail": format!("Unknown mode '{}'.", req.mode)})),
        )
            .into_response();
    }

    // Security: prompt injection detection
    if detect_injection(&req.user) {
        tracing::warn!("Blocked potential prompt injection attempt");
        return (
            StatusCode::BAD_REQUEST,
            Json(json!({"detail": "Potentially unsafe prompt detected."})),
        )
            .into_response();
    }

    // Retrieve memory hits before routing so they can be included in the response.
    let memory_entries: Vec<MemoryEntry> = if req.use_memory {
        state
            .memory_store
            .search(&req.user, 3)
            .await
            .unwrap_or_default()
    } else {
        vec![]
    };
    let memory_hits: Vec<serde_json::Value> = memory_entries
        .iter()
        .cloned()
        .map(|e| serde_json::to_value(e).unwrap_or_default())
        .collect();

    if req.use_memory && state.config.memory_reinforce_enabled() && !memory_entries.is_empty() {
        let store = state.memory_store.clone();
        let cfg = state.config.clone();
        let entries = memory_entries.clone();
        tokio::spawn(async move { reinforce_memory_hits(store, &cfg, entries).await });
    }

    // Inject sovereign identity as system prompt prefix.
    // If the caller already provided a system prompt, append it after the identity block.
    // Use pre-rendered text cached on AppState — render_text() is not called per-request.
    let identity_text = &state.identity_text;
    let current_date = chrono::Utc::now()
        .format("Current date: %Y-%m-%d (UTC).")
        .to_string();
    let mut req = req;
    req.system = Some(match req.system.take() {
        Some(existing) => format!("{}\n{}\n\n{}", identity_text, current_date, existing),
        None => format!("{}\n{}", identity_text, current_date),
    });

    let started = Instant::now();
    let mode_label = req.mode.clone();
    let task_id = req.task_state.as_ref().and_then(|ts| ts.task_id.clone());
    let phase_transition_id = Uuid::new_v4().to_string();
    let retrieval_sources = retrieval_sources_from_hits(&memory_hits);
    let canon_anchor_weight = estimate_canon_anchor_weight(&state, &req);
    let intent_priority_score = estimate_intent_priority_score(&req, consensus_required);
    let authority_shrink_level =
        estimate_authority_shrink_level(&req, consensus_required, memory_hits.len());
    let resonance_amplitude =
        estimate_resonance_amplitude(&req, memory_hits.len(), consensus_required);
    let shear_index = estimate_shear_index(&req, memory_hits.len());
    let predicted_failure_modes =
        predicted_failure_modes(&req, memory_hits.len(), consensus_required);

    match state.router.route(&req).await {
        Ok(mut resp) => {
            // Output-layer contamination scan: replace known provider identity phrases
            // with OmegA-aligned equivalents before the response reaches the caller.
            resp.reply =
                scan_output_contamination(&resp.reply, &state.identity.contamination_signals);

            // Inject real memory hits into the response (overrides the empty vec
            // that providers currently return).
            resp.memory_hits = memory_hits;

            let memory_context_loaded = !resp.memory_hits.is_empty();
            let provider_used = resp.mode.clone();
            let structural_integrity_score = estimate_structural_integrity_score(
                &TraceOutcome::Success,
                shear_index,
                authority_shrink_level,
                consensus_required,
            );

            // Record a trace event for this successful chat inference.
            let _ = state
                .trace
                .record(TraceEvent {
                    id: String::new(),
                    task_id: task_id.clone(),
                    agent: "gateway".to_string(),
                    phase: "execute".to_string(),
                    action: format!("chat/{mode_label}"),
                    outcome: TraceOutcome::Success,
                    duration_ms: started.elapsed().as_millis() as u64,
                    tokens: None,
                    error: None,
                    timestamp: chrono::Utc::now(),
                    provider_used: Some(provider_used),
                    retrieval_sources: retrieval_sources.clone(),
                    identity_shell_loaded: Some(true),
                    memory_context_loaded: Some(memory_context_loaded),
                    tool_invocations: None,
                    failure_tags: None,
                    consensus_required: Some(consensus_required),
                    consensus_outcome: if consensus_required {
                        Some("bypassed".to_string()) // CollectiveBrain not yet enforced
                    } else {
                        None
                    },
                    phase_state: Some("ACT".to_string()),
                    phase_transition_id: Some(phase_transition_id.clone()),
                    resonance_amplitude: Some(resonance_amplitude),
                    shear_index: Some(shear_index),
                    canon_anchor_weight: Some(canon_anchor_weight),
                    structural_integrity_score: Some(structural_integrity_score),
                    intent_priority_score: Some(intent_priority_score),
                    authority_shrink_level: Some(authority_shrink_level),
                    predicted_failure_modes: predicted_failure_modes.clone(),
                    actual_failure_mode: None,
                    promotion_decay_ratio: None,
                })
                .await;

            (StatusCode::OK, Json(resp)).into_response()
        }
        Err(e) => {
            tracing::error!(error = %e, "router error");
            let failure_tags = if consensus_required {
                vec!["RUNTIME_ENV".to_string(), "CONSENSUS_BYPASS".to_string()]
            } else {
                vec!["RUNTIME_ENV".to_string()]
            };
            let actual_failure_mode = failure_tags.first().cloned();
            let structural_integrity_score = estimate_structural_integrity_score(
                &TraceOutcome::Failure,
                shear_index,
                authority_shrink_level,
                consensus_required,
            );

            // Record a trace event for the failure.
            let _ = state
                .trace
                .record(TraceEvent {
                    id: String::new(),
                    task_id,
                    agent: "gateway".to_string(),
                    phase: "execute".to_string(),
                    action: format!("chat/{mode_label}"),
                    outcome: TraceOutcome::Failure,
                    duration_ms: started.elapsed().as_millis() as u64,
                    tokens: None,
                    error: Some(e.to_string()),
                    timestamp: chrono::Utc::now(),
                    provider_used: None,
                    retrieval_sources,
                    identity_shell_loaded: Some(true),
                    memory_context_loaded: None,
                    tool_invocations: None,
                    failure_tags: Some(failure_tags),
                    consensus_required: Some(consensus_required),
                    consensus_outcome: None,
                    phase_state: Some("ACT".to_string()),
                    phase_transition_id: Some(phase_transition_id),
                    resonance_amplitude: Some(resonance_amplitude),
                    shear_index: Some(shear_index),
                    canon_anchor_weight: Some(canon_anchor_weight),
                    structural_integrity_score: Some(structural_integrity_score),
                    intent_priority_score: Some(intent_priority_score),
                    authority_shrink_level: Some(authority_shrink_level),
                    predicted_failure_modes,
                    actual_failure_mode,
                    promotion_decay_ratio: None,
                })
                .await;

            (
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response()
        }
    }
}

/// POST /api/v1/chat/stream — SSE streaming endpoint (auth required).
///
/// Proxies to the failover router's `stream()` method, enabling stream
/// support for the full Council synthesis and fallback chain.
/// Each SSE event: `data: {"chunk": "...", "done": false}`
/// Final event:    `data: {"chunk": "", "done": true}`
pub async fn stream_handler(
    State(state): State<Arc<AppState>>,
    Json(req): Json<ChatRequest>,
) -> Response {
    // Security: prompt injection detection
    if detect_injection(&req.user) {
        tracing::warn!("Blocked potential prompt injection attempt in stream");
        let data =
            json!({"error": "Potentially unsafe prompt detected.", "done": true}).to_string();
        return Sse::new(futures::stream::once(async {
            Ok::<Event, String>(Event::default().data(data))
        }))
        .into_response();
    }

    match state.router.stream(&req).await {
        Err(e) => {
            tracing::error!(error = %e, "stream provider error");
            (
                StatusCode::SERVICE_UNAVAILABLE,
                Json(json!({"detail": e.to_string()})),
            )
                .into_response()
        }
        Ok(chunk_stream) => {
            // Map each ChatChunk into an SSE Event.
            let sse_stream = chunk_stream.map(|result| match result {
                Ok(chunk) => {
                    let data = json!({"chunk": chunk.delta, "done": chunk.done}).to_string();
                    Ok::<Event, String>(Event::default().data(data))
                }
                Err(e) => {
                    let data = json!({"error": e.to_string(), "done": true}).to_string();
                    Ok(Event::default().data(data))
                }
            });

            // Append a terminal done event after the provider stream ends.
            let terminal = futures::stream::once(async {
                let data = json!({"chunk": "", "done": true}).to_string();
                Ok::<Event, String>(Event::default().data(data))
            });

            Sse::new(sse_stream.chain(terminal)).into_response()
        }
    }
}
