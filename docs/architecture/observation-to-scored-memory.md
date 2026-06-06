# Observation → scored memory: end-to-end pipeline

How a raw agent hook becomes a retention-scored memory in agentmemory.

**Key insight:** an observation is *not* scored directly. It must be **promoted**
into a `Memory` (episodic) or `SemanticMemory` record first — only those are
retention-scored. The bridge from observation to memory is consolidation /
summarize (or `mem::remember` for direct saves).

## Pipeline diagram

```
agent hook
   │  (pubsub topic "agentmemory.observation")
   ▼
event::observation ──► mem::observe ──► KV.observations(sessionId)   [RawObservation]
                            │                    │
                            │  compress          ▼
                            └──────────► CompressedObservation  ──► BM25 + vector index
                                         (searchable, NOT scored)
   ── session stop ──────────────────────────────────────────────────────┐
   ▼                                                                       │
event::session::stopped ──► mem::summarize ──► KV.summaries [SessionSummary]
                                                       │
   ── background cron (every 2h, if enabled) / on-demand ──               │
   ▼                                                                       ▼
mem::consolidate ──────► KV.memories  [episodic Memory]      mem::consolidate-pipeline
  (cluster obs by concept,                  ▲                  ├─ semantic: ≥5 summaries ─► KV.semantic [SemanticMemory]
   LLM → Memory, versioned)                 │                  ├─ procedural: pattern×≥2 ─► KV.procedural
mem::remember ──────────────────────────────┘ (direct save)   ├─ reflect:  mem::reflect clustering
                                                               └─ decay:    strength *= 0.9^periods
   │                                              │
   └──────────────► mem::retention-score ◄────────┘
                         │  scores KV.memories (isLatest) + KV.semantic
                         ▼
                    KV.retentionScores  [RetentionScore: score/salience/decay/boost + tier]
                         │
                         ▼
                    mem::retention-evict (score < 0.15)   +   mem::auto-forget (hourly TTL/contradiction)
```

## Stage 1 — Capture: hook → `mem::observe`

An agent hook publishes to the pubsub topic `agentmemory.observation`. The
durable subscriber `event::observation` (`src/triggers/events.ts:38-45`)
forwards to `mem::observe`.

Inside `mem::observe` (`src/functions/observe.ts:43`):
1. **Validate** payload — sessionId/hookType/timestamp required (`observe.ts:46`).
2. **Dedup** — hash of `(sessionId, toolName, tool_input)`; identical repeats
   short-circuit (`observe.ts:63-78`).
3. **Privacy** — `stripPrivateData()` scrubs secrets from raw JSON
   (`observe.ts:80-87`).
4. **Build `RawObservation`** — extracts `toolName/toolInput/toolOutput` for tool
   hooks, `userPrompt` for prompts, and any image (`observe.ts:89-122`).
5. Under a per-session lock (`observe.ts:126`): enforce
   `maxObservationsPerSession`, inherit `agentId`, persist image to disk if
   present, then **write the raw obs** via
   `kv.set(KV.observations(sessionId), obsId, raw)` (`observe.ts:179`).
6. **Bump the session** `observationCount`/`updatedAt` (or implicitly create the
   session) (`observe.ts:222-275`), and **stream** the event to the viewer.

## Stage 2 — Compress (still an observation, now searchable)

Two paths (`observe.ts:281-327`):
- **Default — synthetic, zero-LLM** (`buildSyntheticCompression`,
  `src/functions/compress-synthetic.ts:76`): heuristics infer `type` from
  tool/hook name, extract files, truncate a narrative. Produces a
  `CompressedObservation` with **`importance: 5`, `confidence: 0.3`** baked in.
  Overwrites the obs row, then is **added to the BM25 + vector index**
  (`observe.ts:298-304`).
- **Opt-in — LLM** (`AGENTMEMORY_AUTO_COMPRESS=true`): triggers `mem::compress`
  for a richer summary.

At this point the observation is fully searchable but has **no retention
score** — the scorer never looks at `KV.observations`.

## Stage 3 — Summarize (session stop)

