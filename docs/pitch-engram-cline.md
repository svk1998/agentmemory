# Engram + Cline
### Cline, but it never forgets

---

## Where Cline is today

Cline is a capable AI coding agent living in every developer's editor. But it is **stateless**. Each session begins from zero — no memory of yesterday's decisions, last week's bug fixes, or the conventions the team agreed on. It re-reads context, re-asks settled questions, and re-derives the same conclusions every single time. Knowledge generated in one chat evaporates when the chat closes, and nothing one developer's Cline learns ever reaches another's.

**Today's Cline is brilliant in the moment and amnesiac across time.**

## Where Cline goes with Engram

**Engram** is a persistent, project-scoped, team-shared memory layer that connects to Cline through a single MCP endpoint. With Engram behind it, Cline gains a long-term memory and a shared one:

- It **remembers** architectural decisions, gotchas, and the reasoning behind them — across sessions, indefinitely.
- It **learns** from every bug it fixes and recalls the lesson before repeating the mistake.
- It **shares** — what one engineer's Cline discovers, every engineer's Cline knows.

Same agent, same editor, same workflow. The difference is continuity: **Cline with Engram is brilliant in the moment *and* across time, for the whole team.**

---

## A solid use case: a payments platform team

Picture an 8-person backend team owning a payments service — high stakes, dense domain logic, frequent on-call.

**Without Engram (Cline today):**
> A developer asks Cline to add a refund endpoint. Cline doesn't know the team's hard-won rule that refunds must be idempotent because the gateway silently double-charges on retry. It writes clean-but-wrong code. The bug ships, fires an incident, gets fixed at 2 a.m. Two months later a different developer asks Cline for a *partial* refund endpoint — and Cline, still amnesiac, makes the **same mistake**.

**With Engram (Cline tomorrow):**
> The night the incident is fixed, the engineer's Cline writes a **lesson** to Engram: *"Refund paths must be idempotent — gateway double-charges on retry; key on `refund_request_id`."* Two months later, the second developer asks for the partial-refund endpoint. Before writing a line, their Cline **recalls** that lesson from the shared memory and generates idempotent code on the first try. The 2 a.m. incident never happens twice.

That single saved incident pays for the entire system. Now multiply it across onboarding, architecture decisions, deploy quirks, and naming conventions:

| Scenario | Cline today | Cline + Engram |
|---|---|---|
| New hire's first week | Asks teammates the same questions repeatedly | Cline recalls runbooks, conventions, architecture instantly |
| Senior dev leaves | Tribal knowledge walks out the door | Their captured context stays in the shared brain |
| Recurring class of bug | Repeated every time it's encountered | Recalled and avoided before code is written |
| Cross-service monorepo | Context bleeds between services | Project scoping keeps each service's memory clean |

---

## Architecture

Engram sits beside Cline as an MCP server. Every developer's Cline reads from and writes to one shared, project-scoped memory — with governance and audit built in.

```
   Developer A            Developer B            Developer C
  ┌───────────┐          ┌───────────┐          ┌───────────┐
  │  VS Code  │          │  VS Code  │          │  VS Code  │
  │   Cline   │          │   Cline   │          │   Cline   │
  └─────┬─────┘          └─────┬─────┘          └─────┬─────┘
        │  MCP (recall/save)   │                      │
        └──────────────┬───────┴──────────────────────┘
                       ▼
            ┌──────────────────────────┐
            │      Engram server       │   ← single shared brain
            │  ┌────────────────────┐  │
            │  │  MCP endpoint      │  │   recall · save · lessons
            │  ├────────────────────┤  │
            │  │  Memory engine     │  │   project scoping · dedup
            │  │  Consolidation     │  │   working→episodic→semantic
            │  │  Governance/Audit  │  │   who knew what, purge-on-demand
            │  └────────────────────┘  │
            │  ┌────────────────────┐  │
            │  │  Persistent store  │  │   durable, survives restarts
            │  └────────────────────┘  │
            └──────────────────────────┘
```

**How a request flows:**
1. Developer prompts Cline in VS Code as usual.
2. Before answering, Cline **recalls** relevant memories and lessons for that project from Engram.
3. Cline completes the task with full team context.
4. New decisions, fixes, and lessons are **saved** back to Engram — scoped to the project, available to every teammate's Cline immediately.
5. A consolidation pipeline distills raw notes into durable patterns; every write is audited and can be purged on demand.

---

## The business case

- **Faster onboarding** — Cline gives new hires the team's accumulated context on day one.
- **Knowledge survives turnover** — expertise stays in the shared brain, not in one person's head.
- **Fewer repeated incidents** — one engineer's lesson becomes the whole team's immunity.
- **Lower cost, sharper output** — Cline recalls distilled, relevant memory instead of re-ingesting context every session.

> **In one line:** Keep Cline exactly as your team uses it — and give it a memory, so every session compounds into a shared asset instead of resetting to zero.
