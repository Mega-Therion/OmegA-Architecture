use std::pin::Pin;

use futures::stream::Stream;
use omega_core::{
    error::ProviderError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth},
};
use serde_json::{json, Value};

use crate::openai_compat::map_status_error;

pub struct GeminiProvider {
    api_key: String,
    base_url: String,
    model: String,
    client: reqwest::Client,
}

impl GeminiProvider {
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

/// Convert OpenAI-style messages to Gemini's contents format.
/// System messages are extracted into systemInstruction.
fn build_gemini_payload(
    user: &str,
    system: Option<&str>,
    temperature: f32,
    images: Option<&Vec<String>>,
) -> Value {
    let mut parts = vec![json!({"text": user})];

    if let Some(imgs) = images {
        for img in imgs {
            if img.starts_with("data:image/") {
                // Handle data URI: data:image/png;base64,iVBORw...
                let parts_split: Vec<&str> = img.split(',').collect();
                if parts_split.len() == 2 {
                    let media_type = parts_split[0]
                        .trim_start_matches("data:")
                        .split(';')
                        .next()
                        .unwrap_or("image/jpeg");
                    let base64_data = parts_split[1];
                    parts.push(json!({
                        "inline_data": {
                            "mime_type": media_type,
                            "data": base64_data
                        }
                    }));
                }
            } else if img.starts_with("http") {
                // Note: Gemini API generateContent doesn't directly take external URLs in 'parts'
                // without 'file_data' and a pre-uploaded file.
                // For now, we'll assume the user might want to mention the URL in text
                // or we could fetch it, but let's stick to inline_data for now as canonical vision.
                parts.push(json!({"text": format!("\n[Attached Image: {}]", img)}));
            } else {
                // Assume raw base64 jpeg if not a URL/data-uri
                parts.push(json!({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": img
                    }
                }));
            }
        }
    }

    let contents = json!([
        {
            "role": "user",
            "parts": parts
        }
    ]);

    let mut payload = json!({
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 4096
        }
    });

    if let Some(sys) = system {
        if !sys.is_empty() {
            payload["systemInstruction"] = json!({
                "parts": [{"text": sys}]
            });
        }
    }

    payload
}

#[async_trait::async_trait]
impl LlmProvider for GeminiProvider {
    fn name(&self) -> &str {
        "gemini"
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        if self.api_key.is_empty() {
            return Err(ProviderError::Unavailable { status: 401 });
        }

        let url = format!(
            "{}/v1beta/models/{}:generateContent?key={}",
            self.base_url.trim_end_matches('/'),
            self.model,
            self.api_key
        );

        let payload = build_gemini_payload(
            &req.user,
            req.system.as_deref(),
            req.temperature,
            req.images.as_ref(),
        );

        let resp = self
            .client
            .post(&url)
            .header("Content-Type", "application/json")
            .json(&payload)
            .send()
            .await
            .map_err(ProviderError::Request)?;

        map_status_error(resp.status().as_u16())?;

        let data: Value = resp
            .json()
            .await
            .map_err(|e| ProviderError::Parse(e.to_string()))?;

        let text = data
            .pointer("/candidates/0/content/parts/0/text")
            .and_then(|v| v.as_str())
            .ok_or_else(|| ProviderError::Parse("Gemini returned no content".to_string()))?
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
