#!/usr/bin/env node

/**
 * omega_export_skill_ace.js
 *
 * Full Playwright export skill + Ace-ready knowledge graph synthesis.
 *
 * What this does:
 * 1) Uses a persistent Chromium profile so you can stay logged into Meta / LinkedIn.
 * 2) Triggers export requests for Meta and LinkedIn in a visible browser window.
 * 3) Scans an inbox directory for downloaded ZIP exports.
 * 4) Extracts them.
 * 5) Parses JSON / CSV / basic HTML into timeline-style memory events.
 * 6) Synthesizes a local Ace-ready knowledge graph snapshot and JSONL ingest payload.
 * 7) Optionally POSTs the graph payload to a configured sink if ACE_SINK_URL is set.
 *
 * Real outputs:
 * - <root>/graph/ace_graph_snapshot.json
 * - <root>/graph/ace_ingest_payload.jsonl
 * - <root>/graph/ace_summary.json
 * - <root>/logs/export_skill.log
 *
 * Usage examples:
 *   node omega_export_skill_ace.js
 *   node omega_export_skill_ace.js --mode trigger --providers meta,linkedin
 *   node omega_export_skill_ace.js --mode ingest --input ~/Downloads/my-export
 *   node omega_export_skill_ace.js --mode both --providers meta,linkedin --manual-wait-ms 25000
 *
 * Optional sink push:
 *   ACE_SINK_URL=https://your-endpoint.example/ingest \
 *   ACE_SINK_TOKEN=your_token_here \
 *   node omega_export_skill_ace.js --mode ingest
 */

const { firefox } = require('playwright');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const HOME = os.homedir();
const DEFAULT_ROOT = path.join(HOME, '.omega-export-skill');
const DEFAULT_PROFILE_DIR = path.join(DEFAULT_ROOT, 'browser-profile');
const DEFAULT_DOWNLOADS_DIR = path.join(DEFAULT_ROOT, 'downloads');
const DEFAULT_INBOX_DIR = path.join(DEFAULT_ROOT, 'inbox');
const DEFAULT_EXTRACT_DIR = path.join(DEFAULT_ROOT, 'extracted');
const DEFAULT_GRAPH_DIR = path.join(DEFAULT_ROOT, 'graph');
const DEFAULT_LOG_DIR = path.join(DEFAULT_ROOT, 'logs');

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function nowIso() {
  return new Date().toISOString();
}

function sha256(value) {
  return crypto.createHash('sha256').update(String(value)).digest('hex');
}

function stableId(prefix, naturalKey) {
  return `${prefix}_${sha256(naturalKey).slice(0, 20)}`;
}

function safeJsonStringify(value, spaces = 2) {
  try {
    return JSON.stringify(value, null, spaces);
  } catch {
    return JSON.stringify({ error: 'Failed to stringify value' }, null, spaces);
  }
}

function writeJson(filePath, value) {
  mkdirp(path.dirname(filePath));
  fs.writeFileSync(filePath, safeJsonStringify(value), 'utf8');
}

