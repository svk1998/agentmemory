"""Generate the agentmemory technical presentation — professional edition.

Design system:
  • Modern light theme with refined typography (Segoe UI family)
  • Dark code blocks with syntax highlighting (terminal-style)
  • Native PPTX charts for benchmark data
  • Shape-based diagrams (no ASCII art)
  • Consistent left-edge accent, slide numbers, wordmark
  • Flat cards (no elevation) with borders + accent stripes
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.oxml.ns import qn
from lxml import etree

# ── Slide dimensions ────────────────────────────────────────────────────────
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

# ── Color palette  ──────────────────────────────────────────────────────────
def C(hex_str): return RGBColor(int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

# Surface
BG          = C("FFFFFF")
SURFACE     = C("F8FAFC")
CARD        = C("FFFFFF")
BORDER      = C("E2E8F0")
BORDER_STR  = C("CBD5E1")

# Text
INK         = C("0F172A")  # slate-900
INK_SOFT    = C("334155")  # slate-700
INK_MUTED   = C("64748B")  # slate-500
INK_FAINT   = C("94A3B8")  # slate-400
INVERSE     = C("FFFFFF")

# Brand
PRIMARY     = C("1E3A8A")  # blue-900
BRAND       = C("2563EB")  # blue-600
ACCENT      = C("3B82F6")  # blue-500
PRIMARY_PALE= C("DBEAFE")  # blue-100
PRIMARY_BG  = C("EFF6FF")  # blue-50

# Semantic
GOLD        = C("D97706")  # amber-600
GOLD_PALE   = C("FEF3C7")
SUCCESS     = C("059669")  # emerald-600
SUCCESS_PALE= C("D1FAE5")
ERROR       = C("DC2626")  # red-600
ERROR_PALE  = C("FEE2E2")
PURPLE      = C("7C3AED")
TEAL        = C("0891B2")

# Code (dark terminal style)
CODE_BG       = C("0F172A")
CODE_PANEL_BG = C("1E293B")
CODE_TEXT     = C("E2E8F0")
CODE_KEYWORD  = C("60A5FA")  # blue-400
CODE_STRING   = C("86EFAC")  # green-300
CODE_NUMBER   = C("F0ABFC")  # fuchsia-300
CODE_COMMENT  = C("64748B")  # slate-500
CODE_PROP     = C("FBBF24")  # amber-400
CODE_PUNCT    = C("CBD5E1")  # slate-300

# Light code variant
CODE_LIGHT_BG = C("F8FAFC")
CODE_LIGHT_TX = C("1E293B")

# ── Fonts ───────────────────────────────────────────────────────────────────
F_DISPLAY = "Segoe UI Light"
F_TITLE   = "Segoe UI Semibold"
F_BODY    = "Segoe UI"
F_MONO    = "Consolas"


# ════════════════════════════════════════════════════════════════════════════
# Low-level helpers
# ════════════════════════════════════════════════════════════════════════════

def shape(slide, shape_type, l, t, w, h, fill=None, line=None, line_w=0.75):
    s = slide.shapes.add_shape(shape_type, l, t, w, h)
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(line_w)
    # Disable the shadow inherited from the theme effect style (effectRef idx=2).
    s.shadow.inherit = False
    return s


def rect(slide, l, t, w, h, **kw):
    return shape(slide, MSO_SHAPE.RECTANGLE, l, t, w, h, **kw)


def rounded(slide, l, t, w, h, radius=0.04, **kw):
    s = shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h, **kw)
    # tweak corner radius
    try:
        s.adjustments[0] = radius
    except Exception:
        pass
    return s


def line(slide, l, t, w, h, color, weight=1.0):
    # EMU coordinates must be integers; centering math (/2, /4) yields floats,
    # and add_connector serializes them verbatim -> schema-invalid, triggers repair.
    ln = slide.shapes.add_connector(1, int(l), int(t), int(l + w), int(t + h))
    ln.line.color.rgb = color
    ln.line.width = Pt(weight)
    ln.shadow.inherit = False
    return ln


def txt(slide, l, t, w, h, text,
        size=14, bold=False, italic=False, color=INK,
        align=PP_ALIGN.LEFT, font=F_BODY, anchor=None,
        line_spacing=1.15):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    if anchor is not None:
        tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = line_spacing
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    r.font.name = font
    return tb


def multi_txt(slide, l, t, w, h, paragraphs, anchor=None):
    """paragraphs: list of dicts {text, size, bold, color, font, align, space_before}"""
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    if anchor is not None:
        tf.vertical_anchor = anchor
    for i, p in enumerate(paragraphs):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = p.get('align', PP_ALIGN.LEFT)
        if 'space_before' in p:
            para.space_before = Pt(p['space_before'])
        if 'line_spacing' in p:
            para.line_spacing = p['line_spacing']
        r = para.add_run()
        r.text = p['text']
        r.font.size = Pt(p.get('size', 14))
        r.font.bold = p.get('bold', False)
        r.font.italic = p.get('italic', False)
        r.font.color.rgb = p.get('color', INK)
        r.font.name = p.get('font', F_BODY)
    return tb


# ════════════════════════════════════════════════════════════════════════════
# Slide chrome (header, footer, wordmark, slide number)
# ════════════════════════════════════════════════════════════════════════════

def add_slide(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    # white background
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=BG)
    return s


def chrome(slide, page_num, total, title, eyebrow=None, subtitle=None,
           accent=BRAND):
    """Standard content-slide header."""
    # Left edge accent
    rect(slide, 0, 0, Inches(0.18), SLIDE_H, fill=accent)

    # Top-right wordmark
    txt(slide, Inches(11.2), Inches(0.35), Inches(2.0), Inches(0.35),
        "agentmemory", size=11, color=INK_MUTED, bold=True,
        font=F_BODY, align=PP_ALIGN.RIGHT)

    # Eyebrow tag
    if eyebrow:
        rounded(slide, Inches(0.7), Inches(0.4), Inches(2.1), Inches(0.32),
                radius=0.5, fill=PRIMARY_BG, line=None)
        txt(slide, Inches(0.7), Inches(0.42), Inches(2.1), Inches(0.3),
            eyebrow.upper(), size=10, bold=True, color=BRAND,
            align=PP_ALIGN.CENTER, font=F_TITLE)

    # Title
    title_top = Inches(0.88) if eyebrow else Inches(0.55)
    txt(slide, Inches(0.7), title_top, Inches(12.0), Inches(0.62),
        title, size=28, bold=True, color=INK, font=F_TITLE,
        line_spacing=1.0)

    # Subtitle
    if subtitle:
        txt(slide, Inches(0.7), title_top + Inches(0.66), Inches(12.0), Inches(0.4),
            subtitle, size=15, color=INK_MUTED, font=F_BODY,
            line_spacing=1.15)

    # Accent underline below title block
    sub_off = Inches(1.10) if subtitle else Inches(0.7)
    line(slide, Inches(0.7), title_top + sub_off, Inches(0.6), 0,
         color=BRAND, weight=2.5)

    # Footer: slide number, github
    rect(slide, 0, Inches(7.32), SLIDE_W, Inches(0.18), fill=SURFACE)
    txt(slide, Inches(0.4), Inches(7.34), Inches(6), Inches(0.16),
        "github.com/rohitg00/agentmemory", size=9, color=INK_FAINT, font=F_BODY)
    txt(slide, Inches(7.0), Inches(7.34), Inches(5.9), Inches(0.16),
        f"{page_num:02d}  /  {total:02d}",
        size=9, color=INK_FAINT, font=F_BODY, align=PP_ALIGN.RIGHT)


def content_top(slide, eyebrow=None):
    """Y coordinate where slide content should start (below header)."""
    return Inches(2.05) if eyebrow else Inches(1.75)


# ════════════════════════════════════════════════════════════════════════════
# Components
# ════════════════════════════════════════════════════════════════════════════

def card(slide, l, t, w, h, fill=CARD, accent=None, accent_side='left',
         radius=0.025):
    """Flat card with optional accent stripe (no elevation by design)."""
    s = rounded(slide, l, t, w, h, radius=radius, fill=fill,
                line=BORDER, line_w=0.5)
    if accent:
        if accent_side == 'left':
            rounded(slide, l, t, Inches(0.06), h, radius=0.5, fill=accent)
        elif accent_side == 'top':
            rounded(slide, l, t, w, Inches(0.07), radius=0.5, fill=accent)
    return s


def stat_badge(slide, l, t, w, h, value, label, color=BRAND, bg=PRIMARY_BG):
    rounded(slide, l, t, w, h, radius=0.04, fill=bg, line=None)
    txt(slide, l, t + Inches(0.18), w, Inches(0.55),
        value, size=28, bold=True, color=color, font=F_TITLE,
        align=PP_ALIGN.CENTER, line_spacing=1.0)
    txt(slide, l, t + Inches(0.78), w, Inches(0.3),
        label, size=10, color=INK_MUTED, font=F_BODY,
        align=PP_ALIGN.CENTER)


def icon_circle(slide, cx, cy, r, fill, glyph, glyph_color=INVERSE, glyph_size=14):
    """Circle icon with a glyph in the center."""
    l = cx - r
    t = cy - r
    d = r * 2
    shape(slide, MSO_SHAPE.OVAL, l, t, d, d, fill=fill, line=None)
    txt(slide, l, t + (d - Inches(0.4)) / 2, d, Inches(0.4),
        glyph, size=glyph_size, bold=True, color=glyph_color,
        align=PP_ALIGN.CENTER, font=F_TITLE)


def num_badge(slide, l, t, size, n, color=BRAND):
    """Numbered circle badge."""
    shape(slide, MSO_SHAPE.OVAL, l, t, size, size, fill=color, line=None)
    txt(slide, l, t + Inches(0.04), size, size - Inches(0.08),
        str(n), size=int(size.inches * 18), bold=True, color=INVERSE,
        align=PP_ALIGN.CENTER, font=F_TITLE, anchor=MSO_ANCHOR.MIDDLE)


# ── Syntax highlighting ────────────────────────────────────────────────────

import re

def tokenize_json(code):
    """Yield (text, color) tuples for JSON-ish code."""
    # patterns in priority order
    pat = re.compile(
        r'(//[^\n]*|#[^\n]*)'      # comments
        r'|("[^"\n]*")'             # strings
        r'|(\b\d+\.?\d*\b)'         # numbers
        r'|(\b(?:true|false|null)\b)'  # literals
    )
    pos = 0
    for m in pat.finditer(code):
        if m.start() > pos:
            yield (code[pos:m.start()], CODE_TEXT)
        if m.group(1):
            yield (m.group(1), CODE_COMMENT)
        elif m.group(2):
            # determine if this string is a key (followed by colon) or value
            after = code[m.end():m.end()+5]
            if after.lstrip().startswith(':'):
                yield (m.group(2), CODE_PROP)
            else:
                yield (m.group(2), CODE_STRING)
        elif m.group(3):
            yield (m.group(3), CODE_NUMBER)
        elif m.group(4):
            yield (m.group(4), CODE_NUMBER)
        pos = m.end()
    if pos < len(code):
        yield (code[pos:], CODE_TEXT)


def tokenize_bash(code):
    lines = code.split('\n')
    for i, ln in enumerate(lines):
        if i > 0:
            yield ('\n', CODE_TEXT)
        if ln.strip().startswith('#'):
            yield (ln, CODE_COMMENT)
            continue
        # split into tokens
        # match command (first word) and flags
        m = re.match(r'^(\s*)(\S+)(.*)$', ln)
        if not m:
            yield (ln, CODE_TEXT)
            continue
        indent, cmd, rest = m.groups()
        yield (indent, CODE_TEXT)
        yield (cmd, CODE_KEYWORD)
        # process rest
        pat = re.compile(r'(-{1,2}[A-Za-z0-9_-]+)|("[^"]*")|(\$\w+)')
        pos = 0
        for tm in pat.finditer(rest):
            if tm.start() > pos:
                yield (rest[pos:tm.start()], CODE_TEXT)
            if tm.group(1):
                yield (tm.group(1), CODE_PROP)
            elif tm.group(2):
                yield (tm.group(2), CODE_STRING)
            elif tm.group(3):
                yield (tm.group(3), CODE_NUMBER)
            pos = tm.end()
        if pos < len(rest):
            yield (rest[pos:], CODE_TEXT)


def code_block(slide, code, l, t, w, h, lang='json', size=12, title=None):
    """Dark code block with header bar, syntax highlighting, monospace."""
    # outer container
    rounded(slide, l, t, w, h, radius=0.025, fill=CODE_BG, line=None)
    # header bar (optional)
    header_h = Inches(0.32)
    has_header = title is not None
    if has_header:
        rounded(slide, l, t, w, header_h, radius=0.05, fill=CODE_PANEL_BG, line=None)
        # 3 dots (mac-style)
        for i, c in enumerate([C("EF4444"), C("F59E0B"), C("10B981")]):
            shape(slide, MSO_SHAPE.OVAL,
                  l + Inches(0.15) + i * Inches(0.18),
                  t + Inches(0.1),
                  Inches(0.13), Inches(0.13), fill=c, line=None)
        # title
        txt(slide, l + Inches(0.9), t + Inches(0.05), w - Inches(1.0), header_h,
            title, size=10, color=INK_FAINT, font=F_MONO, italic=True)

    # code content
    code_t = t + (header_h if has_header else Inches(0.15))
    code_h = h - (header_h if has_header else Inches(0.15)) - Inches(0.1)
    tb = slide.shapes.add_textbox(l + Inches(0.25), code_t,
                                   w - Inches(0.5), code_h)
    tf = tb.text_frame
    tf.word_wrap = False
    tf.margin_left = Emu(0)
    tf.margin_top = Emu(0)

    # tokenize
    tokens = list(tokenize_json(code) if lang == 'json' else
                  tokenize_bash(code) if lang == 'bash' else
                  [(code, CODE_TEXT)])

    # split tokens by newlines into paragraphs
    paragraphs = [[]]
    for text, color in tokens:
        parts = text.split('\n')
        for i, part in enumerate(parts):
            if i > 0:
                paragraphs.append([])
            if part:
                paragraphs[-1].append((part, color))

    for i, para_tokens in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.25
        if not para_tokens:
            r = p.add_run()
            r.text = " "
            r.font.size = Pt(size)
            r.font.name = F_MONO
            continue
        for text, color in para_tokens:
            r = p.add_run()
            r.text = text
            r.font.size = Pt(size)
            r.font.name = F_MONO
            r.font.color.rgb = color


# ── Charts ─────────────────────────────────────────────────────────────────

def _style_chart_text(chart):
    """Apply consistent Segoe UI typography to a chart."""
    try:
        if chart.has_title:
            chart.chart_title.text_frame.paragraphs[0].runs[0].font.name = F_TITLE
    except Exception:
        pass


def bar_chart(slide, categories, series_data, l, t, w, h,
              series_colors=None, has_legend=True, max_val=None,
              data_labels=True, suffix=""):
    """Horizontal bar chart."""
    data = CategoryChartData()
    data.categories = categories
    for name, vals in series_data:
        data.add_series(name, vals)
    chart = slide.shapes.add_chart(
        XL_CHART_TYPE.BAR_CLUSTERED, l, t, w, h, data
    ).chart

    chart.has_title = False
    chart.has_legend = has_legend
    if has_legend:
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.include_in_layout = False
        chart.legend.font.name = F_BODY
        chart.legend.font.size = Pt(10)
        chart.legend.font.color.rgb = INK_MUTED

    # style series
    if series_colors:
        for s, color in zip(chart.series, series_colors):
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = color
            s.format.line.fill.background()
            if data_labels:
                s.data_labels.show_value = True
                s.data_labels.font.size = Pt(10)
                s.data_labels.font.bold = True
                s.data_labels.font.color.rgb = INK
                s.data_labels.font.name = F_BODY
                s.data_labels.number_format = f'0.0"{suffix}"' if suffix else '0.0'
                s.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END

    # axis styling
    try:
        cat_axis = chart.category_axis
        cat_axis.tick_labels.font.name = F_BODY
        cat_axis.tick_labels.font.size = Pt(10)
        cat_axis.tick_labels.font.color.rgb = INK_SOFT
        val_axis = chart.value_axis
        val_axis.tick_labels.font.name = F_BODY
        val_axis.tick_labels.font.size = Pt(9)
        val_axis.tick_labels.font.color.rgb = INK_MUTED
        val_axis.visible = False
        if max_val is not None:
            val_axis.maximum_scale = max_val
            val_axis.minimum_scale = 0
    except Exception:
        pass

    return chart


# ── Native table ────────────────────────────────────────────────────────────

def table(slide, l, t, w, headers, rows, col_widths=None,
          header_fill=PRIMARY, header_text=INVERSE,
          row_alt=SURFACE, hdr_size=11, body_size=10,
          first_col_emphasis=True):
    n_cols = len(headers)
    n_rows = len(rows) + 1
    tbl = slide.shapes.add_table(n_rows, n_cols, l, t, w,
                                  Inches(0.42) * n_rows).table

    if col_widths:
        for i, cw in enumerate(col_widths):
            tbl.columns[i].width = cw

    # header
    for i, h in enumerate(headers):
        cell = tbl.cell(0, i)
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = header_fill
        cell.margin_left = Inches(0.12)
        cell.margin_right = Inches(0.12)
        cell.margin_top = Inches(0.08)
        cell.margin_bottom = Inches(0.08)
        p = cell.text_frame.paragraphs[0]
        r = p.add_run()
        r.text = h
        r.font.size = Pt(hdr_size)
        r.font.bold = True
        r.font.color.rgb = header_text
        r.font.name = F_TITLE

    # rows
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri + 1, ci)
            cell.text = ""
            cell.fill.solid()
            cell.fill.fore_color.rgb = row_alt if ri % 2 == 0 else BG
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.12)
            cell.margin_top = Inches(0.06)
            cell.margin_bottom = Inches(0.06)
            p = cell.text_frame.paragraphs[0]
            r = p.add_run()
            # strip **bold** markers
            v = str(val)
            bold = False
            color = INK_SOFT
            if v.startswith("**") and v.endswith("**"):
                v = v[2:-2]
                bold = True
                color = BRAND
            elif ci == 0 and first_col_emphasis:
                bold = True
                color = INK
            r.text = v
            r.font.size = Pt(body_size)
            r.font.bold = bold
            r.font.color.rgb = color
            r.font.name = F_BODY
    return tbl


# ════════════════════════════════════════════════════════════════════════════
# Sections / dividers
# ════════════════════════════════════════════════════════════════════════════

def section_divider(prs, num, title, subtitle):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    # full background
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=INK)
    # left dark + right accent panel split (offset cover style)
    rect(s, Inches(7.5), 0, SLIDE_W - Inches(7.5), SLIDE_H, fill=BRAND)
    # decorative dots
    for i in range(8):
        for j in range(5):
            x = Inches(7.7) + i * Inches(0.65)
            y = Inches(0.5) + j * Inches(1.3)
            shape(s, MSO_SHAPE.OVAL, x, y, Inches(0.08), Inches(0.08),
                  fill=C("3B82F6"), line=None)
    # big section number
    txt(s, Inches(0.6), Inches(1.2), Inches(6), Inches(2),
        f"{num:02d}", size=120, bold=True, color=PRIMARY_PALE,
        font=F_DISPLAY, line_spacing=1.0)
    # section label
    txt(s, Inches(0.6), Inches(3.4), Inches(6), Inches(0.35),
        f"SECTION {num}", size=11, bold=True, color=ACCENT,
        font=F_TITLE)
    # section title
    txt(s, Inches(0.6), Inches(3.8), Inches(7), Inches(1.3),
        title, size=44, bold=True, color=INVERSE, font=F_TITLE,
        line_spacing=1.05)
    # subtitle
    txt(s, Inches(0.6), Inches(5.5), Inches(6.5), Inches(1.5),
        subtitle, size=18, color=C("CBD5E1"), font=F_BODY,
        line_spacing=1.3)
    # wordmark on right panel
    txt(s, Inches(7.5), Inches(0.6), Inches(SLIDE_W.inches - 7.5 - 0.6),
        Inches(0.4),
        "agentmemory", size=12, bold=True, color=INVERSE,
        align=PP_ALIGN.RIGHT, font=F_BODY)
    return s


# ════════════════════════════════════════════════════════════════════════════
# SLIDES
# ════════════════════════════════════════════════════════════════════════════

TOTAL_SLIDES = 34  # used for the page-number footer


def slide_01_title(prs):
    s = add_slide(prs)
    rect(s, 0, 0, SLIDE_W, SLIDE_H, fill=BG)
    # left edge accent
    rect(s, 0, 0, Inches(0.18), SLIDE_H, fill=BRAND)
    # subtle decorative grid pattern in top right
    for i in range(12):
        for j in range(6):
            x = Inches(8.5) + i * Inches(0.4)
            y = Inches(0.5) + j * Inches(0.4)
            shape(s, MSO_SHAPE.OVAL, x, y, Inches(0.05), Inches(0.05),
                  fill=PRIMARY_PALE, line=None)
    # version tag
    rounded(s, Inches(0.7), Inches(2.0), Inches(2.2), Inches(0.4),
            radius=0.5, fill=PRIMARY_BG, line=None)
    txt(s, Inches(0.7), Inches(2.04), Inches(2.2), Inches(0.35),
        "TECHNICAL DEEP DIVE", size=10, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)
    # big wordmark
    txt(s, Inches(0.6), Inches(2.7), Inches(12), Inches(1.6),
        "agentmemory", size=84, color=INK, font=F_DISPLAY,
        line_spacing=1.0, bold=False)
    # subtitle
    txt(s, Inches(0.7), Inches(4.4), Inches(12), Inches(0.7),
        "Persistent memory for AI coding agents",
        size=24, color=INK_SOFT, font=F_BODY, line_spacing=1.1)
    # brand bar
    rect(s, Inches(0.7), Inches(5.15), Inches(0.8), Inches(0.06), fill=BRAND)
    # description
    txt(s, Inches(0.7), Inches(5.4), Inches(11), Inches(0.7),
        "An engineer's walkthrough of architecture, retrieval, benchmarks, and design tradeoffs.",
        size=14, color=INK_MUTED, font=F_BODY, italic=True,
        line_spacing=1.3)
    # footer
    rect(s, 0, Inches(7.0), SLIDE_W, Inches(0.5), fill=SURFACE)
    txt(s, Inches(0.7), Inches(7.12), Inches(8), Inches(0.3),
        "github.com/rohitg00/agentmemory  ·  npm: @agentmemory/agentmemory",
        size=11, color=INK_MUTED, font=F_BODY)
    txt(s, Inches(8), Inches(7.12), Inches(4.6), Inches(0.3),
        "v0.9.26  ·  MIT License",
        size=11, color=INK_MUTED, font=F_BODY, align=PP_ALIGN.RIGHT)
    return s


# ─── SECTION 1: THE PROBLEM ─────────────────────────────────────────────────

def slide_02_amnesia(prs):
    s = add_slide(prs)
    chrome(s, 2, TOTAL_SLIDES,
           "The Amnesia Problem",
           eyebrow="The Problem",
           subtitle="AI coding agents start every session from zero — no memory of what came before.")

    # Two columns: Session 1 / Session 2
    col_w = Inches(5.85)
    col_h = Inches(4.6)
    col_t = Inches(2.45)

    # Session 1 — what was done
    s1_items = [
        ("✓", "Set up JWT auth with jose (Edge-compatible)"),
        ("✓", "Auth middleware lives in src/middleware/auth.ts"),
        ("✓", "Chose jose over jsonwebtoken — runtime constraint"),
        ("✓", "Redis sliding-window rate limiter wired up"),
        ("✓", "Fixed N+1 on /api/users endpoint"),
    ]
    s2_items = [
        ("?", "What auth library are we using?"),
        ("?", "Where does the auth middleware live?"),
        ("?", "Why did we pick jose?"),
        ("?", "Do we have a rate limiter?"),
        ("?", "Any known performance issues?"),
    ]

    for ci, (label, items, color, glyph_color) in enumerate([
        ("Session 1  ·  Monday", s1_items, SUCCESS, SUCCESS),
        ("Session 2  ·  Friday  →  same agent, no memory", s2_items, ERROR, ERROR),
    ]):
        x = Inches(0.7) + ci * Inches(6.1)
        card(s, x, col_t, col_w, col_h, accent=color, accent_side='top')
        txt(s, x + Inches(0.35), col_t + Inches(0.25), col_w - Inches(0.5), Inches(0.4),
            label, size=14, bold=True, color=color, font=F_TITLE)

        for i, (glyph, item) in enumerate(items):
            y = col_t + Inches(0.85) + i * Inches(0.7)
            icon_circle(s, x + Inches(0.55), y + Inches(0.18),
                        Inches(0.16), color, glyph, INVERSE, 11)
            txt(s, x + Inches(0.9), y + Inches(0.07), col_w - Inches(1.1), Inches(0.35),
                item, size=12, color=INK_SOFT)

    # Bottom callout
    callout_t = Inches(7.05)
    txt(s, Inches(0.7), Inches(7.13), Inches(12), Inches(0.3),
        "Re-explaining wastes 10–20 minutes and thousands of tokens at the start of every new session.",
        size=11, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER)


def slide_03_reexplain(prs):
    s = add_slide(prs)
    chrome(s, 3, TOTAL_SLIDES,
           "What You Re-explain Every Session",
           eyebrow="The Problem",
           subtitle="The cost is hidden but compounds — every session, every project, every developer.")

    items = [
        ("Architecture", "Module boundaries · service layout · monorepo structure", BRAND),
        ("Library choices", "Why jose not jsonwebtoken · async-std not tokio", PURPLE),
        ("Team conventions", "Test-first · no DB mocks · functional style preferred", SUCCESS),
        ("Bug history", "Fixed issues · known edge cases · workarounds applied", GOLD),
        ("Auth & security", "Middleware location · JWT strategy · session handling", ERROR),
        ("Deployment", "Env vars · infra constraints · deploy script patterns", TEAL),
    ]

    grid_top = Inches(2.1)
    cw = Inches(4.0)
    ch = Inches(1.55)
    gap_x = Inches(0.2)
    gap_y = Inches(0.2)

    for i, (label, desc, color) in enumerate(items):
        row, col = i // 3, i % 3
        x = Inches(0.7) + col * (cw + gap_x)
        y = grid_top + row * (ch + gap_y)
        card(s, x, y, cw, ch, accent=color, accent_side='left')
        # icon dot
        shape(s, MSO_SHAPE.OVAL, x + Inches(0.3), y + Inches(0.32),
              Inches(0.18), Inches(0.18), fill=color, line=None)
        txt(s, x + Inches(0.6), y + Inches(0.26), cw - Inches(0.8), Inches(0.35),
            label, size=14, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(0.3), y + Inches(0.72), cw - Inches(0.5), Inches(0.75),
            desc, size=11, color=INK_MUTED, line_spacing=1.35)

    # Stats strip
    strip_t = Inches(5.7)
    txt(s, Inches(0.7), strip_t, Inches(12), Inches(0.3),
        "The compounding cost", size=12, bold=True, color=INK,
        font=F_TITLE)
    for i, (val, lbl, color) in enumerate([
        ("10–20m", "Lost per session start", BRAND),
        ("22,000+", "Tokens to paste 240 obs", PURPLE),
        ("$500+/yr", "Cost of LLM-summarized memory", ERROR),
    ]):
        x = Inches(0.7) + i * Inches(4.2)
        stat_badge(s, x, strip_t + Inches(0.4), Inches(4.0), Inches(1.05),
                   val, lbl, color=color, bg=SURFACE)


def slide_04_static_file(prs):
    s = add_slide(prs)
    chrome(s, 4, TOTAL_SLIDES,
           "The Static File Trap",
           eyebrow="The Problem",
           subtitle="CLAUDE.md, .cursorrules, .windsurfrules — they all hit the same wall.")

    problems = [
        ("01", "Manual to maintain",
         "You write it. You keep it current. It never updates itself."),
        ("02", "Truncated at ~200 lines",
         "Anything past the limit is invisible to the agent."),
        ("03", "No retrieval logic",
         "Entire file loaded into context whether relevant or not."),
        ("04", "Goes stale silently",
         "Codebase evolves. The file doesn't. Stale context misleads."),
        ("05", "Single-agent only",
         "CLAUDE.md serves Claude Code. Copilot, Cursor, Codex — they see nothing."),
    ]

    for i, (num, title, desc) in enumerate(problems):
        y = Inches(2.15) + i * Inches(0.92)
        # number column
        txt(s, Inches(0.7), y + Inches(0.1), Inches(0.7), Inches(0.6),
            num, size=24, bold=False, color=INK_FAINT, font=F_DISPLAY)
        # vertical line
        rect(s, Inches(1.4), y + Inches(0.05), Inches(0.02), Inches(0.7),
             fill=BORDER)
        # title
        txt(s, Inches(1.6), y + Inches(0.1), Inches(4), Inches(0.4),
            title, size=15, bold=True, color=INK, font=F_TITLE)
        # description
        txt(s, Inches(1.6), y + Inches(0.45), Inches(11), Inches(0.4),
            desc, size=12, color=INK_MUTED)


def slide_05_existing(prs):
    s = add_slide(prs)
    chrome(s, 5, TOTAL_SLIDES,
           "Existing Solutions Fall Short",
           eyebrow="The Problem",
           subtitle="Nothing on the market was built for the coding-agent use case end-to-end.")

    cols = [
        ("mem0", "53K ★ on GitHub", [
            "Requires manual add() calls",
            "No automatic capture",
            "Must instrument every step",
            "No hook-based integration",
            "No multi-agent coordination",
        ], PURPLE),
        ("Letta / MemGPT", "22K ★ on GitHub", [
            "Full runtime replacement",
            "High framework lock-in",
            "Can't use your existing agent",
            "Requires re-architecting",
            "Not cross-agent",
        ], TEAL),
        ("Static files", "CLAUDE.md · .cursorrules", [
            "Manual maintenance burden",
            "Truncates at ~200 lines",
            "No smart retrieval",
            "Single-agent only",
            "Goes stale silently",
        ], GOLD),
    ]

    col_w = Inches(4.0)
    col_h = Inches(4.55)
    col_t = Inches(2.15)
    gap = Inches(0.18)

    for i, (name, meta, items, color) in enumerate(cols):
        x = Inches(0.7) + i * (col_w + gap)
        card(s, x, col_t, col_w, col_h, accent=color, accent_side='top')
        txt(s, x + Inches(0.3), col_t + Inches(0.3), col_w - Inches(0.6), Inches(0.4),
            name, size=18, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(0.3), col_t + Inches(0.7), col_w - Inches(0.6), Inches(0.3),
            meta, size=10, color=INK_MUTED, italic=True)
        # divider
        line(s, x + Inches(0.3), col_t + Inches(1.15),
             col_w - Inches(0.6), 0, color=BORDER)
        for j, item in enumerate(items):
            y = col_t + Inches(1.4) + j * Inches(0.55)
            txt(s, x + Inches(0.3), y, Inches(0.25), Inches(0.4),
                "✗", size=14, bold=True, color=ERROR, font=F_TITLE)
            txt(s, x + Inches(0.6), y + Inches(0.02), col_w - Inches(0.8), Inches(0.4),
                item, size=11, color=INK_SOFT)

    # bottom gap statement
    rounded(s, Inches(0.7), Inches(6.92), Inches(11.93), Inches(0.32),
            radius=0.4, fill=PRIMARY_BG)
    txt(s, Inches(0.7), Inches(6.95), Inches(11.93), Inches(0.3),
        "The gap: automatic capture · cross-agent · zero external DBs · smart retrieval",
        size=11, bold=True, color=BRAND, align=PP_ALIGN.CENTER, font=F_TITLE)


# ─── SECTION 2: INTRODUCING agentmemory ─────────────────────────────────────

def slide_06_what_is(prs):
    s = add_slide(prs)
    chrome(s, 7, TOTAL_SLIDES,
           "What Is agentmemory?",
           eyebrow="Introducing",
           subtitle="A persistent memory engine that fits into your existing agent — no rewrite, no lock-in.")

    props = [
        ("⚡", "Automatic",
         "12 lifecycle hooks capture observations on every tool use. Zero manual add() calls.",
         BRAND),
        ("◆", "Cross-agent",
         "One memory store for Claude Code, Copilot CLI, Cursor, Codex, Gemini CLI, and 10+ more.",
         PURPLE),
        ("⊕", "Smart retrieval",
         "Hybrid BM25 + Vector + Graph search. 95.2% R@5 on LongMemEval-S (ICLR 2025).",
         SUCCESS),
        ("⬢", "Zero dependencies",
         "SQLite only. No Qdrant, no pgvector, no Postgres. Runs offline.",
         GOLD),
    ]

    cw = Inches(5.85)
    ch = Inches(2.2)
    ct = Inches(2.1)

    for i, (glyph, title_, desc, color) in enumerate(props):
        row, col = i // 2, i % 2
        x = Inches(0.7) + col * Inches(6.1)
        y = ct + row * Inches(2.45)
        card(s, x, y, cw, ch)
        # icon
        icon_circle(s, x + Inches(0.7), y + Inches(0.8),
                    Inches(0.42), color, glyph, INVERSE, 22)
        # title
        txt(s, x + Inches(1.5), y + Inches(0.35), cw - Inches(1.7), Inches(0.45),
            title_, size=20, bold=True, color=INK, font=F_TITLE)
        # description
        txt(s, x + Inches(1.5), y + Inches(0.9), cw - Inches(1.7), Inches(1.2),
            desc, size=13, color=INK_MUTED, line_spacing=1.4)


def slide_07_how_it_fixes(prs):
    s = add_slide(prs)
    chrome(s, 8, TOTAL_SLIDES,
           "How It Fixes the Problem",
           eyebrow="Introducing",
           subtitle="A four-stage pipeline: capture → consolidate → retrieve → inject.")

    steps = [
        ("Capture", "Hooks fire on every tool use.\nDedup + privacy filter applied.", BRAND),
        ("Consolidate", "4-tier memory: Working → Episodic\n→ Semantic → Procedural.", PURPLE),
        ("Retrieve", "Triple-stream hybrid search.\nBM25 + Vector + Graph, RRF-fused.", SUCCESS),
        ("Inject", "~1,900 tokens of relevant context.\nToken-budgeted at session start.", GOLD),
    ]

    cw = Inches(2.85)
    ch = Inches(3.2)
    ct = Inches(2.3)
    gap = Inches(0.2)
    total = 4 * cw + 3 * gap
    start_x = (SLIDE_W - total) / 2

    for i, (label, desc, color) in enumerate(steps):
        x = start_x + i * (cw + gap)
        card(s, x, ct, cw, ch, accent=color, accent_side='top')
        # step number
        num_badge(s, x + (cw - Inches(0.6)) / 2, ct + Inches(0.45),
                  Inches(0.6), i + 1, color=color)
        # title
        txt(s, x, ct + Inches(1.2), cw, Inches(0.5),
            label, size=20, bold=True, color=INK, font=F_TITLE,
            align=PP_ALIGN.CENTER)
        # divider
        line(s, x + Inches(0.9), ct + Inches(1.78),
             cw - Inches(1.8), 0, color=color, weight=2)
        # description
        txt(s, x + Inches(0.25), ct + Inches(2.0), cw - Inches(0.5), Inches(1.1),
            desc, size=12, color=INK_MUTED, align=PP_ALIGN.CENTER, line_spacing=1.45)
        # arrow
        if i < 3:
            ax = x + cw + Inches(0.02)
            txt(s, ax, ct + Inches(1.4), gap, Inches(0.4),
                "→", size=18, bold=True, color=INK_FAINT,
                align=PP_ALIGN.CENTER, font=F_TITLE)

    # bottom impact statement
    rounded(s, Inches(0.7), Inches(5.85), Inches(11.93), Inches(1.0),
            radius=0.04, fill=PRIMARY_BG)
    txt(s, Inches(0.9), Inches(6.0), Inches(11.6), Inches(0.4),
        "RESULT", size=10, bold=True, color=BRAND, font=F_TITLE)
    txt(s, Inches(0.9), Inches(6.3), Inches(11.6), Inches(0.5),
        "Every session begins with full project context — no re-explaining, no wasted tokens.",
        size=15, color=INK, font=F_BODY, italic=False)


def slide_08_quickstart(prs):
    s = add_slide(prs)
    chrome(s, 9, TOTAL_SLIDES,
           "Quick Start",
           eyebrow="Introducing",
           subtitle="Four commands to a fully wired memory backend across your agents.")

    bash_code = """\
