use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum EconomyError {
    #[error("Wallet not found for agent: {0}")]
    WalletNotFound(String),
    #[error("Insufficient balance: need {need}, have {have}")]
    InsufficientBalance { need: f32, have: f32 },
    #[error("Database error: {0}")]
    DatabaseError(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum TransactionType {
    Earn,
    Spend,
    Grant,
    Fine,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Wallet {
    pub agent_id: String,
    pub balance: f32,
    pub total_earned: f32,
    pub total_spent: f32,
    pub is_bankrupt: bool,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transaction {
    pub id: Option<u64>,
    pub agent_id: String,
    pub amount: f32,
    pub transaction_type: TransactionType,
    pub description: String,
    pub balance_after: f32,
    pub created_at: String,
}

#[async_trait]
pub trait NeuroCreditStore: Send + Sync {
    /// Initialise a wallet for an agent.
    async fn init_wallet(&self, agent_id: &str, start_balance: f32)
        -> Result<Wallet, EconomyError>;

    /// Get current wallet for an agent.
    async fn get_wallet(&self, agent_id: &str) -> Result<Wallet, EconomyError>;

    /// Record a transaction (updates balance and logs event).
    async fn record_transaction(
        &self,
        agent_id: &str,
        amount: f32,
        tx_type: TransactionType,
        description: &str,
    ) -> Result<Transaction, EconomyError>;

    /// Check if an agent can afford a specific cost.
    async fn can_afford(&self, agent_id: &str, amount: f32) -> Result<bool, EconomyError> {
        let wallet = self.get_wallet(agent_id).await?;
        Ok(wallet.balance >= amount)
    }
}
