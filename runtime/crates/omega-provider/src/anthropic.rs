use std::pin::Pin;

use futures::stream::Stream;
use omega_core::{
    error::ProviderError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth},
};
use serde_json::{json, Value};

pub struct AnthropicProvider {
    api_key: String,
    base_url: String,
    model: String,
    client: reqwest::Client,
}

impl AnthropicProvider {
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
impl LlmProvider for AnthropicProvider {
    fn name(&self) -> &str {
        "anthropic"
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        if self.api_key.is_empty() {
            return Err(ProviderError::Unavailable { status: 401 });
        }

        let url = format!("{}/v1/messages", self.base_url.trim_end_matches('/'));

        // Anthropic separates system from messages; only "user" and "assistant" roles allowed.
        let mut content = vec![json!({"type": "text", "text": req.user})];

        if let Some(ref imgs) = req.images {
            for img in imgs {
                if img.starts_with("data:image/") {
                    // Extract media type and base64 data
                    let parts: Vec<&str> = img.split(',').collect();
                    if parts.len() == 2 {
                        let media_type = parts[0]
                            .trim_start_matches("data:")
                            .split(';')
                            .next()
                            .unwrap_or("image/jpeg");
                        let base64_data = parts[1];
                        content.push(json!({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_data
                            }
                        }));
                    }
                } else if !img.starts_with("http") {
                    // Assume raw base64 jpeg
                    content.push(json!({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img
                        }
                    }));
                } else {
                    // Anthropic doesn't support direct image URLs in the API messages yet (needs base64)
                    content.push(
                        json!({"type": "text", "text": format!("\n[Attached Image: {}]", img)}),
                    );
                }
            }
        }

        let messages = json!([
            {"role": "user", "content": content}
        ]);

        let mut payload = json!({
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "temperature": req.temperature,
        });

        // Add system prompt if provided.
        if let Some(ref sys) = req.system {
            if !sys.is_empty() {
                payload["system"] = json!(sys);
            }
        }

        let resp = self
            .client
            .post(&url)
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .header("content-type", "application/json")
            .json(&payload)
            .send()
            .await
            .map_err(ProviderError::Request)?;

        let status = resp.status().as_u16();
        if !(200..=299).contains(&status) {
            let body = resp
                .text()
                .await
                .unwrap_or_else(|_| "unable to read Anthropic error body".to_string());
            let compact_body = body.replace('\n', " ");

            if status == 400 {
                tracing::error!(
                    provider = self.name(),
                    model = %self.model,
                    status,
                    body = %compact_body,
                    "Anthropic rejected the request payload"
                );
                return Err(ProviderError::InvalidRequest {
                    status,
                    body: compact_body,
                });
            }

            if status == 402 {
                return Err(ProviderError::QuotaExceeded);
            }

            if status == 429 {
                return Err(ProviderError::RateLimited);
            }

            tracing::warn!(
                provider = self.name(),
                model = %self.model,
                status,
                body = %compact_body,
                "Anthropic request failed"
            );
            return Err(ProviderError::Unavailable { status });
        }

        let data: Value = resp
            .json()
            .await
            .map_err(|e| ProviderError::Parse(e.to_string()))?;

        let text = data
            .pointer("/content/0/text")
            .and_then(|v| v.as_str())
            .ok_or_else(|| ProviderError::Parse("Anthropic returned no content".to_string()))?
            .to_string();

        Ok(ChatResponse {
            reply: text,
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
