//! OmegaCouncilRouter — fans out to Anthropic + Gemini in parallel, then
//! synthesizes the two responses into a single "omega" reply.
//!
//! Flow:
//!   1. tokio::join! Anthropic + Gemini (each with `timeout` cap)
//!   2. Both succeed → call synthesis_provider → mode: "omega"
//!   3. One fails   → return the successful one → mode: "omega-degraded-{anthropic|gemini}"
//!   4. Both fail   → delegate to fallback_chain
//!   5. Synthesis call exceeds 15s → return best raw response → mode: "omega-unsynthesized"

use std::sync::Arc;
use std::time::Duration;

use futures::stream::Stream;
use omega_core::{
    error::RouterError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider},
    router::{CouncilRouter, Router},
};
use std::pin::Pin;
use tokio::time::timeout;

/// Full council synthesis router.
pub struct OmegaCouncilRouter {
    /// First council member (Anthropic / Claude).
    pub anthropic: Arc<dyn LlmProvider>,
    /// Second council member (Gemini).
    pub gemini: Arc<dyn LlmProvider>,
    /// Provider used to synthesize the two responses (fastest available).
    pub synthesis_provider: Arc<dyn LlmProvider>,
    /// Fallback when both council members fail.
    pub fallback_chain: Arc<dyn Router>,
    /// Per-council-member timeout (default: 25 s).
    pub timeout: Duration,
}

impl OmegaCouncilRouter {
    /// Run both council members concurrently, then synthesize or degrade.
    pub async fn route(&self, req: &ChatRequest) -> Result<ChatResponse, RouterError> {
        // Fan out — both providers race concurrently.
        let (res_a, res_b) = tokio::join!(
            timeout(self.timeout, self.anthropic.complete(req)),
            timeout(self.timeout, self.gemini.complete(req)),
        );

        // Unwrap the double-Result: timeout error or provider error both become None.
        let ok_a = res_a.ok().and_then(|r| r.ok());
        let ok_b = res_b.ok().and_then(|r| r.ok());

        match (ok_a, ok_b) {
            // Both succeeded → synthesize.
            (Some(a), Some(b)) => self.synthesize(req, a, b).await,

            // Only Anthropic succeeded → degraded (Gemini leg failed).
            (Some(a), None) => Ok(self.with_mode_tag(a, "omega-degraded-gemini")),

            // Only Gemini succeeded → degraded (Anthropic leg failed).
            (None, Some(b)) => Ok(self.with_mode_tag(b, "omega-degraded-anthropic")),

            // Both failed → fall through to the regular failover chain.
            (None, None) => self.fallback_chain.route(req).await,
        }
    }

    /// Call the synthesis provider with both responses folded into a prompt.
    /// If the synthesis call itself exceeds 15 s, return the best raw response
    /// with mode "omega-unsynthesized".
    async fn synthesize(
        &self,
        req: &ChatRequest,
        a: ChatResponse,
        b: ChatResponse,
    ) -> Result<ChatResponse, RouterError> {
        let synthesis_prompt = format!(
            "You are a synthesis engine. Two AI agents have answered the same question.\n\
             Produce one unified answer that captures the best reasoning from both.\n\
             Do not say \"Agent A said...\" or \"Agent B said...\". Just give the answer.\n\
             If they disagree on facts, note the disagreement briefly and explain which \
             position has stronger support.\n\n\
             USER QUESTION:\n{}\n\n\
             AGENT 1 RESPONSE:\n{}\n\n\
             AGENT 2 RESPONSE:\n{}\n\n\
             SYNTHESIZED ANSWER:",
            req.user, a.reply, b.reply
        );

        let synthesis_req = ChatRequest {
            user: synthesis_prompt,
            mode: "claude-cli".to_string(),
            temperature: req.temperature,
            system: req.system.clone(),
            max_tokens: req.max_tokens,
            namespace: req.namespace.clone(),
            use_memory: false,
            use_collectivebrain: None,
            images: None,
            agent_id: Some("system:council:synthesis".to_string()),
            task_state: None,
        };

        // 15-second cap on synthesis.
        let synthesis_timeout = Duration::from_secs(15);
        match timeout(
            synthesis_timeout,
            self.synthesis_provider.complete(&synthesis_req),
        )
        .await
        {
            Ok(Ok(mut resp)) => {
                resp.mode = "omega".to_string();
                Ok(resp)
            }
            // Synthesis timed out or failed → return the better (first) raw response.
            _ => {
                tracing::warn!("council synthesis timed out or failed — returning unsynthesized");
                // Return response_a (Anthropic) as the best-effort answer.
                Ok(self.with_mode_tag(a, "omega-unsynthesized"))
            }
        }
    }

