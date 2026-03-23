//! Crate-level error type that wraps sqlx errors and maps them to
//! [`omega_core::MemoryError`] for the trait impl.

#[derive(Debug, thiserror::Error)]
pub enum MemoryStoreError {
    #[error("sqlx error: {0}")]
    Sqlx(#[from] sqlx::Error),

    #[error("migration error: {0}")]
    Migrate(#[from] sqlx::migrate::MigrateError),

    #[error("embedding error: {0}")]
    Embedding(String),

    #[error("entry not found: {0}")]
    NotFound(String),
}

impl From<MemoryStoreError> for omega_core::MemoryError {
    fn from(e: MemoryStoreError) -> Self {
        match e {
            MemoryStoreError::NotFound(id) => omega_core::MemoryError::NotFound(id),
            MemoryStoreError::Embedding(msg) => {
                omega_core::MemoryError::Write(format!("embedding: {msg}"))
            }
            MemoryStoreError::Sqlx(inner) => match inner {
                sqlx::Error::RowNotFound => {
                    omega_core::MemoryError::NotFound("row not found".into())
                }
                other => omega_core::MemoryError::Read(other.to_string()),
            },
            MemoryStoreError::Migrate(inner) => {
                omega_core::MemoryError::Write(format!("migration: {inner}"))
            }
        }
    }
}
