# agentmemory — Technical Presentation Design Spec

**Date:** 2026-06-03
**Format:** PPTX (python-pptx)
**Audience:** Technical engineers (developers, DevEx teams)
**Style:** Light/minimal — white background, clean typography, muted accents
**Depth:** Deep dive (~28 slides)
**Code snippets:** Yes — hook config, MCP tool calls, privacy filter examples

---

## Generation Method

- Tool: `python-pptx` (Python library)
- Output: `agentmemory-presentation.pptx` at repo root
- Theme: White background (`#FFFFFF`), dark text (`#1A1A1A`), accent color (`#2563EB` blue), code boxes in light grey (`#F3F4F6`) with monospace font

---

## Slide Structure (28 slides)

### Section 1 — The Problem (Slides 1–5)

**Slide 1 — Title**
- Title: `agentmemory`
- Subtitle: `Persistent Memory for AI Coding Agents`
- Footer: `github.com/rohitg00/agentmemory`

**Slide 2 — The Amnesia Problem**
- Heading: `Every session starts blank`
- Body: AI coding agents have no memory between sessions. Every conversation begins from zero — no project history, no preferences, no decisions.
- Visual: Simple before/after showing Session 1 vs Session 2 with empty context

**Slide 3 — What You Re-explain Every Session**
- Heading: `Re-explaining costs time and tokens`
- Bullet list:
  - Project architecture and module boundaries
  - Why we chose X library over Y (e.g., `jose` vs `jsonwebtoken`)
  - Coding conventions and team preferences
  - Bugs already fixed and why
  - Auth implementation details (`src/middleware/auth.ts`)
  - Deployment patterns and environment constraints

**Slide 4 — The Static File Trap**
- Heading: `CLAUDE.md / .cursorrules hit a wall`
- Bullets:
  - Manual to maintain — you write it, you keep it current
  - Truncated at ~200 lines — everything after is invisible
  - No retrieval — entire file loaded whether relevant or not
  - Goes stale — doesn't update as the codebase evolves
  - Single-agent — not shared across Copilot, Cursor, Codex

**Slide 5 — Existing Solutions Fall Short**
- Heading: `Nothing fits the coding agent use case`
- 3-column layout:
  - **mem0** — requires manual `add()` calls; no automatic capture
  - **Letta/MemGPT** — full runtime replacement; framework lock-in
  - **Per-agent files** — CLAUDE.md, .cursorrules; not cross-agent; scale poorly

---

### Section 2 — Introducing agentmemory (Slides 6–8)

**Slide 6 — What Is agentmemory?**
- Heading: `Persistent memory engine for every AI agent`
- 4 key properties (icon + text):
  - **Automatic** — 12 lifecycle hooks, zero manual `add()` calls
  - **Cross-agent** — Claude Code, Copilot CLI, Cursor, Gemini CLI, Codex, and more
  - **Smart retrieval** — hybrid BM25 + Vector + Graph search, 95.2% R@5
  - **Zero dependencies** — SQLite only, no external DB

**Slide 7 — How It Fixes the Problem**
- Heading: `Capture → Consolidate → Retrieve → Inject`
- 4-step flow (horizontal):
  1. **Capture** — hooks fire on every tool use, auto-store observations
  2. **Consolidate** — 4-tier memory model (Working → Episodic → Semantic → Procedural)
  3. **Retrieve** — triple-stream hybrid search at session start
  4. **Inject** — ~1,900 tokens of relevant context, token-budgeted

**Slide 8 — Quick Start**
- Heading: `Up and running in 4 commands`
- Code block:
```bash
npm install -g @agentmemory/agentmemory
agentmemory                          # start server on :3111
agentmemory demo                     # seed sample sessions, prove recall
agentmemory connect claude-code      # wire MCP into Claude Code
```

---

### Section 3 — Architecture Deep Dive (Slides 9–18)

**Slide 9 — System Architecture Overview**
- Heading: `Component Architecture`
- ASCII/text diagram showing:
  - Top: Agent Ecosystem (Claude Code, Copilot CLI, Cursor, Codex, Gemini CLI)
  - Middle: 3 integration points — Hooks (12), MCP Server (53 tools), REST API (:3111)
  - Core: agentmemory Engine — Capture → Processing → Search → Management layers
  - Bottom: SQLite DB, Real-time Viewer (:3113), iii Console (:3114)

**Slide 10 — The 12 Hooks — What Gets Captured**
- Heading: `12 lifecycle hooks fire automatically`
- Table (Hook | What it captures):
  - `SessionStart` — Project path, session ID
  - `UserPromptSubmit` — User prompts (privacy-filtered)
  - `PreToolUse` — File access patterns + enriched context
  - `PostToolUse` — Tool name, input, output
  - `PostToolUseFailure` — Error context and debugging info
  - `PreCompact` — Re-injects memory before compaction
  - `SubagentStart/Stop` — Nested agent lifecycle
  - `Stop` / `SessionEnd` — End-of-session summary + knowledge graph extraction

