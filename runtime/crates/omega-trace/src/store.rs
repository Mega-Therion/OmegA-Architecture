//! Async SQLite-backed trace store.
//!
//! Records append-only [`TraceEvent`]s that capture agent lifecycle actions.
//! Events are never mutated or deleted after write.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::{migrate::Migrator, Row, SqlitePool};
use thiserror::Error;
use uuid::Uuid;

/// Embedded migrations — resolved from the crate's `migrations/` directory.
static MIGRATOR: Migrator = sqlx::migrate!();

// ---------------------------------------------------------------------------
// Domain types
// ---------------------------------------------------------------------------

/// The outcome of a traced agent action.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TraceOutcome {
    Success,
    Failure,
    Timeout,
    /// Action was blocked by RiskGovernor / policy.
    Blocked,
    /// Action was handed off to a specialist agent.
    Delegated,
}

impl std::fmt::Display for TraceOutcome {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Self::Success => "success",
            Self::Failure => "failure",
            Self::Timeout => "timeout",
            Self::Blocked => "blocked",
            Self::Delegated => "delegated",
        };
        write!(f, "{s}")
    }
}

impl std::str::FromStr for TraceOutcome {
    type Err = String;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "success" => Ok(Self::Success),
            "failure" => Ok(Self::Failure),
            "timeout" => Ok(Self::Timeout),
            "blocked" => Ok(Self::Blocked),
            "delegated" => Ok(Self::Delegated),
            other => Err(format!("unknown TraceOutcome: {other}")),
        }
    }
}

/// A single recorded agent action. Append-only — never mutated after write.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceEvent {
    pub id: String,
    /// Links back to the parent TaskGraph mission.
    pub task_id: Option<String>,
    pub agent: String,
    /// Lifecycle phase: plan | retrieve | execute | validate | synthesise | prune
    pub phase: String,
    pub action: String,
    pub outcome: TraceOutcome,
    pub duration_ms: u64,
    pub tokens: Option<usize>,
    pub error: Option<String>,
    pub timestamp: DateTime<Utc>,
    // --- Extended fields (docs/orchestration_logging_spec.md) ---
    /// The LLM provider actually used (e.g. "anthropic", "gemini", "local").
    pub provider_used: Option<String>,
    /// Memory entry IDs retrieved and injected as context; serialized as JSON in DB.
    pub retrieval_sources: Option<Vec<String>>,
    /// Whether the identity shell (identity.yaml) was loaded for this request.
    pub identity_shell_loaded: Option<bool>,
    /// Whether memory context was injected (memory_hits non-empty).
    pub memory_context_loaded: Option<bool>,
    /// Tool invocations during this action; serialized as JSON in DB.
    pub tool_invocations: Option<Vec<String>>,
    /// Failure taxonomy tags (e.g. "IDENTITY_SHELL", "PROVIDER_CONTAM"); JSON in DB.
    pub failure_tags: Option<Vec<String>>,
    /// Whether DCBFT consensus was required for this action.
    pub consensus_required: Option<bool>,
    /// Outcome of the consensus vote: "approved" | "rejected" | "bypassed".
    pub consensus_outcome: Option<String>,
    /// Canonical lifecycle state for this action.
    pub phase_state: Option<String>,
    /// Unique identifier for this transition into the current phase.
    pub phase_transition_id: Option<String>,
    /// Estimate of active effort/coherence pressure in the current request.
    pub resonance_amplitude: Option<f64>,
    /// Estimate of retrieval discontinuity or contradiction pressure.
    pub shear_index: Option<f64>,
    /// Relative weight exerted by identity/canon anchors.
    pub canon_anchor_weight: Option<f64>,
    /// Aggregate cross-layer integrity estimate.
    pub structural_integrity_score: Option<f64>,
    /// Relative priority of the active objective.
    pub intent_priority_score: Option<f64>,
    /// Amount of autonomy contraction due to uncertainty or risk.
    pub authority_shrink_level: Option<f64>,
    /// Predicted failure tags before execution; serialized as JSON in DB.
    pub predicted_failure_modes: Option<Vec<String>>,
    /// Actual failure mode after execution.
    pub actual_failure_mode: Option<String>,
    /// Ratio between promotion and decay in memory-related flows.
    pub promotion_decay_ratio: Option<f64>,
}

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

