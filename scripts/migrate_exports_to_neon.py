#!/usr/bin/env python3
"""
Migrate Claude and ChatGPT data exports into OmegA's omega_memory_entries table in Neon.
Each conversation becomes one memory entry — title + summary + all messages concatenated.
"""

import json
import os
import sys
import uuid
import psycopg2
from datetime import datetime, timezone

DB_URL = "postgresql://neondb_owner:npg_HbW1Zlkjd7NI@ep-sweet-glade-anvm0pwn.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require"

CLAUDE_CONVOS   = "/home/mega/Downloads/claudedata/conversations.json"
CLAUDE_MEMORIES = "/home/mega/Downloads/claudedata/memories.json"
GPT_FILES = [
    "/home/mega/Downloads/chatgptdata/conversations-000.json",
    "/home/mega/Downloads/chatgptdata/conversations-001.json",
    "/home/mega/Downloads/chatgptdata/conversations-002.json",
    "/home/mega/Downloads/chatgptdata/conversations-003.json",
    "/home/mega/Downloads/chatgptdata/conversations-004.json",
]

MAX_CONTENT = 8000  # chars per entry — keeps individual rows manageable

def truncate(s, n=MAX_CONTENT):
    return s[:n] if len(s) > n else s

def fmt_ts(ts):
    """Accept ISO string or unix float, return datetime."""
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts)
    if isinstance(ts, str):
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return datetime.utcnow()

# ── Claude conversations ──────────────────────────────────────────────────────

def load_claude_convos():
    print("Loading Claude conversations...")
    with open(CLAUDE_CONVOS) as f:
        data = json.load(f)

    entries = []
    for convo in data:
        name    = convo.get("name", "Untitled")
        summary = convo.get("summary", "")
        created = fmt_ts(convo.get("created_at", datetime.utcnow().isoformat()))
        msgs    = convo.get("chat_messages", [])

        lines = [f"[Claude Conversation] {name}"]
        if summary:
            lines.append(f"Summary: {summary[:500]}")
        for m in msgs:
            sender = "RY" if m.get("sender") == "human" else "Claude"
            text   = m.get("text", "").strip()
            if text:
                lines.append(f"{sender}: {text[:800]}")

        content = truncate("\n\n".join(lines))
        if len(content) > 100:  # skip near-empty convos
            entries.append((content, created))

    print(f"  → {len(entries)} Claude conversations")
    return entries

# ── Claude memories ───────────────────────────────────────────────────────────

def load_claude_memories():
    print("Loading Claude memories...")
    with open(CLAUDE_MEMORIES) as f:
        data = json.load(f)

    entries = []
    for item in data:
        mem = item.get("conversations_memory", "").strip()
        if mem:
            content = truncate(f"[Claude Memory Export]\n\n{mem}")
            entries.append((content, datetime.utcnow()))

    print(f"  → {len(entries)} Claude memory entries")
    return entries

# ── ChatGPT conversations ─────────────────────────────────────────────────────

def extract_gpt_messages(mapping, node_id, depth=0):
    """Recursively walk the ChatGPT message tree."""
    if depth > 200 or not node_id or node_id not in mapping:
        return []
    node = mapping[node_id]
    msg  = node.get("message") or {}
    role = (msg.get("author") or {}).get("role", "")
    parts = (msg.get("content") or {}).get("parts") or []
    text  = " ".join(str(p) for p in parts if isinstance(p, str)).strip()

    results = []
    if role in ("user", "assistant") and text:
        label = "RY" if role == "user" else "GPT"
        results.append(f"{label}: {text[:800]}")

    for child_id in node.get("children", []):
        results.extend(extract_gpt_messages(mapping, child_id, depth + 1))

    return results

def load_gpt_convos():
    entries = []
    for path in GPT_FILES:
        print(f"Loading {os.path.basename(path)}...")
        with open(path) as f:
            data = json.load(f)

        for convo in data:
            title   = convo.get("title", "Untitled")
            created = fmt_ts(convo.get("create_time", datetime.utcnow().timestamp()))
            mapping = convo.get("mapping", {})
            root    = next(
                (nid for nid, n in mapping.items() if not n.get("parent")),
                None
            )

            lines = [f"[ChatGPT Conversation] {title}"]
            if root:
                lines.extend(extract_gpt_messages(mapping, root))

            content = truncate("\n\n".join(lines))
            if len(content) > 100:
                entries.append((content, created))

    print(f"  → {len(entries)} ChatGPT conversations")
    return entries

# ── Insert into Neon ──────────────────────────────────────────────────────────

def insert_entries(entries):
    print(f"\nConnecting to Neon...")
    conn = psycopg2.connect(DB_URL)
    cur  = conn.cursor()

    # Deduplicate against existing entries by checking first 200 chars
    cur.execute("SELECT LEFT(content, 200) FROM omega_memory_entries WHERE content NOT LIKE 'smoke-test%'")
    existing = set(row[0] for row in cur.fetchall())

    inserted = skipped = 0
    for content, created_at in entries:
        key = content[:200]
        if key in existing:
            skipped += 1
            continue
        entry_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO omega_memory_entries (id, content, created_at, source, namespace, domain) VALUES (%s, %s, %s, %s, %s, %s)",
            (entry_id, content, created_at, 'data-export', 'biography', 'identity')
        )
        existing.add(key)
        inserted += 1

        if inserted % 100 == 0:
            conn.commit()
            print(f"  {inserted} inserted so far...")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✓ Done — {inserted} inserted, {skipped} skipped (duplicates)")

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    all_entries = []
    all_entries.extend(load_claude_memories())
    all_entries.extend(load_claude_convos())
    all_entries.extend(load_gpt_convos())

    print(f"\nTotal entries to process: {len(all_entries)}")
    insert_entries(all_entries)
