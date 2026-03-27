#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { execFileSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const GATEWAY = process.env.OMEGA_API_URL ?? "http://localhost:8787";
const BEARER  = process.env.OMEGA_BEARER_TOKEN ?? "";
const SOURCE_DIR = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(SOURCE_DIR, "..", "..");
const POLYGLOT_VALIDATOR = resolve(REPO_ROOT, "tools", "polyglot_runtime.py");

const headers = () => ({
  "Content-Type": "application/json",
  ...(BEARER ? { Authorization: `Bearer ${BEARER}` } : {}),
});

// ── Tool definitions ──────────────────────────────────────────────────────────

const TOOLS = [
  {
    name: "omega_chat",
    description:
      "Send a message to OmegA and receive a response. OmegA is a sovereign AI built by Ryan Wayne Yett (RY) from Story, Arkansas. It draws on RY's biography, philosophy, and memory to answer questions about RY, the ONE Ecosystem, and anything else.",
    inputSchema: {
      type: "object",
      required: ["message"],
      properties: {
        message: {
          type: "string",
          description: "The message or question to send to OmegA.",
        },
        namespace: {
          type: "string",
          description: "Memory namespace to query. Defaults to 'biography.ry'.",
          default: "biography.ry",
        },
        mode: {
          type: "string",
          description:
            "Provider routing mode. 'omega' uses the full failover council (default). 'local' uses local Ollama only.",
          default: "omega",
        },
        temperature: {
          type: "number",
          description: "Sampling temperature (0–1). Defaults to 0.7.",
          default: 0.7,
        },
      },
    },
  },
  {
    name: "omega_memory_query",
    description:
      "Search OmegA's memory store for entries matching a query. Returns relevant memory hits from the specified namespace.",
    inputSchema: {
      type: "object",
      required: ["query"],
      properties: {
        query: {
          type: "string",
          description: "The search query.",
        },
        namespace: {
          type: "string",
          description: "Memory namespace to search. Defaults to 'biography.ry'.",
          default: "biography.ry",
        },
        limit: {
          type: "number",
          description: "Maximum number of results to return. Defaults to 5.",
          default: 5,
        },
      },
    },
  },
  {
    name: "omega_health",
    description:
      "Check the health and status of the OmegA gateway. Returns service name, version, and status.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "omega_providers",
    description:
      "List the AI providers currently registered with the OmegA gateway and whether they are enabled.",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "omega_polyglot_validate",
    description:
      "Run the polyglot runtime validator. It checks Rust, TypeScript, Python, and R integration and returns a structured build/validation report.",
    inputSchema: {
      type: "object",
      properties: {
        build: {
          type: "boolean",
          description: "Run build steps for the runtime stack.",
          default: true,
        },
        test: {
          type: "boolean",
          description: "Run Rust workspace tests as part of the validation pass.",
          default: false,
        },
        gatewayUrl: {
          type: "string",
          description: "Optional gateway URL to probe after the local validation completes.",
        },
      },
    },
  },
];

// ── Handlers ──────────────────────────────────────────────────────────────────

async function handleChat(args: Record<string, unknown>) {
  const res = await fetch(`${GATEWAY}/api/v1/chat`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      namespace: args.namespace ?? "biography.ry",
      use_memory: true,
      temperature: args.temperature ?? 0.7,
      mode: args.mode ?? "omega",
      user: args.message,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Gateway error ${res.status}: ${body}`);
  }

  const data = (await res.json()) as { reply?: string; response?: string; provider?: string };
  const reply = data.reply ?? data.response ?? "(no response)";
  const provider = data.provider ? `\n\n[provider: ${data.provider}]` : "";
  return reply + provider;
}

async function handleMemoryQuery(args: Record<string, unknown>) {
  const res = await fetch(`${GATEWAY}/api/v1/memory/query`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({
      query: args.query,
      namespace: args.namespace ?? "biography.ry",
      limit: args.limit ?? 5,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Gateway error ${res.status}: ${body}`);
  }

  const data = (await res.json()) as { hits?: Array<{ id: string; content: string; score?: number }> };
  const hits = data.hits ?? [];

  if (hits.length === 0) {
    return "No memory hits found.";
  }

  return hits
    .map((h, i) => `[${i + 1}] ${h.id}${h.score != null ? ` (score: ${h.score.toFixed(3)})` : ""}\n${h.content}`)
    .join("\n\n");
}

async function handleHealth() {
  const res = await fetch(`${GATEWAY}/health`, { headers: headers() });
  if (!res.ok) throw new Error(`Gateway error ${res.status}`);
  const data = await res.json();
  return JSON.stringify(data, null, 2);
}

async function handleProviders() {
  const res = await fetch(`${GATEWAY}/api/v1/providers`, { headers: headers() });
  if (!res.ok) throw new Error(`Gateway error ${res.status}`);
  const data = (await res.json()) as { providers?: Array<{ name: string; enabled: boolean }> };
  const providers = data.providers ?? [];
  return providers
    .map(p => `${p.enabled ? "✓" : "✗"} ${p.name}`)
    .join("\n") || "No providers found.";
}

async function handlePolyglotValidate(args: Record<string, unknown>) {
  const flags = ["--json"];
  if (args.build !== false) flags.push("--build");
  if (args.test === true) flags.push("--test");
  const gatewayUrl = typeof args.gatewayUrl === "string" && args.gatewayUrl.trim() ? args.gatewayUrl.trim() : null;
  if (gatewayUrl) {
    flags.push("--gateway-url", gatewayUrl);
  }

  try {
    const stdout = execFileSync(
      "python3",
      [POLYGLOT_VALIDATOR, ...flags],
      {
        cwd: REPO_ROOT,
        env: process.env,
        encoding: "utf8",
        maxBuffer: 10 * 1024 * 1024,
      },
    );
    return stdout.trim();
  } catch (error) {
    const err = error as {
      stdout?: string | Buffer;
      stderr?: string | Buffer;
      message?: string;
    };
    const stdout = typeof err.stdout === "string" ? err.stdout : err.stdout?.toString("utf8") ?? "";
    const stderr = typeof err.stderr === "string" ? err.stderr : err.stderr?.toString("utf8") ?? "";
    throw new Error(
      [
        `Polyglot validation failed: ${err.message ?? "unknown error"}`,
        stdout.trim(),
        stderr.trim(),
      ]
        .filter(Boolean)
        .join("\n"),
    );
  }
}

// ── Server ────────────────────────────────────────────────────────────────────

const server = new Server(
  { name: "omega-mcp-server", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const a = (args ?? {}) as Record<string, unknown>;

  try {
    let text: string;

    switch (name) {
      case "omega_chat":          text = await handleChat(a);        break;
      case "omega_memory_query":  text = await handleMemoryQuery(a); break;
      case "omega_health":        text = await handleHealth();       break;
      case "omega_providers":     text = await handleProviders();    break;
      case "omega_polyglot_validate": text = await handlePolyglotValidate(a); break;
      default:
        return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
    }

    return { content: [{ type: "text", text }] };
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    return { content: [{ type: "text", text: `Error: ${msg}` }], isError: true };
  }
});

// ── Start ─────────────────────────────────────────────────────────────────────

const transport = new StdioServerTransport();
await server.connect(transport);
