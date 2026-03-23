/// Integration tests for omega-gateway.
/// Tests run in-process using tower's ServiceExt — no real TCP socket.
/// All provider HTTP calls are intercepted by mock providers.
///
/// Test naming convention:
///   test_auth_*     → auth behaviour tests
///   test_health_*   → health endpoint tests
///   test_chat_*     → chat endpoint tests
///   test_failover_* → failover chain behaviour
///   test_omega_*    → council synthesis tests
///   contract_*      → exact JSON shape assertions (compatibility contract)
mod helpers;

use axum::{
    body::Body,
    http::{Request, StatusCode},
};
use helpers::*;
use omega_core::provider::LlmProvider;
use std::sync::Arc;
use tower::ServiceExt; // .oneshot()

// ============================================================================
// Test 1: GET /health → no auth required, exact JSON shape
// ============================================================================

#[tokio::test]
async fn test_health_no_auth_required() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
}

#[tokio::test]
async fn contract_health_shape() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;

    // Exact contract from Python: {"ok": true, "service": "Gateway", "version": "0.1"}
    assert_eq!(body["ok"], true, "/health 'ok' must be true boolean");
    assert_eq!(
        body["service"], "Gateway",
        "/health 'service' must be exact string"
    );
    assert_eq!(body["version"], "0.1", "/health 'version' must be '0.1'");
    assert_eq!(
        body.as_object().unwrap().len(),
        3,
        "/health must have exactly 3 fields"
    );
}

// ============================================================================
// Test 2: POST /api/v1/chat with missing Authorization header → 401
// ============================================================================

#[tokio::test]
async fn test_auth_missing_token_401() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "hello"));
    let app = build_test_app(test_config(), vec![mock]).await;

    let resp = app
        .oneshot(chat_request_no_auth(r#"{"user":"hi","mode":"perplexity"}"#))
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::UNAUTHORIZED,
        "missing token must return 401"
    );
    let body = parse_body(resp).await;
    assert_eq!(
        body["detail"], "Missing bearer token.",
        "detail must match Python contract exactly"
    );
}

// ============================================================================
// Test 3: POST /api/v1/chat with wrong token → 403
// ============================================================================

#[tokio::test]
async fn test_auth_wrong_token_403() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "hello"));
    let app = build_test_app(test_config(), vec![mock]).await;

    let resp = app
        .oneshot(chat_request_with_auth(
            r#"{"user":"hi","mode":"perplexity"}"#,
            "Bearer wrong-token",
        ))
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::FORBIDDEN,
        "wrong token must return 403, not 401"
    );
    let body = parse_body(resp).await;
    assert_eq!(
        body["detail"], "Invalid bearer token.",
        "detail must match Python contract exactly"
    );
}

// ============================================================================
// Test 4: POST /api/v1/chat with correct token + mock provider → 200
//         Response must have "reply" and "memory_hits" fields
// ============================================================================

#[tokio::test]
async fn test_chat_happy_path() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "hello world"));
    let app = build_test_app(test_config(), vec![mock]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"say hello","mode":"perplexity"}"#))
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "correct token must return 200"
    );
    let body = parse_body(resp).await;

    assert_eq!(
        body["reply"], "hello world",
        "reply must contain provider response"
    );
    assert_eq!(
        body["mode"], "perplexity",
        "mode must echo the requested mode"
    );
    assert!(
        body["memory_hits"].is_array(),
        "memory_hits must always be an array"
    );
}

#[tokio::test]
async fn test_chat_response_has_all_required_fields() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "response text"));
    let app = build_test_app(test_config(), vec![mock]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"perplexity"}"#))
        .await
        .unwrap();

    let body = parse_body(resp).await;
    let obj = body.as_object().unwrap();

    assert!(
        obj.contains_key("reply"),
        "response must have 'reply' field"
    );
    assert!(obj.contains_key("mode"), "response must have 'mode' field");
    assert!(
        obj.contains_key("memory_hits"),
        "response must have 'memory_hits' field"
    );
    assert!(
        body["memory_hits"].is_array(),
        "memory_hits must be an array (never null)"
    );
}

// ============================================================================
// Test 5: mode = "perplexity" → only Perplexity called (via FailoverRouter)
// ============================================================================