**Slide 11 — Memory Capture Pipeline**
- Heading: `PostToolUse → stored, compressed, indexed`
- Vertical pipeline diagram:
  1. PostToolUse hook fires
  2. SHA-256 dedup (5-minute window) — prevents duplicate captures
  3. Privacy filter — strips API keys, secrets, `<private>` tags
  4. Store raw observation → SQLite
  5. LLM compress → structured facts + semantic concepts + narrative
  6. Embed → vector (6 providers, fallback chain)
  7. Index → BM25 shards + HNSW vector index

**Slide 12 — The 4-Tier Memory Model**
- Heading: `Inspired by human memory consolidation`
- 4-row table (Tier | What | Analogy | Lifecycle):
  - **Working** | Raw tool observations | Short-term | 5-min session window
  - **Episodic** | Compressed session summaries | "What happened" | Per-session stories
  - **Semantic** | Extracted facts and patterns | "What I know" | Distilled knowledge
  - **Procedural** | Workflows and decision patterns | "How to do it" | Recurring processes
- Footer note: Borrowed from neuroscience sleep consolidation research

**Slide 13 — Ebbinghaus Decay & Memory Strengthening**
- Heading: `Memories decay and strengthen like human memory`
- Two bullets:
  - **Decay** — old observations lose relevance over time (Ebbinghaus forgetting curve)
  - **Strengthening** — frequently recalled memories become more accessible
- Secondary bullets:
  - Contradictions detected and resolved automatically
  - Stale memories auto-evict when disk quota is reached (`--quota` flag)

**Slide 14 — Storage — SQLite, Zero External DBs**
- Heading: `Everything in a single SQLite file`
- Bullets:
  - Database: `~/.agentmemory/memory.db`
  - Schema: observations + compressed facts + embeddings + decay weights + citation provenance
  - Index: sharded BM25 + HNSW vector with manifest commit/rollback for safety
  - Multi-agent: namespaced storage (`project:agent1`, `project:agent2`)
  - No Qdrant, no pgvector, no Postgres — ships and works offline

**Slide 15 — Triple-Stream Hybrid Search**
- Heading: `BM25 + Vector + Graph — each finds what the others miss`
- 3-column layout:
  - **BM25 (Keyword)**
    - Stemmed keyword matching
    - Synonym expansion
    - CJK/Cyrillic/Hebrew support
    - Best for: exact terms, file names, error messages
  - **Vector (Semantic)**
    - Cosine similarity on embeddings
    - Local (all-MiniLM-L6-v2, free) or OpenAI/Gemini
    - Best for: conceptual queries, paraphrased ideas
  - **Graph (Knowledge)**
    - Entity matching + BFS traversal
    - Links adjacent decisions
    - Best for: "why did we choose X?" chains

**Slide 16 — RRF Fusion**
- Heading: `Reciprocal Rank Fusion combines all 3 streams`
- Steps:
  1. Each stream returns Top-10 results with ranks
  2. Normalize: `RRF score = Σ 1/(k + rank_i)` where k=60
  3. Sort by combined score
  4. Diversify: max 3 results per session (avoid repetition)
  5. Return Top-5 memories
- Result: 95.2% R@5 on LongMemEval-S

**Slide 17 — Session Start — Injection Flow**
- Heading: `What happens when you open a new session`
- Sequential steps:
  1. `SessionStart` hook fires
  2. Load project profile (top concepts, files, patterns)
  3. Run hybrid search against all stored memories
  4. Token budget enforcement (default: 2,000 tokens max)
  5. Inject top-N relevant memories into agent system prompt
  6. Agent begins with full context — no re-explaining needed

**Slide 18 — Multi-Agent Coordination**
- Heading: `Multiple agents, one shared memory`
- Bullets:
  - **Leases** — exclusive action locks prevent race conditions when 2 agents touch the same task
  - **Signals** — agents communicate state changes without polling
  - **Namespaced storage** — shared team memory + private per-agent observations
  - **Mesh sync** — one agent hands off work to another with full memory context
- Use case: Claude Code captures implementation decisions; Copilot CLI retrieves them mid-PR review

---

### Section 4 — Code & Integration (Slides 19–21)

**Slide 19 — Hook Config in Practice**
- Heading: `Wired into Claude Code settings.json`
- Code block (JSON):
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "agentmemory hook post-tool-use"
      }]
    }],
    "SessionEnd": [{
      "hooks": [{
        "type": "command",
        "command": "agentmemory hook session-end"
      }]
    }]
  }
}
```

**Slide 20 — MCP Tool Call Example**
- Heading: `53 MCP tools — smart search in action`
- Code block (tool call + result):
```json
// Tool call
{
  "tool": "memory_smart_search",
  "input": {
    "query": "why did we choose jose over jsonwebtoken",
    "limit": 5
  }
}

