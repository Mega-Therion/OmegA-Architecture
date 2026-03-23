use futures_util::StreamExt;
use omega_core::provider::ChatResponse;

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

    /// Check gateway health.
    pub async fn health(&self) -> anyhow::Result<()> {
        self.client
            .get(format!("{}/health", self.base_url))
            .send()
            .await?
            .error_for_status()?;
        Ok(())
    }
}
