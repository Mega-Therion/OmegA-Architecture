use futures_util::StreamExt;
use omega_core::provider::ChatResponse;
use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct GatewayStatus {
    pub model: String,
    pub base_url: String,
    pub db: String,
    pub auth: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct HealthStatus {
    pub ok: bool,
    pub service: String,
    pub version: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct DeepHealthStatus {
    pub ok: bool,
    pub state: String,
    pub services: serde_json::Value,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ProviderEntry {
    pub name: String,
    pub enabled: bool,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ProvidersResponse {
    pub providers: Vec<ProviderEntry>,
}

pub struct GatewayClient {
    client: reqwest::Client,
    base_url: String,
    bearer_token: String,
}

impl GatewayClient {
    pub fn new(base_url: String, bearer_token: String) -> Self {
        Self {
            client: reqwest::Client::new(),
            base_url,
            bearer_token,
        }
    }

    /// Send a chat request and return the response text.
    pub async fn chat(&self, prompt: &str, mode: &str) -> anyhow::Result<String> {
        let resp = self
            .client
            .post(format!("{}/api/v1/chat", self.base_url))
            .bearer_auth(&self.bearer_token)
            .json(&serde_json::json!({
                "user": prompt,
                "mode": mode,
                "temperature": 0.4
            }))
            .send()
            .await?
            .error_for_status()?
            .json::<ChatResponse>()
            .await?;

        Ok(resp.reply)
    }

    /// Check gateway health.
    pub async fn health(&self) -> anyhow::Result<HealthStatus> {
        let resp = self
            .client
            .get(format!("{}/health", self.base_url))
            .send()
            .await?
            .error_for_status()?
            .json::<HealthStatus>()
            .await?;
        Ok(resp)
    }

    /// Fetch gateway status/config details.
    pub async fn status(&self) -> anyhow::Result<GatewayStatus> {
        let resp = self
            .client
            .get(format!("{}/api/v1/status", self.base_url))
            .bearer_auth(&self.bearer_token)
            .send()
            .await?
            .error_for_status()?
            .json::<GatewayStatus>()
            .await?;
        Ok(resp)
    }

    /// Fetch deep health details.
    pub async fn deep_health(&self) -> anyhow::Result<DeepHealthStatus> {
        let resp = self
            .client
            .get(format!("{}/health/deep", self.base_url))
            .send()
            .await?
            .error_for_status()?
            .json::<DeepHealthStatus>()
            .await?;
        Ok(resp)
    }

    /// Fetch provider availability for the linked gateway.
    pub async fn providers(&self) -> anyhow::Result<ProvidersResponse> {
        let resp = self
            .client
            .get(format!("{}/api/v1/providers", self.base_url))
            .bearer_auth(&self.bearer_token)
            .send()
            .await?
            .error_for_status()?
            .json::<ProvidersResponse>()
            .await?;
        Ok(resp)
    }

    /// Send a chat request and return a stream of chunks.
    pub async fn stream(
        &self,
        prompt: &str,
        mode: &str,
    ) -> anyhow::Result<impl futures_util::Stream<Item = anyhow::Result<String>>> {
        let resp = self
            .client
            .post(format!("{}/api/v1/chat/stream", self.base_url))
            .bearer_auth(&self.bearer_token)
            .json(&serde_json::json!({
                "user": prompt,
                "mode": mode,
                "temperature": 0.4
            }))
            .send()
            .await?
            .error_for_status()?;

        let stream = resp.bytes_stream().map(|result| match result {
            Ok(bytes) => {
                let s = String::from_utf8_lossy(&bytes);
                // Simple SSE parsing for the demo (ideally use a real SSE crate/eventsource)
                // Format: data: {"chunk": "...", "done": false}
                let mut chunk_text = String::new();
                for line in s.lines() {
                    if line.starts_with("data: ") {
                        let json_str = &line[6..];
                        if let Ok(v) = serde_json::from_str::<serde_json::Value>(json_str) {
                            if let Some(chunk) = v["chunk"].as_str() {
                                chunk_text.push_str(chunk);
                            }
                        }
                    }
                }
                Ok(chunk_text)
            }
            Err(e) => Err(anyhow::anyhow!("stream error: {}", e)),
        });

        Ok(stream)
    }
}
