"""Generate the compact (5-slide) *Engram + Cline* pitch — Samsung Tizen edition.

A management-facing short deck:

  1. Title
  2. Cline today vs. Cline with Engram (problem + solution)
  3. Use case — Samsung TV / Tizen app development (without vs. with Engram)
  4. Architecture + request flow
  5. Rollout roadmap (how we release / adopt features in phases)

Reuses the design system (palette, typography, components) from
``generate_pptx.py``. Output: ``docs/engram-cline-tizen-pitch.pptx``.
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
    shape, rect, rounded, line, txt,
    add_slide, card, icon_circle, num_badge, _arch_arrow,
)

WORDMARK = "Engram"
TOTAL = 5
INK_PILL = RGBColor(0x0F, 0x17, 0x2A)
SLATE_300 = RGBColor(0xCB, 0xD5, 0xE1)


def chrome(slide, page_num, title, eyebrow=None, subtitle=None, accent=BRAND):
    rect(slide, 0, 0, Inches(0.18), SLIDE_H, fill=accent)
    txt(slide, Inches(11.0), Inches(0.35), Inches(2.2), Inches(0.35),
        WORDMARK + "  ×  Cline", size=11, color=INK_MUTED, bold=True,
        font=F_BODY, align=PP_ALIGN.RIGHT)
    if eyebrow:
        rounded(slide, Inches(0.7), Inches(0.4), Inches(2.5), Inches(0.32),
                radius=0.5, fill=PRIMARY_BG, line=None)
        txt(slide, Inches(0.7), Inches(0.42), Inches(2.5), Inches(0.3),
            eyebrow.upper(), size=10, bold=True, color=BRAND,
            align=PP_ALIGN.CENTER, font=F_TITLE)
    title_top = Inches(0.88) if eyebrow else Inches(0.55)
    txt(slide, Inches(0.7), title_top, Inches(12.0), Inches(0.62),
        title, size=28, bold=True, color=INK, font=F_TITLE, line_spacing=1.0)
    if subtitle:
        txt(slide, Inches(0.7), title_top + Inches(0.66), Inches(12.0), Inches(0.4),
            subtitle, size=15, color=INK_MUTED, font=F_BODY, line_spacing=1.15)
    sub_off = Inches(1.10) if subtitle else Inches(0.7)
    line(slide, Inches(0.7), title_top + sub_off, Inches(0.6), 0, color=BRAND, weight=2.5)
    rect(slide, 0, Inches(7.32), SLIDE_W, Inches(0.18), fill=SURFACE)
    txt(slide, Inches(0.4), Inches(7.34), Inches(6), Inches(0.16),
        "Engram — persistent memory for AI coding agents",
        size=9, color=INK_FAINT, font=F_BODY)
    txt(slide, Inches(7.0), Inches(7.34), Inches(5.9), Inches(0.16),
        f"{page_num:02d}  /  {TOTAL:02d}",
        size=9, color=INK_FAINT, font=F_BODY, align=PP_ALIGN.RIGHT)


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
    rounded(s, Inches(0.7), Inches(1.95), Inches(3.1), Inches(0.4),
            radius=0.5, fill=PRIMARY_BG, line=None)
    txt(s, Inches(0.7), Inches(1.99), Inches(3.1), Inches(0.35),
        "MANAGEMENT BRIEFING  ·  5 MIN", size=10, bold=True, color=BRAND,
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
        "A shared, compounding knowledge brain for the Samsung TV / Tizen team.",
        size=14, color=INK_MUTED, font=F_BODY, line_spacing=1.3)
    rect(s, 0, Inches(7.0), SLIDE_W, Inches(0.5), fill=SURFACE)
    txt(s, Inches(0.7), Inches(7.12), Inches(8), Inches(0.3),
        "Persistent · Project-scoped · Team-shared",
        size=11, color=INK_MUTED, font=F_BODY)
    txt(s, Inches(8), Inches(7.12), Inches(4.6), Inches(0.3),
        "Powered by agentmemory", size=11, color=INK_MUTED,
        font=F_BODY, align=PP_ALIGN.RIGHT)
    return s


def slide_02_problem_solution(prs):
    s = add_slide(prs)
    chrome(s, 2, "Cline Today vs. Cline With Engram",
           eyebrow="Problem → Solution",
           subtitle="Cline is brilliant in the moment — Engram makes it brilliant across time, for the whole team.")

    # red "today" banner
    rounded(s, Inches(0.7), Inches(2.15), Inches(11.93), Inches(0.62),
            radius=0.06, fill=ERROR_PALE, line=None)
    txt(s, Inches(1.0), Inches(2.26), Inches(0.6), Inches(0.4),
        "✗", size=20, bold=True, color=ERROR, font=F_TITLE)
    txt(s, Inches(1.5), Inches(2.28), Inches(10.9), Inches(0.4),
        "Today  —  every Cline session starts from zero: context is re-explained, "
        "knowledge evaporates when the chat closes, and one mistake gets repeated team-wide.",
        size=13, color=INK_SOFT, line_spacing=1.1, anchor=MSO_ANCHOR.MIDDLE)

    props = [
        ("⟳", "Remember",
         "Architecture, decisions, and Tizen gotchas — kept across sessions, indefinitely.",
         BRAND),
        ("✦", "Learn",
         "Every bug Cline fixes becomes a lesson it recalls before it can repeat it.",
         SUCCESS),
        ("⇄", "Share",
         "What one engineer's Cline learns, every engineer's Cline knows — instantly.",
         PURPLE),
    ]
    cw = Inches(3.85)
    ch = Inches(2.75)
    ct = Inches(3.05)
    gap = Inches(0.19)
    for i, (glyph, title_, desc, color) in enumerate(props):
        x = Inches(0.7) + i * (cw + gap)
        card(s, x, ct, cw, ch, accent=color, accent_side='top')
        icon_circle(s, x + cw / 2, ct + Inches(0.85),
                    Inches(0.46), color, glyph, INVERSE, 24)
        txt(s, x, ct + Inches(1.4), cw, Inches(0.45),
            title_, size=21, bold=True, color=INK, font=F_TITLE, align=PP_ALIGN.CENTER)
        txt(s, x + Inches(0.35), ct + Inches(1.92), cw - Inches(0.7), Inches(0.8),
            desc, size=12.5, color=INK_MUTED, align=PP_ALIGN.CENTER, line_spacing=1.35)

    rounded(s, Inches(0.7), Inches(6.1), Inches(11.93), Inches(0.7),
            radius=0.06, fill=PRIMARY_BG)
    txt(s, Inches(0.7), Inches(6.27), Inches(11.93), Inches(0.4),
        "Same agent, same editor, same workflow — the only difference is continuity.",
        size=14, bold=True, color=BRAND, align=PP_ALIGN.CENTER, font=F_TITLE)


def slide_03_tizen_usecase(prs):
    s = add_slide(prs)
    chrome(s, 3, "Use Case — Samsung TV / Tizen App",
           eyebrow="The Payoff",
           subtitle="A real Tizen gotcha, captured once, protects every future screen and every developer.")

    col_w = Inches(5.85)
    col_h = Inches(4.05)
    ct = Inches(2.3)

    # ── Without Engram ──
    x = Inches(0.7)
    card(s, x, ct, col_w, col_h, accent=ERROR, accent_side='top')
    txt(s, x + Inches(0.35), ct + Inches(0.22), col_w - Inches(0.6), Inches(0.4),
        "Without Engram", size=15, bold=True, color=ERROR, font=F_TITLE)
    without = [
        "Dev asks Cline to add remote playback controls.",
        "Cline writes standard JS keydown handlers.",
        "On the TV, the media / colour remote keys never fire.",
        "Hours lost — the keys were never registered with Tizen.",
        "Weeks later, a new screen → the same dead-key bug.",
    ]
    for i, t in enumerate(without):
        y = ct + Inches(0.78) + i * Inches(0.62)
        txt(s, x + Inches(0.35), y, Inches(0.3), Inches(0.4),
            "✗", size=13, bold=True, color=ERROR, font=F_TITLE)
        txt(s, x + Inches(0.7), y + Inches(0.02), col_w - Inches(1.0), Inches(0.55),
            t, size=12, color=INK_SOFT, line_spacing=1.15)

    # ── With Engram ──
    x2 = Inches(6.78)
    card(s, x2, ct, col_w, col_h, accent=SUCCESS, accent_side='top')
    txt(s, x2 + Inches(0.35), ct + Inches(0.22), col_w - Inches(0.6), Inches(0.4),
        "With Engram", size=15, bold=True, color=SUCCESS, font=F_TITLE)
    # lesson pill
    rounded(s, x2 + Inches(0.35), ct + Inches(0.72), col_w - Inches(0.7), Inches(1.0),
            radius=0.05, fill=INK_PILL, line=None)
    txt(s, x2 + Inches(0.55), ct + Inches(0.82), col_w - Inches(1.05), Inches(0.85),
        "lesson saved:  \"Tizen remote media/colour keys emit keydown only after "
        "tizen.tvinputdevice.registerKey(); register on init, unregister on teardown.\"",
        size=11, color=SLATE_300, font=F_MONO, italic=True, line_spacing=1.2)
    withe = [
        "Next feature: Cline recalls the lesson before coding.",
        "It registers the keys correctly on the first try.",
        "The dead-key bug never returns — for anyone.",
    ]
    for i, t in enumerate(withe):
        y = ct + Inches(2.0) + i * Inches(0.62)
        txt(s, x2 + Inches(0.35), y, Inches(0.3), Inches(0.4),
            "✓", size=13, bold=True, color=SUCCESS, font=F_TITLE)
        txt(s, x2 + Inches(0.7), y + Inches(0.02), col_w - Inches(1.0), Inches(0.55),
            t, size=12, color=INK_SOFT, line_spacing=1.15)

    rounded(s, Inches(0.7), Inches(6.55), Inches(11.93), Inches(0.34),
            radius=0.4, fill=SUCCESS_PALE)
    txt(s, Inches(0.7), Inches(6.59), Inches(11.93), Inches(0.3),
        "Multiply across AVPlay codecs, focus navigation, app lifecycle, and device signing — the lessons compound.",
        size=11, bold=True, color=SUCCESS, align=PP_ALIGN.CENTER, font=F_TITLE)


def slide_04_architecture(prs):
    s = add_slide(prs)
    chrome(s, 4, "Architecture & Request Flow",
           eyebrow="How It Works",
           subtitle="Engram sits beside Cline as an MCP server — one shared, project-scoped brain.")

    # ── Cline instances ──
    top_y = Inches(2.1)
    devs = ["TV App — Dev A", "TV App — Dev B", "TV App — Dev C"]
    box_w = Inches(2.7)
    box_h = Inches(0.9)
    gap = Inches(0.65)
    total_w = 3 * box_w + 2 * gap
    start_x = (SLIDE_W - total_w) / 2
    txt(s, Inches(0.7), top_y - Inches(0.28), Inches(6), Inches(0.3),
        "EVERY DEVELOPER'S EDITOR", size=9, bold=True, color=INK_MUTED, font=F_TITLE)
    centers = []
    for i, d in enumerate(devs):
        x = start_x + i * (box_w + gap)
        rounded(s, x, top_y, box_w, box_h, radius=0.06, fill=INK, line=None)
        txt(s, x, top_y + Inches(0.13), box_w, Inches(0.3),
            "VS Code  ·  Cline", size=12, bold=True, color=INVERSE,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x, top_y + Inches(0.48), box_w, Inches(0.3),
            d, size=10, color=SLATE_300, align=PP_ALIGN.CENTER, font=F_BODY)
        centers.append(x + box_w / 2)

    # ── Engram core ──
    core_y = Inches(3.7)
    core_w = Inches(10.8)
    core_h = Inches(1.7)
    core_x = (SLIDE_W - core_w) / 2
    rounded(s, core_x, core_y, core_w, core_h, radius=0.035,
            fill=PRIMARY_BG, line=BRAND, line_w=1.5)
    txt(s, core_x, core_y + Inches(0.12), core_w, Inches(0.35),
        "ENGRAM SERVER  ·  one shared brain", size=12, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)
    subs = [
        ("MCP Endpoint", "recall · save · lessons"),
        ("Memory Engine", "project scoping · dedup"),
        ("Consolidation", "notes → durable patterns"),
        ("Governance / Audit", "who knew what · purge"),
    ]
    sub_w = (core_w - Inches(0.7)) / 4
    sub_y = core_y + Inches(0.58)
    for i, (lbl, sub) in enumerate(subs):
        x = core_x + Inches(0.14) + i * (sub_w + Inches(0.14))
        rounded(s, x, sub_y, sub_w, Inches(0.92), radius=0.06,
                fill=BG, line=PRIMARY_PALE)
        txt(s, x + Inches(0.05), sub_y + Inches(0.12), sub_w - Inches(0.1), Inches(0.32),
            lbl, size=10.5, bold=True, color=INK, align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x + Inches(0.05), sub_y + Inches(0.46), sub_w - Inches(0.1), Inches(0.4),
            sub, size=9, color=INK_MUTED, align=PP_ALIGN.CENTER, italic=True, line_spacing=1.2)
    for cx in centers:
        _arch_arrow(s, cx, top_y + box_h, cx, core_y, color=BORDER_STR)

    # ── flow strip ──
    flow_y = Inches(5.85)
    txt(s, Inches(0.7), flow_y - Inches(0.28), Inches(6), Inches(0.3),
        "EVERY REQUEST", size=9, bold=True, color=INK_MUTED, font=F_TITLE)
    steps = [("1", "Prompt", BRAND), ("2", "Recall", PURPLE), ("3", "Work", SUCCESS),
             ("4", "Save", GOLD), ("5", "Share", TEAL)]
    chip_w = Inches(2.05)
    chip_h = Inches(0.7)
    cgap = Inches(0.32)
    ctot = 5 * chip_w + 4 * cgap
    cstart = (SLIDE_W - ctot) / 2
    for i, (n, label, color) in enumerate(steps):
        x = cstart + i * (chip_w + cgap)
        rounded(s, x, flow_y, chip_w, chip_h, radius=0.1, fill=BG, line=color, line_w=1.25)
        shape(s, MSO_SHAPE.OVAL, x + Inches(0.18), flow_y + Inches(0.19),
              Inches(0.32), Inches(0.32), fill=color, line=None)
        txt(s, x + Inches(0.18), flow_y + Inches(0.22), Inches(0.32), Inches(0.28),
            n, size=12, bold=True, color=INVERSE, align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x + Inches(0.6), flow_y + Inches(0.2), chip_w - Inches(0.7), Inches(0.32),
            label, size=13, bold=True, color=INK, font=F_TITLE)
        if i < 4:
            txt(s, x + chip_w, flow_y + Inches(0.16), cgap, Inches(0.4),
                "→", size=16, bold=True, color=INK_FAINT,
                align=PP_ALIGN.CENTER, font=F_TITLE)


def slide_05_roadmap(prs):
    s = add_slide(prs)
    chrome(s, 5, "Rollout Roadmap",
           eyebrow="Release Plan",
           subtitle="How we adopt Engram in phases — each phase ships value and de-risks the next.")

    phases = [
        ("Q1", "Pilot", "Tizen team",
         ["Wire Engram to Cline", "Capture lessons & decisions", "Per-app project scoping"],
         BRAND),
        ("Q2", "Team Memory", "Shared brain",
         ["Team-wide shared recall", "Tizen lessons library grows", "Gotchas auto-surfaced"],
         PURPLE),
        ("Q3", "Onboarding", "New-hire recall",
         ["Runbooks on day one", "Conventions & history recall", "Ramp-up weeks → queries"],
         SUCCESS),
        ("Q4", "Org Rollout", "Scale out",
         ["Governance + audit on", "Expand to other product teams", "Cross-team knowledge mesh"],
         GOLD),
    ]

    # timeline base line
    ct = Inches(2.55)
    cw = Inches(2.85)
    chh = Inches(3.6)
    gap = Inches(0.18)
    total = 4 * cw + 3 * gap
    start_x = (SLIDE_W - total) / 2

    # connecting arrow under the cards
    arrow_y = ct + chh + Inches(0.25)
    line(s, start_x, arrow_y, total, 0, color=BORDER_STR, weight=2)
    _arch_arrow(s, start_x + total - Inches(0.6), arrow_y, start_x + total, arrow_y, color=BORDER_STR)

    for i, (q, title_, tag, items, color) in enumerate(phases):
        x = start_x + i * (cw + gap)
        card(s, x, ct, cw, chh, accent=color, accent_side='top')
        # quarter badge
        rounded(s, x + Inches(0.3), ct + Inches(0.3), Inches(1.0), Inches(0.42),
                radius=0.4, fill=color, line=None)
        txt(s, x + Inches(0.3), ct + Inches(0.34), Inches(1.0), Inches(0.35),
            q, size=13, bold=True, color=INVERSE, align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x + Inches(0.3), ct + Inches(0.92), cw - Inches(0.6), Inches(0.45),
            title_, size=18, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(0.3), ct + Inches(1.38), cw - Inches(0.6), Inches(0.32),
            tag, size=11, color=color, italic=True, font=F_BODY)
        line(s, x + Inches(0.3), ct + Inches(1.78), cw - Inches(0.6), 0,
             color=BORDER, weight=1)
        for j, it in enumerate(items):
            y = ct + Inches(1.95) + j * Inches(0.52)
            shape(s, MSO_SHAPE.OVAL, x + Inches(0.32), y + Inches(0.08),
                  Inches(0.1), Inches(0.1), fill=color, line=None)
            txt(s, x + Inches(0.52), y, cw - Inches(0.78), Inches(0.5),
                it, size=11, color=INK_SOFT, line_spacing=1.15)

        # connector node on the timeline
        shape(s, MSO_SHAPE.OVAL, x + cw / 2 - Inches(0.08), arrow_y - Inches(0.08),
              Inches(0.16), Inches(0.16), fill=color, line=None)

    txt(s, Inches(0.7), Inches(6.75), Inches(12), Inches(0.4),
        "Each phase is independently useful — we can stop, measure, and expand on real results at every step.",
        size=12, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER, line_spacing=1.3)


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    slide_01_title(prs)
    slide_02_problem_solution(prs)
    slide_03_tizen_usecase(prs)
    slide_04_architecture(prs)
    slide_05_roadmap(prs)
    out = "F:/agentmemory/docs/engram-cline-tizen-pitch.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = "F:/agentmemory/docs/engram-cline-tizen-pitch-v2.pptx"
        prs.save(out)
        print("[note] Original file was locked (open in PowerPoint?). Saved as v2.")
    print(f"Saved: {out}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    build()
