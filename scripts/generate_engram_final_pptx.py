"""Generate the *Engram + Cline* explainer deck (final, short version).

A lean, explanatory deck — not a sales pitch. It shows what Cline is today,
what Engram adds (shared memory), and four concrete use cases where a team
working on a shared memory benefits, plus a team-lead "focus map" view.

Reuses the design system (palette, typography, components) from
``generate_pptx.py`` — same look-and-feel, Engram branding.

  1. Title
  2. Cline today (stateless / amnesiac)
  3. With Engram (remember / learn / share)
  4. Use case — recurring bug/incident
  5. Use case — new-hire onboarding
  6. Use case — senior dev leaves (knowledge continuity)
  7. Use case — async / timezone handoff
  8. Team activity & focus map
  9. Token-cost reduction (recall vs re-ingestion)
 10. How it works + summary
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_pptx import (  # noqa: E402
    Presentation, Inches, Pt, Emu, RGBColor,
    PP_ALIGN, MSO_ANCHOR, MSO_SHAPE,
    SLIDE_W, SLIDE_H,
    BG, SURFACE, CARD, BORDER, BORDER_STR,
    INK, INK_SOFT, INK_MUTED, INK_FAINT, INVERSE,
    PRIMARY, BRAND, ACCENT, PRIMARY_PALE, PRIMARY_BG,
    GOLD, GOLD_PALE, SUCCESS, SUCCESS_PALE, ERROR, ERROR_PALE, PURPLE, TEAL,
    F_DISPLAY, F_TITLE, F_BODY, F_MONO,
    shape, rect, rounded, line, txt, multi_txt,
    add_slide, card, stat_badge, icon_circle, num_badge,
    _arch_arrow,
)

WORDMARK = "Engram"
TOTAL = 10


def C_LIGHT():
    return RGBColor(0xCB, 0xD5, 0xE1)


# ════════════════════════════════════════════════════════════════════════════
# Engram-branded chrome
# ════════════════════════════════════════════════════════════════════════════

def chrome(slide, page_num, title, eyebrow=None, subtitle=None, accent=BRAND):
    rect(slide, 0, 0, Inches(0.18), SLIDE_H, fill=accent)
    txt(slide, Inches(11.0), Inches(0.35), Inches(2.2), Inches(0.35),
        WORDMARK + "  ×  Cline", size=11, color=INK_MUTED, bold=True,
        font=F_BODY, align=PP_ALIGN.RIGHT)

    if eyebrow:
        rounded(slide, Inches(0.7), Inches(0.4), Inches(2.6), Inches(0.32),
                radius=0.5, fill=PRIMARY_BG, line=None)
        txt(slide, Inches(0.7), Inches(0.42), Inches(2.6), Inches(0.3),
            eyebrow.upper(), size=10, bold=True, color=BRAND,
            align=PP_ALIGN.CENTER, font=F_TITLE)

    title_top = Inches(0.88) if eyebrow else Inches(0.55)
    txt(slide, Inches(0.7), title_top, Inches(12.0), Inches(0.62),
        title, size=28, bold=True, color=INK, font=F_TITLE, line_spacing=1.0)

    if subtitle:
        txt(slide, Inches(0.7), title_top + Inches(0.66), Inches(12.0), Inches(0.4),
            subtitle, size=15, color=INK_MUTED, font=F_BODY, line_spacing=1.15)

    sub_off = Inches(1.10) if subtitle else Inches(0.7)
    line(slide, Inches(0.7), title_top + sub_off, Inches(0.6), 0,
         color=BRAND, weight=2.5)

    rect(slide, 0, Inches(7.32), SLIDE_W, Inches(0.18), fill=SURFACE)
    txt(slide, Inches(0.4), Inches(7.34), Inches(6), Inches(0.16),
        "Engram — shared memory for AI coding agents",
        size=9, color=INK_FAINT, font=F_BODY)
    txt(slide, Inches(7.0), Inches(7.34), Inches(5.9), Inches(0.16),
        f"{page_num:02d}  /  {TOTAL:02d}",
        size=9, color=INK_FAINT, font=F_BODY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# Reusable two-column "Cline today vs With Engram" use-case body
# ════════════════════════════════════════════════════════════════════════════

def usecase_body(slide, today_lines, engram_lines, takeaway):
    """Two side-by-side cards + a takeaway strip. Lines are (glyph, text)."""
    col_w = Inches(5.85)
    col_h = Inches(4.05)
    col_t = Inches(2.35)

    cols = [
        ("Cline today", today_lines, ERROR, "✕"),
        ("Cline + Engram", engram_lines, SUCCESS, "✓"),
    ]
    for ci, (label, lines, color, _badge) in enumerate(cols):
        x = Inches(0.7) + ci * Inches(6.1)
        card(slide, x, col_t, col_w, col_h, accent=color, accent_side='top')
        txt(slide, x + Inches(0.35), col_t + Inches(0.28), col_w - Inches(0.6),
            Inches(0.4), label, size=15, bold=True, color=color, font=F_TITLE)
        for i, (glyph, item) in enumerate(lines):
            y = col_t + Inches(0.95) + i * Inches(0.92)
            icon_circle(slide, x + Inches(0.55), y + Inches(0.2),
                        Inches(0.15), color, glyph, INVERSE, 10)
            txt(slide, x + Inches(0.9), y, col_w - Inches(1.15), Inches(0.85),
                item, size=12.5, color=INK_SOFT, line_spacing=1.25)

    strip_t = col_t + col_h + Inches(0.2)
    rounded(slide, Inches(0.7), strip_t, Inches(11.93), Inches(0.42),
            radius=0.4, fill=PRIMARY_BG)
    txt(slide, Inches(0.7), strip_t + Inches(0.07), Inches(11.93), Inches(0.3),
        takeaway, size=12.5, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)


# ════════════════════════════════════════════════════════════════════════════
# Slides
# ════════════════════════════════════════════════════════════════════════════

def slide_01_title(prs):
    s = add_slide(prs)
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=BG)
    rect(s, 0, 0, Inches(0.18), SLIDE_H, fill=BRAND)

    for i in range(12):
        for j in range(6):
            x = Inches(8.5) + i * Inches(0.4)
            y = Inches(0.5) + j * Inches(0.4)
            shape(s, MSO_SHAPE.OVAL, x, y, Inches(0.05), Inches(0.05),
                  fill=PRIMARY_PALE, line=None)

    rounded(s, Inches(0.7), Inches(1.95), Inches(3.0), Inches(0.4),
            radius=0.5, fill=PRIMARY_BG, line=None)
    txt(s, Inches(0.7), Inches(1.99), Inches(3.0), Inches(0.35),
        "SHARED MEMORY FOR YOUR TEAM", size=10, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)

    txt(s, Inches(0.6), Inches(2.65), Inches(12), Inches(1.5),
        "Engram", size=88, color=INK, font=F_DISPLAY, line_spacing=1.0)
    txt(s, Inches(0.72), Inches(4.15), Inches(12), Inches(0.6),
        "memory for Cline", size=26, color=BRAND, font=F_TITLE)

    txt(s, Inches(0.72), Inches(4.95), Inches(12), Inches(0.7),
        "Cline, but it never forgets.",
        size=22, color=INK_SOFT, font=F_BODY, italic=True, line_spacing=1.1)

    rect(s, Inches(0.72), Inches(5.7), Inches(0.8), Inches(0.06), fill=BRAND)
    txt(s, Inches(0.72), Inches(5.95), Inches(11), Inches(0.7),
        "A persistent, project-scoped memory every developer's Cline reads from and writes to.",
        size=14, color=INK_MUTED, font=F_BODY, line_spacing=1.3)

    rect(s, 0, Inches(7.0), SLIDE_W, Inches(0.5), fill=SURFACE)
    txt(s, Inches(0.7), Inches(7.12), Inches(8), Inches(0.3),
        "Persistent · Project-scoped · Team-shared",
        size=11, color=INK_MUTED, font=F_BODY)
    return s


def slide_02_today(prs):
    s = add_slide(prs)
    chrome(s, 2, "Cline Today",
           eyebrow="The Problem",
           subtitle="Cline is brilliant in the moment — and forgets everything between sessions.")

    # left: a short narrative; right: the "forgets" list
    lx = Inches(0.7)
    lw = Inches(5.7)
    lt = Inches(2.45)
    card(s, lx, lt, lw, Inches(4.2), accent=INK_MUTED, accent_side='top')
    multi_txt(s, lx + Inches(0.4), lt + Inches(0.4), lw - Inches(0.8), Inches(3.5), [
        {'text': "Every session starts from zero.", 'size': 17, 'bold': True,
         'color': INK, 'font': F_TITLE, 'line_spacing': 1.2},
        {'text': "Cline re-reads context, re-asks settled questions, and "
                 "re-derives the same conclusions every time.", 'size': 13,
         'color': INK_SOFT, 'space_before': 12, 'line_spacing': 1.4},
        {'text': "Knowledge from one chat evaporates when it closes — and "
                 "nothing one developer's Cline learns ever reaches another's.",
         'size': 13, 'color': INK_SOFT, 'space_before': 12, 'line_spacing': 1.4},
        {'text': "It's stateless. Amnesiac across time, and isolated per developer.",
         'size': 13, 'bold': True, 'color': ERROR, 'space_before': 14,
         'line_spacing': 1.4},
    ])

    rx = Inches(6.6)
    rw = Inches(6.03)
    card(s, rx, lt, rw, Inches(4.2), accent=ERROR, accent_side='top')
    txt(s, rx + Inches(0.4), lt + Inches(0.35), rw - Inches(0.8), Inches(0.4),
        "What Cline can't remember tomorrow", size=14, bold=True,
        color=ERROR, font=F_TITLE)
    forgets = [
        "Why we made the refund flow idempotent",
        "How this service gets deployed",
        "The naming conventions we agreed on",
        "That this exact bug was hit before",
        "What a teammate's Cline figured out yesterday",
    ]
    for i, item in enumerate(forgets):
        y = lt + Inches(0.95) + i * Inches(0.62)
        icon_circle(s, rx + Inches(0.6), y + Inches(0.16), Inches(0.15),
                    INK_MUTED, "?", INVERSE, 11)
        txt(s, rx + Inches(0.95), y + Inches(0.02), rw - Inches(1.3),
            Inches(0.4), item, size=12.5, color=INK_SOFT)


def slide_03_with_engram(prs):
    s = add_slide(prs)
    chrome(s, 3, "Cline With Engram",
           eyebrow="The Idea",
           subtitle="One MCP endpoint gives every developer's Cline a long-term, shared memory.")

    props = [
        ("⟳", "Remember",
         "Architecture decisions, gotchas, and the reasoning behind them — kept across sessions, indefinitely.",
         BRAND),
        ("✦", "Learn",
         "Every bug Cline fixes becomes a lesson. It recalls the lesson before it can repeat the mistake.",
         SUCCESS),
        ("⇄", "Share",
         "What one engineer's Cline discovers, every engineer's Cline knows — instantly, team-wide.",
         PURPLE),
    ]

    cw = Inches(3.85)
    ch = Inches(3.3)
    ct = Inches(2.35)
    gap = Inches(0.19)

    for i, (glyph, title_, desc, color) in enumerate(props):
        x = Inches(0.7) + i * (cw + gap)
        card(s, x, ct, cw, ch, accent=color, accent_side='top')
        icon_circle(s, x + cw / 2, ct + Inches(0.95),
                    Inches(0.5), color, glyph, INVERSE, 26)
        txt(s, x, ct + Inches(1.55), cw, Inches(0.5),
            title_, size=22, bold=True, color=INK, font=F_TITLE,
            align=PP_ALIGN.CENTER)
        txt(s, x + Inches(0.35), ct + Inches(2.15), cw - Inches(0.7), Inches(1.0),
            desc, size=12.5, color=INK_MUTED, align=PP_ALIGN.CENTER,
            line_spacing=1.4)

    rounded(s, Inches(0.7), Inches(5.95), Inches(11.93), Inches(0.95),
            radius=0.04, fill=PRIMARY_BG)
    txt(s, Inches(0.9), Inches(6.08), Inches(11.6), Inches(0.35),
        "SAME AGENT, SAME EDITOR, SAME WORKFLOW", size=10, bold=True,
        color=BRAND, font=F_TITLE)
    txt(s, Inches(0.9), Inches(6.38), Inches(11.6), Inches(0.45),
        "The only difference is continuity — every session compounds into a shared team asset instead of resetting to zero.",
        size=14, color=INK, font=F_BODY)


def slide_04_usecase_incident(prs):
    s = add_slide(prs)
    chrome(s, 4, "One Fix, Remembered Forever",
           eyebrow="Use Case · Recurring Bug",
           subtitle="A bug fixed once shouldn't cost the team twice.")
    usecase_body(
        s,
        today_lines=[
            ("✕", "A dev asks Cline for a refund endpoint. Cline doesn't know refunds must be idempotent — the gateway double-charges on retry."),
            ("✕", "Clean-but-wrong code ships. An incident fires at 2 a.m."),
            ("✕", "Months later another dev asks for a partial refund — and Cline makes the exact same mistake."),
        ],
        engram_lines=[
            ("✓", "The night it's fixed, Cline saves the lesson to Engram: refund paths must be idempotent."),
            ("✓", "Months later, before writing a line, the next dev's Cline recalls it."),
            ("✓", "It writes correct code on the first try. The incident never repeats."),
        ],
        takeaway="One captured lesson immunizes every developer's Cline against the same class of bug.",
    )


def slide_05_usecase_onboarding(prs):
    s = add_slide(prs)
    chrome(s, 5, "Productive on Day One",
           eyebrow="Use Case · Onboarding",
           subtitle="New hires start with the team's context, not a blank slate.")
    usecase_body(
        s,
        today_lines=[
            ("✕", "A new engineer spends two weeks pinging teammates: how do we deploy? what's the convention? why is this split this way?"),
            ("✕", "Cline can't help — it knows none of the team's history."),
            ("✕", "Ramp-up burns senior engineers' time too, one interruption at a time."),
        ],
        engram_lines=[
            ("✓", "Their Cline recalls the team's runbooks, conventions, and architecture decisions instantly."),
            ("✓", "The new hire asks Cline what they'd have asked a senior — without interrupting anyone."),
            ("✓", "They ship a real change in days, not weeks."),
        ],
        takeaway="Onboarding context is recalled on demand, not re-explained by hand.",
    )


def slide_06_usecase_busfactor(prs):
    s = add_slide(prs)
    chrome(s, 6, "Knowledge That Doesn't Walk Out",
           eyebrow="Use Case · Knowledge Continuity",
           subtitle="When someone leaves, their context stays with the team.")
    usecase_body(
        s,
        today_lines=[
            ("✕", "The one engineer who understood the billing edge-cases gives notice."),
            ("✕", "Their reasoning lived in their head and their private chats."),
            ("✕", "Two weeks later it's gone — the team inherits the code but not the why."),
        ],
        engram_lines=[
            ("✓", "Every decision and gotcha that engineer's Cline captured is already in the shared brain."),
            ("✓", "After they leave, the team's Cline still recalls why the edge-cases work the way they do."),
            ("✓", "The bus factor stops being a single point of failure."),
        ],
        takeaway="The shared brain outlives any single contributor.",
    )


def slide_07_usecase_handoff(prs):
    s = add_slide(prs)
    chrome(s, 7, "One Continuous Brain, Across the Clock",
           eyebrow="Use Case · Async Handoff",
           subtitle="Work handed off between timezones doesn't start cold.")
    usecase_body(
        s,
        today_lines=[
            ("✕", "A dev in IST ends the day mid-decision on a tricky migration."),
            ("✕", "A teammate in EST picks it up hours later and re-derives the context from scratch."),
            ("✕", "Sometimes they choose a different path that later has to be reconciled."),
        ],
        engram_lines=[
            ("✓", "The first dev's decisions and half-finished reasoning are saved to Engram."),
            ("✓", "The second dev's Cline recalls exactly where things stood and continues."),
            ("✓", "No cold start, no conflicting rework — the handoff is seamless."),
        ],
        takeaway="The team works as one continuous brain, around the clock.",
    )


def slide_08_focus_map(prs):
    s = add_slide(prs)
    chrome(s, 8, "See Where the Team's Effort Is Going",
           eyebrow="Team View",
           subtitle="A live map of what the team's agents are working on — for planning, not monitoring.")

    # ── Left panel: focus areas (horizontal bars) ──
    lx = Inches(0.7)
    lw = Inches(6.0)
    lt = Inches(2.35)
    lh = Inches(3.95)
    card(s, lx, lt, lw, lh, accent=BRAND, accent_side='top')
    txt(s, lx + Inches(0.4), lt + Inches(0.3), lw - Inches(0.8), Inches(0.35),
        "Focus areas this sprint", size=14, bold=True, color=INK, font=F_TITLE)

    areas = [
        ("payments service", 0.92, BRAND),
        ("onboarding / docs", 0.64, SUCCESS),
        ("billing edge-cases", 0.48, PURPLE),
        ("infra & deploy", 0.33, GOLD),
        ("internal tooling", 0.20, TEAL),
    ]
    bar_x = lx + Inches(0.4)
    bar_w_max = lw - Inches(0.8)
    for i, (name, frac, color) in enumerate(areas):
        y = lt + Inches(0.95) + i * Inches(0.58)
        txt(s, bar_x, y, bar_w_max, Inches(0.25),
            name, size=11.5, bold=True, color=INK_SOFT, font=F_BODY)
        track_y = y + Inches(0.28)
        rounded(s, bar_x, track_y, bar_w_max, Inches(0.16),
                radius=0.5, fill=SURFACE, line=None)
        rounded(s, bar_x, track_y, Emu(int(bar_w_max * frac)), Inches(0.16),
                radius=0.5, fill=color, line=None)

    # ── Right panel: recent decisions feed ──
    rx = Inches(6.9)
    rw = Inches(5.73)
    card(s, rx, lt, rw, lh, accent=PURPLE, accent_side='top')
    txt(s, rx + Inches(0.4), lt + Inches(0.3), rw - Inches(0.8), Inches(0.35),
        "Recent decisions captured", size=14, bold=True, color=INK, font=F_TITLE)

    feed = [
        ("payments", "Refund paths must key on refund_request_id"),
        ("infra", "Deploy v2 rollout runbook documented"),
        ("billing", "Proration rounds half-up, not half-even"),
        ("onboarding", "Service split rationale written down"),
        ("tooling", "Local stack now one make command"),
    ]
    for i, (tag, body) in enumerate(feed):
        y = lt + Inches(0.95) + i * Inches(0.58)
        rounded(s, rx + Inches(0.4), y, Inches(1.35), Inches(0.34),
                radius=0.3, fill=PRIMARY_BG, line=None)
        txt(s, rx + Inches(0.4), y + Inches(0.05), Inches(1.35), Inches(0.26),
            tag, size=9.5, bold=True, color=BRAND, align=PP_ALIGN.CENTER,
            font=F_TITLE)
        txt(s, rx + Inches(1.9), y + Inches(0.02), rw - Inches(2.3), Inches(0.4),
            body, size=11, color=INK_SOFT, line_spacing=1.1)

    rounded(s, Inches(0.7), Inches(6.5), Inches(11.93), Inches(0.42),
            radius=0.4, fill=PRIMARY_BG)
    txt(s, Inches(0.7), Inches(6.57), Inches(11.93), Inches(0.3),
        "Visibility into work and decisions — for standups and planning, not keystrokes or individuals.",
        size=12, bold=True, color=BRAND, align=PP_ALIGN.CENTER, font=F_TITLE)


def slide_09_token_cost(prs):
    s = add_slide(prs)
    chrome(s, 9, "Recall Costs Less Than Re-Reading",
           eyebrow="Token Cost",
           subtitle="Cline recalls a small, distilled memory instead of re-ingesting full context every session.")

    # ── Left: the mechanisms ──
    lx = Inches(0.7)
    lw = Inches(6.5)
    lt = Inches(2.35)
    mechs = [
        ("No re-ingesting context",
         "Today Cline re-reads files, docs, and past chat each session. Engram returns just the relevant memory.",
         BRAND),
        ("Distilled, not raw",
         "Consolidation compresses sprawling history into small durable notes — recall pulls a few lessons, not whole transcripts.",
         SUCCESS),
        ("Fewer wasted turns",
         "No re-asking settled questions or re-deriving the same conclusions — each avoided turn is tokens saved.",
         PURPLE),
        ("Less repeated rework",
         "Bugs that aren't repeated mean fewer long, expensive debugging sessions in the first place.",
         GOLD),
    ]
    for i, (title_, desc, color) in enumerate(mechs):
        y = lt + i * Inches(1.07)
        card(s, lx, y, lw, Inches(0.92), accent=color, accent_side='left')
        txt(s, lx + Inches(0.35), y + Inches(0.13), lw - Inches(0.6), Inches(0.35),
            title_, size=14, bold=True, color=INK, font=F_TITLE)
        txt(s, lx + Inches(0.35), y + Inches(0.46), lw - Inches(0.6), Inches(0.42),
            desc, size=11, color=INK_MUTED, line_spacing=1.2)

    # ── Right: illustrative token comparison ──
    rx = Inches(7.5)
    rw = Inches(5.13)
    rt = Inches(2.35)
    rh = Inches(4.5)
    card(s, rx, rt, rw, rh, accent=TEAL, accent_side='top')
    txt(s, rx + Inches(0.4), rt + Inches(0.28), rw - Inches(0.8), Inches(0.35),
        "Tokens per session", size=13, bold=True, color=INK, font=F_TITLE)
    txt(s, rx + Inches(0.4), rt + Inches(0.62), rw - Inches(0.8), Inches(0.25),
        "illustrative — not a benchmark", size=9.5, italic=True, color=INK_FAINT)

    base_y = rt + Inches(3.95)   # baseline the bars grow up from
    bar_w = Inches(1.5)
    # without Engram: one tall bar (re-ingested context)
    wx = rx + Inches(0.85)
    wh = Inches(2.7)
    rounded(s, wx, base_y - wh, bar_w, wh, radius=0.04, fill=ERROR_PALE, line=None)
    rounded(s, wx, base_y - wh, bar_w, wh, radius=0.04, fill=None, line=ERROR, line_w=1.0)
    txt(s, wx, base_y - wh - Inches(0.3), bar_w, Inches(0.28),
        "re-ingest", size=10, bold=True, color=ERROR, align=PP_ALIGN.CENTER,
        font=F_TITLE)
    txt(s, wx, base_y + Inches(0.06), bar_w, Inches(0.3),
        "Without Engram", size=10, color=INK_MUTED, align=PP_ALIGN.CENTER)

    # with Engram: small task bar + thin recall sliver
    ex = rx + Inches(2.75)
    eh = Inches(0.95)
    sliver_h = Inches(0.35)
    rounded(s, ex, base_y - eh, bar_w, eh, radius=0.06, fill=PRIMARY_PALE, line=None)
    rounded(s, ex, base_y - eh - sliver_h, bar_w, sliver_h, radius=0.06,
            fill=TEAL, line=None)
    txt(s, ex, base_y - eh - sliver_h - Inches(0.3), bar_w, Inches(0.28),
        "+ recall", size=10, bold=True, color=TEAL, align=PP_ALIGN.CENTER,
        font=F_TITLE)
    txt(s, ex, base_y + Inches(0.06), bar_w, Inches(0.3),
        "With Engram", size=10, color=INK_MUTED, align=PP_ALIGN.CENTER)

    line(s, rx + Inches(0.4), base_y, rw - Inches(0.8), 0, color=BORDER, weight=1.0)

    txt(s, rx + Inches(0.4), rt + rh - Inches(0.5), rw - Inches(0.8), Inches(0.4),
        "Recall adds a little; targeted recall ≪ broad re-ingestion.",
        size=10, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER,
        line_spacing=1.2)


def slide_10_how_it_works(prs):
    s = add_slide(prs)
    chrome(s, 10, "One Shared Brain Behind Every Cline",
           eyebrow="How It Works",
           subtitle="Engram sits beside Cline as an MCP server — recall before answering, save after working.")

    # ── Layer 1: developers' Cline instances ──
    top_y = Inches(2.25)
    devs = ["Developer A", "Developer B", "Developer C"]
    box_w = Inches(2.7)
    box_h = Inches(0.9)
    gap = Inches(0.65)
    total_w = 3 * box_w + 2 * gap
    start_x = (SLIDE_W - total_w) / 2

    centers = []
    for i, d in enumerate(devs):
        x = start_x + i * (box_w + gap)
        rounded(s, x, top_y, box_w, box_h, radius=0.06, fill=INK, line=None)
        txt(s, x, top_y + Inches(0.13), box_w, Inches(0.3),
            "VS Code  ·  Cline", size=12, bold=True, color=INVERSE,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x, top_y + Inches(0.48), box_w, Inches(0.3),
            d, size=10, color=C_LIGHT(), align=PP_ALIGN.CENTER, font=F_BODY)
        centers.append(x + box_w / 2)

    # ── Layer 2: Engram server ──
    core_y = Inches(3.95)
    core_w = Inches(10.0)
    core_h = Inches(1.5)
    core_x = (SLIDE_W - core_w) / 2

    rounded(s, core_x, core_y, core_w, core_h, radius=0.04,
            fill=PRIMARY_BG, line=BRAND, line_w=1.5)
    txt(s, core_x, core_y + Inches(0.16), core_w, Inches(0.35),
        "ENGRAM SERVER  ·  one shared brain", size=12, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)

    subs = [
        ("Recall", "relevant memory before answering"),
        ("Save", "decisions & lessons after working"),
        ("Project scope", "each service's memory stays clean"),
    ]
    sub_w = (core_w - Inches(0.6)) / 3
    sub_y = core_y + Inches(0.6)
    for i, (lbl, sub) in enumerate(subs):
        x = core_x + Inches(0.15) + i * (sub_w + Inches(0.15))
        rounded(s, x, sub_y, sub_w, Inches(0.78), radius=0.06,
                fill=BG, line=PRIMARY_PALE)
        txt(s, x + Inches(0.05), sub_y + Inches(0.1), sub_w - Inches(0.1),
            Inches(0.3), lbl, size=11.5, bold=True, color=INK,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x + Inches(0.05), sub_y + Inches(0.42), sub_w - Inches(0.1),
            Inches(0.3), sub, size=9, color=INK_MUTED, align=PP_ALIGN.CENTER,
            italic=True, line_spacing=1.2)

    for cx in centers:
        _arch_arrow(s, cx, top_y + box_h, cx, core_y, color=BORDER_STR)

    # ── Layer 3: persistent store ──
    store_y = Inches(5.95)
    store_w = Inches(6.0)
    store_x = (SLIDE_W - store_w) / 2
    rounded(s, store_x, store_y, store_w, Inches(0.62), radius=0.06,
            fill=BG, line=BORDER, line_w=0.75)
    rounded(s, store_x, store_y, Inches(0.07), Inches(0.62), radius=0.5, fill=TEAL)
    txt(s, store_x + Inches(0.25), store_y + Inches(0.16), store_w - Inches(0.4),
        Inches(0.32), "⬢  Persistent store · durable · survives restarts",
        size=11.5, bold=True, color=INK, font=F_TITLE)

    _arch_arrow(s, core_x + core_w / 2, core_y + core_h,
                core_x + core_w / 2, store_y, color=BORDER_STR)

    # summary line
    rounded(s, Inches(0.7), Inches(6.85), Inches(11.93), Inches(0.42),
            radius=0.4, fill=PRIMARY_BG)
    txt(s, Inches(0.7), Inches(6.92), Inches(11.93), Inches(0.3),
        "Keep Cline exactly as your team uses it — and give it a shared memory, so the team's knowledge compounds.",
        size=12.5, bold=True, color=BRAND, align=PP_ALIGN.CENTER, font=F_TITLE)


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_01_title(prs)
    slide_02_today(prs)
    slide_03_with_engram(prs)
    slide_04_usecase_incident(prs)
    slide_05_usecase_onboarding(prs)
    slide_06_usecase_busfactor(prs)
    slide_07_usecase_handoff(prs)
    slide_08_focus_map(prs)
    slide_09_token_cost(prs)
    slide_10_how_it_works(prs)

    out = "F:/agentmemory/docs/engram-final-pitch.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = "F:/agentmemory/docs/engram-final-pitch-v2.pptx"
        prs.save(out)
        print("[note] Original file was locked (open in PowerPoint?). Saved as v2.")
    print(f"Saved: {out}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    build()