    fn with_mode_tag(&self, mut resp: ChatResponse, mode: &str) -> ChatResponse {
        resp.mode = mode.to_string();
        resp
    }

    pub async fn stream(
        &self,
        req: &ChatRequest,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, RouterError>> + Send>>, RouterError>
    {
        let (res_a, res_b) = tokio::join!(
            timeout(self.timeout, self.anthropic.complete(req)),
            timeout(self.timeout, self.gemini.complete(req)),
        );

        let ok_a = res_a.ok().and_then(|r| r.ok());
        let ok_b = res_b.ok().and_then(|r| r.ok());

        match (ok_a, ok_b) {
            (Some(a), Some(b)) => self.synthesize_stream(req, a, b).await,
            (Some(a), None) => {
                Ok(self.stream_from_text(self.with_mode_tag(a, "omega-degraded-gemini").reply))
            }
            (None, Some(b)) => {
                Ok(self.stream_from_text(self.with_mode_tag(b, "omega-degraded-anthropic").reply))
            }
            (None, None) => self.fallback_chain.stream(req).await,
        }
    }

    async fn synthesize_stream(
        &self,
        req: &ChatRequest,
        a: ChatResponse,
        b: ChatResponse,
    ) -> Result<Pin<Box<dyn Stream<Item = Result<ChatChunk, RouterError>> + Send>>, RouterError>
    {
        let synthesis_prompt = format!(
            "You are a synthesis engine. Two AI agents have answered the same question.\n\
             Produce one unified answer that captures the best reasoning from both.\n\
             Do not say \"Agent A said...\" or \"Agent B said...\". Just give the answer.\n\
             If they disagree on facts, note the disagreement briefly and explain which \
             position has stronger support.\n\n\
             USER QUESTION:\n{}\n\n\
             AGENT 1 RESPONSE:\n{}\n\n\
             AGENT 2 RESPONSE:\n{}\n\n\
             SYNTHESIZED ANSWER:",
            req.user, a.reply, b.reply
        );

        let synthesis_req = ChatRequest {
            user: synthesis_prompt,
            mode: "claude-cli".to_string(),
            temperature: req.temperature,
            system: req.system.clone(),
            max_tokens: req.max_tokens,
            namespace: req.namespace.clone(),
            use_memory: false,
            use_collectivebrain: None,
            images: None,
            agent_id: Some("system:council:synthesis".to_string()),
            task_state: None,
        };

        match self.synthesis_provider.stream(&synthesis_req).await {
            Ok(stream) => {
                use futures::stream::StreamExt;
                Ok(Box::pin(
                    stream.map(|res| res.map_err(RouterError::Provider)),
                ))
            }
            Err(_) => {
                tracing::warn!("council synthesis stream failed — returning unsynthesized");
                Ok(self.stream_from_text(self.with_mode_tag(a, "omega-unsynthesized").reply))
            }
        }
    }

    fn stream_from_text(
        &self,
        text: String,
    ) -> Pin<Box<dyn Stream<Item = Result<ChatChunk, RouterError>> + Send>> {
        let chunks: Vec<Result<ChatChunk, RouterError>> = vec![
            Ok(ChatChunk {
                delta: text,
                done: false,
            }),
            Ok(ChatChunk {
                delta: String::new(),
                done: true,
            }),
        ];
        Box::pin(futures::stream::iter(chunks))
    }
}

#[async_trait::async_trait]
impl CouncilRouter for OmegaCouncilRouter {
    async fn council_route(&self, req: &ChatRequest) -> Result<ChatResponse, RouterError> {
        self.route(req).await
    }
}
