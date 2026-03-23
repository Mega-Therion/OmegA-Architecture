use std::pin::Pin;

use futures::stream::Stream;
use omega_core::{
    error::ProviderError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth},
};

use crate::openai_compat::post_openai_compat;

pub struct DeepSeekProvider {
    api_key: String,
    base_url: String,
    model: String,
    client: reqwest::Client,
}

impl DeepSeekProvider {
    pub fn new(api_key: String, base_url: String, model: String) -> Self {
        Self {
            api_key,
            base_url,
            model,
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(60))
                .build()
                .unwrap_or_default(),
        }
    }
}

#[async_trait::async_trait]
impl LlmProvider for DeepSeekProvider {
    fn name(&self) -> &str {
        "deepseek"
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        if self.api_key.is_empty() {
            return Err(ProviderError::Unavailable { status: 401 });
        }
        let (reply, _model) = post_openai_compat(
            &self.client,
            &self.base_url,
            &self.api_key,
            &self.model,
            &req.user,
            req.system.as_deref(),
            req.temperature,
            req.images.as_ref(),
        )
        .await?;

        Ok(ChatResponse {
            reply,
            mode: self.name().to_string(),
            memory_hits: vec![],
        })
    }

    async fn stream(
        &self,
        _req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>, ProviderError>
    {
        Err(ProviderError::Unavailable { status: 501 })
    }

    async fn health(&self) -> ProviderHealth {
        ProviderHealth {
            available: !self.api_key.is_empty(),
            latency_ms: None,
        }
    }
}