# 1. Install globally
npm install -g @agentmemory/agentmemory

# 2. Start the memory server (port 3111)
agentmemory

# 3. Seed sample sessions and verify recall
agentmemory demo

# 4. Wire MCP + 12 hooks into your agent
agentmemory connect claude-code
# Also: copilot-cli  codex  cursor  gemini-cli  opencode  ..."""

    code_block(s, bash_code, Inches(0.7), Inches(2.2),
               Inches(8.5), Inches(3.9),
               lang='bash', size=13, title="terminal — install & wire up")

    # right side: what it does
    info_x = Inches(9.45)
    info_w = Inches(3.2)
    info_t = Inches(2.2)
    card(s, info_x, info_t, info_w, Inches(3.9))

    txt(s, info_x + Inches(0.25), info_t + Inches(0.25),
        info_w - Inches(0.5), Inches(0.4),
        "What happens", size=14, bold=True, color=INK, font=F_TITLE)
    line(s, info_x + Inches(0.25), info_t + Inches(0.7),
         Inches(0.5), 0, color=BRAND, weight=2)

    bullets = [
        ("connect", "Writes MCP config to .claude/settings.json"),
        ("12 hooks", "Installed automatically for the agent"),
        ("Skills", "8 native skills installed via npx"),
        ("Viewer", "Live UI available at :3113"),
    ]
    for i, (lbl, desc) in enumerate(bullets):
        y = info_t + Inches(0.95) + i * Inches(0.7)
        shape(s, MSO_SHAPE.OVAL, info_x + Inches(0.25), y + Inches(0.12),
              Inches(0.1), Inches(0.1), fill=BRAND, line=None)
        txt(s, info_x + Inches(0.45), y, info_w - Inches(0.6), Inches(0.3),
            lbl, size=11, bold=True, color=INK, font=F_TITLE)
        txt(s, info_x + Inches(0.45), y + Inches(0.25),
            info_w - Inches(0.6), Inches(0.35),
            desc, size=10, color=INK_MUTED, line_spacing=1.3)

    # bottom: time to value
    txt(s, Inches(0.7), Inches(6.4), Inches(12), Inches(0.3),
        "Total time to value: ~90 seconds.",
        size=12, color=INK_MUTED, italic=True, font=F_BODY)


