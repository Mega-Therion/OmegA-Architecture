use crate::state::AppState;
use axum::{
    extract::{Path, State},
    Json,
};
use omega_core::economy::{Transaction, TransactionType, Wallet};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Debug, Deserialize)]
pub struct InitWalletRequest {
    pub agent_id: String,
    pub start_balance: f32,
}

#[derive(Debug, Deserialize)]
pub struct TransactionRequest {
    pub agent_id: String,
    pub amount: f32,
    pub transaction_type: TransactionType,
    pub description: String,
}

#[derive(Debug, Serialize)]
pub struct EconomyResponse<T> {
    pub success: bool,
    pub data: Option<T>,
    pub error: Option<String>,
}

pub async fn init_wallet_handler(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<InitWalletRequest>,
) -> Json<EconomyResponse<Wallet>> {
    match state
        .economy
        .init_wallet(&payload.agent_id, payload.start_balance)
        .await
    {
        Ok(wallet) => Json(EconomyResponse {
            success: true,
            data: Some(wallet),
            error: None,
        }),
        Err(e) => Json(EconomyResponse {
            success: false,
            data: None,
            error: Some(e.to_string()),
        }),
    }
}

pub async fn get_wallet_handler(
    State(state): State<Arc<AppState>>,
    Path(agent_id): Path<String>,
) -> Json<EconomyResponse<Wallet>> {
    match state.economy.get_wallet(&agent_id).await {
        Ok(wallet) => Json(EconomyResponse {
            success: true,
            data: Some(wallet),
            error: None,
        }),
        Err(e) => Json(EconomyResponse {
            success: false,
            data: None,
            error: Some(e.to_string()),
        }),
    }
}

pub async fn record_transaction_handler(
    State(state): State<Arc<AppState>>,
    Json(payload): Json<TransactionRequest>,
) -> Json<EconomyResponse<Transaction>> {
    match state
        .economy
        .record_transaction(
            &payload.agent_id,
            payload.amount,
            payload.transaction_type,
            &payload.description,
        )
        .await
    {
        Ok(tx) => Json(EconomyResponse {
            success: true,
            data: Some(tx),
            error: None,
        }),
        Err(e) => Json(EconomyResponse {
            success: false,
            data: None,
            error: Some(e.to_string()),
        }),
    }
}