#[tokio::test]
async fn test_mode_perplexity_routes_only_to_perplexity() {
    // Put a perplexity mock first; if gemini/anthropic were called they'd return something different.
    let perplexity: Arc<dyn LlmProvider> =
        Arc::new(MockProvider::new("perplexity", "from perplexity"));
    let gemini: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("gemini", "from gemini"));

    let app = build_test_app(test_config(), vec![perplexity, gemini]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"perplexity"}"#))
        .await
        .unwrap();

    let body = parse_body(resp).await;
    assert_eq!(
        body["reply"], "from perplexity",
        "perplexity mode must route only to perplexity provider"
    );
}

// ============================================================================
// Auth disabled when token is empty (permissive mode)
// ============================================================================

#[tokio::test]
async fn test_auth_disabled_when_token_empty() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "ok"));
    let app = build_test_app(test_config_no_auth(), vec![mock]).await;

    // No Authorization header — should still succeed when auth is disabled
    let resp = app
        .oneshot(chat_request_no_auth(r#"{"user":"hi","mode":"perplexity"}"#))
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "auth must be skipped when OMEGA_API_BEARER_TOKEN is empty"
    );
}

// ============================================================================
// Failover: rate-limited provider triggers next in chain
// ============================================================================

#[tokio::test]
async fn test_failover_rate_limited_tries_next() {
    let failing: Arc<dyn LlmProvider> = Arc::new(FailingProvider::rate_limited("perplexity"));
    let working: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("deepseek", "from deepseek"));

    let app = build_test_app(test_config(), vec![failing, working]).await;

    // omega mode = full failover chain
    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"omega"}"#))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(
        body["reply"], "from deepseek",
        "failover must advance to next provider on 429"
    );
}

// ============================================================================
// Failover: all providers exhausted → 503
// ============================================================================

#[tokio::test]
async fn test_failover_exhausted_returns_503() {
    let chain: Vec<Arc<dyn LlmProvider>> = vec![
        Arc::new(FailingProvider::rate_limited("perplexity")),
        Arc::new(FailingProvider::rate_limited("deepseek")),
    ];

    let app = build_test_app(test_config(), chain).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"omega"}"#))
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::SERVICE_UNAVAILABLE,
        "exhausted chain must return 503"
    );
}

// ============================================================================
// Mode aliases: claude → anthropic, grok → xai, gemini → gemini
// ============================================================================

#[tokio::test]
async fn test_alias_claude_routes_to_anthropic() {
    let anthropic: Arc<dyn LlmProvider> =
        Arc::new(MockProvider::new("anthropic", "from anthropic"));
    let app = build_test_app(test_config(), vec![anthropic]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"claude"}"#))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(
        body["reply"], "from anthropic",
        "'claude' mode must route to anthropic provider"
    );
}

#[tokio::test]
async fn test_alias_grok_routes_to_xai() {
    let xai: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("xai", "from xai"));
    let app = build_test_app(test_config(), vec![xai]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"grok"}"#))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(
        body["reply"], "from xai",
        "'grok' mode must route to xai provider"
    );
}

#[tokio::test]
async fn test_alias_google_routes_to_gemini() {
    let gemini: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("gemini", "from gemini"));
    let app = build_test_app(test_config(), vec![gemini]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"google"}"#))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(body["reply"], "from gemini");
}

// ============================================================================
// Unknown mode → returns 200 with OMEGA_GATEWAY message (Python compat)
// ============================================================================

#[tokio::test]
async fn test_unknown_mode_returns_400() {
    let app = build_test_app(test_config(), vec![]).await;

    let resp = app
        .oneshot(chat_request(
            r#"{"user":"test","mode":"totally_unknown_mode"}"#,
        ))
        .await
        .unwrap();

    // Unknown modes must be rejected with 400 Bad Request.
    assert_eq!(resp.status(), StatusCode::BAD_REQUEST);
    let body = parse_body(resp).await;
    assert!(
        body["detail"]
            .as_str()
            .unwrap_or("")
            .contains("totally_unknown_mode"),
        "400 response must name the unknown mode"
    );
}

// ============================================================================
// use_collectivebrain field: must be accepted without 422
// ============================================================================