function appendJsonl(filePath, record) {
  mkdirp(path.dirname(filePath));
  fs.appendFileSync(filePath, `${JSON.stringify(record)}\n`, 'utf8');
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function readJsonSafe(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function exists(filePath) {
  return fs.existsSync(filePath);
}

function isDirectory(filePath) {
  try {
    return fs.statSync(filePath).isDirectory();
  } catch {
    return false;
  }
}

function isFile(filePath) {
  try {
    return fs.statSync(filePath).isFile();
  } catch {
    return false;
  }
}

function truncate(text, max = 300) {
  const s = String(text ?? '').replace(/\s+/g, ' ').trim();
  return s.length <= max ? s : `${s.slice(0, max - 1)}…`;
}

function unique(arr) {
  return [...new Set(arr.filter(Boolean))];
}

function normalizePathInput(p) {
  if (!p) return p;
  if (p.startsWith('~/')) return path.join(HOME, p.slice(2));
  return path.resolve(p);
}

function walk(dir, out = []) {
  if (!exists(dir)) return out;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
  return out;
}

function stripHtml(html) {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

function maybeIsoFromNumber(value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null;
  if (value > 1e12) return new Date(value).toISOString();      // ms
  if (value > 1e9) return new Date(value * 1000).toISOString(); // seconds
  return null;
}

function normalizeTime(value) {
  if (value == null) return null;

  if (typeof value === 'number') {
    return maybeIsoFromNumber(value);
  }

  if (typeof value === 'string') {
    const s = value.trim();
    if (!s) return null;

    if (/^\d+$/.test(s)) {
      return maybeIsoFromNumber(Number(s));
    }

    const d = new Date(s);
    if (!Number.isNaN(d.getTime())) return d.toISOString();

    const monthStyle = s.match(/\b([A-Z][a-z]{2,8}\s+\d{1,2},\s+\d{4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?\b/);
    if (monthStyle) {
      const d2 = new Date(monthStyle[0]);
      if (!Number.isNaN(d2.getTime())) return d2.toISOString();
    }
  }

  return null;
}

function extractEmails(text) {
  const s = String(text ?? '');
  return unique((s.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || []).map(v => v.toLowerCase()));
}

function extractUrls(text) {
  const s = String(text ?? '');
  return unique((s.match(/https?:\/\/[^\s"'<>]+/gi) || []).map(v => v.trim()));
}

function inferProviderFromPath(filePath) {
  const p = filePath.toLowerCase();
  if (p.includes('linkedin')) return 'linkedin';
  if (p.includes('facebook') || p.includes('instagram') || p.includes('meta') || p.includes('accounts_center')) return 'meta';
  return 'unknown';
}

function inferEventType(filePath, pathTokens = []) {
  const joined = `${filePath} ${pathTokens.join(' ')}`.toLowerCase();

  if (joined.includes('message')) return 'message';
  if (joined.includes('inbox')) return 'message';
  if (joined.includes('comment')) return 'comment';
  if (joined.includes('reaction') || joined.includes('like')) return 'reaction';
  if (joined.includes('post')) return 'post';
  if (joined.includes('search')) return 'search';
  if (joined.includes('connection')) return 'connection';
  if (joined.includes('profile')) return 'profile';
  if (joined.includes('ad')) return 'advertising';
  if (joined.includes('job')) return 'job';
  if (joined.includes('education') || joined.includes('school')) return 'education';
  if (joined.includes('company') || joined.includes('employment')) return 'employment';
  return 'activity';
}

function parseArgs(argv) {
  const args = {
    mode: 'both',
    providers: ['meta', 'linkedin'],
    input: null,
    rootDir: DEFAULT_ROOT,
    profileDir: DEFAULT_PROFILE_DIR,
    downloadsDir: DEFAULT_DOWNLOADS_DIR,
    inboxDir: DEFAULT_INBOX_DIR,
    extractDir: DEFAULT_EXTRACT_DIR,
    graphDir: DEFAULT_GRAPH_DIR,
    logDir: DEFAULT_LOG_DIR,
    manualWaitMs: 20000,
    finalBrowserWaitMs: 30000,
    maxEventsPerFile: 500,
    maxFiles: 2000,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = argv[i + 1];

    if (a === '--mode' && next) {
      args.mode = next;
      i++;
    } else if (a === '--providers' && next) {
      args.providers = next.split(',').map(v => v.trim().toLowerCase()).filter(Boolean);
      i++;
    } else if (a === '--input' && next) {
      args.input = normalizePathInput(next);
      i++;
    } else if (a === '--root-dir' && next) {
      args.rootDir = normalizePathInput(next);
      i++;
    } else if (a === '--profile-dir' && next) {
      args.profileDir = normalizePathInput(next);
      i++;
    } else if (a === '--downloads-dir' && next) {
      args.downloadsDir = normalizePathInput(next);
      i++;
    } else if (a === '--inbox-dir' && next) {
      args.inboxDir = normalizePathInput(next);
      i++;
    } else if (a === '--extract-dir' && next) {
      args.extractDir = normalizePathInput(next);
      i++;
    } else if (a === '--graph-dir' && next) {
      args.graphDir = normalizePathInput(next);
      i++;
    } else if (a === '--log-dir' && next) {
      args.logDir = normalizePathInput(next);
      i++;
    } else if (a === '--manual-wait-ms' && next) {
      args.manualWaitMs = Number(next);
      i++;
    } else if (a === '--final-browser-wait-ms' && next) {
      args.finalBrowserWaitMs = Number(next);
      i++;
    } else if (a === '--max-events-per-file' && next) {
      args.maxEventsPerFile = Number(next);
      i++;
    } else if (a === '--max-files' && next) {
      args.maxFiles = Number(next);
      i++;
    }
  }

  return args;
}

class Logger {
  constructor(logFile) {
    this.logFile = logFile;
    mkdirp(path.dirname(logFile));
  }

  line(level, message, meta = null) {
    const record = {
      ts: nowIso(),
      level,
      message,
      ...(meta ? { meta } : {}),
    };
    fs.appendFileSync(this.logFile, `${JSON.stringify(record)}\n`, 'utf8');

    const prefix = `[${record.ts}] [${level}]`;
    if (meta) {
      console.log(prefix, message, meta);
    } else {
      console.log(prefix, message);
    }
  }

  info(message, meta = null) {
    this.line('INFO', message, meta);
  }

  warn(message, meta = null) {
    this.line('WARN', message, meta);
  }

  error(message, meta = null) {
    this.line('ERROR', message, meta);
  }
}

class AceKnowledgeGraphBridge {
  constructor({ graphDir, logger }) {
    this.graphDir = graphDir;
    this.logger = logger;
    this.nodes = new Map();
    this.edges = new Map();
    this.payloadFile = path.join(graphDir, 'ace_ingest_payload.jsonl');
    this.snapshotFile = path.join(graphDir, 'ace_graph_snapshot.json');
    this.summaryFile = path.join(graphDir, 'ace_summary.json');
    this.runId = null;
    this.eventCount = 0;
    this.fileCount = 0;

    mkdirp(graphDir);
    if (exists(this.payloadFile)) fs.unlinkSync(this.payloadFile);
  }

  startRun(meta = {}) {
    const naturalKey = `export_run|${nowIso()}|${JSON.stringify(meta)}`;
    this.runId = this.addNode('export_run', naturalKey, {
      startedAt: nowIso(),
      ...meta,
    });
    return this.runId;
  }

  finishRun(meta = {}) {
    if (!this.runId) return;
    this.patchNode(this.runId, {
      finishedAt: nowIso(),
      ...meta,
    });
  }

  addNode(type, naturalKey, properties = {}) {
    const id = stableId(type, `${type}|${naturalKey}`);
    if (!this.nodes.has(id)) {
      this.nodes.set(id, {
        id,
        type,
        properties: { ...properties },
      });
    } else {
      const existing = this.nodes.get(id);
      existing.properties = { ...existing.properties, ...properties };
      this.nodes.set(id, existing);
    }
    return id;
  }

  patchNode(id, properties = {}) {
    const node = this.nodes.get(id);
    if (!node) return;
    node.properties = { ...node.properties, ...properties };
    this.nodes.set(id, node);
  }

  addEdge(type, from, to, naturalKey, properties = {}) {
    const id = stableId('edge', `${type}|${naturalKey}|${from}|${to}`);
    if (!this.edges.has(id)) {
      this.edges.set(id, {
        id,
        type,
        from,
        to,
        properties: { ...properties },
      });
    } else {
      const existing = this.edges.get(id);
      existing.properties = { ...existing.properties, ...properties };
      this.edges.set(id, existing);
    }
    return id;
  }

  recordExportRequest({ provider, status, url = null, notes = null }) {
    const providerId = this.addNode('provider', provider, { name: provider });
    const requestId = this.addNode(
      'export_request',
      `${provider}|${nowIso()}|${status}|${url || ''}`,
      {
        provider,
        status,
        requestedAt: nowIso(),
        url,
        notes,
      }
    );

    this.addEdge('RUN_REQUESTED_EXPORT', this.runId, requestId, `run->request|${this.runId}|${requestId}`);
    this.addEdge('PROVIDER_HAS_REQUEST', providerId, requestId, `provider->request|${providerId}|${requestId}`);
    appendJsonl(this.payloadFile, {
      kind: 'export_request',
      provider,
      status,
      url,
      notes,
      requestedAt: nowIso(),
    });

    return requestId;
  }

  recordSourceFile({ provider, filePath, extractedFrom = null }) {
    const providerId = this.addNode('provider', provider, { name: provider });
    const docId = this.addNode('source_document', filePath, {
      provider,
      filePath,
      extractedFrom,
      seenAt: nowIso(),
    });

    this.addEdge('PROVIDER_HAS_DOCUMENT', providerId, docId, `provider->document|${providerId}|${docId}`);
    this.fileCount += 1;

    appendJsonl(this.payloadFile, {
      kind: 'source_document',
      provider,
      filePath,
      extractedFrom,
      seenAt: nowIso(),
    });

    return docId;
  }

  recordMemoryEvent(event) {
    const provider = event.provider || 'unknown';
    const providerId = this.addNode('provider', provider, { name: provider });
    const accountId = this.addNode('account', `${provider}|${event.account || 'default'}`, {
      provider,
      label: event.account || 'default',
    });
    const docId = this.addNode('source_document', event.sourceFile, {
      provider,
      filePath: event.sourceFile,
      extractedFrom: event.extractedFrom || null,
    });

    const eventKey = [
      provider,
      event.sourceFile,
      event.type,
      event.time || '',
      event.text || '',
      (event.people || []).join('|'),
      (event.emails || []).join('|'),
      (event.urls || []).join('|'),
      event.sourcePath || '',
    ].join('||');

    const eventId = this.addNode('memory_event', eventKey, {
      provider,
      account: event.account || 'default',
      eventType: event.type || 'activity',
      time: event.time || null,
      text: event.text || '',
      sourceFile: event.sourceFile,
      sourcePath: event.sourcePath || '',
      extractedFrom: event.extractedFrom || null,
      rawPreview: event.rawPreview || null,
      ingestedAt: nowIso(),
    });

    this.addEdge('PROVIDER_HAS_ACCOUNT', providerId, accountId, `provider->account|${providerId}|${accountId}`);
    this.addEdge('ACCOUNT_HAS_DOCUMENT', accountId, docId, `account->document|${accountId}|${docId}`);
    this.addEdge('DOCUMENT_EMITS_EVENT', docId, eventId, `document->event|${docId}|${eventId}`);

    for (const person of unique(event.people || [])) {
      const personId = this.addNode('person', `${provider}|${person}`, {
        provider,
        name: person,
      });
      this.addEdge('EVENT_MENTIONS_PERSON', eventId, personId, `event->person|${eventId}|${personId}`);
    }

    for (const email of unique(event.emails || [])) {
      const emailId = this.addNode('email', email, { value: email });
      this.addEdge('EVENT_MENTIONS_EMAIL', eventId, emailId, `event->email|${eventId}|${emailId}`);
    }

    for (const url of unique(event.urls || [])) {
      const urlId = this.addNode('url', url, { value: url });
      this.addEdge('EVENT_MENTIONS_URL', eventId, urlId, `event->url|${eventId}|${urlId}`);
    }

    this.eventCount += 1;
    appendJsonl(this.payloadFile, {
      kind: 'memory_event',
      ...event,
      ingestedAt: nowIso(),
    });

    return eventId;
  }

  save() {
    const snapshot = {
      generatedAt: nowIso(),
      runId: this.runId,
      counts: {
        nodes: this.nodes.size,
        edges: this.edges.size,
        sourceFiles: this.fileCount,
        memoryEvents: this.eventCount,
      },
      nodes: [...this.nodes.values()],
      edges: [...this.edges.values()],
    };

    const summary = {
      generatedAt: snapshot.generatedAt,
      runId: this.runId,
      counts: snapshot.counts,
      files: {
        snapshot: this.snapshotFile,
        payload: this.payloadFile,
      },
    };

    writeJson(this.snapshotFile, snapshot);
    writeJson(this.summaryFile, summary);
    this.logger.info('Saved Ace-ready graph artifacts', summary);
    return { snapshot, summary };
  }

  async pushToSinkIfConfigured() {
    const sinkUrl = process.env.ACE_SINK_URL;
    const sinkToken = process.env.ACE_SINK_TOKEN || '';
    if (!sinkUrl) {
      this.logger.info('ACE_SINK_URL not set; skipping remote graph push');
      return { skipped: true };
    }

    if (typeof fetch !== 'function') {
      this.logger.warn('Global fetch is unavailable in this Node runtime; skipping remote graph push');
      return { skipped: true, reason: 'fetch_unavailable' };
    }

    const payload = {
      generatedAt: nowIso(),
      snapshot: readJsonSafe(this.snapshotFile),
    };

    const headers = {
      'content-type': 'application/json',
    };
    if (sinkToken) headers.authorization = `Bearer ${sinkToken}`;

    const res = await fetch(sinkUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    const body = await res.text().catch(() => '');
    const result = {
      ok: res.ok,
      status: res.status,
      body: truncate(body, 1000),
      sinkUrl,
    };

    if (res.ok) {
      this.logger.info('Pushed graph snapshot to remote sink', result);
    } else {
      this.logger.warn('Remote graph push failed', result);
    }

    return result;
  }
}

async function createContext(config, logger) {
  mkdirp(config.profileDir);
  mkdirp(config.downloadsDir);
  const headless = process.env.OMEGA_HEADLESS === 'true';

  const context = await firefox.launchPersistentContext(config.profileDir, {
    headless,
    acceptDownloads: true,
    viewport: { width: 1440, height: 920 },
    args: [
      '--disable-notifications',
      '--no-default-browser-check',
    ],
  });

  const pages = context.pages();
  const page = pages[0] || await context.newPage();

  page.on('download', async download => {
    try {
      const suggested = download.suggestedFilename();
      const target = path.join(config.downloadsDir, suggested);
      await download.saveAs(target);
      logger.info('Captured browser download', { target });
    } catch (err) {
      logger.warn('Failed to persist browser download', { error: String(err) });
    }
  });

  return { context, page };
}

async function clickFirst(page, selectors, logger, label) {
  for (const selector of selectors) {
    try {
      const locator = page.locator(selector).first();
      await locator.waitFor({ state: 'visible', timeout: 1500 });
      await locator.click({ timeout: 3000 });
      logger.info(`Clicked ${label}`, { selector });
      return selector;
    } catch {
      // keep trying
    }
  }
  logger.warn(`Could not find clickable target for ${label}`, { selectors });
  return null;
}

async function ensureManualAuthWindow(label, waitMs, logger) {
  logger.info(`${label}: if needed, log in / solve 2FA / handle captchas in the visible browser window`, { waitMs });
  await sleep(waitMs);
}

async function triggerMetaExport(page, config, logger, kg) {
  const url = 'https://www.facebook.com/settings?tab=your_facebook_information';
  logger.info('Starting Meta export flow', { url });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => null);

  await ensureManualAuthWindow('META', config.manualWaitMs, logger);

  await clickFirst(
    page,
    [
      'text=Download your information',
      'text=Export your information',
      'text=Download profile information',
      'text=Access your information',
      'text=Accounts Center',
    ],
    logger,
    'Meta export entry'
  );

  await page.waitForLoadState('networkidle').catch(() => null);
  await sleep(3000);

  await clickFirst(
    page,
    [
      'button:has-text("Date range")',
      'text=Date range',
    ],
    logger,
    'Meta date range dropdown'
  );

  await clickFirst(
    page,
    [
      'text=All time',
      'text=All available time',
    ],
    logger,
    'Meta all time option'
  );

  await clickFirst(
    page,
    [
      'text=All available information',
      'text=Complete copy',
      'text=All information',
    ],
    logger,
    'Meta all information option'
  );

  await clickFirst(
    page,
    [
      'button:has-text("Format")',
      'text=Format',
    ],
    logger,
    'Meta format dropdown'
  );

  await clickFirst(
    page,
    [
      'text=HTML',
      'text=JSON',
    ],
    logger,
    'Meta format option'
  );

  const clicked = await clickFirst(
    page,
    [
      'text=Create export',
      'text=Start export',
      'button:has-text("Create export")',
      'button:has-text("Start export")',
      'button:has-text("Request download")',
    ],
    logger,
    'Meta export submit'
  );

  kg.recordExportRequest({
    provider: 'meta',
    status: clicked ? 'requested' : 'manual_adjustment_needed',
    url,
    notes: clicked ? 'Automated submit click succeeded' : 'Adjust selectors in UI; submit button not found',
  });

  logger.info('Meta export flow completed');
}

async function triggerLinkedInExport(page, config, logger, kg) {
  const url = 'https://www.linkedin.com/psettings/member-data';
  logger.info('Starting LinkedIn export flow', { url });
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.waitForLoadState('networkidle').catch(() => null);

  await ensureManualAuthWindow('LINKEDIN', config.manualWaitMs, logger);

  await clickFirst(
    page,
    [
      'text=Download a copy of your data',
      'text=Get a copy of your data',
      'text=Data privacy',
      'text=Export data',
    ],
    logger,
    'LinkedIn export entry'
  );

  await sleep(2500);

  await clickFirst(
    page,
    [
      'text=The works',
      'text=Download larger data archive',
      'text=All data',
      'label:has-text("The works")',
    ],
    logger,
    'LinkedIn full archive option'
  );

  const clicked = await clickFirst(
    page,
    [
      'button:has-text("Request archive")',
      'button:has-text("Request data archive")',
      'button:has-text("Request")',
      'text=Request archive',
    ],
    logger,
    'LinkedIn archive submit'
  );

  kg.recordExportRequest({
    provider: 'linkedin',
    status: clicked ? 'requested' : 'manual_adjustment_needed',
    url,
    notes: clicked ? 'Automated submit click succeeded' : 'Adjust selectors in UI; request button not found',
  });

  logger.info('LinkedIn export flow completed');
}

async function triggerExports(config, logger, kg) {
  const { context, page } = await createContext(config, logger);

  try {
    if (config.providers.includes('meta')) {
      await triggerMetaExport(page, config, logger, kg);
      await sleep(3000);
    }

    if (config.providers.includes('linkedin')) {
      await triggerLinkedInExport(page, config, logger, kg);
      await sleep(3000);
    }

    logger.info('All requested export trigger flows completed', {
      providers: config.providers,
      finalBrowserWaitMs: config.finalBrowserWaitMs,
    });

    await sleep(config.finalBrowserWaitMs);
  } finally {
    await context.close().catch(() => null);
  }
}

function extractZip(zipPath, destination, logger) {
  mkdirp(destination);

  try {
    if (process.platform === 'win32') {
      execFileSync(
        'powershell',
        [
          '-NoProfile',
          '-Command',
          `Expand-Archive -LiteralPath '${zipPath.replace(/'/g, "''")}' -DestinationPath '${destination.replace(/'/g, "''")}' -Force`,
        ],
        { stdio: 'ignore' }
      );
    } else {
      execFileSync('unzip', ['-o', zipPath, '-d', destination], { stdio: 'ignore' });
    }

    logger.info('Extracted ZIP archive', { zipPath, destination });
    return true;
  } catch (err) {
    logger.warn('ZIP extraction failed', { zipPath, destination, error: String(err) });
    return false;
  }
}

function discoverInputRoots(config, logger) {
  const roots = [];

  if (config.input) {
    if (exists(config.input)) {
      roots.push(config.input);
    } else {
      logger.warn('Configured input path does not exist', { input: config.input });
    }
  }

  mkdirp(config.inboxDir);
  mkdirp(config.extractDir);

  const inboxFiles = walk(config.inboxDir).filter(f => f.toLowerCase().endsWith('.zip'));
  for (const zipFile of inboxFiles) {
    const base = path.basename(zipFile, path.extname(zipFile));
    const outDir = path.join(config.extractDir, base);
    const ok = extractZip(zipFile, outDir, logger);
    if (ok) roots.push(outDir);
  }

  const extractChildren = exists(config.extractDir)
    ? fs.readdirSync(config.extractDir).map(v => path.join(config.extractDir, v)).filter(isDirectory)
    : [];

  for (const dir of extractChildren) {
    roots.push(dir);
  }

  return unique(roots);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ',') {
      row.push(field);
      field = '';
    } else if (ch === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (ch === '\r') {
      // ignore
    } else {
      field += ch;
    }
  }

  row.push(field);
  if (row.length > 1 || row[0] !== '') rows.push(row);

  if (!rows.length) return [];
  const headers = rows[0].map(h => String(h).trim());
  return rows.slice(1).map(cols => {
    const obj = {};
    for (let i = 0; i < headers.length; i++) {
      obj[headers[i] || `col_${i}`] = cols[i] ?? '';
    }
    return obj;
  });
}

function compactPreview(value) {
  const raw = typeof value === 'string' ? value : safeJsonStringify(value, 0);
  return truncate(raw, 2000);
}

function candidateTextFields(obj) {
  const textKeys = [
    'title', 'text', 'body', 'message', 'content', 'caption', 'summary', 'subject',
    'headline', 'description', 'name', 'company', 'school', 'position', 'action'
  ];

  const out = [];
  for (const [k, v] of Object.entries(obj || {})) {
    if (typeof v !== 'string') continue;
    const key = k.toLowerCase();
    if (textKeys.some(tk => key.includes(tk))) out.push(v);
  }
  return unique(out);
}

function candidatePeopleFields(obj) {
  const personKeys = [
    'name', 'sender', 'recipient', 'author', 'actor', 'contact', 'participant',
    'connection', 'full name'
  ];

  const out = [];
  for (const [k, v] of Object.entries(obj || {})) {
    if (typeof v !== 'string') continue;
    const key = k.toLowerCase();
    if (personKeys.some(pk => key.includes(pk))) out.push(v.trim());
  }
  return unique(out.filter(v => v.length <= 120));
}

function candidateTimeFields(obj) {
  const out = [];
  for (const [k, v] of Object.entries(obj || {})) {
    const key = k.toLowerCase();
    if (
      key.includes('time') ||
      key.includes('date') ||
      key.includes('created') ||
      key.includes('updated') ||
      key.includes('sent') ||
      key.includes('timestamp')
    ) {
      const t = normalizeTime(v);
      if (t) out.push(t);
    }
  }
  return unique(out);
}

function buildEventFromObject({ provider, account, sourceFile, sourcePath, raw, extractedFrom }) {
  const times = candidateTimeFields(raw);
  const textParts = candidateTextFields(raw);
  const people = candidatePeopleFields(raw);
  const rawTextBlob = `${textParts.join(' ')} ${safeJsonStringify(raw, 0)}`;
  const emails = extractEmails(rawTextBlob);
  const urls = extractUrls(rawTextBlob);

  const time = times[0] || null;
  const text = truncate(textParts.join(' | '), 500);
  const recognizedSignals = [
    time ? 1 : 0,
    text ? 1 : 0,
    people.length ? 1 : 0,
    emails.length ? 1 : 0,
    urls.length ? 1 : 0,
  ].reduce((a, b) => a + b, 0);

  if (recognizedSignals < 2 && !time) return null;

  return {
    provider,
    account,
    type: inferEventType(sourceFile, sourcePath.split('.')),
    time,
    text,
    people,
    emails,
    urls,
    sourceFile,
    sourcePath,
    extractedFrom,
    rawPreview: compactPreview(raw),
  };
}

function traverseJsonForEvents(value, context, events, maxEvents) {
  if (events.length >= maxEvents) return;

  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      traverseJsonForEvents(value[i], { ...context, sourcePath: `${context.sourcePath}[${i}]` }, events, maxEvents);
      if (events.length >= maxEvents) return;
    }
    return;
  }

  if (value && typeof value === 'object') {
    const event = buildEventFromObject({
      provider: context.provider,
      account: context.account,
      sourceFile: context.sourceFile,
      sourcePath: context.sourcePath,
      raw: value,
      extractedFrom: context.extractedFrom,
    });

    if (event) events.push(event);

    for (const [key, child] of Object.entries(value)) {
      const nextPath = context.sourcePath ? `${context.sourcePath}.${key}` : key;
      traverseJsonForEvents(child, { ...context, sourcePath: nextPath }, events, maxEvents);
      if (events.length >= maxEvents) return;
    }
  }
}

function parseJsonFileToEvents(filePath, provider, config, extractedFrom) {
  const json = readJsonSafe(filePath);
  if (json == null) return [];

  const events = [];
  traverseJsonForEvents(
    json,
    {
      provider,
      account: 'default',
      sourceFile: filePath,
      sourcePath: '',
      extractedFrom,
    },
    events,
    config.maxEventsPerFile
  );

  return events;
}

function parseCsvFileToEvents(filePath, provider, config, extractedFrom) {
  const text = readText(filePath);
  const rows = parseCsv(text);
  const events = [];

  for (const row of rows.slice(0, config.maxEventsPerFile)) {
    const time = candidateTimeFields(row)[0] || null;
    const textValue = truncate(candidateTextFields(row).join(' | '), 500);
    const people = candidatePeopleFields(row);
    const blob = safeJsonStringify(row, 0);
    const emails = extractEmails(blob);
    const urls = extractUrls(blob);

    if (!time && !textValue && !people.length && !emails.length && !urls.length) continue;

    events.push({
      provider,
      account: 'default',
      type: inferEventType(filePath),
      time,
      text: textValue,
      people,
      emails,
      urls,
      sourceFile: filePath,
      sourcePath: '',
      extractedFrom,
      rawPreview: compactPreview(row),
    });
  }

  return events;
}

function parseHtmlFileToEvents(filePath, provider, config, extractedFrom) {
  const html = readText(filePath);
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const title = titleMatch ? truncate(stripHtml(titleMatch[1]), 200) : '';
  const text = stripHtml(html);
  const foundTimes = unique(
    [
      ...(text.match(/\b20\d{2}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?Z?)?\b/g) || []),
      ...(text.match(/\b[A-Z][a-z]{2,8}\s+\d{1,2},\s+20\d{2}\b/g) || []),
    ]
      .map(normalizeTime)
      .filter(Boolean)
  );

  if (!title && !foundTimes.length) return [];

  return [
    {
      provider,
      account: 'default',
      type: inferEventType(filePath),
      time: foundTimes[0] || null,
      text: truncate(`${title} ${text}`.trim(), 500),
      people: [],
      emails: extractEmails(text),
      urls: extractUrls(html),
      sourceFile: filePath,
      sourcePath: '',
      extractedFrom,
      rawPreview: truncate(text, 1500),
    },
  ];
}

function ingestRoot(rootDir, config, logger, kg) {
  const files = walk(rootDir).slice(0, config.maxFiles);
  logger.info('Ingesting extracted root', { rootDir, fileCount: files.length });

  let parsedFiles = 0;
  let parsedEvents = 0;

  for (const file of files) {
    const ext = path.extname(file).toLowerCase();
    const provider = inferProviderFromPath(file) !== 'unknown' ? inferProviderFromPath(file) : inferProviderFromPath(rootDir);
    kg.recordSourceFile({ provider, filePath: file, extractedFrom: rootDir });

    let events = [];

    try {
      if (ext === '.json') {
        events = parseJsonFileToEvents(file, provider, config, rootDir);
      } else if (ext === '.csv') {
        events = parseCsvFileToEvents(file, provider, config, rootDir);
      } else if (ext === '.html' || ext === '.htm') {
        events = parseHtmlFileToEvents(file, provider, config, rootDir);
      }

      for (const event of events) kg.recordMemoryEvent(event);

      parsedFiles += 1;
      parsedEvents += events.length;
    } catch (err) {
      logger.warn('Failed to parse file during ingest', { file, error: String(err) });
    }
  }

  logger.info('Completed ingest root', { rootDir, parsedFiles, parsedEvents });
  return { parsedFiles, parsedEvents };
}

async function ingestExports(config, logger, kg) {
  const roots = discoverInputRoots(config, logger);

  if (!roots.length) {
    logger.warn('No input roots found for ingest', {
      input: config.input,
      inboxDir: config.inboxDir,
      extractDir: config.extractDir,
    });
    return { roots: [], parsedFiles: 0, parsedEvents: 0 };
  }

  let parsedFiles = 0;
  let parsedEvents = 0;

  for (const root of roots) {
    if (!exists(root)) continue;
    if (isFile(root) && root.toLowerCase().endsWith('.zip')) {
      const outDir = path.join(config.extractDir, path.basename(root, path.extname(root)));
      const ok = extractZip(root, outDir, logger);
      if (!ok) continue;
      const result = ingestRoot(outDir, config, logger, kg);
      parsedFiles += result.parsedFiles;
      parsedEvents += result.parsedEvents;
    } else if (isDirectory(root)) {
      const result = ingestRoot(root, config, logger, kg);
      parsedFiles += result.parsedFiles;
      parsedEvents += result.parsedEvents;
    }
  }

  return { roots, parsedFiles, parsedEvents };
}

async function main() {
  const config = parseArgs(process.argv.slice(2));

  mkdirp(config.rootDir);
  mkdirp(config.profileDir);
  mkdirp(config.downloadsDir);
  mkdirp(config.inboxDir);
  mkdirp(config.extractDir);
  mkdirp(config.graphDir);
  mkdirp(config.logDir);

  const logger = new Logger(path.join(config.logDir, 'export_skill.log'));
  const kg = new AceKnowledgeGraphBridge({ graphDir: config.graphDir, logger });

  logger.info('Starting OmegA export skill with Ace-ready graph synthesis', {
    mode: config.mode,
    providers: config.providers,
    rootDir: config.rootDir,
    profileDir: config.profileDir,
    downloadsDir: config.downloadsDir,
    inboxDir: config.inboxDir,
    extractDir: config.extractDir,
    graphDir: config.graphDir,
  });

  kg.startRun({
    mode: config.mode,
    providers: config.providers,
    host: os.hostname(),
  });

  try {
    if (config.mode === 'trigger' || config.mode === 'both') {
      await triggerExports(config, logger, kg);
    }

    let ingestResult = { roots: [], parsedFiles: 0, parsedEvents: 0 };
    if (config.mode === 'ingest' || config.mode === 'both') {
      ingestResult = await ingestExports(config, logger, kg);
      logger.info('Ingest summary', ingestResult);
    }

    kg.finishRun({
      ingestRoots: ingestResult.roots,
      parsedFiles: ingestResult.parsedFiles,
      parsedEvents: ingestResult.parsedEvents,
    });

    const saved = kg.save();
    await kg.pushToSinkIfConfigured().catch(err => {
      logger.warn('Graph sink push threw an error', { error: String(err) });
    });

    logger.info('Export skill run complete', saved.summary);
  } catch (err) {
    kg.finishRun({
      error: String(err),
    });
    kg.save();
    logger.error('Fatal error in export skill', { error: String(err), stack: err && err.stack ? err.stack : null });
    process.exitCode = 1;
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  main,
  createContext,
  triggerExports,
  triggerMetaExport,
  triggerLinkedInExport,
  ingestExports,
  AceKnowledgeGraphBridge,
};
