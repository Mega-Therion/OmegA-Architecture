use chrono::Utc;
use omega_trace::{TraceEvent, TraceOutcome, TraceStore};

async fn in_memory_store() -> TraceStore {
    let store = TraceStore::new("sqlite::memory:")
        .await
        .expect("store init failed");
    store.migrate().await.expect("migration failed");
    store
}

fn make_event(agent: &str, task_id: Option<&str>) -> TraceEvent {
    TraceEvent {
        id: String::new(), // store will generate
        task_id: task_id.map(|s| s.to_string()),
        agent: agent.to_string(),
        phase: "execute".to_string(),
        action: "test_action".to_string(),
        outcome: TraceOutcome::Success,
        duration_ms: 42,
        tokens: Some(100),
        error: None,
        timestamp: Utc::now(),
        provider_used: None,
        retrieval_sources: None,
        identity_shell_loaded: None,
        memory_context_loaded: None,
        tool_invocations: None,
        failure_tags: None,
        consensus_required: None,
        consensus_outcome: None,
        phase_state: None,
        phase_transition_id: None,
        resonance_amplitude: None,
        shear_index: None,
        canon_anchor_weight: None,
        structural_integrity_score: None,
        intent_priority_score: None,
        authority_shrink_level: None,
        predicted_failure_modes: None,
        actual_failure_mode: None,
        promotion_decay_ratio: None,
    }
}

#[tokio::test]
async fn test_record_and_retrieve() {
    let store = in_memory_store().await;

    let recorded = store
        .record(make_event("gateway", Some("task-001")))
        .await
        .expect("record failed");

    // id should have been assigned
    assert!(!recorded.id.is_empty());
    assert_eq!(recorded.agent, "gateway");
    assert_eq!(recorded.outcome, TraceOutcome::Success);
    assert_eq!(recorded.duration_ms, 42);
    assert_eq!(recorded.tokens, Some(100));

    let recent = store.recent(10).await.expect("recent failed");
    assert_eq!(recent.len(), 1);
    assert_eq!(recent[0].id, recorded.id);
    assert_eq!(recent[0].agent, "gateway");
    assert_eq!(recent[0].task_id, Some("task-001".to_string()));
}

#[tokio::test]
async fn test_filter_by_task() {
    let store = in_memory_store().await;

    store
        .record(make_event("claude", Some("task-1")))
        .await
        .expect("record 1");
    store
        .record(make_event("codex", Some("task-1")))
        .await
        .expect("record 2");
    store
        .record(make_event("gemini", Some("task-2")))
        .await
        .expect("record 3");

    let task1_events = store.by_task("task-1").await.expect("by_task failed");
    let task2_events = store.by_task("task-2").await.expect("by_task failed");
    let task3_events = store.by_task("task-3").await.expect("by_task failed");

    assert_eq!(task1_events.len(), 2);
    assert_eq!(task2_events.len(), 1);
    assert_eq!(task3_events.len(), 0);
}

#[tokio::test]
async fn test_filter_by_agent() {
    let store = in_memory_store().await;

    store
        .record(make_event("codex", Some("t1")))
        .await
        .expect("record 1");
    store
        .record(make_event("codex", Some("t2")))
        .await
        .expect("record 2");
    store
        .record(make_event("claude", Some("t3")))
        .await
        .expect("record 3");

    let codex_events = store.by_agent("codex").await.expect("by_agent failed");
    let claude_events = store.by_agent("claude").await.expect("by_agent failed");
    let gemini_events = store.by_agent("gemini").await.expect("by_agent failed");

    assert_eq!(codex_events.len(), 2);
    assert_eq!(claude_events.len(), 1);
    assert_eq!(gemini_events.len(), 0);
}

#[tokio::test]
async fn test_outcome_variants_roundtrip() {
    let store = in_memory_store().await;

    let outcomes = vec![
        TraceOutcome::Success,
        TraceOutcome::Failure,
        TraceOutcome::Timeout,
        TraceOutcome::Blocked,
        TraceOutcome::Delegated,
    ];

    for outcome in &outcomes {
        let mut ev = make_event("gateway", None);
        ev.outcome = outcome.clone();
        store.record(ev).await.expect("record failed");
    }

    let events = store.recent(10).await.expect("recent failed");
    assert_eq!(events.len(), outcomes.len());
    // Newest first, so reverse
    for (ev, expected) in events.iter().rev().zip(outcomes.iter()) {
        assert_eq!(&ev.outcome, expected);
    }
}

#[tokio::test]
async fn test_teleodynamic_fields_roundtrip() {
    let store = in_memory_store().await;

    let mut ev = make_event("gateway", Some("teleo-1"));
    ev.phase_state = Some("ACT".to_string());
    ev.phase_transition_id = Some("pt-001".to_string());
    ev.resonance_amplitude = Some(0.61);
    ev.shear_index = Some(0.23);
    ev.canon_anchor_weight = Some(0.77);
    ev.structural_integrity_score = Some(0.91);
    ev.intent_priority_score = Some(0.64);
    ev.authority_shrink_level = Some(0.28);
    ev.predicted_failure_modes = Some(vec!["RETRIEVAL".to_string()]);
    ev.actual_failure_mode = Some("RUNTIME_ENV".to_string());
    ev.promotion_decay_ratio = Some(1.5);

    store.record(ev).await.expect("record failed");

    let recent = store.recent(10).await.expect("recent failed");
    assert_eq!(recent.len(), 1);
    let got = &recent[0];
    assert_eq!(got.phase_state.as_deref(), Some("ACT"));
    assert_eq!(got.phase_transition_id.as_deref(), Some("pt-001"));
    assert_eq!(got.actual_failure_mode.as_deref(), Some("RUNTIME_ENV"));
    assert_eq!(
        got.predicted_failure_modes.as_ref().unwrap()[0],
        "RETRIEVAL"
    );
    assert_eq!(got.resonance_amplitude, Some(0.61));
    assert_eq!(got.promotion_decay_ratio, Some(1.5));
}
