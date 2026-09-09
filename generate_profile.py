#!/usr/bin/env python3
from pathlib import Path
import json
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
LINES = (ROOT / "ascii" / "helix.txt").read_text(encoding="utf-8", errors="ignore").splitlines()

while LINES and not LINES[0].strip():
    LINES.pop(0)
while LINES and not LINES[-1].strip():
    LINES.pop()
min_lead = min((len(line)-len(line.lstrip(" ")) for line in LINES if line.strip()), default=0)
LINES = [line[min_lead:].rstrip() for line in LINES]

def build_svg(theme="dark"):
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    text = "#c9d1d9" if dark else "#24292f"
    muted = "#7d8590" if dark else "#57606a"
    accent = "#3fb950" if dark else "#1a7f37"
    dim = "#484f58" if dark else "#8c959f"

    W = 1120
    divider_x = 430
    x = divider_x + 26
    dots_x = x + 126
    value_x = x + 218
    body_fs = 10.3
    row_h = 16.7

    right_rows = (
        len(PROFILE["overview"]) + len(PROFILE["stack"]) + len(PROFILE["work"]) +
        len(PROFILE["experience"]) + len(PROFILE["contact"])
    )
    right_content_h = 70 + right_rows * row_h + 4 * 24 + 34

    ascii_font = 8.3
    ascii_line = 8.0
    ascii_h = len(LINES) * ascii_line
    H = int(max(right_content_h + 36, ascii_h + 54))

    max_ascii_h = H - 46
    if ascii_h > max_ascii_h:
        scale = max_ascii_h / ascii_h
        ascii_font *= scale
        ascii_line *= scale
        ascii_h = len(LINES) * ascii_line

    max_cols = max((len(line) for line in LINES), default=1)
    char_w = ascii_font * 0.62
    ascii_w = max_cols * char_w
    panel_left = 18
    panel_right = divider_x - 18
    panel_w = panel_right - panel_left
    ascii_x = panel_left + max(0, (panel_w - ascii_w) / 2)
    ascii_top = (H - ascii_h) / 2

    tspans = "".join(
        f'<tspan x="{ascii_x:.2f}" y="{ascii_top + i * ascii_line:.2f}">{escape(line)}</tspan>'
        for i, line in enumerate(LINES)
    )

    parts = []
    parts.append(f'<text x="{x}" y="29" class="header">{escape(PROFILE["display_name"])}@github</text>')
    parts.append(f'<line x1="{x+118}" y1="24" x2="{W-28}" y2="24" stroke="{border}" />')
    parts.append(f'<text x="{W-30}" y="43" text-anchor="end" class="sub">{escape(PROFILE["location_line"])}</text>')

    def add_row(label, value, y):
        parts.append(f'<text x="{x}" y="{y:.1f}" class="key">{escape(label)}</text>')
        parts.append(f'<text x="{dots_x}" y="{y:.1f}" class="dots">..........</text>')
        parts.append(f'<text x="{value_x}" y="{y:.1f}" class="value">{escape(value)}</text>')
        return y + row_h

    def add_section(title, y):
        parts.append(f'<text x="{x}" y="{y:.1f}" class="section">— {escape(title)} ——————————————————————————</text>')
        return y + 18

    y = 66
    for label, value in PROFILE["overview"]:
        y = add_row(label, value, y)
    y += 5
    y = add_section("stack / capability", y)
    for label, value in PROFILE["stack"]:
        y = add_row(label, value, y)
    y += 5
    y = add_section("current / selected work", y)
    for label, value in PROFILE["work"]:
        y = add_row(label, value, y)
    y += 5
    y = add_section("experience", y)
    for label, value in PROFILE["experience"]:
        y = add_row(label, value, y)
    y += 5
    y = add_section("contact", y)
    for label, value in PROFILE["contact"]:
        y = add_row(label, value, y)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
text { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; white-space: pre; }
.ascii { fill: {text}; }
.header { fill: {text}; font-size: 15px; font-weight: 600; }
.sub { fill: {muted}; font-size: 10.3px; }
.key { fill: {accent}; font-size: {body_fs}px; }
.value { fill: {text}; font-size: {body_fs}px; }
.dots { fill: {dim}; font-size: {body_fs}px; letter-spacing: 0.15px; }
.section { fill: {muted}; font-size: 10px; }
</style>
<rect width="{W}" height="{H}" rx="16" fill="{bg}" stroke="{border}" />
<line x1="{divider_x}" y1="18" x2="{divider_x}" y2="{H-18}" stroke="{border}" />
<text class="ascii" font-size="{ascii_font:.3f}px">{tspans}</text>
{''.join(parts)}
</svg>"""

for theme in ("dark", "light"):
    (ROOT / "assets" / f"profile-{theme}.svg").write_text(build_svg(theme), encoding="utf-8")

print("Updated SVGs.")
