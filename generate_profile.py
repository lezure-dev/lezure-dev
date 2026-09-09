#!/usr/bin/env python3
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
import calendar
import datetime as dt
import json

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
LINES = (ROOT / "ascii" / "helix.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
while LINES and not LINES[0].strip(): LINES.pop(0)
while LINES and not LINES[-1].strip(): LINES.pop()
lead = min((len(x) - len(x.lstrip(" ")) for x in LINES if x.strip()), default=0)
LINES = [x[lead:].rstrip() for x in LINES]

DARK = {"bg":"#161b22","main":"#c9d1d9","key":"#ffa657","value":"#a5d6ff","add":"#3fb950","delete":"#f85149","cc":"#616e7f"}
LIGHT = {"bg":"#f6f8fa","main":"#24292f","key":"#953800","value":"#0a3069","add":"#1a7f37","delete":"#cf222e","cc":"#c2cfde"}

W, H = 985, 530
RIGHT_X = 300
RIGHT_EDGE = 970
FONT_SIZE = 16
CHAR_W = 9.6
ROW = 20

def add_months(d, months):
    total = d.year * 12 + d.month - 1 + months
    year, m0 = divmod(total, 12)
    month = m0 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return dt.date(year, month, day)

def age_text():
    birthday = dt.date.fromisoformat(PROFILE["birthday"])
    today = dt.datetime.now(ZoneInfo("America/Chicago")).date()
    years = today.year - birthday.year
    anniversary = birthday.replace(year=birthday.year + years)
    if anniversary > today:
        years -= 1
        anniversary = birthday.replace(year=birthday.year + years)
    months = 0
    cursor = anniversary
    while add_months(cursor, 1) <= today:
        cursor = add_months(cursor, 1)
        months += 1
    days = (today - cursor).days
    return f"{years} years, {months} months, {days} days"

def dots_between(label, value, min_dots=3):
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = RIGHT_EDGE - len(str(value)) * CHAR_W
    gap = value_start - label_end
    return "." * max(min_dots, int(gap / CHAR_W) - 1)

def item(label, value, y):
    value = str(value)
    dots = dots_between(label, value)
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="cc"> {dots} </tspan>'
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="value">{escape(value)}</tspan>'
    )

def continuation(value, y):
    return (
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="value">'
        f'{escape(str(value))}</tspan>'
    )

def render(theme):
    C = DARK if theme == "dark" else LIGHT

    ascii_font, ascii_line, ascii_top = 16.6, 14.15, 18
    ascii_h = len(LINES) * ascii_line
    if ascii_h > H - 34:
        scale = (H - 34) / ascii_h
        ascii_font *= scale
        ascii_line *= scale
    max_cols = max(map(len, LINES)) if LINES else 1
    art_w = max_cols * ascii_font * 0.60
    art_x = max(15, (RIGHT_X - art_w) / 2)
    art = "".join(
        f'<tspan x="{art_x:.2f}" y="{ascii_top + i * ascii_line:.2f}">{escape(line)}</tspan>'
        for i, line in enumerate(LINES)
    )

    body = [
        f'<tspan x="{RIGHT_X}" y="30">{escape(PROFILE["header"])}</tspan>'
        f'<tspan class="cc"> -{"—" * 54}-</tspan>'
    ]

    y = 50
    for label, value in PROFILE["system"]:
        body.append(item(label, age_text() if value == "__AGE__" else value, y))
        y += ROW

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>')
    y += ROW

    for label, value in PROFILE["stack"]:
        if isinstance(value, list):
            body.append(item(label, value[0], y))
            y += ROW
            for cont in value[1:]:
                body.append(continuation(cont, y))
                y += ROW
        else:
            body.append(item(label, value, y))
            y += ROW

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>')
    y += ROW

    for label, value in PROFILE["hobbies"]:
        body.append(item(label, value, y))
        y += ROW

    body.append(
        f'<tspan x="{RIGHT_X}" y="360">- Contact </tspan>'
        f'<tspan class="cc">{"—" * 56}</tspan>'
    )
    cy = 380
    for label, value in PROFILE["contact"]:
        body.append(item(label, value, cy))
        cy += ROW

    body.append(
        f'<tspan x="{RIGHT_X}" y="450">- GitHub Stats </tspan>'
        f'<tspan class="cc">{"—" * 51}</tspan>'
    )

    PIPE_X = 775
    RIGHT_LABEL_X = 795

    def left_dots(label):
        label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
        return "." * max(3, int((PIPE_X - 18 - label_end) / CHAR_W))

    def right_dots(label):
        label_end = RIGHT_LABEL_X + (len(label) + 2) * CHAR_W
        return "." * max(3, int((RIGHT_EDGE - label_end) / CHAR_W))

    body.append(
        f'<tspan x="{RIGHT_X}" y="470" class="cc">. </tspan>'
        f'<tspan class="key">Repos</tspan>:'
        f'<tspan class="cc"> {left_dots("Repos")} </tspan>'
        f'<tspan x="{PIPE_X}" y="470" class="cc">|</tspan>'
        f'<tspan x="{RIGHT_LABEL_X}" y="470" class="key">Stars</tspan>:'
        f'<tspan class="cc"> {right_dots("Stars")}</tspan>'
    )

    body.append(
        f'<tspan x="{RIGHT_X}" y="490" class="cc">. </tspan>'
        f'<tspan class="key">Commits</tspan>:'
        f'<tspan class="cc"> {left_dots("Commits")} </tspan>'
        f'<tspan x="{PIPE_X}" y="490" class="cc">|</tspan>'
        f'<tspan x="{RIGHT_LABEL_X}" y="490" class="key">Followers</tspan>:'
        f'<tspan class="cc"> {right_dots("Followers")}</tspan>'
    )

    loc_label = "Lines of Code on GitHub"
    loc_label_end = RIGHT_X + (2 + len(loc_label) + 2) * CHAR_W
    loc_dots = "." * max(3, int((PIPE_X - 18 - loc_label_end) / CHAR_W))
    body.append(
        f'<tspan x="{RIGHT_X}" y="510" class="cc">. </tspan>'
        f'<tspan class="key">{loc_label}</tspan>:'
        f'<tspan class="cc"> {loc_dots} </tspan>'
        f'<tspan x="{PIPE_X}" y="510" class="cc">( </tspan>'
        f'<tspan class="addColor">........++</tspan>'
        f'<tspan class="cc">, </tspan>'
        f'<tspan class="delColor">........--</tspan>'
        f'<tspan class="cc"> )</tspan>'
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{W}px" height="{H}px" font-size="{FONT_SIZE}px">
<style>
@font-face{{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;-webkit-size-adjust:109%;size-adjust:109%;}}
.key{{fill:{C["key"]};}} .value{{fill:{C["value"]};}} .addColor{{fill:{C["add"]};}} .delColor{{fill:{C["delete"]};}} .cc{{fill:{C["cc"]};}}
text,tspan{{white-space:pre;}}
</style>
<rect width="{W}px" height="{H}px" fill="{C["bg"]}" rx="15"/>
<text x="15" y="30" fill="{C["main"]}" class="ascii" font-size="{ascii_font:.3f}px">{art}</text>
<text x="{RIGHT_X}" y="30" fill="{C["main"]}">{''.join(body)}</text>
</svg>'''

def main():
    for theme in ("dark", "light"):
        (ROOT / "assets" / f"{theme}_mode.svg").write_text(render(theme), encoding="utf-8")
    print("Uptime:", age_text())
    print("GitHub stats intentionally render as dotted placeholders.")

if __name__ == "__main__":
    main()