# ─── SECTION 3: ARCHITECTURE ────────────────────────────────────────────────

def _arch_block(slide, l, t, w, h, label, sublabel=None,
                fill=BG, border=BORDER, label_color=INK, sublabel_color=INK_MUTED):
    rounded(slide, l, t, w, h, radius=0.05, fill=fill, line=border, line_w=0.75)
    if sublabel:
        txt(slide, l, t + Inches(0.1), w, Inches(0.4),
            label, size=12, bold=True, color=label_color,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(slide, l, t + Inches(0.42), w, Inches(0.3),
            sublabel, size=9, color=sublabel_color,
            align=PP_ALIGN.CENTER, font=F_BODY)
    else:
        txt(slide, l, t + Inches(0.15), w, h - Inches(0.3),
            label, size=11, bold=True, color=label_color,
            align=PP_ALIGN.CENTER, font=F_TITLE, anchor=MSO_ANCHOR.MIDDLE)


def _arch_arrow(slide, x1, y1, x2, y2, color=INK_FAINT):
    ln = slide.shapes.add_connector(2, int(x1), int(y1), int(x2), int(y2))  # straight
    ln.line.color.rgb = color
    ln.line.width = Pt(1.5)
    ln.shadow.inherit = False
    # arrow head via XML
    lnEl = ln.line._get_or_add_ln()
    tail = etree.SubElement(lnEl, qn('a:tailEnd'))
    tail.set('type', 'triangle')
    tail.set('w', 'sm')
    tail.set('len', 'sm')


def slide_09_architecture(prs):
    s = add_slide(prs)
    chrome(s, 10, TOTAL_SLIDES,
           "System Architecture",
           eyebrow="Architecture",
           subtitle="Three integration surfaces, one engine, one SQLite file. No external services.")

    # ── Layer 1: Agents ─────────────────────────────────────────
    top_y = Inches(2.05)
    agents = ["Claude Code", "Copilot CLI", "Cursor", "Codex", "Gemini CLI", "OpenCode"]
    agent_w = Inches(1.65)
    agent_h = Inches(0.55)
    agent_gap = Inches(0.1)
    total_w = 6 * agent_w + 5 * agent_gap
    start_x = (SLIDE_W - total_w) / 2

    txt(s, Inches(0.7), top_y - Inches(0.32), Inches(4), Inches(0.3),
        "AGENT ECOSYSTEM", size=9, bold=True, color=INK_MUTED, font=F_TITLE)

    for i, a in enumerate(agents):
        x = start_x + i * (agent_w + agent_gap)
        rounded(s, x, top_y, agent_w, agent_h, radius=0.1,
                fill=INK, line=None)
        txt(s, x, top_y + Inches(0.13), agent_w, Inches(0.3),
            a, size=10, bold=True, color=INVERSE,
            align=PP_ALIGN.CENTER, font=F_TITLE)

    # ── Layer 2: Integration surfaces ─────────────────────────────
    surf_y = Inches(3.0)
    surf_w = Inches(3.6)
    surf_h = Inches(0.7)
    surf_gap = Inches(0.4)
    surf_total = 3 * surf_w + 2 * surf_gap
    surf_start = (SLIDE_W - surf_total) / 2

    surfaces = [
        ("12 Lifecycle Hooks", "auto-capture on every tool use", BRAND),
        ("MCP Server", "53 tools · Model Context Protocol", PURPLE),
        ("REST API  ·  :3111", "language-agnostic integration", TEAL),
    ]
    txt(s, Inches(0.7), surf_y - Inches(0.32), Inches(4), Inches(0.3),
        "INTEGRATION SURFACES", size=9, bold=True, color=INK_MUTED, font=F_TITLE)

    for i, (label, sublabel, color) in enumerate(surfaces):
        x = surf_start + i * (surf_w + surf_gap)
        rounded(s, x, surf_y, surf_w, surf_h, radius=0.05,
                fill=BG, line=color, line_w=1.5)
        txt(s, x, surf_y + Inches(0.08), surf_w, Inches(0.32),
            label, size=12, bold=True, color=color,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x, surf_y + Inches(0.4), surf_w, Inches(0.28),
            sublabel, size=9, color=INK_MUTED, italic=True,
            align=PP_ALIGN.CENTER)

    # arrows: agents -> surfaces (just visual)
    for i in range(3):
        ax = surf_start + i * (surf_w + surf_gap) + surf_w / 2
        _arch_arrow(s, ax, top_y + agent_h, ax, surf_y, color=BORDER_STR)

    # ── Layer 3: Core engine ─────────────────────────────────────
    core_y = Inches(4.15)
    core_w = Inches(10.8)
    core_h = Inches(1.55)
    core_x = (SLIDE_W - core_w) / 2

    rounded(s, core_x, core_y, core_w, core_h, radius=0.04,
            fill=PRIMARY_BG, line=BRAND, line_w=1.5)
    txt(s, core_x, core_y + Inches(0.12), core_w, Inches(0.35),
        "AGENTMEMORY CORE  ·  iii-engine",
        size=11, bold=True, color=BRAND,
        align=PP_ALIGN.CENTER, font=F_TITLE)
    # Four sub-blocks
    sub_w = (core_w - Inches(0.6)) / 4
    sub_x_start = core_x + Inches(0.12)
    sub_y = core_y + Inches(0.55)
    subs = [
        ("Capture", "dedup · privacy filter"),
        ("Processing", "compress · embed · index"),
        ("Retrieval", "BM25 + Vector + Graph"),
        ("Management", "decay · leases · multi-agent"),
    ]
    for i, (lbl, sub) in enumerate(subs):
        x = sub_x_start + i * (sub_w + Inches(0.16))
        rounded(s, x, sub_y, sub_w, Inches(0.9), radius=0.06,
                fill=BG, line=PRIMARY_PALE)
        txt(s, x, sub_y + Inches(0.12), sub_w, Inches(0.3),
            lbl, size=11, bold=True, color=INK,
            align=PP_ALIGN.CENTER, font=F_TITLE)
        txt(s, x, sub_y + Inches(0.45), sub_w, Inches(0.4),
            sub, size=9, color=INK_MUTED,
            align=PP_ALIGN.CENTER, italic=True, line_spacing=1.3)

    # arrow surfaces -> core
    for i in range(3):
        ax = surf_start + i * (surf_w + surf_gap) + surf_w / 2
        _arch_arrow(s, ax, surf_y + surf_h, ax, core_y, color=BORDER_STR)

    # ── Layer 4: Storage & UIs ─────────────────────────────────
    bot_y = Inches(6.0)
    bot_items = [
        ("⬢ SQLite  ·  ~/.agentmemory/memory.db", "single-file storage", INK),
        ("◐ Real-time Viewer  ·  :3113", "live observation stream", PURPLE),
        ("⌘ iii Console  ·  :3114", "full operation trace", TEAL),
    ]
    bot_w = Inches(3.6)
    bot_h = Inches(0.85)
    bot_gap = Inches(0.4)
    bot_total = 3 * bot_w + 2 * bot_gap
    bot_start = (SLIDE_W - bot_total) / 2

    for i, (lbl, sub, color) in enumerate(bot_items):
        x = bot_start + i * (bot_w + bot_gap)
        rounded(s, x, bot_y, bot_w, bot_h, radius=0.05,
                fill=BG, line=BORDER, line_w=0.75)
        rounded(s, x, bot_y, Inches(0.07), bot_h, radius=0.5, fill=color)
        txt(s, x + Inches(0.2), bot_y + Inches(0.12), bot_w - Inches(0.4), Inches(0.32),
            lbl, size=11, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(0.2), bot_y + Inches(0.45), bot_w - Inches(0.4), Inches(0.32),
            sub, size=9, color=INK_MUTED, italic=True)

    # core -> storage arrows
    cx_mid = core_x + core_w / 2
    _arch_arrow(s, cx_mid, core_y + core_h, cx_mid, bot_y, color=BORDER_STR)


def slide_10_hooks(prs):
    s = add_slide(prs)
    chrome(s, 11, TOTAL_SLIDES,
           "The 12 Lifecycle Hooks",
           eyebrow="Architecture",
           subtitle="Every tool use fires a hook — zero manual instrumentation, full coverage.")

    headers = ["Hook", "When it fires", "What it captures"]
    rows = [
        ["SessionStart", "Agent boots", "Project path, session ID, environment"],
        ["UserPromptSubmit", "User sends a prompt", "Prompt text (privacy-filtered)"],
        ["PreToolUse", "Before tool execution", "File access patterns, enriched context"],
        ["PostToolUse", "After tool execution", "Tool name, input params, full output"],
        ["PostToolUseFailure", "Tool errors", "Error message, stack, debugging info"],
        ["PreCompact", "Before context compaction", "Re-injects relevant memory"],
        ["SubagentStart", "Nested agent begins", "Inherits parent memory scope"],
        ["SubagentStop", "Nested agent ends", "Merges observations back to parent"],
        ["Stop", "Agent session ending", "Triggers session summary generation"],
        ["SessionEnd", "Session fully complete", "Runs 4-tier consolidation + graph extract"],
    ]
    table(s, Inches(0.7), Inches(2.15), Inches(11.93),
          headers, rows,
          col_widths=[Inches(2.5), Inches(3.0), Inches(6.43)],
          hdr_size=12, body_size=10.5,
          first_col_emphasis=True)


def slide_11_pipeline(prs):
    s = add_slide(prs)
    chrome(s, 12, TOTAL_SLIDES,
           "Memory Capture Pipeline",
           eyebrow="Architecture",
           subtitle="From PostToolUse to indexed memory in one async flow.")

    steps = [
        ("Hook fires", "PostToolUse intercepts every tool result", BRAND),
        ("Dedup", "SHA-256 hash · 5-minute window", PURPLE),
        ("Privacy filter", "Strip API keys, secrets, <private> tags", SUCCESS),
        ("Store raw", "Write observation row to SQLite", TEAL),
        ("LLM compress", "Extract facts · concepts · narrative", GOLD),
        ("Embed", "Vector via 6-provider fallback chain", ERROR),
        ("Index", "BM25 shards + HNSW vector index", BRAND),
    ]

    # Two columns of cards with arrows between
    cw = Inches(11.5)
    ch = Inches(0.62)
    cy_start = Inches(2.15)
    gap = Inches(0.1)

    for i, (label, desc, color) in enumerate(steps):
        y = cy_start + i * (ch + gap)
        x = Inches(0.91)
        # number badge
        num_badge(s, Inches(0.7), y + Inches(0.11),
                  Inches(0.4), i + 1, color=color)
        # card
        rounded(s, x + Inches(0.25), y, cw - Inches(0.3), ch,
                radius=0.05, fill=BG, line=BORDER, line_w=0.5)
        # vertical accent
        rounded(s, x + Inches(0.25), y, Inches(0.07), ch, radius=0.5, fill=color)
        # text
        txt(s, x + Inches(0.5), y + Inches(0.08), Inches(2.5), Inches(0.4),
            label, size=13, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(3.2), y + Inches(0.12), Inches(8.0), Inches(0.4),
            desc, size=11, color=INK_MUTED)


def slide_12_4tier(prs):
    s = add_slide(prs)
    chrome(s, 13, TOTAL_SLIDES,
           "The 4-Tier Memory Model",
           eyebrow="Architecture",
           subtitle="Inspired by human sleep-based memory consolidation — neuroscience meets agent design.")

    tiers = [
        ("Working", "Raw tool observations", "Short-term memory",
         "5-min session window · decays on inactivity", BRAND),
        ("Episodic", "Compressed session summaries", '"What happened"',
         "Per-session stories · distilled from working", PURPLE),
        ("Semantic", "Extracted facts & patterns", '"What I know"',
         "Persistent · grows over time · cross-session", SUCCESS),
        ("Procedural", "Recurring workflows", '"How to do it"',
         "Detected from semantic pattern repetition", GOLD),
    ]

    # Stacked vertical "pyramid" - each tier as a card
    cw = Inches(11.93)
    ch = Inches(0.95)
    ct = Inches(2.15)
    gap = Inches(0.12)

    for i, (name, what, analogy, lifecycle, color) in enumerate(tiers):
        y = ct + i * (ch + gap)
        card(s, Inches(0.7), y, cw, ch, accent=color, accent_side='left')
        # Big tier number
        txt(s, Inches(0.95), y + Inches(0.2), Inches(0.7), Inches(0.7),
            f"0{i+1}", size=22, color=color, font=F_DISPLAY, bold=False)
        # Name
        txt(s, Inches(1.7), y + Inches(0.12), Inches(2.5), Inches(0.4),
            name, size=18, bold=True, color=INK, font=F_TITLE)
        txt(s, Inches(1.7), y + Inches(0.5), Inches(2.5), Inches(0.4),
            analogy, size=10, color=color, italic=True, font=F_BODY)
        # What
        txt(s, Inches(4.5), y + Inches(0.16), Inches(3.5), Inches(0.35),
            "WHAT", size=8, bold=True, color=INK_FAINT, font=F_TITLE)
        txt(s, Inches(4.5), y + Inches(0.4), Inches(3.5), Inches(0.5),
            what, size=12, color=INK)
        # Lifecycle
        txt(s, Inches(8.3), y + Inches(0.16), Inches(4.2), Inches(0.35),
            "LIFECYCLE", size=8, bold=True, color=INK_FAINT, font=F_TITLE)
        txt(s, Inches(8.3), y + Inches(0.4), Inches(4.2), Inches(0.5),
            lifecycle, size=12, color=INK)

    # flow indicator
    txt(s, Inches(0.7), Inches(6.6), Inches(12), Inches(0.3),
        "Memories flow upward as they are reinforced and compressed:  Working → Episodic → Semantic → Procedural",
        size=11, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER)


def slide_13_decay(prs):
    s = add_slide(prs)
    chrome(s, 14, TOTAL_SLIDES,
           "Decay & Strengthening",
           eyebrow="Architecture",
           subtitle="Memories age, fade, and get reinforced — the Ebbinghaus forgetting curve, applied.")

    # Two cards
    cards = [
        ("Forgetting (decay)", ERROR, [
            "Observations lose relevance over time (Ebbinghaus curve)",
            "Per-memory decay weight: recent = high, old = low",
            "Decay is per-memory, not per-session — key decisions stay alive",
            "Memories at relevance floor become eviction candidates",
            "--quota flag triggers importance-based eviction on disk pressure",
        ]),
        ("Strengthening (reinforcement)", SUCCESS, [
            "Frequently retrieved memories get a weight boost",
            "More recall = more accessible (positive feedback loop)",
            "Contradictions auto-detected and resolved",
            "Supersession: newer fact replaces older one on same topic",
            "Git snapshots allow rolling back memory state if needed",
        ]),
    ]

    cw = Inches(5.85)
    ch = Inches(4.7)
    ct = Inches(2.15)

    for ci, (title_, color, items) in enumerate(cards):
        x = Inches(0.7) + ci * Inches(6.1)
        card(s, x, ct, cw, ch, accent=color, accent_side='top')
        # title
        txt(s, x + Inches(0.35), ct + Inches(0.3),
            cw - Inches(0.5), Inches(0.4),
            title_, size=18, bold=True, color=color, font=F_TITLE)
        line(s, x + Inches(0.35), ct + Inches(0.85),
             Inches(0.7), 0, color=color, weight=2)
        for i, item in enumerate(items):
            y = ct + Inches(1.15) + i * Inches(0.7)
            # icon
            shape(s, MSO_SHAPE.OVAL,
                  x + Inches(0.4), y + Inches(0.12),
                  Inches(0.16), Inches(0.16),
                  fill=color, line=None)
            glyph = "✓" if color == SUCCESS else "↓"
            txt(s, x + Inches(0.4), y + Inches(0.05),
                Inches(0.16), Inches(0.3),
                glyph, size=9, bold=True, color=INVERSE,
                align=PP_ALIGN.CENTER, font=F_TITLE)
            txt(s, x + Inches(0.7), y + Inches(0.05),
                cw - Inches(1.0), Inches(0.6),
                item, size=11.5, color=INK_SOFT, line_spacing=1.3)


def slide_14_storage(prs):
    s = add_slide(prs)
    chrome(s, 15, TOTAL_SLIDES,
           "Storage  ·  SQLite, Zero External DBs",
           eyebrow="Architecture",
           subtitle="A single file. No server. No Postgres. No Qdrant. Works offline.")

    items = [
        ("Single file", "~/.agentmemory/memory.db — portable, backup-friendly, offline-first"),
        ("Schema", "observations + facts + embeddings + decay weights + provenance"),
        ("BM25 index", "Sharded for scale · manifest commit/rollback prevents corruption"),
        ("Vector index", "HNSW (Hierarchical Navigable Small World) · cosine similarity"),
        ("Multi-agent", "Namespaced: project:agent1 (shared) + project:agent1:private"),
        ("No externals", "No Qdrant · no pgvector · no Postgres · no Redis · just SQLite"),
    ]

    for i, (label, desc) in enumerate(items):
        row, col = i // 2, i % 2
        x = Inches(0.7) + col * Inches(6.1)
        y = Inches(2.15) + row * Inches(1.3)
        card(s, x, y, Inches(5.85), Inches(1.15), accent=BRAND, accent_side='left')
        txt(s, x + Inches(0.35), y + Inches(0.18),
            Inches(5.0), Inches(0.4),
            label, size=14, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(0.35), y + Inches(0.55),
            Inches(5.4), Inches(0.55),
            desc, size=11, color=INK_MUTED, line_spacing=1.4)

    # File size pill
    rounded(s, Inches(0.7), Inches(6.5), Inches(11.93), Inches(0.55),
            radius=0.5, fill=PRIMARY_BG)
    txt(s, Inches(0.9), Inches(6.6), Inches(11.6), Inches(0.4),
        "Typical size after 1 year of heavy use:  ~80 MB.  Backs up with one cp.",
        size=12, color=BRAND, bold=True, align=PP_ALIGN.CENTER, font=F_TITLE)


def slide_15_hybrid_search(prs):
    s = add_slide(prs)
    chrome(s, 16, TOTAL_SLIDES,
           "Triple-Stream Hybrid Search",
           eyebrow="Architecture",
           subtitle="BM25 + Vector + Graph — three streams find what the others miss.")

    streams = [
        ("BM25", "Keyword", [
            "Porter stemmer algorithm",
            "Synonym expansion",
            "CJK · Cyrillic · Hebrew support",
            "Exact matches: filenames, APIs",
            "Best for error messages, IDs",
        ], BRAND, '"PostToolUse hook config"'),
        ("Vector", "Semantic", [
            "Cosine similarity on embeddings",
            "Local: all-MiniLM-L6-v2 (free)",
            "Cloud: OpenAI / Gemini / Voyage",
            "Fallback chain on provider down",
            "Best for paraphrased queries",
        ], PURPLE, '"async runtime choice"'),
        ("Graph", "Knowledge", [
            "Entity extraction + BFS traversal",
            "Relationship edges between facts",
            "Links adjacent decisions",
            "Traverses 'why did we pick X?'",
            "Best for cause-effect chains",
        ], SUCCESS, '"why jose not jsonwebtoken"'),
    ]

    cw = Inches(4.0)
    ch = Inches(4.6)
    ct = Inches(2.15)
    gap = Inches(0.18)

    for i, (name, kind, items, color, example) in enumerate(streams):
        x = Inches(0.7) + i * (cw + gap)
        card(s, x, ct, cw, ch)
        # header
        rounded(s, x, ct, cw, Inches(0.85), radius=0.025, fill=color, line=None)
        # mask bottom of header so card edges look right
        rect(s, x, ct + Inches(0.5), cw, Inches(0.35), fill=color)
        txt(s, x + Inches(0.3), ct + Inches(0.15), cw - Inches(0.6), Inches(0.4),
            name, size=20, bold=True, color=INVERSE, font=F_TITLE)
        txt(s, x + Inches(0.3), ct + Inches(0.5), cw - Inches(0.6), Inches(0.32),
            kind + "  search", size=11, color=PRIMARY_PALE, italic=True)
        # items
        for j, item in enumerate(items):
            y = ct + Inches(1.1) + j * Inches(0.5)
            shape(s, MSO_SHAPE.OVAL,
                  x + Inches(0.35), y + Inches(0.13),
                  Inches(0.08), Inches(0.08),
                  fill=color, line=None)
            txt(s, x + Inches(0.55), y + Inches(0.03),
                cw - Inches(0.75), Inches(0.4),
                item, size=10.5, color=INK_SOFT)
        # example query
        ex_y = ct + ch - Inches(0.85)
        rounded(s, x + Inches(0.3), ex_y, cw - Inches(0.6), Inches(0.65),
                radius=0.1, fill=SURFACE, line=BORDER, line_w=0.5)
        txt(s, x + Inches(0.4), ex_y + Inches(0.08),
            cw - Inches(0.8), Inches(0.25),
            "EXAMPLE QUERY", size=8, bold=True, color=INK_FAINT, font=F_TITLE)
        txt(s, x + Inches(0.4), ex_y + Inches(0.3),
            cw - Inches(0.8), Inches(0.3),
            example, size=10, color=color, italic=True, font=F_MONO)

    # fusion arrow at bottom
    txt(s, Inches(0.7), Inches(6.95), Inches(12), Inches(0.3),
        "↓  All three streams merge via Reciprocal Rank Fusion  ↓",
        size=11, italic=True, color=INK_MUTED, align=PP_ALIGN.CENTER)


def slide_16_rrf(prs):
    s = add_slide(prs)
    chrome(s, 17, TOTAL_SLIDES,
           "RRF Fusion  ·  Combining Three Streams",
           eyebrow="Architecture",
           subtitle="Reciprocal Rank Fusion (k=60) produces one ranked list from three independent searches.")

    # Left side: formula card
    fx = Inches(0.7)
    fy = Inches(2.15)
    fw = Inches(5.5)
    fh = Inches(4.7)
    card(s, fx, fy, fw, fh)
    txt(s, fx + Inches(0.35), fy + Inches(0.3),
        fw - Inches(0.5), Inches(0.4),
        "The formula", size=14, bold=True, color=INK, font=F_TITLE)
    line(s, fx + Inches(0.35), fy + Inches(0.75),
         Inches(0.6), 0, color=BRAND, weight=2)

    # formula
    rounded(s, fx + Inches(0.35), fy + Inches(1.0),
            fw - Inches(0.7), Inches(1.2),
            radius=0.05, fill=CODE_BG)
    txt(s, fx + Inches(0.35), fy + Inches(1.3),
        fw - Inches(0.7), Inches(0.4),
        "score(d) = Σ 1 / (k + rank_i(d))",
        size=20, bold=True, color=CODE_KEYWORD,
        align=PP_ALIGN.CENTER, font=F_MONO)
    txt(s, fx + Inches(0.35), fy + Inches(1.75),
        fw - Inches(0.7), Inches(0.3),
        "where k = 60 · sum across streams · lower rank = higher score",
        size=10, color=CODE_COMMENT, italic=True,
        align=PP_ALIGN.CENTER, font=F_MONO)

    # properties
    props = [
        ("Cross-stream normalization", "Different score scales unified"),
        ("Rank-based (not score-based)", "Robust to scale differences"),
        ("Industry-standard k=60", "Established sweet spot"),
        ("O(N) merge", "Negligible runtime cost"),
    ]
    for i, (a, b) in enumerate(props):
        y = fy + Inches(2.5) + i * Inches(0.5)
        shape(s, MSO_SHAPE.OVAL,
              fx + Inches(0.45), y + Inches(0.12),
              Inches(0.1), Inches(0.1), fill=BRAND, line=None)
        txt(s, fx + Inches(0.65), y, fw - Inches(0.8), Inches(0.3),
            a, size=11, bold=True, color=INK, font=F_TITLE)
        txt(s, fx + Inches(3.4), y + Inches(0.02),
            fw - Inches(3.5), Inches(0.3),
            b, size=10, color=INK_MUTED)

    # Right side: pipeline
    rx = Inches(6.5)
    ry = Inches(2.15)
    rw = Inches(6.13)
    rh = Inches(4.7)
    card(s, rx, ry, rw, rh)
    txt(s, rx + Inches(0.35), ry + Inches(0.3),
        rw - Inches(0.5), Inches(0.4),
        "The pipeline", size=14, bold=True, color=INK, font=F_TITLE)
    line(s, rx + Inches(0.35), ry + Inches(0.75),
         Inches(0.6), 0, color=BRAND, weight=2)

    steps = [
        ("Each stream returns Top-10",
         "BM25 · Vector · Graph rank independently"),
        ("Compute RRF score",
         "1/(k + rank) summed across streams"),
        ("Merge & sort",
         "Unified ranking across all candidates"),
        ("Session diversification",
         "Max 3 results per session"),
        ("Return Top-5",
         "Injected into agent context  →  95.2% R@5"),
    ]
    for i, (a, b) in enumerate(steps):
        y = ry + Inches(1.05) + i * Inches(0.7)
        # number
        num_badge(s, rx + Inches(0.3), y + Inches(0.05),
                  Inches(0.42), i + 1, color=BRAND)
        txt(s, rx + Inches(0.85), y, rw - Inches(1.0), Inches(0.3),
            a, size=12, bold=True, color=INK, font=F_TITLE)
        txt(s, rx + Inches(0.85), y + Inches(0.27),
            rw - Inches(1.0), Inches(0.35),
            b, size=10, color=INK_MUTED, line_spacing=1.3)


def slide_17_injection(prs):
    s = add_slide(prs)
    chrome(s, 18, TOTAL_SLIDES,
           "Session Start  ·  Memory Injection",
           eyebrow="Architecture",
           subtitle="What happens in the first few seconds of every new agent session.")

    steps = [
        ("SessionStart hook fires",
         "Project path + session ID captured",
         "0 ms", BRAND),
        ("Project profile loaded",
         "Top concepts, active files, patterns from SQLite",
         "3 ms", PURPLE),
        ("Hybrid search runs",
         "BM25 + Vector + Graph over all stored memories",
         "11 ms", SUCCESS),
        ("Token budget applied",
         "Default 2,000 tokens · prioritized by relevance × recency",
         "0 ms", TEAL),
        ("Injected into system prompt",
         "Relevant memories formatted and prepended",
         "1 ms", GOLD),
        ("Agent ready  ·  full context loaded",
         "Total cold-start overhead: ~15 ms",
         "= 15 ms", ERROR),
    ]

    cw = Inches(11.93)
    ch = Inches(0.78)
    ct = Inches(2.15)
    gap = Inches(0.08)

    for i, (title_, desc, timing, color) in enumerate(steps):
        y = ct + i * (ch + gap)
        card(s, Inches(0.7), y, cw, ch, accent=color, accent_side='left')
        # step number
        num_badge(s, Inches(1.0), y + Inches(0.21),
                  Inches(0.4), i + 1, color=color)
        # title
        txt(s, Inches(1.6), y + Inches(0.13),
            Inches(6.8), Inches(0.35),
            title_, size=13, bold=True, color=INK, font=F_TITLE)
        # desc
        txt(s, Inches(1.6), y + Inches(0.42),
            Inches(7.5), Inches(0.32),
            desc, size=10.5, color=INK_MUTED)
        # timing
        rounded(s, Inches(11.2), y + Inches(0.21),
                Inches(1.1), Inches(0.35),
                radius=0.5, fill=PRIMARY_BG)
        txt(s, Inches(11.2), y + Inches(0.24),
            Inches(1.1), Inches(0.3),
            timing, size=11, bold=True, color=BRAND,
            align=PP_ALIGN.CENTER, font=F_MONO)


def slide_18_multiagent(prs):
    s = add_slide(prs)
    chrome(s, 19, TOTAL_SLIDES,
           "Multi-Agent Coordination",
           eyebrow="Architecture",
           subtitle="One memory store · multiple agents · no conflicts.")

    features = [
        ("⊕", "Leases",
         "Exclusive action locks prevent race conditions when two agents touch the same task or file at once.",
         BRAND),
        ("◐", "Signals",
         "Agents broadcast state changes to peers without polling. Task completion notifies instantly.",
         PURPLE),
        ("⬢", "Namespaced storage",
         "project:agent1 for shared team memory. project:agent1:private for per-agent observations.",
         SUCCESS),
        ("→", "Mesh sync",
         "Claude Code captures decisions · Copilot CLI retrieves them in PR review. One brain, multiple workers.",
         GOLD),
    ]

    cw = Inches(5.85)
    ch = Inches(2.2)
    ct = Inches(2.15)

    for i, (glyph, name, desc, color) in enumerate(features):
        row, col = i // 2, i % 2
        x = Inches(0.7) + col * Inches(6.1)
        y = ct + row * Inches(2.45)
        card(s, x, y, cw, ch)
        icon_circle(s, x + Inches(0.7), y + Inches(0.78),
                    Inches(0.42), color, glyph, INVERSE, 22)
        txt(s, x + Inches(1.5), y + Inches(0.35),
            cw - Inches(1.7), Inches(0.4),
            name, size=18, bold=True, color=INK, font=F_TITLE)
        txt(s, x + Inches(1.5), y + Inches(0.88),
            cw - Inches(1.7), Inches(1.2),
            desc, size=12, color=INK_MUTED, line_spacing=1.4)


# ─── SECTION 4: CODE & INTEGRATION ───────────────────────────────────────────

def slide_19_hook_config(prs):
    s = add_slide(prs)
    chrome(s, 21, TOTAL_SLIDES,
           "Hook Config in Practice",
           eyebrow="Code",
           subtitle="`agentmemory connect claude-code` writes this configuration automatically.")

    json_code = """\
{
  "hooks": {
    "PostToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "agentmemory hook post-tool-use"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "agentmemory hook stop"
      }]
    }],
    "SessionEnd": [{
      "hooks": [{
        "type": "command",
        "command": "agentmemory hook session-end"
      }]
    }]
  }
}"""
    code_block(s, json_code, Inches(0.7), Inches(2.15),
               Inches(7.5), Inches(4.85),
               lang='json', size=12, title=".claude/settings.json")

    # right info
    rx = Inches(8.4)
    ry = Inches(2.15)
    rw = Inches(4.23)
    card(s, rx, ry, rw, Inches(4.85))
    txt(s, rx + Inches(0.3), ry + Inches(0.3),
        rw - Inches(0.5), Inches(0.4),
        "What this does", size=14, bold=True, color=INK, font=F_TITLE)
    line(s, rx + Inches(0.3), ry + Inches(0.75),
         Inches(0.6), 0, color=BRAND, weight=2)

    notes = [
        ('matcher: ".*"',
         "Fires on every tool: Read, Write, Bash, Edit, Grep, Glob — all of them"),
        ("Idempotent",
         "Safe to re-run · skips already-wired hooks"),
        ("Re-runnable",
         "Updates config on agentmemory version bumps"),
        ("Skills installed",
         "npx skills add rohitg00/agentmemory installs 8 native skills"),
    ]
    for i, (a, b) in enumerate(notes):
        y = ry + Inches(1.0) + i * Inches(0.95)
        rounded(s, rx + Inches(0.3), y,
                Inches(0.07), Inches(0.7),
                radius=0.5, fill=BRAND)
        txt(s, rx + Inches(0.5), y, rw - Inches(0.7), Inches(0.3),
            a, size=12, bold=True, color=INK, font=F_MONO)
        txt(s, rx + Inches(0.5), y + Inches(0.3),
            rw - Inches(0.7), Inches(0.45),
            b, size=10, color=INK_MUTED, line_spacing=1.3)


def slide_20_mcp_tool(prs):
    s = add_slide(prs)
    chrome(s, 22, TOTAL_SLIDES,
           "MCP Tool Call  ·  memory_smart_search",
           eyebrow="Code",
           subtitle="53 MCP tools available — `memory_smart_search` is the daily workhorse.")

    call_code = """\
{
  "tool": "memory_smart_search",
  "input": {
    "query": "why did we choose jose over jsonwebtoken",
    "limit": 5
  }
}"""
    code_block(s, call_code, Inches(0.7), Inches(2.15),
               Inches(6.1), Inches(2.0),
               lang='json', size=12, title="agent  →  MCP server")

    result_code = """\
{
  "content": "Session 4 (2026-01-14): Chose jose middleware (src/middleware/auth.ts) over jsonwebtoken. Reason: jose works on Edge runtime; jsonwebtoken does not. Tests in auth.test.ts.",
  "score": 0.94,
  "tier": "semantic",
  "session": 4,
  "citations": ["obs_4_221", "obs_4_308"]
}"""
    code_block(s, result_code, Inches(6.95), Inches(2.15),
               Inches(5.68), Inches(2.0),
               lang='json', size=10.5, title="MCP server  →  agent")

    # arrow between
    txt(s, Inches(6.78), Inches(2.95), Inches(0.2), Inches(0.4),
        "→", size=24, bold=True, color=INK_FAINT,
        align=PP_ALIGN.CENTER, font=F_TITLE)

    # other tools
    other_tools_top = Inches(4.4)
    txt(s, Inches(0.7), other_tools_top, Inches(12), Inches(0.4),
        "Other key MCP tools", size=14, bold=True, color=INK, font=F_TITLE)
    line(s, Inches(0.7), other_tools_top + Inches(0.45),
         Inches(0.6), 0, color=BRAND, weight=2)

    tools = [
        ("memory_store", "Manually store a fact or decision", PURPLE),
        ("memory_get_session", "Retrieve all observations from a session", SUCCESS),
        ("memory_forget", "Remove a memory (GDPR · cleanup)", ERROR),
        ("memory_graph_query", "Traverse the knowledge graph directly", TEAL),
    ]
    for i, (name, desc, color) in enumerate(tools):
        row, col = i // 2, i % 2
        x = Inches(0.7) + col * Inches(6.1)
        y = other_tools_top + Inches(0.7) + row * Inches(0.85)
        card(s, x, y, Inches(5.85), Inches(0.7), accent=color, accent_side='left')
        txt(s, x + Inches(0.3), y + Inches(0.1), Inches(2.6), Inches(0.4),
            name, size=12, bold=True, color=INK, font=F_MONO)
        txt(s, x + Inches(0.3), y + Inches(0.4), Inches(5.4), Inches(0.3),
            desc, size=10, color=INK_MUTED)


def slide_21_privacy(prs):
    s = add_slide(prs)
    chrome(s, 23, TOTAL_SLIDES,
           "Privacy Filter in Action",
           eyebrow="Code",
           subtitle="Secrets stripped before any observation hits disk. Regex + tag-based stripping.")

    before_code = """\
# Raw tool output (NEVER stored)

OPENAI_API_KEY=sk-proj-abc123xyz789...
DATABASE_URL=postgres://user:s3cr3t@db.internal/prod
Authorization: Bearer eyJhbGciOiJSUzI1NiJ9...
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

<private>
  Internal strategy: migrate to v2 by Q3.
  This reasoning is confidential.
</private>

AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG..."""

    after_code = """\
# Stored observation (privacy-filtered)

OPENAI_API_KEY=[REDACTED]
DATABASE_URL=[REDACTED]
Authorization: [REDACTED]
GITHUB_TOKEN=[REDACTED]

[PRIVATE BLOCK REMOVED]



AWS_SECRET_ACCESS_KEY=[REDACTED]"""

    # Labels with colored dot
    shape(s, MSO_SHAPE.OVAL, Inches(0.7), Inches(2.25),
          Inches(0.18), Inches(0.18), fill=ERROR, line=None)
    txt(s, Inches(0.95), Inches(2.22), Inches(5.8), Inches(0.32),
        "BEFORE  ·  raw tool output", size=11, bold=True,
        color=ERROR, font=F_TITLE)

    shape(s, MSO_SHAPE.OVAL, Inches(6.95), Inches(2.25),
          Inches(0.18), Inches(0.18), fill=SUCCESS, line=None)
    txt(s, Inches(7.2), Inches(2.22), Inches(5.8), Inches(0.32),
        "AFTER  ·  stored safely", size=11, bold=True,
        color=SUCCESS, font=F_TITLE)

    code_block(s, before_code, Inches(0.7), Inches(2.65),
               Inches(6.0), Inches(4.2),
               lang='bash', size=10.5)
    code_block(s, after_code, Inches(6.95), Inches(2.65),
               Inches(5.68), Inches(4.2),
               lang='bash', size=10.5)


# ─── SECTION 5: BENCHMARKS ───────────────────────────────────────────────────

def slide_22_longmemeval(prs):
    s = add_slide(prs)
    chrome(s, 25, TOTAL_SLIDES,
           "LongMemEval-S Results",
           eyebrow="Benchmarks",
           subtitle="ICLR 2025 benchmark · 500 questions · ~115K tokens each · five reasoning types.")

    # Headline stat
    stat_t = Inches(2.15)
    rounded(s, Inches(0.7), stat_t, Inches(4.5), Inches(2.2),
            radius=0.04, fill=PRIMARY, line=None)
    txt(s, Inches(0.7), stat_t + Inches(0.3), Inches(4.5), Inches(0.35),
        "RECALL @ 5", size=10, bold=True, color=PRIMARY_PALE, font=F_TITLE,
        align=PP_ALIGN.CENTER)
    txt(s, Inches(0.7), stat_t + Inches(0.7), Inches(4.5), Inches(1.0),
        "95.2%", size=64, bold=True, color=INVERSE,
        align=PP_ALIGN.CENTER, font=F_DISPLAY, line_spacing=1.0)
    txt(s, Inches(0.7), stat_t + Inches(1.7), Inches(4.5), Inches(0.4),
        "agentmemory hybrid (BM25 + Vector + Graph)",
        size=11, color=PRIMARY_PALE, italic=True,
        align=PP_ALIGN.CENTER)

    # Bar chart comparison
    cats = [
        "agentmemory  hybrid",
        "agentmemory  BM25-only",
        "Letta / MemGPT",
        "Mem0",
    ]
    chart = bar_chart(s,
        cats,
        [("Recall @ 5", (95.2, 86.2, 83.2, 68.5))],
        Inches(5.4), Inches(2.15), Inches(7.23), Inches(2.2),
        series_colors=[BRAND],
        has_legend=False, max_val=100, suffix="%")

    # Per-question breakdown
    bd_t = Inches(4.55)
    txt(s, Inches(0.7), bd_t, Inches(12), Inches(0.4),
        "Breakdown by question type  ·  agentmemory hybrid",
        size=13, bold=True, color=INK, font=F_TITLE)
    line(s, Inches(0.7), bd_t + Inches(0.4),
         Inches(0.6), 0, color=BRAND, weight=2)

    breakdown = [
        ("98.7%", "Knowledge updates", SUCCESS),
        ("97.7%", "Multi-session reasoning", SUCCESS),
        ("96.4%", "Single-session  ·  assistant", SUCCESS),
        ("95.5%", "Temporal reasoning", SUCCESS),
        ("83.3%", "Single-session  ·  preferences", GOLD),
    ]
    bw = Inches(2.32)
    bh = Inches(1.65)
    bg_y = bd_t + Inches(0.7)
    bgap = Inches(0.1)
    for i, (val, lbl, color) in enumerate(breakdown):
        x = Inches(0.7) + i * (bw + bgap)
        card(s, x, bg_y, bw, bh)
        txt(s, x, bg_y + Inches(0.3), bw, Inches(0.7),
            val, size=28, bold=True, color=color,
            font=F_TITLE, align=PP_ALIGN.CENTER, line_spacing=1.0)
        txt(s, x + Inches(0.15), bg_y + Inches(1.0),
            bw - Inches(0.3), Inches(0.55),
            lbl, size=10, color=INK_MUTED,
            align=PP_ALIGN.CENTER, line_spacing=1.3)


def slide_23_tokens(prs):
    s = add_slide(prs)
    chrome(s, 26, TOTAL_SLIDES,
           "Token Efficiency",
           eyebrow="Benchmarks",
           subtitle="92% fewer tokens · $0/yr with local embeddings · 240 obs/yr baseline.")

    # Headline pill
    rounded(s, Inches(0.7), Inches(2.15), Inches(11.93), Inches(0.55),
            radius=0.05, fill=SUCCESS_PALE)
    txt(s, Inches(0.9), Inches(2.25), Inches(11.6), Inches(0.4),
        "92% token reduction vs LLM-summarized memory  ·  near-zero cost",
        size=14, bold=True, color=SUCCESS, font=F_TITLE,
        align=PP_ALIGN.CENTER)

    # Cost comparison chart
    chart_data_categories = [
        "Paste full history",
        "LLM-summarized",
        "agentmemory (API)",
        "agentmemory (local)",
    ]
    chart = bar_chart(s,
        chart_data_categories,
        [("Tokens / year (M)", (19.5, 0.65, 0.17, 0.17))],
        Inches(0.7), Inches(2.95), Inches(6.0), Inches(3.8),
        series_colors=[BRAND], has_legend=False, suffix="M")

    # Cost table on right
    rx = Inches(6.95)
    ry = Inches(2.95)
    rw = Inches(5.68)
    rh = Inches(3.8)
    card(s, rx, ry, rw, rh)
    txt(s, rx + Inches(0.3), ry + Inches(0.25),
        rw - Inches(0.6), Inches(0.4),
        "Cost per year", size=14, bold=True, color=INK, font=F_TITLE)
    line(s, rx + Inches(0.3), ry + Inches(0.7),
         Inches(0.6), 0, color=BRAND, weight=2)

    costs = [
        ("Paste full history", "Impossible", "Exceeds context", ERROR),
        ("LLM-summarized", "~$500", "Lossy, drops detail", GOLD),
        ("agentmemory (API)", "~$10", "Cloud embeddings", BRAND),
        ("agentmemory (local)", "$0", "all-MiniLM-L6-v2", SUCCESS),
    ]
    for i, (label, cost, note, color) in enumerate(costs):
        y = ry + Inches(1.0) + i * Inches(0.65)
        rounded(s, rx + Inches(0.3), y,
                Inches(0.08), Inches(0.5),
                radius=0.5, fill=color)
        txt(s, rx + Inches(0.5), y + Inches(0.04),
            Inches(2.6), Inches(0.3),
            label, size=12, bold=True, color=INK, font=F_TITLE)
        txt(s, rx + Inches(0.5), y + Inches(0.3),
            Inches(2.6), Inches(0.3),
            note, size=9.5, color=INK_MUTED, italic=True)
        txt(s, rx + Inches(3.4), y + Inches(0.1),
            Inches(2.1), Inches(0.4),
            cost, size=18, bold=True, color=color,
            font=F_TITLE, align=PP_ALIGN.RIGHT)


def slide_24_inhouse(prs):
    s = add_slide(prs)
    chrome(s, 27, TOTAL_SLIDES,
           "In-house Benchmark  ·  coding-agent-life-v1",
           eyebrow="Benchmarks",
           subtitle="15 Claude Code sessions · 10 days · real Rust CLI project · 100% hit rate.")

    # Top stats row
    stats = [
        ("100%", "Hit rate", SUCCESS),
        ("1.000", "Recall @ 5", SUCCESS),
        ("0.240", "Precision @ 5 (at ceiling)", BRAND),
        ("14 ms", "p50 latency", BRAND),
    ]
    for i, (val, lbl, color) in enumerate(stats):
        x = Inches(0.7) + i * Inches(3.05)
        card(s, x, Inches(2.15), Inches(2.85), Inches(1.5), accent=color, accent_side='top')
        txt(s, x, Inches(2.35), Inches(2.85), Inches(0.65),
            val, size=34, bold=True, color=color,
            font=F_TITLE, align=PP_ALIGN.CENTER, line_spacing=1.0)
        txt(s, x + Inches(0.1), Inches(3.05),
            Inches(2.65), Inches(0.5),
            lbl, size=11, color=INK_MUTED,
            align=PP_ALIGN.CENTER, line_spacing=1.3)

    # Comparison row title
    cmp_t = Inches(3.95)
    txt(s, Inches(0.7), cmp_t, Inches(12), Inches(0.4),
        "Hybrid vs grep baseline",
        size=14, bold=True, color=INK, font=F_TITLE)
    line(s, Inches(0.7), cmp_t + Inches(0.4),
         Inches(0.6), 0, color=BRAND, weight=2)

    # Table
    headers = ["System", "Hit Rate", "R@5", "P@5", "p50 Latency"]
    rows = [
        ["**agentmemory hybrid**", "**100%**", "**1.000**", "**0.240**", "**14 ms**"],
        ["grep baseline", "96.7%", "0.967", "—", "0 ms"],
    ]
    table(s, Inches(0.7), Inches(4.7), Inches(11.93),
          headers, rows,
          col_widths=[Inches(3.5), Inches(2.1), Inches(2.1), Inches(2.1), Inches(2.13)],
          hdr_size=12, body_size=11.5)

    # Key finding callout
    rounded(s, Inches(0.7), Inches(6.5), Inches(11.93), Inches(0.55),
            radius=0.05, fill=PRIMARY_BG)
    txt(s, Inches(0.95), Inches(6.55), Inches(11.5), Inches(0.45),
        "KEY FINDING  ·  ", size=10, bold=True, color=BRAND, font=F_TITLE)
    txt(s, Inches(2.3), Inches(6.55), Inches(10.3), Inches(0.45),
        "Temporal queries: grep finds 1/2 gold sessions  ·  agentmemory finds 2/2",
        size=12, color=INK, font=F_BODY)


# ─── SECTION 6: COMPARISON & ROADMAP ─────────────────────────────────────────

def slide_25_vs_native(prs):
    s = add_slide(prs)
    chrome(s, 29, TOTAL_SLIDES,
           "agentmemory vs Native Claude Code Memory",
           eyebrow="Comparison",
           subtitle="Built-in CLAUDE.md is file-based. agentmemory is a query engine.")

    headers = ["Feature", "Claude Code native", "agentmemory"]
    rows = [
        ["Cross-agent support", "Claude Code only", "15+ agents"],
        ["Retrieval method", "Loads full MEMORY.md", "Hybrid search · 95.2% R@5"],
        ["Scale ceiling", "Degrades past ~200 lines", "Stays efficient at scale"],
        ["Auto-capture", "Manual Write calls", "12 hooks · automatic"],
        ["Token efficiency", "Grows unbounded", "~1,900 tokens/session"],
        ["Cross-project memory", "Per working directory only", "Shared across projects"],
        ["Multi-agent coordination", "None", "Leases · signals · namespaces"],
        ["Real-time viewer", "None", "Yes  ·  port 3113"],
    ]
    table(s, Inches(0.7), Inches(2.15), Inches(11.93),
          headers, rows,
          col_widths=[Inches(3.3), Inches(3.8), Inches(4.83)],
          hdr_size=12, body_size=11)


def slide_26_matrix(prs):
    s = add_slide(prs)
    chrome(s, 30, TOTAL_SLIDES,
           "Full Competitive Matrix",
           eyebrow="Comparison",
           subtitle="agentmemory vs mem0 vs Letta vs CLAUDE.md across 12 dimensions.")

    headers = ["Feature", "agentmemory", "mem0", "Letta", "CLAUDE.md"]
    rows = [
        ["Retrieval R@5", "**95.2%**", "68.5%", "83.2%", "N/A"],
        ["Auto-capture", "**12 hooks**", "Manual add()", "Agent-managed", "Manual edit"],
        ["Search type", "**BM25+Vector+Graph**", "Vector+Graph", "Vector", "Full load"],
        ["Multi-agent", "**MCP + leases**", "API only", "Runtime-internal", "No"],
        ["Framework lock-in", "**None**", "None", "High (Letta)", "Per-agent"],
        ["External DB", "**None  ·  SQLite**", "Qdrant/pgvector", "Postgres+vector", "None"],
        ["Lifecycle", "**4-tier + decay**", "Passive extraction", "Agent-managed", "Manual"],
        ["Tokens/session", "**~1,900**", "Varies", "In-context", "22K+"],
        ["Real-time viewer", "**Built-in :3113**", "Cloud only", "Cloud only", "No"],
        ["Self-hosted", "**Default**", "Optional", "Optional", "Yes"],
        ["MCP tools", "**53**", "Few", "None", "None"],
        ["Open source", "**Yes  ·  MIT**", "Yes", "Yes", "N/A"],
    ]
    table(s, Inches(0.7), Inches(2.15), Inches(11.93),
          headers, rows,
          col_widths=[Inches(2.6), Inches(2.7), Inches(2.0), Inches(2.0), Inches(2.63)],
          hdr_size=11, body_size=10)


def slide_27_roadmap(prs):
    s = add_slide(prs)
    chrome(s, 31, TOTAL_SLIDES,
           "Roadmap to v1.0",
           eyebrow="Roadmap",
           subtitle="Quarterly themes through Q1 2027  ·  Depth · Breadth · Trust · Stability.")

    quarters = [
        ("Q2 2026", "Depth", [
            "Multimodal memory (images)",
            "Filesystem connector",
            "OpenCode hooks (22 hooks)",
            "Governance baseline",
        ], BRAND),
        ("Q3 2026", "Breadth", [
            "Slack / Discord connector",
            "OpenSSF Scorecard",
            "Additional maintainers",
            "Plugin ecosystem growth",
        ], PURPLE),
        ("Q4 2026", "Trust", [
            "SSO gateway (OIDC)",
            "Audit log export",
            "RBAC on memory scope",
            "External security audit",
        ], SUCCESS),
        ("Q1 2027", "v1.0", [
            "REST + MCP surface freeze",
            "LTS branch v1.x · 12-month fixes",
            "Foundation membership",
            "Semver stability guarantee",
        ], GOLD),
    ]

    cw = Inches(2.95)
    ch = Inches(4.6)
    ct = Inches(2.15)
    gap = Inches(0.13)

    for i, (quarter, theme, items, color) in enumerate(quarters):
        x = Inches(0.7) + i * (cw + gap)
        card(s, x, ct, cw, ch)
        # header
        rounded(s, x, ct, cw, Inches(0.95), radius=0.025, fill=color, line=None)
        rect(s, x, ct + Inches(0.55), cw, Inches(0.4), fill=color)
        txt(s, x + Inches(0.25), ct + Inches(0.18), cw - Inches(0.5), Inches(0.4),
            quarter, size=12, bold=True, color=PRIMARY_PALE, font=F_TITLE)
        txt(s, x + Inches(0.25), ct + Inches(0.5), cw - Inches(0.5), Inches(0.4),
            theme, size=20, bold=True, color=INVERSE, font=F_TITLE)
        # items
        for j, item in enumerate(items):
            y = ct + Inches(1.2) + j * Inches(0.75)
            shape(s, MSO_SHAPE.OVAL,
                  x + Inches(0.3), y + Inches(0.12),
                  Inches(0.1), Inches(0.1), fill=color, line=None)
            txt(s, x + Inches(0.5), y + Inches(0.02),
                cw - Inches(0.7), Inches(0.7),
                item, size=11, color=INK_SOFT, line_spacing=1.35)


def slide_28_summary(prs):
    s = add_slide(prs)
    chrome(s, 32, TOTAL_SLIDES,
           "Summary  ·  Why agentmemory",
           eyebrow="Wrap-up",
           subtitle="Five reasons engineers choose agentmemory as their persistent memory layer.")

    points = [
        ("01", "Zero manual effort",
         "12 hooks capture everything automatically. No add() calls, no file maintenance.",
         BRAND),
        ("02", "Works with every agent",
         "One store across Claude Code · Copilot CLI · Cursor · Gemini CLI · Codex · and 10+ more.",
         PURPLE),
        ("03", "Highest recall",
         "95.2% R@5 via BM25 + Vector + Graph hybrid. Temporal queries grep misses.",
         SUCCESS),
        ("04", "Near-zero cost",
         "$0/yr with local embeddings (all-MiniLM-L6-v2). 92% fewer tokens.",
         GOLD),
        ("05", "Self-hosted & simple",
         "SQLite only. No external DBs. Works offline. Real-time viewer included.",
         TEAL),
    ]

    for i, (num, title_, desc, color) in enumerate(points):
        y = Inches(2.15) + i * Inches(0.9)
        # number badge
        rounded(s, Inches(0.7), y, Inches(0.85), Inches(0.78),
                radius=0.04, fill=color)
        txt(s, Inches(0.7), y + Inches(0.18), Inches(0.85), Inches(0.5),
            num, size=22, bold=True, color=INVERSE,
            font=F_TITLE, align=PP_ALIGN.CENTER)
        # content
        rounded(s, Inches(1.7), y, Inches(10.93), Inches(0.78),
                radius=0.04, fill=BG, line=BORDER)
        txt(s, Inches(1.9), y + Inches(0.1), Inches(4.0), Inches(0.4),
            title_, size=15, bold=True, color=INK, font=F_TITLE)
        txt(s, Inches(1.9), y + Inches(0.42), Inches(10.6), Inches(0.32),
            desc, size=11, color=INK_MUTED)

    # CTA bar
    rounded(s, Inches(0.7), Inches(6.85), Inches(11.93), Inches(0.5),
            radius=0.05, fill=INK)
    txt(s, Inches(0.7), Inches(6.93), Inches(11.93), Inches(0.35),
        "npm install -g @agentmemory/agentmemory   &&   agentmemory connect claude-code",
        size=13, bold=True, color=PRIMARY_PALE,
        align=PP_ALIGN.CENTER, font=F_MONO)


# ════════════════════════════════════════════════════════════════════════════
# BUILD
# ════════════════════════════════════════════════════════════════════════════

def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # Title
    slide_01_title(prs)

    # Section 1
    section_divider(prs, 1, "The Problem",
                    "Why AI coding agents need persistent memory.\nThe hidden cost of context amnesia.")
    slide_02_amnesia(prs)
    slide_03_reexplain(prs)
    slide_04_static_file(prs)
    slide_05_existing(prs)

    # Section 2
    section_divider(prs, 2, "Introducing agentmemory",
                    "Automatic capture · Smart retrieval · Zero friction.\nWhat it is and how it fits in.")
    slide_06_what_is(prs)
    slide_07_how_it_fixes(prs)
    slide_08_quickstart(prs)

    # Section 3
    section_divider(prs, 3, "Architecture Deep Dive",
                    "How it works under the hood.\nHooks · pipeline · 4-tier memory · hybrid search.")
    slide_09_architecture(prs)
    slide_10_hooks(prs)
    slide_11_pipeline(prs)
    slide_12_4tier(prs)
    slide_13_decay(prs)
    slide_14_storage(prs)
    slide_15_hybrid_search(prs)
    slide_16_rrf(prs)
    slide_17_injection(prs)
    slide_18_multiagent(prs)

    # Section 4
    section_divider(prs, 4, "Code & Integration",
                    "Real config · real tool calls · real privacy guarantees.")
    slide_19_hook_config(prs)
    slide_20_mcp_tool(prs)
    slide_21_privacy(prs)

    # Section 5
    section_divider(prs, 5, "Benchmarks",
                    "Numbers that matter.\nAcademic eval · token efficiency · in-house corpus.")
    slide_22_longmemeval(prs)
    slide_23_tokens(prs)
    slide_24_inhouse(prs)

    # Section 6
    section_divider(prs, 6, "Comparison & Roadmap",
                    "Where it stands today · where it's going.")
    slide_25_vs_native(prs)
    slide_26_matrix(prs)
    slide_27_roadmap(prs)
    slide_28_summary(prs)

    import os
    out = "F:/agentmemory/agentmemory-presentation.pptx"
    try:
        prs.save(out)
    except PermissionError:
        out = "F:/agentmemory/agentmemory-presentation-v2.pptx"
        prs.save(out)
        print("[note] Original file was locked (open in PowerPoint?). Saved as v2.")
    print(f"Saved: {out}")
    print(f"Total slides: {len(prs.slides)}")


if __name__ == "__main__":
    build()