// Result (top memory)
{
  "content": "Session 4: Chose jose middleware (src/middleware/auth.ts)
               over jsonwebtoken — jose works on the Edge runtime,
               jsonwebtoken does not. Decision made 2026-01-14.",
  "score": 0.94,
  "tier": "semantic",
  "session": 4
}
```

**Slide 21 — Privacy Filter in Action**
- Heading: `Secrets never reach storage`
- Two code blocks side by side:

Before (raw tool output):
```
OPENAI_API_KEY=sk-proj-abc123...
DATABASE_URL=postgres://user:pass@host/db
Token: Bearer eyJhbGc...
```

After (privacy-filtered, stored):
```
OPENAI_API_KEY=[REDACTED]
DATABASE_URL=[REDACTED]
Token: [REDACTED]
```
- Bullet: Also strips `<private>...</private>` tagged content from prompts

---

### Section 5 — Benchmarks (Slides 22–24)

**Slide 22 — LongMemEval-S Results**
- Heading: `95.2% recall on academic benchmark (ICLR 2025)`
- Table (System | R@5 | R@10 | MRR):
  - agentmemory hybrid | **95.2%** | **98.6%** | **88.2%**
  - BM25-only fallback | 86.2% | 94.6% | 71.5%
  - Mem0 | 68.5% | — | —
  - Letta/MemGPT | 83.2% | — | —
- Footer: LongMemEval-S: 500 questions, ~115K tokens/question, tests knowledge updates / multi-session reasoning / temporal reasoning

**Slide 23 — Token Efficiency**
- Heading: `92% fewer tokens — from $500/yr to $0–$10/yr`
- Table (Approach | Tokens/yr | Cost/yr):
  - Paste full history | 19.5M+ | Impossible (exceeds context)
  - LLM-summarized | ~650K | ~$500
  - agentmemory (API embeddings) | ~170K | ~$10
  - agentmemory (local embeddings) | ~170K | **$0**
- Footer: Based on 240 observations/yr; local uses all-MiniLM-L6-v2 in-process

**Slide 24 — In-house Benchmark**
- Heading: `coding-agent-life-v1: 100% hit rate`
- Context: 15 Claude Code sessions over 10 days on a real Rust CLI project
- Table (System | Hit Rate | R@5 | p50 Latency):
  - agentmemory hybrid | **100%** | **1.000** | 14ms
  - grep baseline | 96.7% | 0.967 | 0ms
- Key insight bullet: Temporal queries (date-based) — grep finds 1 of 2 gold sessions; agentmemory finds both

---

### Section 6 — Competitive Comparison & Roadmap (Slides 25–28)

**Slide 25 — vs Native Claude Code Memory**
- Heading: `Built-in memory vs agentmemory`
- Side-by-side comparison table:
  | Feature | Claude Code native | agentmemory |
  |---|---|---|
  | Works cross-agent | No | Yes (15+ agents) |
  | Retrieval | Loads full MEMORY.md | Hybrid search (R@5 95.2%) |
  | Scale | Degrades past 200 lines | Stays efficient |
  | Auto-capture | No (manual write) | Yes (12 hooks) |
  | Token efficiency | Grows unbounded | ~1,900 tokens/session |
  | Cross-project | No | Yes |
  | Multi-agent coordination | No | Leases + signals |
  | Real-time viewer | No | Yes (:3113) |

**Slide 26 — Full Competitive Matrix**
- Heading: `How agentmemory compares`
- Feature matrix table across: agentmemory | mem0 | Letta | CLAUDE.md
- 12 features: retrieval R@5, auto-capture, search type, multi-agent, lock-in, external deps, lifecycle, token efficiency, viewer, self-hosted, MCP tools, open source

**Slide 27 — Roadmap to v1.0**
- Heading: `Q2 2026 → Q1 2027`
- 4-column timeline table:
  | Q2 2026 | Q3 2026 | Q4 2026 | Q1 2027 |
  |---|---|---|---|
  | Multimodal memory (images) | Slack/Discord connector | SSO gateway (OIDC) | REST + MCP surface freeze |
  | Filesystem connector | OpenSSF Scorecard | Audit log export | LTS branch v1.x |
  | OpenCode hooks (22) | Additional maintainers | RBAC on memory scope | Foundation membership |
  | Governance baseline | | Security audit | |

**Slide 28 — Summary**
- Heading: `5 reasons engineers choose agentmemory`
- 5 bold bullets:
  1. **Zero manual effort** — 12 hooks capture everything automatically
  2. **Works everywhere** — single memory store across 15+ AI agents
  3. **Highest recall** — 95.2% R@5 via BM25 + Vector + Graph hybrid
  4. **Near-zero cost** — $0/yr with local embeddings, 92% token savings
  5. **Self-hosted** — SQLite only, no external DBs, runs offline
- Footer CTA: `npm install -g @agentmemory/agentmemory`

---

## Visual Style Spec

- **Background:** `#FFFFFF` (white)
- **Title text:** `#1A1A1A` (near-black), 32pt, bold
- **Body text:** `#374151` (dark grey), 16pt
- **Accent / highlight:** `#2563EB` (blue) for headings, section dividers
- **Code boxes:** `#F3F4F6` background, `#111827` text, `Courier New` 12pt
- **Table header:** `#2563EB` background, white text
- **Table rows:** alternating `#F9FAFB` / `#FFFFFF`
- **Section divider slides:** `#2563EB` background, white title

## Output

- File: `agentmemory-presentation.pptx` (repo root)
- Dimensions: 13.33" × 7.5" (standard widescreen 16:9)
