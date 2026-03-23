//! `omega-memory` — persistent memory store for the OmegA gateway.
//!
//! Exposes [`SqliteMemoryStore`], a [`MemoryStore`](omega_core::memory::MemoryStore)
//! implementation backed by SQLite via `sqlx`.
//!
//! Also exposes [`PgMemoryStore`], a Postgres + pgvector backend intended for
//! Supabase (schema managed externally).

pub mod error;
pub mod federated;
pub mod gaing;
pub mod pg;
pub mod schema;
pub mod sqlite;

pub use error::MemoryStoreError;
pub use federated::FederatedMemoryStore;
pub use gaing::GaingRestMemoryStore;
pub use pg::{EmbedText, PgMemoryStore};
pub use sqlite::SqliteMemoryStore;