#[tokio::test]
async fn test_use_collectivebrain_field_accepted() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "response"));
    let app = build_test_app(test_config(), vec![mock]).await;

    let resp = app
        .oneshot(chat_request(
            r#"{"user":"test","mode":"perplexity","use_collectivebrain":true}"#,
        ))
        .await
        .unwrap();

    // Must not return 422 Unprocessable Entity
    assert_ne!(
        resp.status(),
        StatusCode::UNPROCESSABLE_ENTITY,
        "use_collectivebrain field must not cause a parse error"
    );
    assert_eq!(resp.status(), StatusCode::OK);
}

// ============================================================================
// Trace endpoint should expose teleodynamic observability fields for chat events
// ============================================================================

#[tokio::test]
async fn test_trace_exposes_teleodynamic_fields() {
    let mock: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("perplexity", "trace ok"));
    let app = build_test_app(test_config(), vec![mock]).await;

    let resp = app
        .clone()
        .oneshot(chat_request(r#"{"user":"test","mode":"perplexity"}"#))
        .await
        .unwrap();
    assert_eq!(resp.status(), StatusCode::OK);

    let trace_resp = app
        .oneshot(
            Request::builder()
                .uri("/api/v1/trace")
                .header("Authorization", "Bearer test-secret-token")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(trace_resp.status(), StatusCode::OK);
    let body = parse_body(trace_resp).await;
    let events = body["events"].as_array().expect("events must be an array");
    let event = events
        .first()
        .expect("trace must contain at least one event");

    assert_eq!(event["phase_state"], "ACT");
    assert!(event["phase_transition_id"].is_string());
    assert!(event["resonance_amplitude"].is_number());
    assert!(event["shear_index"].is_number());
    assert!(event["canon_anchor_weight"].is_number());
    assert!(event["structural_integrity_score"].is_number());
    assert!(event["intent_priority_score"].is_number());
    assert!(event["authority_shrink_level"].is_number());
    assert!(
        event["predicted_failure_modes"].is_array() || event["predicted_failure_modes"].is_null()
    );
}

// ============================================================================
// Contract: /healthz shape
// ============================================================================

#[tokio::test]
async fn contract_healthz_shape() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/healthz")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    // {"ok": true} — exactly one field
    assert_eq!(body["ok"], true);
    assert_eq!(
        body.as_object().unwrap().len(),
        1,
        "/healthz must have exactly 1 field"
    );
}

// ============================================================================
// Contract: GET / shape
// ============================================================================

#[tokio::test]
async fn contract_root_shape() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(body["service"], "OMEGA Gateway");
    assert_eq!(body["version"], "0.1");
    assert_eq!(body["status"], "operational");
    assert_eq!(body.as_object().unwrap().len(), 3);
}

// ============================================================================
// Contract: GET /api/v1/health same as /health
// ============================================================================

#[tokio::test]
async fn contract_api_v1_health_shape() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .uri("/api/v1/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(body["ok"], true);
    assert_eq!(body["service"], "Gateway");
    assert_eq!(body["version"], "0.1");
}

// ============================================================================
// Memory endpoints: wire-compatible response shapes
// ============================================================================

#[tokio::test]
async fn test_memory_upsert_returns_id() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/upsert")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(
                    r#"{"namespace":"default","content":"test content"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert!(body["id"].is_string(), "upsert must return an 'id' field");
}

#[tokio::test]
async fn test_memory_query_returns_hits() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/query")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(
                    r#"{"namespace":"default","query":"test query"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert!(body["hits"].is_array(), "query must return a 'hits' array");
}

// ============================================================================
// Memory: GET /api/v1/memory/:id and DELETE /api/v1/memory/:id (Task 3)
// ============================================================================

#[tokio::test]
async fn test_memory_get_by_id_not_found() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/api/v1/memory/nonexistent-id-12345")
                .header("Authorization", "Bearer test-secret-token")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "unknown id must return 404"
    );
}

