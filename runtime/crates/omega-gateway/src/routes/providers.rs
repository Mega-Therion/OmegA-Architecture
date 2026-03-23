use axum::{extract::State, http::StatusCode, response::IntoResponse, Json};
use serde_json::json;
use std::sync::Arc;

use crate::state::AppState;

/// GET /api/v1/providers — list configured providers (auth required).
pub async fn providers_handler(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    let has = |key: &str| !key.is_empty();
    (
        StatusCode::OK,
        Json(json!({
            "providers": [
                { "name": "codex",      "enabled": has(&state.config.omega_codex_cli_path)      },
                { "name": "claude-cli", "enabled": has(&state.config.omega_claude_cli_path)     },
                { "name": "gemini-cli", "enabled": has(&state.config.omega_gemini_cli_path)     },
                { "name": "openai",     "enabled": has(&state.config.omega_openai_api_key)       },
                { "name": "perplexity", "enabled": has(&state.config.omega_perplexity_api_key) },
                { "name": "deepseek",   "enabled": has(&state.config.omega_deepseek_api_key)   },
                { "name": "gemini",     "enabled": has(&state.config.omega_gemini_api_key)      },
                { "name": "anthropic",  "enabled": has(&state.config.omega_anthropic_api_key)   },
                { "name": "xai",        "enabled": has(&state.config.omega_xai_api_key)         },
                { "name": "local",      "enabled": true                                          },
            ]
        })),
    )
}
