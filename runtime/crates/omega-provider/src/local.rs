use std::pin::Pin;

use futures::stream::{self, Stream, StreamExt};
use omega_core::{
    error::ProviderError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth},
};
use serde::Deserialize;
use serde_json::json;

#[derive(Debug, Deserialize)]
struct OllamaMessage {
    #[serde(default)]
    content: String,
}

#[derive(Debug, Deserialize)]
struct OllamaChatResponse {
    #[serde(default)]
    message: Option<OllamaMessage>,
    #[serde(default)]
    done: bool,
    #[serde(default)]
    error: Option<String>,
}

/// Local provider backed by Ollama's native `/api/chat` endpoint.
pub struct LocalProvider {
    base_url: String,
    model: String,
    client: reqwest::Client,
}

impl LocalProvider {
    pub fn new(base_url: Option<String>, model: Option<String>) -> Self {
        Self {
            base_url: base_url.unwrap_or_else(|| "http://localhost:11434/v1".to_string()),
            model: model.unwrap_or_else(|| "llama3.2:3b".to_string()),
            client: reqwest::Client::builder()
                .timeout(std::time::Duration::from_secs(120))
                .tcp_keepalive(std::time::Duration::from_secs(15))
                .pool_idle_timeout(std::time::Duration::from_secs(30))
                .connection_verbose(false)
                .build()
                .unwrap_or_default(),
        }
    }

    fn ollama_root(&self) -> &str {
        self.base_url.trim_end_matches("/v1")
    }

    fn chat_url(&self) -> String {
        format!("{}/api/chat", self.ollama_root())
    }

    fn build_messages(&self, req: &ChatRequest) -> Result<serde_json::Value, ProviderError> {
        if req.images.as_ref().is_some_and(|images| !images.is_empty()) {
            return Err(ProviderError::InvalidRequest {
                status: 400,
                body: "local Ollama provider does not support image inputs".to_string(),
            });
        }

        let mut messages = Vec::new();
        if let Some(system) = req.system.as_deref() {
            if !system.is_empty() {
                messages.push(json!({
                    "role": "system",
                    "content": system,
                }));
            }
        }
        messages.push(json!({
            "role": "user",
            "content": req.user,
        }));
        Ok(json!(messages))
    }

    async fn map_error_response(&self, resp: reqwest::Response) -> ProviderError {
        let status = resp.status().as_u16();
        let body = resp.text().await.unwrap_or_default();
        match status {
            400 | 404 => ProviderError::InvalidRequest { status, body },
            429 => ProviderError::RateLimited,
            402 => ProviderError::QuotaExceeded,
            s => ProviderError::Unavailable { status: s },
        }
    }
}

#[async_trait::async_trait]
impl LlmProvider for LocalProvider {
    fn name(&self) -> &str {
        "local"
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        let messages = self.build_messages(req)?;
        let payload = json!({
            "model": self.model,
            "messages": messages,
            "stream": false,
            "options": { "temperature": req.temperature },
        });

        // Retry once on transient connection errors (e.g. stale keep-alive after Ollama restart).
        let resp = {
            let attempt = self
                .client
                .post(self.chat_url())
                .json(&payload)
                .send()
                .await;
            match attempt {
                Ok(r) => r,
                Err(e) if e.is_connect() || e.is_request() => {
                    // One retry after a short pause — clears any stale pooled connection.
                    tokio::time::sleep(std::time::Duration::from_millis(200)).await;
                    self.client
                        .post(self.chat_url())
                        .json(&payload)
                        .send()
                        .await
                        .map_err(ProviderError::Request)?
                }
                Err(e) => return Err(ProviderError::Request(e)),
            }
        };

        if !resp.status().is_success() {
            return Err(self.map_error_response(resp).await);
        }

        let data: OllamaChatResponse = resp
            .json()
            .await
            .map_err(|e| ProviderError::Parse(e.to_string()))?;

        if let Some(error) = data.error {
            return Err(ProviderError::InvalidRequest {
                status: 400,
                body: error,
            });
        }

        let reply = data
            .message
            .map(|message| message.content)
            .filter(|content| !content.is_empty())
            .ok_or_else(|| ProviderError::Parse("missing assistant message".to_string()))?;

        Ok(ChatResponse {
            reply,
            mode: self.name().to_string(),
            memory_hits: vec![],
        })
    }

    async fn stream(
        &self,
        req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, ProviderError>> + Send>>, ProviderError>
    {
        let messages = self.build_messages(req)?;
        let resp = self
            .client
            .post(self.chat_url())
            .header("Content-Type", "application/json")
            .json(&json!({
                "model": self.model,
                "messages": messages,
                "stream": true,
                "options": {
                    "temperature": req.temperature,
                },
            }))
            .send()
            .await
            .map_err(ProviderError::Request)?;

        if !resp.status().is_success() {
            return Err(self.map_error_response(resp).await);
        }

        let chunk_stream = resp
            .bytes_stream()
            .map(|result| result.map_err(ProviderError::Request))
            .flat_map(|result| {
                stream::iter(match result {
                    Err(e) => vec![Err(e)],
                    Ok(bytes) => String::from_utf8_lossy(&bytes)
                        .lines()
                        .filter(|line| !line.trim().is_empty())
                        .map(
                            |line| match serde_json::from_str::<OllamaChatResponse>(line) {
                                Ok(chunk) => {
                                    if let Some(error) = chunk.error {
                                        return Err(ProviderError::InvalidRequest {
                                            status: 400,
                                            body: error,
                                        });
                                    }

                                    Ok(ChatChunk {
                                        delta: chunk
                                            .message
                                            .map(|message| message.content)
                                            .unwrap_or_default(),
                                        done: chunk.done,
                                    })
                                }
                                Err(e) => Err(ProviderError::Parse(e.to_string())),
                            },
                        )
                        .collect(),
                })
            });

        Ok(Box::pin(chunk_stream))
    }

    async fn health(&self) -> ProviderHealth {
        let url = format!("{}/api/tags", self.ollama_root());
        match self.client.get(&url).send().await {
            Ok(r) if r.status().is_success() => ProviderHealth {
                available: true,
                latency_ms: None,
            },
            _ => ProviderHealth {
                available: false,
                latency_ms: None,
            },
        }
    }
}