#[tokio::test]
async fn test_memory_get_by_id_found_after_upsert() {
    let app = build_test_app(test_config(), vec![]).await;

    // Upsert first.
    let upsert_resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/upsert")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(
                    r#"{"namespace":"default","content":"council test content","id":"test-id-get"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();
    assert_eq!(upsert_resp.status(), StatusCode::OK);

    // Now GET it.
    let get_resp = app
        .oneshot(
            Request::builder()
                .method("GET")
                .uri("/api/v1/memory/test-id-get")
                .header("Authorization", "Bearer test-secret-token")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(
        get_resp.status(),
        StatusCode::OK,
        "existing id must return 200"
    );
    let body = parse_body(get_resp).await;
    assert_eq!(body["content"], "council test content");
}

#[tokio::test]
async fn test_memory_delete_by_id() {
    let app = build_test_app(test_config(), vec![]).await;

    // Upsert first.
    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/upsert")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(
                    r#"{"namespace":"default","content":"to be deleted","id":"test-id-del"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    // Delete it.
    let del_resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri("/api/v1/memory/test-id-del")
                .header("Authorization", "Bearer test-secret-token")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(
        del_resp.status(),
        StatusCode::NO_CONTENT,
        "delete must return 204"
    );
}

#[tokio::test]
async fn test_memory_delete_not_found() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .method("DELETE")
                .uri("/api/v1/memory/ghost-id-999")
                .header("Authorization", "Bearer test-secret-token")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::NOT_FOUND,
        "delete of unknown id must return 404"
    );
}

// ============================================================================
// Memory: POST /api/v1/memory/consolidate stub (Task 4)
// ============================================================================

#[tokio::test]
async fn test_memory_consolidate_stub() {
    let app = build_test_app(test_config(), vec![]).await;
    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/consolidate")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;
    assert_eq!(body["status"], "ok");
    assert_eq!(body["consolidated"], 0);
    assert!(
        body["message"].as_str().unwrap_or("").contains("Week 4"),
        "consolidate stub must mention Week 4 in message"
    );
}

// ============================================================================
// Council Synthesis Tests (Task 1)
// ============================================================================

/// Both council members succeed → synthesis provider is called with both responses.
#[tokio::test]
async fn test_omega_mode_synthesizes() {
    let anthropic: Arc<dyn LlmProvider> =
        Arc::new(MockProvider::new("anthropic", "answer from anthropic"));
    let gemini: Arc<dyn LlmProvider> = Arc::new(MockProvider::new("gemini", "answer from gemini"));

    // The synthesis provider records the prompts it receives.
    let (synthesis_raw, synthesis_calls) =
        RecordingProvider::new("anthropic", "synthesized answer");
    let synthesis: Arc<dyn LlmProvider> = Arc::new(synthesis_raw);

    let app = build_test_app_with_council(
        test_config(),
        anthropic,
        gemini,
        synthesis,
        vec![], // fallback chain empty — shouldn't be needed
    )
    .await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"What is 2+2?","mode":"omega"}"#))
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::OK,
        "council synthesis must return 200"
    );
    let body = parse_body(resp).await;

    assert_eq!(
        body["mode"], "omega",
        "mode must be 'omega' when both council members succeed"
    );
    assert_eq!(
        body["reply"], "synthesized answer",
        "reply must come from synthesis provider"
    );

    // Verify synthesis provider was called.
    let calls = synthesis_calls.lock().unwrap();
    assert_eq!(
        calls.len(),
        1,
        "synthesis provider must be called exactly once"
    );
    // The synthesis prompt must include both agent responses.
    let synthesis_prompt = &calls[0];
    assert!(
        synthesis_prompt.contains("answer from anthropic"),
        "synthesis prompt must contain Anthropic response"
    );
    assert!(
        synthesis_prompt.contains("answer from gemini"),
        "synthesis prompt must contain Gemini response"
    );
    assert!(
        synthesis_prompt.contains("What is 2+2?"),
        "synthesis prompt must contain the original user question"
    );
}

/// One council member fails → degraded mode tag in response.
#[tokio::test]
async fn test_omega_mode_degraded_one_fail() {
    // Gemini fails; Anthropic succeeds.
    let anthropic: Arc<dyn LlmProvider> =
        Arc::new(MockProvider::new("anthropic", "anthropic answer"));
    let gemini: Arc<dyn LlmProvider> = Arc::new(FailingProvider::rate_limited("gemini"));

    // Synthesis should NOT be called — only one leg succeeded.
    let (synthesis_raw, synthesis_calls) = RecordingProvider::new("anthropic", "should not appear");
    let synthesis: Arc<dyn LlmProvider> = Arc::new(synthesis_raw);

    let app =
        build_test_app_with_council(test_config(), anthropic, gemini, synthesis, vec![]).await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"omega"}"#))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK);
    let body = parse_body(resp).await;

    assert_eq!(
        body["mode"], "omega-degraded-gemini",
        "mode must indicate which council member failed"
    );
    assert_eq!(body["reply"], "anthropic answer");

    // Synthesis must not have been called.
    let calls = synthesis_calls.lock().unwrap();
    assert_eq!(
        calls.len(),
        0,
        "synthesis must not run when only one council member succeeds"
    );
}

