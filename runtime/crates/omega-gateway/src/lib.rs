pub mod agency;
pub mod config;
pub mod correction;
pub mod dream;
pub mod livekit;
pub mod middleware;
pub mod routes;
pub mod state;

use std::sync::Arc;
use std::time::Duration;

use axum::{
    middleware as axum_middleware,
    routing::{get, post},
    Router,
};

use crate::state::AppState;

/// Build the Axum router from the given state and timeout.
/// Extracted here (in lib.rs) so integration tests can call it without a running server.
pub fn build_app(state: Arc<AppState>, timeout: Duration) -> Router {
    let auth = axum_middleware::from_fn_with_state(state.clone(), middleware::auth::bearer_auth);
    let policy =
        axum_middleware::from_fn_with_state(state.clone(), middleware::policy::policy_check);

    Router::new()
        .route("/", get(routes::health::root_handler))
        .route("/health", get(routes::health::health_handler))
        .route("/health/deep", get(routes::health::deep_health_handler))
        .route("/healthz", get(routes::health::healthz_handler))
        .route("/ready", get(routes::health::ready_handler))
        .route(
            "/api/v1/chat",
            post(routes::chat::chat_handler)
                .route_layer(policy)
                .route_layer(auth.clone()),
        )
        .route("/api/v1/health", get(routes::health::health_handler))
        .route(
            "/api/v1/status",
            get(routes::health::status_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/providers",
            get(routes::providers::providers_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/chat/stream",
            post(routes::chat::stream_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/memory/upsert",
            post(routes::memory::upsert_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/memory/query",
            post(routes::memory::query_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/memory/consolidate",
            post(routes::memory::consolidate_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/memory/:id",
            get(routes::memory::get_by_id_handler)
                .delete(routes::memory::delete_by_id_handler)
                .route_layer(auth.clone()),
        )
        // Consensus routes
        .route(
            "/api/v1/consensus/initiate",
            post(routes::consensus::initiate_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/consensus/:id/vote",
            post(routes::consensus::vote_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/consensus/:id",
            get(routes::consensus::status_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/economy/init",
            post(routes::economy::init_wallet_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/economy/wallet/:agent_id",
            get(routes::economy::get_wallet_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/economy/transaction",
            post(routes::economy::record_transaction_handler).route_layer(auth.clone()),
        )
        // Trace routes
        .route(
            "/api/v1/trace",
            get(routes::trace::list_handler).route_layer(auth.clone()),
        )
        .route(
            "/api/v1/trace/task/:task_id",
            get(routes::trace::by_task_handler).route_layer(auth.clone()),
        )
        // Ingest route
        .route(
            "/api/v1/memory/ingest",
            post(routes::ingest::ingest_handler).route_layer(auth.clone()),
        )
        .with_state(state)
        .layer(
            tower::ServiceBuilder::new()
                .layer(tower_http::trace::TraceLayer::new_for_http())
                .layer(tower_http::timeout::TimeoutLayer::new(timeout))
                .layer(tower_http::cors::CorsLayer::permissive())
                .layer(tower_http::compression::CompressionLayer::new()),
        )
}
