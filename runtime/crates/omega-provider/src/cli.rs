use std::{
    path::Path,
    pin::Pin,
    time::{Duration, SystemTime, UNIX_EPOCH},
};

use futures::stream::Stream;
use omega_core::{
    error::ProviderError,
    provider::{ChatChunk, ChatRequest, ChatResponse, LlmProvider, ProviderHealth},
};
use tokio::{fs, process::Command};

#[derive(Clone, Copy)]
pub enum CliKind {
    Codex,
    Claude,
    Gemini,
}

pub struct CliProvider {
    kind: CliKind,
    /// Unique name used for cooldown tracking. Gemini includes the model slug
    /// so each model in the fallthrough chain has its own circuit-breaker slot.
    name: String,
    command_path: String,
    home_dir: String,
    timeout: Duration,
    model: Option<String>,
    /// Extra CLI flags injected into the command (e.g. reasoning effort, thinking budget).
    extra_args: Vec<String>,
}

impl CliProvider {
    pub fn new(
        kind: CliKind,
        command_path: String,
        home_dir: String,
        timeout_secs: u64,
        model: Option<String>,
        extra_args: Vec<String>,
    ) -> Self {
        let model = model.filter(|v| !v.is_empty());
        let name = match (&kind, &model) {
            (CliKind::Gemini, Some(m)) => format!("gemini-cli:{}", m),
            (CliKind::Gemini, None) => "gemini-cli".to_string(),
            (CliKind::Codex, _) => "codex".to_string(),
            (CliKind::Claude, _) => "claude-cli".to_string(),
        };

        Self {
            kind,
            name,
            command_path,
            home_dir,
            timeout: Duration::from_secs(timeout_secs.max(5)),
            model,
            extra_args,
        }
    }

    fn build_prompt(&self, req: &ChatRequest) -> Result<String, ProviderError> {
        if req.images.as_ref().is_some_and(|images| !images.is_empty()) {
            return Err(ProviderError::InvalidRequest {
                status: 400,
                body: format!("{} does not support image inputs", self.name),
            });
        }

        let mut parts = Vec::new();
        if let Some(system) = req.system.as_deref() {
            if !system.is_empty() {
                parts.push(format!("SYSTEM:\n{}", system));
            }
        }
        parts.push(format!("USER:\n{}", req.user));
        parts.push("Respond only as the assistant to the latest user message.".to_string());
        Ok(parts.join("\n\n"))
    }

    async fn run_command(&self, req: &ChatRequest) -> Result<String, ProviderError> {
        let prompt = self.build_prompt(req)?;
        match self.kind {
            CliKind::Codex => self.run_codex(prompt).await,
            CliKind::Claude => self.run_claude(prompt).await,
            CliKind::Gemini => self.run_gemini(prompt).await,
        }
    }

    async fn run_claude(&self, prompt: String) -> Result<String, ProviderError> {
        let mut command = Command::new(&self.command_path);
        command
            .env("HOME", &self.home_dir)
            .current_dir(&self.home_dir)
            .env_remove("ANTHROPIC_API_KEY")
            .env_remove("ANTHROPIC_AUTH_TOKEN")
            .arg("-p")
            .arg("--permission-mode")
            .arg("plan")
            .arg("--output-format")
            .arg("text");

        if let Some(model) = &self.model {
            command.arg("--model").arg(model);
        }

        // Extra args (e.g. thinking budget flags) go before the prompt.
        for arg in &self.extra_args {
            command.arg(arg);
        }

        command.arg(prompt);
        let output = tokio::time::timeout(self.timeout, command.output())
            .await
            .map_err(|_| ProviderError::Unavailable { status: 504 })?
            .map_err(|e| ProviderError::Parse(e.to_string()))?;

        self.parse_text_output(output.stdout, output.stderr)
    }