/// Both council members fail → fallback chain runs.
#[tokio::test]
async fn test_omega_mode_both_fail_uses_failover() {
    let anthropic: Arc<dyn LlmProvider> = Arc::new(FailingProvider::rate_limited("anthropic"));
    let gemini: Arc<dyn LlmProvider> = Arc::new(FailingProvider::rate_limited("gemini"));

    // Synthesis not needed — both legs fail.
    let synthesis: Arc<dyn LlmProvider> =
        Arc::new(MockProvider::new("anthropic", "should not appear"));

    // Fallback chain has a working provider.
    let fallback: Arc<dyn LlmProvider> =
        Arc::new(MockProvider::new("perplexity", "from fallback chain"));

    let app =
        build_test_app_with_council(test_config(), anthropic, gemini, synthesis, vec![fallback])
            .await;

    let resp = app
        .oneshot(chat_request(r#"{"user":"test","mode":"omega"}"#))
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK, "fallback chain must succeed");
    let body = parse_body(resp).await;

    assert_eq!(
        body["reply"], "from fallback chain",
        "reply must come from fallback chain when both council members fail"
    );
}

// ============================================================================
// Ingest endpoint tests (Synthesis Sprint Task 4)
// ============================================================================

/// POST /api/v1/memory/ingest with inline content → chunks written correctly.
#[tokio::test]
async fn test_ingest_chunks_content() {
    let app = build_test_app(test_config(), vec![]).await;

    // Three paragraphs separated by blank lines → 3 chunks.
    let body_str = r#"{"content":"para one\n\npara two\n\npara three","source":"test"}"#;

    let resp = app
        .clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/ingest")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(body_str))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(resp.status(), StatusCode::OK, "ingest must return 200");
    let body = parse_body(resp).await;
    assert_eq!(body["ingested"], 3, "three paragraphs → 3 chunks ingested");
    assert_eq!(body["chunks"], 3, "chunk count must match ingested");
}

/// POST /api/v1/memory/ingest with a non-existent path → 400.
#[tokio::test]
async fn test_ingest_missing_file_returns_400() {
    let app = build_test_app(test_config(), vec![]).await;

    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/ingest")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(
                    r#"{"path":"/tmp/this-file-should-not-exist-omega-test-xyz.txt"}"#,
                ))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::BAD_REQUEST,
        "missing file must return 400"
    );
}

/// POST /api/v1/memory/ingest with neither content nor path → 400.
#[tokio::test]
async fn test_ingest_no_content_no_path_returns_400() {
    let app = build_test_app(test_config(), vec![]).await;

    let resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/ingest")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(r#"{"source":"test"}"#))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(
        resp.status(),
        StatusCode::BAD_REQUEST,
        "missing content and path must return 400"
    );
}

/// POST /api/v1/memory/ingest → verify chunks are searchable in memory.
#[tokio::test]
async fn test_ingest_chunks_are_searchable() {
    let app = build_test_app(test_config(), vec![]).await;

    // Ingest two distinct paragraphs.
    let ingest_body = r#"{"content":"quantum entanglement is fascinating\n\nrust ownership model rocks","source":"test-ingest","namespace":"default"}"#;

    app.clone()
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/ingest")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(ingest_body))
                .unwrap(),
        )
        .await
        .unwrap();

    // Query memory for one of the ingested chunks.
    let query_resp = app
        .oneshot(
            Request::builder()
                .method("POST")
                .uri("/api/v1/memory/query")
                .header("Authorization", "Bearer test-secret-token")
                .header("Content-Type", "application/json")
                .body(Body::from(r#"{"query":"quantum","limit":5}"#))
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(query_resp.status(), StatusCode::OK);
    let qbody = parse_body(query_resp).await;
    let hits = qbody["hits"].as_array().expect("hits must be array");
    assert!(
        !hits.is_empty(),
        "ingested chunk about quantum should be findable in memory"
    );
}
