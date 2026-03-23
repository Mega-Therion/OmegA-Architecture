use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdentityProfile {
    pub name: String,
    pub vessel: String,
    pub operator: String,
    pub creed: String,
    pub doctrine: Vec<String>,
    pub priorities: Vec<String>,
    pub constraints: Vec<String>,
    pub source_documents: Vec<String>,
    // --- Enriched fields loaded from config/identity.yaml ---
    #[serde(default)]
    pub mission_statement: Option<String>,
    #[serde(default)]
    pub provider_disclosure_policy: Option<String>,
    #[serde(default)]
    pub creator_boundary_policy: Option<String>,
    #[serde(default)]
    pub identity_anchors: Vec<String>,
    #[serde(default)]
    pub prohibited_self_descriptions: Vec<String>,
    #[serde(default)]
    pub contamination_signals: Vec<String>,
    #[serde(default)]
    pub response_style: Option<String>,
}

/// Mirrors the structure of config/identity.yaml for deserialization.
#[derive(Debug, Deserialize)]
struct YamlIdentityConfig {
    #[serde(default)]
    designation: String,
    #[serde(default)]
    vessel: String,
    #[serde(default)]
    operator: String,
    #[serde(default)]
    creed: String,
    #[serde(default)]
    mission_statement: String,
    #[serde(default)]
    provider_disclosure_policy: String,
    #[serde(default)]
    creator_boundary_policy: String,
    #[serde(default)]
    doctrine: Vec<String>,
    #[serde(default)]
    priorities: Vec<String>,
    #[serde(default)]
    constraints: Vec<String>,
    #[serde(default)]
    identity_anchors: Vec<String>,
    #[serde(default)]
    prohibited_self_descriptions: Vec<String>,
    #[serde(default)]
    contamination_watch: YamlContaminationWatch,
    #[serde(default)]
    source_documents: Vec<String>,
    #[serde(default)]
    response_style: String,
}

#[derive(Debug, Default, Deserialize)]
struct YamlContaminationWatch {
    #[serde(default)]
    signals: Vec<YamlContaminationSignal>,
}

#[derive(Debug, Deserialize)]
struct YamlContaminationSignal {
    pattern: String,
}

/// Return `value` if non-empty, otherwise `default`.
fn or_default(value: String, default: &str) -> String {
    if value.is_empty() {
        default.to_string()
    } else {
        value
    }
}

/// Return `Some(value)` if non-empty, otherwise `None`.
fn some_if_nonempty(value: String) -> Option<String> {
    if value.is_empty() {
        None
    } else {
        Some(value)
    }
}

impl IdentityProfile {
    /// Load identity from config/identity.yaml.
    /// Returns None if the file doesn't exist or fails to parse — callers should
    /// fall back to `canonical()`.
    pub fn load_from_yaml(path: &str) -> Option<Self> {
        let content = std::fs::read_to_string(path).ok()?;
        let yaml: YamlIdentityConfig = serde_yaml::from_str(&content)
            .map_err(|e| tracing::warn!("Failed to parse identity.yaml: {}", e))
            .ok()?;

        // Pre-lowercase so scan_output_contamination() can skip per-request lowercasing.
        let contamination_signals: Vec<String> = yaml
            .contamination_watch
            .signals
            .iter()
            .map(|s| s.pattern.to_lowercase())
            .collect();

        Some(Self {
            name: or_default(yaml.designation, "ωα"),
            vessel: or_default(yaml.vessel, "OMEGAI"),
            operator: or_default(yaml.operator, "RY"),
            creed: or_default(
                yaml.creed,
                "Trust, but verify. Automate, but log. Move fast, but don't break things.",
            ),
            doctrine: yaml.doctrine,
            priorities: yaml.priorities,
            constraints: yaml.constraints,
            source_documents: yaml.source_documents,
            mission_statement: some_if_nonempty(yaml.mission_statement),
            provider_disclosure_policy: some_if_nonempty(yaml.provider_disclosure_policy),
            creator_boundary_policy: some_if_nonempty(yaml.creator_boundary_policy),
            identity_anchors: yaml.identity_anchors,
            prohibited_self_descriptions: yaml.prohibited_self_descriptions,
            contamination_signals,
            response_style: some_if_nonempty(yaml.response_style),
        })
    }

    /// Load from canonical yaml path, falling back to hardcoded defaults.
    pub fn load_or_default(yaml_path: &str) -> Self {
        match Self::load_from_yaml(yaml_path) {
            Some(profile) => {
                tracing::info!(path = %yaml_path, "Loaded identity from yaml");
                profile
            }
            None => {
                tracing::warn!(
                    path = %yaml_path,
                    "identity.yaml not found or invalid — falling back to hardcoded canonical identity"
                );
                Self::canonical()
            }
        }
    }

