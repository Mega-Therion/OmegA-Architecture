use serde::{Deserialize, Serialize};

use crate::error::MemoryError;

/// Logical domain that classifies a memory entry's provenance and usage.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "snake_case")]
pub enum MemoryDomain {
    Canonical,
    #[default]
    Operational,
    Audit,
    Mission,
    Observation,
}

fn default_confidence() -> f32 {
    1.0
}

fn default_version() -> u32 {
    1
}

fn default_retrieval_count() -> u64 {
    0
}

/// Opaque identifier for a memory entry.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct MemoryId(pub String);

impl MemoryId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }
}

impl std::fmt::Display for MemoryId {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        self.0.fmt(f)
    }
}

/// A single entry in the memory store.
///
/// All fields are present to match the SQLite schema and wire contract.
/// `id` is `None` before write; the store assigns a UUID on write.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    /// Assigned by the store on write. `None` for new entries.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub id: Option<MemoryId>,
    /// The text content of the memory.
    pub content: String,
    /// Where this memory originated (e.g. "chat", "system"). Default: "chat".
    #[serde(default = "default_source")]
    pub source: String,
    /// Importance score in [0.0, 1.0]. Higher = more important. Default: 0.5.
    #[serde(default = "default_importance")]
    pub importance: f64,
    /// ISO-8601 creation timestamp. Assigned by the store if not set.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub created_at: Option<String>,
    /// Logical namespace for partitioning memories. Default: "default".
    #[serde(default = "default_namespace")]
    pub namespace: String,
    /// Free-form tags (retained for backward compatibility; not stored in SQLite).
    #[serde(default)]
    pub tags: Vec<String>,
    /// Logical domain for the memory. Default: Operational.
    #[serde(default)]
    pub domain: MemoryDomain,
    /// Confidence score in [0.0, 1.0]. Default: 1.0.
    #[serde(default = "default_confidence")]
    pub confidence: f32,
    /// Version counter — incremented on supersession. Default: 1.
    #[serde(default = "default_version")]
    pub version: u32,
    /// Successful retrieval count persisted by the memory store. Default: 0.
    #[serde(default = "default_retrieval_count")]
    pub retrieval_count: u64,
    /// Unix timestamp of the most recent successful retrieval.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub last_retrieved_at: Option<i64>,
    /// ID of the entry this supersedes (if updating an existing key). Optional.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub superseded_by: Option<String>,
    /// Optional key for key-based memory lookup (e.g. "kernel_boot"). Default: None.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub key: Option<String>,
    /// Optional link to a raw artifact (file path, URL). Default: None.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub raw_artifact: Option<String>,
    /// Memory tier classification per MEMORY_CONSTITUTION.md (e.g. "hot", "warm", "cold"). Optional.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tier: Option<String>,
}

fn default_source() -> String {
    "chat".to_string()
}

fn default_importance() -> f64 {
    0.5
}

fn default_namespace() -> String {
    "default".to_string()
}

pub enum MemoryWriteResult {
    Written(MemoryId),
    Contradiction {
        new_id: MemoryId,
        conflicting_ids: Vec<MemoryId>,
        conflicting_contents: Vec<String>,
        similarity: f32,
    },
}

impl MemoryWriteResult {
    pub fn into_id(self) -> MemoryId {
        match self {
            Self::Written(id) => id,
            Self::Contradiction { new_id, .. } => new_id,
        }
    }
}

/// Trait for any persistent memory backend.
#[async_trait::async_trait]
pub trait MemoryStore: Send + Sync {
    async fn write(&self, entry: MemoryEntry) -> Result<MemoryWriteResult, MemoryError>;
    async fn read(&self, id: &MemoryId) -> Result<Option<MemoryEntry>, MemoryError>;
    async fn search(&self, query: &str, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError>;
    /// Delete a memory entry by its ID.
    /// Returns `true` if the entry existed and was deleted, `false` if not found.
    async fn delete(&self, id: &MemoryId) -> Result<bool, MemoryError>;

    /// Fetch random memories (used for background Dream State reflection).
    async fn get_random(&self, limit: usize) -> Result<Vec<MemoryEntry>, MemoryError>;
}