On `event::session::stopped` (`events.ts:47`), `mem::summarize` rolls the
session's observations into a **`SessionSummary`** → `KV.summaries`
(`src/functions/summarize.ts:359`). Optionally fires graph-extraction and
slot-reflect.

## Stage 4 — Promotion into scorable memory (the bridge)

Where an observation actually *becomes* a memory. Two consolidators, run by the
2-hour cron (`src/index.ts:582-590`, gated on `CONSOLIDATION_ENABLED` + an LLM
provider) or on demand:

- **`mem::consolidate` → episodic `Memory`** (`src/functions/consolidate.ts`):
  groups observations by **concept** (clusters of ≥3, `consolidate.ts:122-124`),
  sends the top-8 by importance to the LLM, parses into a `Memory`, writes to
  `KV.memories` (`consolidate.ts:218`). If a same-title memory exists it
  **evolves** it: old marked `isLatest=false`, new version with `version++`,
  `parentId`, `supersedes[]`, `sourceObservationIds` (`consolidate.ts:175-206`).
  This is the v1→v2 chain behind the dashboard's "latest versions" count.
- **`mem::consolidate-pipeline`** (`src/functions/consolidation-pipeline.ts:50`):
  four tiers —
  - **semantic**: ≥5 summaries → LLM fact-merge → `SemanticMemory` with parsed
    `confidence` → `KV.semantic` (lines 63-121); duplicate facts bump
    `accessCount` and take `max(confidence)`.
  - **procedural**: `Memory` of `type:"pattern"` seen ≥2× → `ProceduralMemory`
    (lines 150-229).
  - **reflect**: delegates to `mem::reflect`.
  - **decay**: mutates `strength *= 0.9^periods` on semantic/procedural after
    `decayDays` idle (lines 21-43, 231-248).

**Direct shortcut:** `mem::remember` (`src/functions/remember.ts:128`) writes a
`Memory` straight to `KV.memories` with its own supersession logic — this is what
the `memory_remember` MCP tool and `/agentmemory/remember` use, bypassing the
observation pipeline entirely.

## Stage 5 — Scoring

`mem::retention-score` (`src/functions/retention.ts:127`) iterates
**`KV.memories` (only `isLatest`) + `KV.semantic`** (`retention.ts:135-139,
162-235`) and for each computes:

```
salience            = typeWeight (or max(typeWeight, confidence)) + min(0.2, accessCount×0.02)
temporalDecay       = exp(−0.01 · ageDays)
reinforcementBoost  = 0.3 · Σ(1 / daysSinceAccess)   over the access log
score               = min(1, salience × temporalDecay + reinforcementBoost)
```

It writes a `RetentionScore` row per memory to `KV.retentionScores`
(`retention.ts:241-245`) and buckets them: **hot ≥0.7, warm ≥0.4, cold ≥0.15,
evictable <0.15**.

## Stage 6 — Cleanup

- `mem::retention-evict` deletes memories scoring below cold and removes their
  index entries (`retention.ts:292`).
- `mem::auto-forget` (hourly, `index.ts:539`) independently handles TTL expiry,
  contradiction collapse (Jaccard >0.9), and stale low-value observations.

## Two things not to confuse

1. **`KV.observations` vs `KV.memories`/`KV.semantic`** are different tiers.
   Search hits observations directly; only memories get retention scores. The
   bridge is consolidation/summarize (or `mem::remember`).
2. **Two separate "decay" mechanisms:**
   - *Strength decay* (`consolidation-pipeline.ts` `applyDecay`) — `0.9^periods`,
     **mutates** the stored `strength` field of semantic/procedural memories.
   - *Retention-score decay* (`retention.ts`) — `exp(−λt)`, a **computed,
     non-destructive** score used for tiering/eviction.

## Trigger timing

| Stage | Trigger | Cadence |
|-------|---------|---------|
| observe | pubsub `agentmemory.observation` | per hook |
| summarize | `event::session::stopped` | session end |
| consolidate-pipeline | cron | every 2h (`CONSOLIDATION_INTERVAL_MS`, if enabled) |
| retention-score | on-demand (dashboard/operator) | not on a default timer |
| auto-forget | cron | hourly |
| lesson/insight decay | cron | daily |
