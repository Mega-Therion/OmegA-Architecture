use chrono::Utc;
use dashmap::DashMap;
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use thiserror::Error;
use uuid::Uuid;

#[derive(Error, Debug)]
pub enum ConsensusError {
    #[error("Decision not found: {0}")]
    NotFound(String),
    #[error("Unauthorized agent: {0}")]
    Unauthorized(String),
    #[error("Agent {0} already voted")]
    DuplicateVote(String),
    #[error("Decision already finalized")]
    AlreadyFinalized,
    #[error("Insufficient agents: need {min}, got {got}")]
    InsufficientAgents { min: usize, got: usize },
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum VoteType {
    Approve,
    Reject,
    Abstain,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ConsensusStatus {
    Reached,
    Failed,
    InsufficientVotes,
    ByzantineDetected,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoteRecord {
    pub agent_id: String,
    pub vote: VoteType,
    pub justification: Option<String>,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConsolidationDecision {
    pub id: String,
    pub description: String,
    pub required_agents: Vec<String>,
    pub votes: DashMap<String, VoteRecord>,
    pub quorum_required: usize,
    pub status: String,
    pub initiated_at: String,
    pub finalized_at: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TallyResult {
    pub decision_id: String,
    pub status: ConsensusStatus,
    pub approve_count: usize,
    pub reject_count: usize,
    pub abstain_count: usize,
    pub total_votes: usize,
    pub quorum_required: usize,
    pub consensus_percentage: f32,
    pub finalized_at: String,
}

pub struct DCBFTEngine {
    pub max_faulty_agents: usize,
    pending_decisions: DashMap<String, Arc<ConsolidationDecision>>,
    finalized_decisions: DashMap<String, TallyResult>,
}

impl DCBFTEngine {
    pub fn new(max_faulty_agents: usize) -> Self {
        Self {
            max_faulty_agents,
            pending_decisions: DashMap::new(),
            finalized_decisions: DashMap::new(),
        }
    }

    fn calculate_min_agents(&self) -> usize {
        (3 * self.max_faulty_agents) + 1
    }

    fn calculate_quorum(&self, total: usize) -> usize {
        (total * 2 + 2) / 3 // Ceiling of 2/3 * total
    }

    pub async fn initiate_vote(
        &self,
        decision_id: Option<String>,
        description: String,
        required_agents: Vec<String>,
    ) -> Result<Arc<ConsolidationDecision>, ConsensusError> {
        let min_required = self.calculate_min_agents();
        if required_agents.len() < min_required {
            return Err(ConsensusError::InsufficientAgents {
                min: min_required,
                got: required_agents.len(),
            });
        }

        let id = decision_id.unwrap_or_else(|| Uuid::new_v4().to_string());
        let quorum = self.calculate_quorum(required_agents.len());

        let decision = Arc::new(ConsolidationDecision {
            id: id.clone(),
            description,
            required_agents,
            votes: DashMap::new(),
            quorum_required: quorum,
            status: "pending".to_string(),
            initiated_at: Utc::now().to_rfc3339(),
            finalized_at: None,
        });

        self.pending_decisions.insert(id, Arc::clone(&decision));
        Ok(decision)
    }

    pub async fn cast_vote(
        &self,
        decision_id: &str,
        agent_id: &str,
        vote: VoteType,
        justification: Option<String>,
    ) -> Result<(), ConsensusError> {
        let decision = self
            .pending_decisions
            .get(decision_id)
            .ok_or_else(|| ConsensusError::NotFound(decision_id.to_string()))?;

        if !decision.required_agents.contains(&agent_id.to_string()) {
            return Err(ConsensusError::Unauthorized(agent_id.to_string()));
        }

        if decision.votes.contains_key(agent_id) {
            return Err(ConsensusError::DuplicateVote(agent_id.to_string()));
        }

        decision.votes.insert(
            agent_id.to_string(),
            VoteRecord {
                agent_id: agent_id.to_string(),
                vote,
                justification,
                timestamp: Utc::now().to_rfc3339(),
            },
        );

        Ok(())
    }

    pub async fn tally(&self, decision_id: &str) -> Result<TallyResult, ConsensusError> {
        if let Some(finalized) = self.finalized_decisions.get(decision_id) {
            return Ok(finalized.clone());
        }

        let decision = self
            .pending_decisions
            .get(decision_id)
            .ok_or_else(|| ConsensusError::NotFound(decision_id.to_string()))?;

        let total_cast = decision.votes.len();
        let mut approve = 0;
        let mut reject = 0;
        let mut abstain = 0;

        for entry in decision.votes.iter() {
            match entry.value().vote {
                VoteType::Approve => approve += 1,
                VoteType::Reject => reject += 1,
                VoteType::Abstain => abstain += 1,
            }
        }

        if total_cast < decision.quorum_required {
            return Ok(TallyResult {
                decision_id: decision_id.to_string(),
                status: ConsensusStatus::InsufficientVotes,
                approve_count: approve,
                reject_count: reject,
                abstain_count: abstain,
                total_votes: total_cast,
                quorum_required: decision.quorum_required,
                consensus_percentage: (approve as f32 / total_cast as f32) * 100.0,
                finalized_at: Utc::now().to_rfc3339(),
            });
        }

        let status = if approve >= decision.quorum_required {
            ConsensusStatus::Reached
        } else {
            ConsensusStatus::Failed
        };

        let result = TallyResult {
            decision_id: decision_id.to_string(),
            status,
            approve_count: approve,
            reject_count: reject,
            abstain_count: abstain,
            total_votes: total_cast,
            quorum_required: decision.quorum_required,
            consensus_percentage: (approve as f32 / total_cast as f32) * 100.0,
            finalized_at: Utc::now().to_rfc3339(),
        };

        self.finalized_decisions
            .insert(decision_id.to_string(), result.clone());
        self.pending_decisions.remove(decision_id);

        Ok(result)
    }
}