#[derive(Debug, Error)]
pub enum TraceError {
    #[error("sqlx error: {0}")]
    Sqlx(#[from] sqlx::Error),
    #[error("migration error: {0}")]
    Migration(#[from] sqlx::migrate::MigrateError),
    #[error("parse error: {0}")]
    Parse(String),
}

// ---------------------------------------------------------------------------
// TraceStore
// ---------------------------------------------------------------------------

/// SQLite-backed, async, append-only trace store.
pub struct TraceStore {
    pool: SqlitePool,
}

impl TraceStore {
    /// Open (or create) the SQLite database at `db_url`.
    ///
    /// Accepts any valid `sqlx` SQLite connection string, e.g.:
    /// - `"sqlite::memory:"` — in-process, for tests
    /// - `"sqlite:///home/mega/.omega/trace.db"` — persistent file
    pub async fn new(db_url: &str) -> Result<Self, TraceError> {
        let pool = SqlitePool::connect(db_url).await?;
        Ok(Self { pool })
    }

    /// Apply pending migrations. Idempotent — safe to call on every startup.
    pub async fn migrate(&self) -> Result<(), TraceError> {
        MIGRATOR.run(&self.pool).await?;
        Ok(())
    }

    /// Append a trace event and persist to the database.
    ///
    /// If `event.id` is empty a new UUID v4 is generated.
    pub async fn record(&self, mut event: TraceEvent) -> Result<TraceEvent, TraceError> {
        if event.id.is_empty() {
            event.id = Uuid::new_v4().to_string();
        }

        let outcome_str = event.outcome.to_string();
        let ts = event.timestamp.to_rfc3339();
        let tokens = event.tokens.map(|t| t as i64);
        let retrieval_sources_json = event
            .retrieval_sources
            .as_ref()
            .map(|v| serde_json::to_string(v).unwrap_or_default());
        let tool_invocations_json = event
            .tool_invocations
            .as_ref()
            .map(|v| serde_json::to_string(v).unwrap_or_default());
        let failure_tags_json = event
            .failure_tags
            .as_ref()
            .map(|v| serde_json::to_string(v).unwrap_or_default());
        let predicted_failure_modes_json = event
            .predicted_failure_modes
            .as_ref()
            .map(|v| serde_json::to_string(v).unwrap_or_default());
        let identity_shell_loaded = event.identity_shell_loaded.map(|b| b as i64);
        let memory_context_loaded = event.memory_context_loaded.map(|b| b as i64);
        let consensus_required = event.consensus_required.map(|b| b as i64);

        sqlx::query(
            r#"
            INSERT INTO trace_events
                (id, task_id, agent, phase, action, outcome, duration_ms, tokens, error, timestamp,
                 provider_used, retrieval_sources, identity_shell_loaded, memory_context_loaded,
                 tool_invocations, failure_tags, consensus_required, consensus_outcome,
                 phase_state, phase_transition_id, resonance_amplitude, shear_index,
                 canon_anchor_weight, structural_integrity_score, intent_priority_score,
                 authority_shrink_level, predicted_failure_modes, actual_failure_mode,
                 promotion_decay_ratio)
            VALUES
                (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10,
                 ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18,
                 ?19, ?20, ?21, ?22, ?23, ?24, ?25,
                 ?26, ?27, ?28, ?29)
            "#,
        )
        .bind(&event.id)
        .bind(&event.task_id)
        .bind(&event.agent)
        .bind(&event.phase)
        .bind(&event.action)
        .bind(&outcome_str)
        .bind(event.duration_ms as i64)
        .bind(tokens)
        .bind(&event.error)
        .bind(&ts)
        .bind(&event.provider_used)
        .bind(&retrieval_sources_json)
        .bind(identity_shell_loaded)
        .bind(memory_context_loaded)
        .bind(&tool_invocations_json)
        .bind(&failure_tags_json)
        .bind(consensus_required)
        .bind(&event.consensus_outcome)
        .bind(&event.phase_state)
        .bind(&event.phase_transition_id)
        .bind(event.resonance_amplitude)
        .bind(event.shear_index)
        .bind(event.canon_anchor_weight)
        .bind(event.structural_integrity_score)
        .bind(event.intent_priority_score)
        .bind(event.authority_shrink_level)
        .bind(&predicted_failure_modes_json)
        .bind(&event.actual_failure_mode)
        .bind(event.promotion_decay_ratio)
        .execute(&self.pool)
        .await?;

        tracing::debug!(
            id = %event.id,
            agent = %event.agent,
            phase = %event.phase,
            outcome = %outcome_str,
            "trace event recorded"
        );

        Ok(event)
    }

    /// Return the most recent `limit` events, newest first.
    pub async fn recent(&self, limit: usize) -> Result<Vec<TraceEvent>, TraceError> {
        let limit_i64 = limit as i64;
        let rows = sqlx::query(
            r#"
            SELECT id, task_id, agent, phase, action, outcome, duration_ms, tokens, error, timestamp,
                   provider_used, retrieval_sources, identity_shell_loaded, memory_context_loaded,
                   tool_invocations, failure_tags, consensus_required, consensus_outcome,
                   phase_state, phase_transition_id, resonance_amplitude, shear_index,
                   canon_anchor_weight, structural_integrity_score, intent_priority_score,
                   authority_shrink_level, predicted_failure_modes, actual_failure_mode,
                   promotion_decay_ratio
            FROM trace_events
            ORDER BY timestamp DESC
            LIMIT ?1
            "#,
        )
        .bind(limit_i64)
        .fetch_all(&self.pool)
        .await?;

        rows.iter().map(row_to_event).collect()
    }

    /// Return all events linked to `task_id`, in chronological order.
    pub async fn by_task(&self, task_id: &str) -> Result<Vec<TraceEvent>, TraceError> {
        let rows = sqlx::query(
            r#"
            SELECT id, task_id, agent, phase, action, outcome, duration_ms, tokens, error, timestamp,
                   provider_used, retrieval_sources, identity_shell_loaded, memory_context_loaded,
                   tool_invocations, failure_tags, consensus_required, consensus_outcome,
                   phase_state, phase_transition_id, resonance_amplitude, shear_index,
                   canon_anchor_weight, structural_integrity_score, intent_priority_score,
                   authority_shrink_level, predicted_failure_modes, actual_failure_mode,
                   promotion_decay_ratio
            FROM trace_events
            WHERE task_id = ?1
            ORDER BY timestamp ASC
            "#,
        )
        .bind(task_id)
        .fetch_all(&self.pool)
        .await?;

        rows.iter().map(row_to_event).collect()
    }

    /// Return all events for the given agent, in chronological order.
    pub async fn by_agent(&self, agent: &str) -> Result<Vec<TraceEvent>, TraceError> {
        let rows = sqlx::query(
            r#"
            SELECT id, task_id, agent, phase, action, outcome, duration_ms, tokens, error, timestamp,
                   provider_used, retrieval_sources, identity_shell_loaded, memory_context_loaded,
                   tool_invocations, failure_tags, consensus_required, consensus_outcome,
                   phase_state, phase_transition_id, resonance_amplitude, shear_index,
                   canon_anchor_weight, structural_integrity_score, intent_priority_score,
                   authority_shrink_level, predicted_failure_modes, actual_failure_mode,
                   promotion_decay_ratio
            FROM trace_events
            WHERE agent = ?1
            ORDER BY timestamp ASC
            "#,
        )
        .bind(agent)
        .fetch_all(&self.pool)
        .await?;

        rows.iter().map(row_to_event).collect()
    }
}

// ---------------------------------------------------------------------------
// Row mapping
// ---------------------------------------------------------------------------

fn row_to_event(r: &sqlx::sqlite::SqliteRow) -> Result<TraceEvent, TraceError> {
    let outcome_str: String = r.try_get("outcome").unwrap_or_default();
    let outcome: TraceOutcome = outcome_str.parse().map_err(TraceError::Parse)?;

    let ts_str: String = r.try_get("timestamp").unwrap_or_default();
    let timestamp: DateTime<Utc> = ts_str.parse().unwrap_or_else(|_| Utc::now());

    let tokens: Option<i64> = r.try_get("tokens").unwrap_or(None);

    let retrieval_sources: Option<Vec<String>> = r
        .try_get::<Option<String>, _>("retrieval_sources")
        .unwrap_or(None)
        .and_then(|s| serde_json::from_str(&s).ok());
    let tool_invocations: Option<Vec<String>> = r
        .try_get::<Option<String>, _>("tool_invocations")
        .unwrap_or(None)
        .and_then(|s| serde_json::from_str(&s).ok());
    let failure_tags: Option<Vec<String>> = r
        .try_get::<Option<String>, _>("failure_tags")
        .unwrap_or(None)
        .and_then(|s| serde_json::from_str(&s).ok());
    let predicted_failure_modes: Option<Vec<String>> = r
        .try_get::<Option<String>, _>("predicted_failure_modes")
        .unwrap_or(None)
        .and_then(|s| serde_json::from_str(&s).ok());

    Ok(TraceEvent {
        id: r.try_get("id").unwrap_or_default(),
        task_id: r.try_get("task_id").unwrap_or(None),
        agent: r.try_get("agent").unwrap_or_default(),
        phase: r.try_get("phase").unwrap_or_default(),
        action: r.try_get("action").unwrap_or_default(),
        outcome,
        duration_ms: r.try_get::<i64, _>("duration_ms").unwrap_or(0) as u64,
        tokens: tokens.map(|t| t as usize),
        error: r.try_get("error").unwrap_or(None),
        timestamp,
        provider_used: r.try_get("provider_used").unwrap_or(None),
        retrieval_sources,
        identity_shell_loaded: r
            .try_get::<Option<i64>, _>("identity_shell_loaded")
            .unwrap_or(None)
            .map(|v| v != 0),
        memory_context_loaded: r
            .try_get::<Option<i64>, _>("memory_context_loaded")
            .unwrap_or(None)
            .map(|v| v != 0),
        tool_invocations,
        failure_tags,
        consensus_required: r
            .try_get::<Option<i64>, _>("consensus_required")
            .unwrap_or(None)
            .map(|v| v != 0),
        consensus_outcome: r.try_get("consensus_outcome").unwrap_or(None),
        phase_state: r.try_get("phase_state").unwrap_or(None),
        phase_transition_id: r.try_get("phase_transition_id").unwrap_or(None),
        resonance_amplitude: r.try_get("resonance_amplitude").unwrap_or(None),
        shear_index: r.try_get("shear_index").unwrap_or(None),
        canon_anchor_weight: r.try_get("canon_anchor_weight").unwrap_or(None),
        structural_integrity_score: r.try_get("structural_integrity_score").unwrap_or(None),
        intent_priority_score: r.try_get("intent_priority_score").unwrap_or(None),
        authority_shrink_level: r.try_get("authority_shrink_level").unwrap_or(None),
        predicted_failure_modes,
        actual_failure_mode: r.try_get("actual_failure_mode").unwrap_or(None),
        promotion_decay_ratio: r.try_get("promotion_decay_ratio").unwrap_or(None),
    })
}
