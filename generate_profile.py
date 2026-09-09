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
W, H, RIGHT_X, VALUE_X, FONT_SIZE = 985, 530, 300, 560, 16


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


def leader_dots(label):
    current = RIGHT_X + (2 + len(label) + 2) * 9.6
    return "." * max(3, int((VALUE_X - current) / 9.6))


def item(label, value, y):
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="cc"> {leader_dots(label)} </tspan>'
        f'<tspan x="{VALUE_X}" y="{y}" class="value">{escape(str(value))}</tspan>'
    )


def render(theme):
    C = DARK if theme == "dark" else LIGHT
    stats = PROFILE["stats_preview"]

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
        y += 20

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>')
    y += 20

    for label, value in PROFILE["stack"]:
        if isinstance(value, list):
            body.append(item(label, value[0], y))
            y += 20
            for continuation in value[1:]:
                body.append(f'<tspan x="{VALUE_X}" y="{y}" class="value">{escape(continuation)}</tspan>')
                y += 20
        else:
            body.append(item(label, value, y))
            y += 20

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>')
    y += 20

    for label, value in PROFILE["hobbies"]:
        body.append(item(label, value, y))
        y += 20

    body.append(f'<tspan x="{RIGHT_X}" y="360">- Contact </tspan><tspan class="cc">{"—" * 56}</tspan>')
    cy = 380
    for label, value in PROFILE["contact"]:
        body.append(item(label, value, cy))
        cy += 20

    body.append(f'<tspan x="{RIGHT_X}" y="450">- GitHub Stats </tspan><tspan class="cc">{"—" * 51}</tspan>')

    s = lambda key: str(stats.get(key, "N/A"))
    PIPE_X, RIGHT_LABEL_X, RIGHT_VALUE_X, LEFT_VALUE_X = 775, 795, 970, 745

    body.append(
        f'<tspan x="{RIGHT_X}" y="470" class="cc">. </tspan>'
        f'<tspan class="key">Repos</tspan>:<tspan class="cc"> ........ </tspan>'
        f'<tspan class="value">{escape(s("repos"))}</tspan> '
        f'{{<tspan class="key">Contributed</tspan>: <tspan class="value">{escape(s("contributed"))}</tspan>}}'
        f'<tspan x="{PIPE_X}" y="470" class="cc"> | </tspan>'
        f'<tspan x="{RIGHT_LABEL_X}" y="470" class="key">Stars</tspan>:'
        f'<tspan class="cc"> ............ </tspan>'
        f'<tspan x="{RIGHT_VALUE_X}" y="470" text-anchor="end" class="value">{escape(s("stars"))}</tspan>'
    )

    body.append(
        f'<tspan x="{RIGHT_X}" y="490" class="cc">. </tspan>'
        f'<tspan class="key">Commits</tspan>:<tspan class="cc"> ........................ </tspan>'
        f'<tspan x="{LEFT_VALUE_X}" y="490" text-anchor="end" class="value">{escape(s("commits"))}</tspan>'
        f'<tspan x="{PIPE_X}" y="490" class="cc"> | </tspan>'
        f'<tspan x="{RIGHT_LABEL_X}" y="490" class="key">Followers</tspan>:'
        f'<tspan class="cc"> ....... </tspan>'
        f'<tspan x="{RIGHT_VALUE_X}" y="490" text-anchor="end" class="value">{escape(s("followers"))}</tspan>'
    )

    body.append(
        f'<tspan x="{RIGHT_X}" y="510" class="cc">. </tspan>'
        f'<tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc"> ........ </tspan>'
        f'<tspan class="value">{escape(s("loc"))}</tspan><tspan class="cc"> ( </tspan>'
        f'<tspan class="addColor">{escape(s("additions"))}++</tspan><tspan class="cc">, </tspan>'
        f'<tspan class="delColor">{escape(s("deletions"))}--</tspan><tspan class="cc"> )</tspan>'
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
    print("GitHub stats intentionally remain N/A for now.")


if __name__ == "__main__":
    main()