    async fn run_gemini(&self, prompt: String) -> Result<String, ProviderError> {
        let mut command = Command::new(&self.command_path);
        command
            .env("HOME", &self.home_dir)
            .current_dir(&self.home_dir)
            .env_remove("GEMINI_API_KEY")
            .env_remove("GOOGLE_API_KEY")
            .env_remove("GOOGLE_APPLICATION_CREDENTIALS")
            .arg("-p")
            .arg(prompt)
            .arg("-o")
            .arg("text")
            .arg("--approval-mode")
            .arg("plan");

        if let Some(model) = &self.model {
            command.arg("--model").arg(model);
        }

        // Extra args appended after model selection.
        for arg in &self.extra_args {
            command.arg(arg);
        }

        let output = tokio::time::timeout(self.timeout, command.output())
            .await
            .map_err(|_| ProviderError::Unavailable { status: 504 })?
            .map_err(|e| ProviderError::Parse(e.to_string()))?;

        self.parse_text_output(output.stdout, output.stderr)
    }

    async fn run_codex(&self, prompt: String) -> Result<String, ProviderError> {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis();
        let output_path = format!("/tmp/omega-codex-{}-{}.txt", std::process::id(), stamp);

        let mut command = Command::new(&self.command_path);
        command
            .env("HOME", &self.home_dir)
            .current_dir(&self.home_dir)
            .env_remove("OPENAI_API_KEY")
            .env_remove("OPENAI_BASE_URL")
            .arg("-a")
            .arg("never")
            .arg("-s")
            .arg("read-only");

        if let Some(model) = &self.model {
            command.arg("-m").arg(model);
        }

        // Extra args (e.g. --reasoning-effort medium) go before the subcommand.
        for arg in &self.extra_args {
            command.arg(arg);
        }

        command
            .arg("exec")
            .arg("--skip-git-repo-check")
            .arg("--ephemeral")
            .arg("-o")
            .arg(&output_path)
            .arg(prompt);

        let output = tokio::time::timeout(self.timeout, command.output())
            .await
            .map_err(|_| ProviderError::Unavailable { status: 504 })?
            .map_err(|e| ProviderError::Parse(e.to_string()))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr).to_string();
            return Err(ProviderError::InvalidRequest {
                status: 502,
                body: stderr,
            });
        }

        let text = fs::read_to_string(&output_path)
            .await
            .map_err(|e| ProviderError::Parse(e.to_string()))?;
        let _ = fs::remove_file(&output_path).await;
        Ok(text.trim().to_string())
    }

    fn parse_text_output(&self, stdout: Vec<u8>, stderr: Vec<u8>) -> Result<String, ProviderError> {
        let stdout = String::from_utf8_lossy(&stdout).trim().to_string();
        let stderr = String::from_utf8_lossy(&stderr).trim().to_string();
        let combined = format!("{}\n{}", stdout, stderr).to_lowercase();

        if combined.contains("opening authentication page") {
            return Err(ProviderError::InvalidRequest {
                status: 401,
                body: format!(
                    "{} requires interactive login before headless use",
                    self.name
                ),
            });
        }

        // Detect rate-limit / quota errors in stderr so the failover chain
        // can skip to the next provider immediately instead of hanging.
        if combined.contains("429")
            || combined.contains("ratelimitexceeded")
            || combined.contains("resource_exhausted")
            || combined.contains("model_capacity_exhausted")
            || combined.contains("quota exceeded")
            || combined.contains("too many requests")
        {
            return Err(ProviderError::RateLimited);
        }

        if stdout.is_empty() {
            return Err(ProviderError::InvalidRequest {
                status: 502,
                body: if stderr.is_empty() {
                    format!("{} returned no output", self.name)
                } else {
                    stderr
                },
            });
        }

        Ok(stdout)
    }
}

#[async_trait::async_trait]
impl LlmProvider for CliProvider {
    fn name(&self) -> &str {
        &self.name
    }

    async fn complete(&self, req: &ChatRequest) -> Result<ChatResponse, ProviderError> {
        let reply = self.run_command(req).await?;
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
            available: Path::new(&self.command_path).exists() && Path::new(&self.home_dir).exists(),
            latency_ms: None,
        }
    }
}
