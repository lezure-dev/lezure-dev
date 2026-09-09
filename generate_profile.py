#!/usr/bin/env python3
from pathlib import Path
import json
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
ASCII_LINES = (ROOT / "ascii" / "helix.txt").read_text(encoding="utf-8", errors="ignore").splitlines()

while ASCII_LINES and not ASCII_LINES[0].strip():
    ASCII_LINES.pop(0)
while ASCII_LINES and not ASCII_LINES[-1].strip():
    ASCII_LINES.pop()
min_lead = min((len(line) - len(line.lstrip(" ")) for line in ASCII_LINES if line.strip()), default=0)
ASCII_LINES = [line[min_lead:].rstrip("\n\r") for line in ASCII_LINES]

def build_svg(theme="dark"):
    dark = theme == "dark"
    bg = "#0d1117" if dark else "#ffffff"
    border = "#30363d" if dark else "#d0d7de"
    text = "#c9d1d9" if dark else "#24292f"
    muted = "#7d8590" if dark else "#57606a"
    accent = "#3fb950" if dark else "#1a7f37"
    dim = "#484f58" if dark else "#8c959f"

    W, H = 1120, 1280
    divider_x = 458

    ascii_font = 7.9
    ascii_line = 7.55
    max_ascii_height = H - 70
    ascii_h = len(ASCII_LINES) * ascii_line
    if ascii_h > max_ascii_height:
        scale = max_ascii_height / ascii_h
        ascii_font *= scale
        ascii_line *= scale
        ascii_h = len(ASCII_LINES) * ascii_line

    max_cols = max((len(line) for line in ASCII_LINES), default=1)
    char_w = ascii_font * 0.62
    ascii_w = max_cols * char_w
    panel_left = 22
    panel_right = divider_x - 22
    left_panel_w = panel_right - panel_left
    ascii_x = panel_left + max(0, (left_panel_w - ascii_w) / 2)
    ascii_top = 30

    tspans = "".join(
        f'<tspan x="{ascii_x:.2f}" y="{ascii_top + i * ascii_line:.2f}">{escape(line)}</tspan>'
        for i, line in enumerate(ASCII_LINES)
    )

    x = divider_x + 28
    dots_x = x + 128
    value_x = x + 220
    body_fs = 10.4
    row_h = 17.3

    parts = []
    parts.append(f'<text x="{x}" y="31" class="header">{escape(PROFILE["display_name"])}@github</text>')
    parts.append(f'<line x1="{x+118}" y1="26" x2="{W-32}" y2="26" stroke="{border}" />')
    parts.append(f'<text x="{W-34}" y="45" text-anchor="end" class="sub">{escape(PROFILE["location_line"])}</text>')

    def add_row(label, value, y):
        parts.append(f'<text x="{x}" y="{y}" class="key">{escape(label)}</text>')
        parts.append(f'<text x="{dots_x}" y="{y}" class="dots">..........</text>')
        parts.append(f'<text x="{value_x}" y="{y}" class="value">{escape(value)}</text>')
        return y + row_h

    def add_section(title, y, dash_count=28):
        parts.append(f'<text x="{x}" y="{y}" class="section">— {escape(title)} {"—"*dash_count}</text>')
        return y + 18

    y = 70
    for label, value in PROFILE["overview"]:
        y = add_row(label, value, y)

    y += 6
    y = add_section("stack / capability", y)
    for label, value in PROFILE["stack"]:
        y = add_row(label, value, y)

    y += 6
    y = add_section("current / selected work", y)
    for label, value in PROFILE["work"]:
        y = add_row(label, value, y)

    y += 6
    y = add_section("experience", y)
    for label, value in PROFILE["experience"]:
        y = add_row(label, value, y)

    y += 6
    y = add_section("contact", y)
    for label, value in PROFILE["contact"]:
        y = add_row(label, value, y)

    parts.append(f'<line x1="{x}" y1="{H-44}" x2="{W-32}" y2="{H-44}" stroke="{border}" />')

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <style>
    text {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      white-space: pre;
    }}
    .ascii {{ fill: {text}; }}
    .header {{ fill: {text}; font-size: 15px; font-weight: 600; }}
    .sub {{ fill: {muted}; font-size: 10.4px; }}
    .key {{ fill: {accent}; font-size: {body_fs}px; }}
    .value {{ fill: {text}; font-size: {body_fs}px; }}
    .dots {{ fill: {dim}; font-size: {body_fs}px; letter-spacing: 0.2px; }}
    .section {{ fill: {muted}; font-size: 10.1px; }}
  </style>
  <rect width="{W}" height="{H}" rx="16" fill="{bg}" stroke="{border}" />
  <line x1="{divider_x}" y1="20" x2="{divider_x}" y2="{H-20}" stroke="{border}" />
  <text class="ascii" font-size="{ascii_font:.3f}px">{tspans}</text>
  {''.join(parts)}
</svg>"""

for theme in ("dark", "light"):
    (ROOT / "assets" / f"profile-{theme}.svg").write_text(build_svg(theme), encoding="utf-8")

print("Wrote SVG files.")
