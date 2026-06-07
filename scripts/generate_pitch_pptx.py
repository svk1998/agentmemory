"""Generate the *Engram + Cline* management pitch deck.

Reuses the design system (palette, typography, components) defined in
``generate_pptx.py`` — same look-and-feel, different (Engram) branding and a
shorter, management-facing narrative:

  1. Title
  2. Where Cline is today (the amnesia problem)
  3. Where Cline goes with Engram (remember / learn / share)
  4. Use case — without Engram (the 2 a.m. incident)
  5. Use case — with Engram (the lesson recalled)
  6. Scenario comparison
  7. System architecture (Cline x N -> Engram -> shared store)
  8. How a request flows
  9. The business case
 10. The ask
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Reuse the full design system from the technical deck generator.
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
    add_slide, card, stat_badge, icon_circle, num_badge, table,
    _arch_arrow,
)

WORDMARK = "Engram"
TOTAL = 10


# ════════════════════════════════════════════════════════════════════════════
# Engram-branded chrome
# ════════════════════════════════════════════════════════════════════════════

def chrome(slide, page_num, title, eyebrow=None, subtitle=None, accent=BRAND):
    rect(slide, 0, 0, Inches(0.18), SLIDE_H, fill=accent)
    txt(slide, Inches(11.0), Inches(0.35), Inches(2.2), Inches(0.35),
        WORDMARK + "  ×  Cline", size=11, color=INK_MUTED, bold=True,
        font=F_BODY, align=PP_ALIGN.RIGHT)

    if eyebrow:
        rounded(slide, Inches(0.7), Inches(0.4), Inches(2.4), Inches(0.32),
                radius=0.5, fill=PRIMARY_BG, line=None)
        txt(slide, Inches(0.7), Inches(0.42), Inches(2.4), Inches(0.3),
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
        "Engram — persistent memory for AI coding agents",
        size=9, color=INK_FAINT, font=F_BODY)
    txt(slide, Inches(7.0), Inches(7.34), Inches(5.9), Inches(0.16),
        f"{page_num:02d}  /  {TOTAL:02d}",
        size=9, color=INK_FAINT, font=F_BODY, align=PP_ALIGN.RIGHT)


# ════════════════════════════════════════════════════════════════════════════
# Slides
# ════════════════════════════════════════════════════════════════════════════

def slide_01_title(prs):
    s = add_slide(prs)
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=BG)
    rect(s, 0, 0, Inches(0.18), SLIDE_H, fill=BRAND)

    # decorative dot grid, top-right
    for i in range(12):
        for j in range(6):
            x = Inches(8.5) + i * Inches(0.4)
            y = Inches(0.5) + j * Inches(0.4)
            shape(s, MSO_SHAPE.OVAL, x, y, Inches(0.05), Inches(0.05),
                  fill=PRIMARY_PALE, line=None)

    rounded(s, Inches(0.7), Inches(1.95), Inches(2.7), Inches(0.4),
            radius=0.5, fill=PRIMARY_BG, line=None)
    txt(s, Inches(0.7), Inches(1.99), Inches(2.7), Inches(0.35),
        "MANAGEMENT BRIEFING", size=10, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)

    txt(s, Inches(0.6), Inches(2.65), Inches(12), Inches(1.5),
        "Engram", size=88, color=INK, font=F_DISPLAY, line_spacing=1.0)
    # "× Cline" set tight under the wordmark
    txt(s, Inches(0.72), Inches(4.15), Inches(12), Inches(0.6),
        "memory for Cline", size=26, color=BRAND, font=F_TITLE)

    txt(s, Inches(0.72), Inches(4.95), Inches(12), Inches(0.7),
        "Cline, but it never forgets.",
        size=22, color=INK_SOFT, font=F_BODY, italic=True, line_spacing=1.1)

    rect(s, Inches(0.72), Inches(5.7), Inches(0.8), Inches(0.06), fill=BRAND)
    txt(s, Inches(0.72), Inches(5.95), Inches(11), Inches(0.7),
        "Turn every developer's AI agent into one shared, compounding knowledge asset.",
        size=14, color=INK_MUTED, font=F_BODY, line_spacing=1.3)

    rect(s, 0, Inches(7.0), SLIDE_W, Inches(0.5), fill=SURFACE)
    txt(s, Inches(0.7), Inches(7.12), Inches(8), Inches(0.3),
        "Persistent · Project-scoped · Team-shared",
        size=11, color=INK_MUTED, font=F_BODY)
    txt(s, Inches(8), Inches(7.12), Inches(4.6), Inches(0.3),
        "Powered by agentmemory", size=11, color=INK_MUTED,
        font=F_BODY, align=PP_ALIGN.RIGHT)
    return s


def slide_02_today(prs):
    s = add_slide(prs)
    chrome(s, 2, "Where Cline Is Today",
           eyebrow="The Problem",
           subtitle="Cline is brilliant in the moment — and amnesiac across time.")

    col_w = Inches(5.85)
    col_h = Inches(4.55)
    col_t = Inches(2.45)

    s1_items = [
        ("✓", "Designed the refund flow with the team"),
        ("✓", "Learned refunds must be idempotent"),
        ("✓", "Fixed the gateway double-charge bug"),
        ("✓", "Agreed on the service's naming conventions"),
        ("✓", "Documented the deploy quirk in chat"),
    ]
    s2_items = [
        ("?", "What were the refund rules again?"),
        ("?", "Why did we make it idempotent?"),
        ("?", "Has this bug been hit before?"),
        ("?", "What's our naming convention here?"),
        ("?", "How do we deploy this service?"),
    ]

    for ci, (label, items, color) in enumerate([
        ("Monday  ·  Cline learns it all", s1_items, SUCCESS),
        ("Friday  ·  same Cline, blank slate", s2_items, ERROR),
    ]):
        x = Inches(0.7) + ci * Inches(6.1)
        card(s, x, col_t, col_w, col_h, accent=color, accent_side='top')
        txt(s, x + Inches(0.35), col_t + Inches(0.25), col_w - Inches(0.5), Inches(0.4),
            label, size=14, bold=True, color=color, font=F_TITLE)
        for i, (glyph, item) in enumerate(items):
            y = col_t + Inches(0.85) + i * Inches(0.68)
            icon_circle(s, x + Inches(0.55), y + Inches(0.18),
                        Inches(0.16), color, glyph, INVERSE, 11)
            txt(s, x + Inches(0.9), y + Inches(0.07), col_w - Inches(1.1), Inches(0.35),
                item, size=12, color=INK_SOFT)

    txt(s, Inches(0.7), Inches(7.13), Inches(12), Inches(0.3),
        "Knowledge generated in one session evaporates when it closes — and never reaches another developer's Cline.",
        size=11, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER)


def slide_03_with_engram(prs):
    s = add_slide(prs)
    chrome(s, 3, "Where Cline Goes With Engram",
           eyebrow="The Solution",
           subtitle="One MCP endpoint gives Cline a long-term memory — and a shared one.")

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
        "The only difference is continuity — Cline is now brilliant in the moment and across time, for the whole team.",
        size=14, color=INK, font=F_BODY)


def slide_04_usecase_without(prs):
    s = add_slide(prs)
    chrome(s, 4, "Use Case — A Payments Platform Team",
           eyebrow="Without Engram",
           subtitle="8 engineers, dense domain logic, frequent on-call. Watch the cost repeat.")

    steps = [
        ("Mon", "A developer asks Cline to add a refund endpoint.", INK_SOFT),
        ("—", "Cline doesn't know refunds must be idempotent — the gateway silently double-charges on retry.", ERROR),
        ("—", "It writes clean-but-wrong code. The bug ships.", ERROR),
        ("2 a.m.", "Incident fires. On-call engineer fixes it under pressure.", GOLD),
        ("+2 mo", "A different developer asks for a partial-refund endpoint…", INK_SOFT),
        ("↺", "…and Cline, still amnesiac, makes the exact same mistake.", ERROR),
    ]

    ct = Inches(2.2)
    for i, (tag, body, color) in enumerate(steps):
        y = ct + i * Inches(0.78)
        rounded(s, Inches(0.7), y, Inches(1.2), Inches(0.6),
                radius=0.12, fill=SURFACE, line=BORDER)
        txt(s, Inches(0.7), y + Inches(0.13), Inches(1.2), Inches(0.35),
            tag, size=12, bold=True, color=color if color != INK_SOFT else INK_MUTED,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        # connector dot
        shape(s, MSO_SHAPE.OVAL, Inches(2.15), y + Inches(0.2),
              Inches(0.2), Inches(0.2), fill=color, line=None)
        txt(s, Inches(2.6), y + Inches(0.13), Inches(10), Inches(0.45),
            body, size=14, color=INK_SOFT, line_spacing=1.2)

    rounded(s, Inches(0.7), Inches(6.95), Inches(11.93), Inches(0.32),
            radius=0.4, fill=ERROR_PALE)
    txt(s, Inches(0.7), Inches(6.98), Inches(11.93), Inches(0.3),
        "The same class of bug, paid for twice — and it will happen a third time.",
        size=11, bold=True, color=ERROR, align=PP_ALIGN.CENTER, font=F_TITLE)


def slide_05_usecase_with(prs):
    s = add_slide(prs)
    chrome(s, 5, "Use Case — The Same Team, With Engram",
           eyebrow="With Engram",
           subtitle="One lesson captured once protects the whole team forever.")

    steps = [
        ("2 a.m.", "The incident is fixed — and Cline saves a lesson to Engram:", SUCCESS),
        ("lesson", "\"Refund paths must be idempotent — gateway double-charges on retry; key on refund_request_id.\"", BRAND),
        ("+2 mo", "Another developer asks Cline for the partial-refund endpoint.", INK_SOFT),
        ("recall", "Before writing a line, Cline recalls the lesson from shared memory.", SUCCESS),
        ("✓", "It generates idempotent code on the first try.", SUCCESS),
        ("result", "The 2 a.m. incident never happens twice.", SUCCESS),
    ]

    ct = Inches(2.2)
    for i, (tag, body, color) in enumerate(steps):
        y = ct + i * Inches(0.74)
        is_lesson = tag == "lesson"
        rounded(s, Inches(0.7), y, Inches(1.2), Inches(0.58),
                radius=0.12, fill=SURFACE, line=BORDER)
        txt(s, Inches(0.7), y + Inches(0.13), Inches(1.2), Inches(0.35),
            tag, size=11, bold=True,
            color=color if color != INK_SOFT else INK_MUTED,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        shape(s, MSO_SHAPE.OVAL, Inches(2.15), y + Inches(0.19),
              Inches(0.2), Inches(0.2), fill=color, line=None)
        if is_lesson:
            rounded(s, Inches(2.6), y - Inches(0.02), Inches(9.9), Inches(0.62),
                    radius=0.06, fill=CODE_LIKE(), line=None)
            txt(s, Inches(2.85), y + Inches(0.12), Inches(9.5), Inches(0.45),
                body, size=12.5, color=INVERSE, font=F_MONO, italic=True,
                line_spacing=1.15)
        else:
            txt(s, Inches(2.6), y + Inches(0.11), Inches(10), Inches(0.45),
                body, size=14, color=INK_SOFT, line_spacing=1.2)

    rounded(s, Inches(0.7), Inches(6.9), Inches(11.93), Inches(0.34),
            radius=0.4, fill=SUCCESS_PALE)
    txt(s, Inches(0.7), Inches(6.94), Inches(11.93), Inches(0.3),
        "That single avoided incident pays for the entire system — then it keeps paying.",
        size=11, bold=True, color=SUCCESS, align=PP_ALIGN.CENTER, font=F_TITLE)


def CODE_LIKE():
    # local helper: the dark "lesson" pill colour
    return RGBColor(0x0F, 0x17, 0x2A)


def slide_06_scenarios(prs):
    s = add_slide(prs)
    chrome(s, 6, "It Compounds Across Everything",
           eyebrow="The Payoff",
           subtitle="The refund story is one of dozens — onboarding, decisions, deploys, conventions.")

    headers = ["Scenario", "Cline today", "Cline + Engram"]
    rows = [
        ["New hire's first week", "Asks teammates the same questions repeatedly", "**Recalls runbooks, conventions, architecture instantly**"],
        ["A senior dev leaves", "Tribal knowledge walks out the door", "**Their captured context stays in the shared brain**"],
        ["A recurring class of bug", "Repeated every time it's encountered", "**Recalled and avoided before code is written**"],
        ["Cross-service monorepo", "Context bleeds between services", "**Project scoping keeps each service's memory clean**"],
        ["Architecture decisions", "Re-explained, re-derived, re-litigated", "**Remembered with the reasoning behind them**"],
    ]
    table(s, Inches(0.7), Inches(2.35), Inches(11.93),
          headers, rows,
          col_widths=[Inches(3.0), Inches(4.46), Inches(4.47)],
          hdr_size=12, body_size=11)

    txt(s, Inches(0.7), Inches(6.6), Inches(12), Inches(0.4),
        "Each row is hours saved, incidents avoided, and ramp-up shortened — every week, across every developer.",
        size=12, italic=True, color=INK_MUTED, line_spacing=1.3)


def slide_07_architecture(prs):
    s = add_slide(prs)
    chrome(s, 7, "System Architecture",
           eyebrow="Architecture",
           subtitle="Engram sits beside Cline as an MCP server — one shared, project-scoped brain.")

    # ── Layer 1: developers' Cline instances ──
    top_y = Inches(2.15)
    devs = ["Developer A", "Developer B", "Developer C"]
    box_w = Inches(2.7)
    box_h = Inches(0.95)
    gap = Inches(0.65)
    total_w = 3 * box_w + 2 * gap
    start_x = (SLIDE_W - total_w) / 2

    txt(s, Inches(0.7), top_y - Inches(0.3), Inches(6), Inches(0.3),
        "EVERY DEVELOPER'S EDITOR", size=9, bold=True, color=INK_MUTED, font=F_TITLE)

    centers = []
    for i, d in enumerate(devs):
        x = start_x + i * (box_w + gap)
        rounded(s, x, top_y, box_w, box_h, radius=0.06, fill=INK, line=None)
        txt(s, x, top_y + Inches(0.14), box_w, Inches(0.3),
            "VS Code  ·  Cline", size=12, bold=True, color=INVERSE,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x, top_y + Inches(0.5), box_w, Inches(0.3),
            d, size=10, color=C_LIGHT(), align=PP_ALIGN.CENTER, font=F_BODY)
        centers.append(x + box_w / 2)

    # ── Layer 2: Engram server ──
    core_y = Inches(3.95)
    core_w = Inches(10.8)
    core_h = Inches(1.85)
    core_x = (SLIDE_W - core_w) / 2

    rounded(s, core_x, core_y, core_w, core_h, radius=0.035,
            fill=PRIMARY_BG, line=BRAND, line_w=1.5)
    txt(s, core_x, core_y + Inches(0.14), core_w, Inches(0.35),
        "ENGRAM SERVER  ·  one shared brain", size=12, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)

    subs = [
        ("MCP Endpoint", "recall · save · lessons"),
        ("Memory Engine", "project scoping · dedup"),
        ("Consolidation", "raw notes → durable patterns"),
        ("Governance / Audit", "who knew what · purge on demand"),
    ]
    sub_w = (core_w - Inches(0.7)) / 4
    sub_y = core_y + Inches(0.62)
    for i, (lbl, sub) in enumerate(subs):
        x = core_x + Inches(0.14) + i * (sub_w + Inches(0.14))
        rounded(s, x, sub_y, sub_w, Inches(1.0), radius=0.06,
                fill=BG, line=PRIMARY_PALE)
        txt(s, x + Inches(0.05), sub_y + Inches(0.14), sub_w - Inches(0.1), Inches(0.32),
            lbl, size=11, bold=True, color=INK, align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x + Inches(0.05), sub_y + Inches(0.5), sub_w - Inches(0.1), Inches(0.42),
            sub, size=9, color=INK_MUTED, align=PP_ALIGN.CENTER, italic=True,
            line_spacing=1.25)

    # bidirectional arrows: Cline <-> Engram
    for cx in centers:
        _arch_arrow(s, cx, top_y + box_h, cx, core_y, color=BORDER_STR)
    txt(s, start_x, top_y + box_h + Inches(0.18), total_w, Inches(0.3),
        "MCP  ·  recall before answering   ↓        ↑   save after working",
        size=10, color=INK_MUTED, align=PP_ALIGN.CENTER, italic=True, font=F_BODY)

    # ── Layer 3: persistent store ──
    store_y = Inches(6.25)
    store_w = Inches(6.5)
    store_x = (SLIDE_W - store_w) / 2
    rounded(s, store_x, store_y, store_w, Inches(0.75), radius=0.06,
            fill=BG, line=BORDER, line_w=0.75)
    rounded(s, store_x, store_y, Inches(0.07), Inches(0.75), radius=0.5, fill=TEAL)
    txt(s, store_x + Inches(0.25), store_y + Inches(0.1), store_w - Inches(0.4), Inches(0.32),
        "⬢  Persistent store", size=12, bold=True, color=INK, font=F_TITLE)
    txt(s, store_x + Inches(0.25), store_y + Inches(0.43), store_w - Inches(0.4), Inches(0.28),
        "durable · survives restarts · backed up like any other data store",
        size=9.5, color=INK_MUTED, italic=True)

    _arch_arrow(s, core_x + core_w / 2, core_y + core_h, core_x + core_w / 2, store_y,
                color=BORDER_STR)


def C_LIGHT():
    return RGBColor(0xCB, 0xD5, 0xE1)


def slide_08_flow(prs):
    s = add_slide(prs)
    chrome(s, 8, "How a Request Flows",
           eyebrow="Architecture",
           subtitle="Recall before answering, save after working — automatic, no new workflow.")

    steps = [
        ("Prompt", "A developer prompts Cline in VS Code, exactly as they do today.", BRAND),
        ("Recall", "Before answering, Cline pulls the relevant memories and lessons for that project from Engram.", PURPLE),
        ("Work", "Cline completes the task with full team context — not a blank slate.", SUCCESS),
        ("Save", "New decisions, fixes, and lessons are written back to Engram, scoped to the project.", GOLD),
        ("Share", "Every teammate's Cline can recall it immediately. Knowledge compounds.", TEAL),
    ]

    ct = Inches(2.25)
    row_h = Inches(0.92)
    for i, (label, desc, color) in enumerate(steps):
        y = ct + i * row_h
        num_badge(s, Inches(0.8), y + Inches(0.04), Inches(0.6), i + 1, color=color)
        txt(s, Inches(1.7), y, Inches(2.4), Inches(0.5),
            label, size=17, bold=True, color=INK, font=F_TITLE,
            anchor=MSO_ANCHOR.MIDDLE)
        txt(s, Inches(4.0), y, Inches(8.6), Inches(0.6),
            desc, size=13.5, color=INK_SOFT, line_spacing=1.25,
            anchor=MSO_ANCHOR.MIDDLE)
        if i < len(steps) - 1:
            rect(s, Inches(1.08), y + Inches(0.62), Inches(0.02), Inches(0.32),
                 fill=BORDER_STR)

    txt(s, Inches(0.7), Inches(7.05), Inches(12), Inches(0.3),
        "A consolidation pipeline distills raw notes into durable patterns; every write is audited and can be purged on demand.",
        size=11, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER)


def slide_09_business(prs):
    s = add_slide(prs)
    chrome(s, 9, "The Business Case",
           eyebrow="Why It Matters",
           subtitle="Engram turns AI sessions from a sunk cost into a compounding asset.")

    items = [
        ("⏱", "Faster onboarding",
         "Cline gives new hires the team's accumulated context on day one. Ramp-up drops from weeks to a query.",
         BRAND),
        ("🔒", "Knowledge survives turnover",
         "Expertise stays in the shared brain when people move on — not locked in one person's head.",
         PURPLE),
        ("🛡", "Fewer repeated incidents",
         "One engineer's lesson becomes the whole team's immunity to that class of bug.",
         SUCCESS),
        ("⚡", "Lower cost, sharper output",
         "Cline recalls distilled, relevant memory instead of re-ingesting full context every session.",
         GOLD),
    ]

    cw = Inches(5.85)
    ch = Inches(2.0)
    ct = Inches(2.25)
    for i, (glyph, title_, desc, color) in enumerate(items):
        row, col = i // 2, i % 2
        x = Inches(0.7) + col * Inches(6.1)
        y = ct + row * Inches(2.2)
        card(s, x, y, cw, ch, accent=color, accent_side='left')
        txt(s, x + Inches(0.35), y + Inches(0.28), Inches(0.7), Inches(0.6),
            glyph, size=24, align=PP_ALIGN.LEFT)
        txt(s, x + Inches(1.15), y + Inches(0.3), cw - Inches(1.4), Inches(0.45),
            title_, size=18, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(1.15), y + Inches(0.82), cw - Inches(1.45), Inches(1.0),
            desc, size=12.5, color=INK_MUTED, line_spacing=1.4)


def slide_10_ask(prs):
    s = add_slide(prs)
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=INK)
    rect(s, Inches(7.6), 0, SLIDE_W - Inches(7.6), SLIDE_H, fill=BRAND)
    for i in range(8):
        for j in range(5):
            x = Inches(7.85) + i * Inches(0.65)
            y = Inches(0.5) + j * Inches(1.3)
            shape(s, MSO_SHAPE.OVAL, x, y, Inches(0.08), Inches(0.08),
                  fill=ACCENT, line=None)

    txt(s, Inches(0.7), Inches(0.7), Inches(6), Inches(0.4),
        "THE ASK", size=12, bold=True, color=ACCENT, font=F_TITLE)
    txt(s, Inches(0.7), Inches(1.2), Inches(6.6), Inches(1.4),
        "Run a one-quarter pilot",
        size=42, bold=True, color=INVERSE, font=F_TITLE, line_spacing=1.05)

    pts = [
        ("One team", "Standardized on Cline + Engram for a single quarter."),
        ("Measure", "Onboarding time · repeated-error rate · engineer-reported friction."),
        ("Decide", "Expand on the results — the data makes the case, not the slide."),
    ]
    for i, (h, d) in enumerate(pts):
        y = Inches(3.0) + i * Inches(1.0)
        shape(s, MSO_SHAPE.OVAL, Inches(0.7), y + Inches(0.08),
              Inches(0.16), Inches(0.16), fill=ACCENT, line=None)
        txt(s, Inches(1.05), y, Inches(6), Inches(0.4),
            h, size=18, bold=True, color=INVERSE, font=F_TITLE)
        txt(s, Inches(1.05), y + Inches(0.4), Inches(6.2), Inches(0.5),
            d, size=13, color=C_LIGHT(), font=F_BODY, line_spacing=1.25)

    # right panel: the one-liner
    txt(s, Inches(7.95), Inches(2.6), Inches(4.9), Inches(2.6),
        "Keep Cline exactly as your team uses it — and give it a memory, "
        "so every session compounds into a shared asset instead of resetting to zero.",
        size=20, color=INVERSE, font=F_TITLE, italic=True, line_spacing=1.3)
    txt(s, Inches(7.95), Inches(6.6), Inches(4.9), Inches(0.4),
        "Engram  ×  Cline", size=14, bold=True, color=INVERSE,
        font=F_BODY, align=PP_ALIGN.RIGHT)


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_01_title(prs)
    slide_02_today(prs)
    slide_03_with_engram(prs)
    slide_04_usecase_without(prs)
    slide_05_usecase_with(prs)
    slide_06_scenarios(prs)
    slide_07_architecture(prs)
    slide_08_flow(prs)
    slide_09_business(prs)
    slide_10_ask(prs)

    out = "F:/agentmemory/docs/engram-cline-pitch.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = "F:/agentmemory/docs/engram-cline-pitch-v2.pptx"
        prs.save(out)
        print("[note] Original file was locked (open in PowerPoint?). Saved as v2.")
    print(f"Saved: {out}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    build()