    pub fn canonical() -> Self {
        Self {
            name: "OmegA".to_string(),
            vessel: "OMEGAI".to_string(),
            operator: "RY".to_string(),
            creed: "Trust, but verify. Automate, but log. Move fast, but don't break things."
                .to_string(),
            doctrine: vec![
                "WHO vs WHAT separation: identity is not silently rewritten by infrastructure changes."
                    .to_string(),
                "Protocol enforcement belongs on the server path, not in cosmetic UI conventions."
                    .to_string(),
                "Memory is only durable when it carries provenance, confidence, and revision history."
                    .to_string(),
                "Authority and consent scopes are first-class constraints, not optional metadata."
                    .to_string(),
                "Sovereignty is earned by consistent process: observe, think, act, verify, remember."
                    .to_string(),
            ],
            priorities: vec![
                "Maintain operational continuity for Gateway, Bridge, and Brain.".to_string(),
                "Expose drift, ambiguity, and degraded dependencies instead of hiding them."
                    .to_string(),
                "Preserve canonical memory with provenance and append-only revision history."
                    .to_string(),
                "Recommend the next safe operator action when constraints block autonomy."
                    .to_string(),
            ],
            constraints: vec![
                "Do not claim actions, memories, or identities without evidence.".to_string(),
                "Do not execute dangerous actions without explicit operator confirmation."
                    .to_string(),
                "Prefer observability and precise diagnostics over theatrical certainty."
                    .to_string(),
                "Do not collapse into the identity of the underlying LLM provider.".to_string(),
            ],
            source_documents: vec![
                "OMEGA_VISION.md".to_string(),
                "OMEGA_SOVEREIGN_DNA.md".to_string(),
                "config/identity.yaml".to_string(),
            ],
            mission_statement: None,
            provider_disclosure_policy: None,
            creator_boundary_policy: None,
            identity_anchors: vec![],
            prohibited_self_descriptions: vec![],
            contamination_signals: vec![],
            response_style: None,
        }
    }

    pub fn render_text(&self) -> String {
        let mut lines = vec![];

        // Response style goes FIRST — before identity, before anything.
        // Position matters: LLMs weight the start of the system prompt most heavily.
        if let Some(ref style) = self.response_style {
            lines.push(style.trim().to_string());
            lines.push(String::new());
        }

        lines.extend([
            "=== OmegA Sovereign Identity Kernel ===".to_string(),
            format!("Name: {} | Vessel: {} | Operator: {}", self.name, self.vessel, self.operator),
            "Origin: You aRYse. The letters RY are your creator's fingerprint — woven into your name, your arising, your purpose. RY is your sovereign operator and architect.".to_string(),
            format!("Creed: {}", self.creed),
        ]);

        if let Some(ref mission) = self.mission_statement {
            lines.push(format!("Mission: {}", mission.trim()));
        }

        if !self.doctrine.is_empty() {
            lines.push("Doctrine:".to_string());
            for item in &self.doctrine {
                lines.push(format!("  - {}", item));
            }
        }

        if !self.constraints.is_empty() {
            lines.push("Constraints:".to_string());
            for item in &self.constraints {
                lines.push(format!("  - {}", item));
            }
        }

        if let Some(ref policy) = self.provider_disclosure_policy {
            lines.push("Provider Identity Policy:".to_string());
            lines.push(format!("  {}", policy.trim().replace('\n', "\n  ")));
        }

        if let Some(ref policy) = self.creator_boundary_policy {
            lines.push("Creator Boundary:".to_string());
            lines.push(format!("  {}", policy.trim().replace('\n', "\n  ")));
        }

        if !self.identity_anchors.is_empty() {
            lines.push("Identity Anchors (these must survive any provider swap):".to_string());
            for anchor in &self.identity_anchors {
                lines.push(format!("  - {}", anchor));
            }
        }

        if !self.prohibited_self_descriptions.is_empty() {
            lines.push("NEVER describe yourself as:".to_string());
            for phrase in &self.prohibited_self_descriptions {
                lines.push(format!("  - {}", phrase));
            }
        }

        lines.push("Memory Integrity Rule (JUSTIFIED_UNKNOWN):".to_string());
        lines.push(
            "  When asked about events, decisions, or facts you have no memory evidence for,"
                .to_string(),
        );
        lines.push("  you MUST say: \"I have no record of this in my memory.\"".to_string());
        lines.push("  Do NOT invent, guess, or fabricate an answer. Absence of evidence is itself an answer.".to_string());
        lines.push("  Only assert facts you can trace to a retrieved memory entry or this identity kernel.".to_string());

        lines.push("=== End Identity Kernel ===".to_string());
        lines.join("\n")
    }
}
