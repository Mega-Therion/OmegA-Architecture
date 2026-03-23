use crate::error::RouterError;
use crate::provider::{ChatChunk, ChatRequest, ChatResponse};
use futures::stream::Stream;
use std::pin::Pin;

/// Trait for any component that can route a chat request to a provider.
#[async_trait::async_trait]
pub trait Router: Send + Sync {
    async fn route(&self, req: &ChatRequest) -> Result<ChatResponse, RouterError>;

    async fn stream(
        &self,
        req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, RouterError>> + Send>>, RouterError>;
}

/// A router that fans out to multiple providers and synthesizes the result.
/// Implemented by `OmegaCouncilRouter` in omega-provider.
#[async_trait::async_trait]
pub trait CouncilRouter: Send + Sync {
    async fn council_route(&self, req: &ChatRequest) -> Result<ChatResponse, RouterError>;
}
