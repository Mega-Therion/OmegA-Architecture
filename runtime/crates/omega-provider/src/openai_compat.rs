/// Shared request/response logic for OpenAI-compatible APIs.
/// Covers: OpenAI, Perplexity, DeepSeek, xAI/Grok, Ollama (local).
use omega_core::error::ProviderError;
use serde::Deserialize;
use serde_json::{json, Value};

/// Parsed text response from a /chat/completions endpoint.
#[derive(Debug, Deserialize)]
pub struct OpenAiResponse {
    pub choices: Vec<OpenAiChoice>,
    pub model: Option<String>,
    pub usage: Option<OpenAiUsage>,
}

#[derive(Debug, Deserialize)]
pub struct OpenAiChoice {
    pub message: OpenAiMessage,
}

#[derive(Debug, Deserialize)]
pub struct OpenAiMessage {
    pub content: String,
}

#[derive(Debug, Deserialize)]
pub struct OpenAiUsage {
    pub prompt_tokens: u32,
    pub completion_tokens: u32,
    pub total_tokens: u32,
}

/// Build a messages array from a plain user prompt + optional system text + optional images.
pub fn build_messages(user: &str, system: Option<&str>, images: Option<&Vec<String>>) -> Value {
    let mut msgs = Vec::new();

    if let Some(sys) = system {
        if !sys.is_empty() {
            msgs.push(json!({"role": "system", "content": sys}));
        }
    }

    if let Some(imgs) = images {
        if !imgs.is_empty() {
            let mut content = vec![json!({"type": "text", "text": user})];
            for img in imgs {
                let url = if img.starts_with("http") {
                    img.clone()
                } else if img.starts_with("data:image/") {
                    img.clone()
                } else {
                    // For raw base64, assume jpeg
                    format!("data:image/jpeg;base64,{}", img)
                };
                content.push(json!({
                    "type": "image_url",
                    "image_url": { "url": url }
                }));
            }
            msgs.push(json!({"role": "user", "content": content}));
        } else {
            msgs.push(json!({"role": "user", "content": user}));
        }
    } else {
        msgs.push(json!({"role": "user", "content": user}));
    }

    json!(msgs)
}

/// POST to a /chat/completions endpoint and return the assistant text.
pub async fn post_openai_compat(
    client: &reqwest::Client,
    base_url: &str,
    api_key: &str,
    model: &str,
    user: &str,
    system: Option<&str>,
    temperature: f32,
    images: Option<&Vec<String>>,
) -> Result<(String, Option<String>), ProviderError> {
    let url = format!("{}/chat/completions", base_url.trim_end_matches('/'));
    let messages = build_messages(user, system, images);

    let resp = client
        .post(&url)
        .header("Authorization", format!("Bearer {}", api_key))
        .header("Content-Type", "application/json")
        .json(&json!({
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }))
        .send()
        .await
        .map_err(ProviderError::Request)?;

    map_status_error(resp.status().as_u16())?;

    let data: OpenAiResponse = resp
        .json()
        .await
        .map_err(|e| ProviderError::Parse(e.to_string()))?;

    let text = data
        .choices
        .into_iter()
        .next()
        .map(|c| c.message.content)
        .ok_or_else(|| ProviderError::Parse("no choices in response".to_string()))?;

    let model_name = data.model;
    Ok((text, model_name))
}

/// Map provider HTTP status codes to typed ProviderError variants.
pub fn map_status_error(status: u16) -> Result<(), ProviderError> {
    match status {
        200..=299 => Ok(()),
        400 => Err(ProviderError::InvalidRequest {
            status,
            body: "provider rejected request".to_string(),
        }),
        429 => Err(ProviderError::RateLimited),
        402 => Err(ProviderError::QuotaExceeded),
        s => Err(ProviderError::Unavailable { status: s }),
    }
}
