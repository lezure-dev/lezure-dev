#!/usr/bin/env python3
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
import calendar
import datetime as dt
import json
import os
import urllib.request

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
LINES = (ROOT / "ascii" / "helix.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
while LINES and not LINES[0].strip(): LINES.pop(0)
while LINES and not LINES[-1].strip(): LINES.pop()
lead = min((len(x)-len(x.lstrip(" ")) for x in LINES if x.strip()), default=0)
LINES = [x[lead:].rstrip() for x in LINES]

USERNAME = "fkpanni"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
DARK = {"bg":"#161b22","main":"#c9d1d9","key":"#ffa657","value":"#a5d6ff","add":"#3fb950","delete":"#f85149","cc":"#616e7f"}
LIGHT = {"bg":"#f6f8fa","main":"#24292f","key":"#953800","value":"#0a3069","add":"#1a7f37","delete":"#cf222e","cc":"#c2cfde"}
W,H,RIGHT_X,VALUE_X,FONT_SIZE = 985,530,300,560,16

def add_months(d, months):
    total = d.year*12 + d.month-1 + months
    year,m0 = divmod(total,12)
    month=m0+1
    day=min(d.day, calendar.monthrange(year,month)[1])
    return dt.date(year,month,day)

def age_text():
    birthday = dt.date.fromisoformat(PROFILE["birthday"])
    today = dt.datetime.now(ZoneInfo("America/Chicago")).date()
    years = today.year-birthday.year
    ann = birthday.replace(year=birthday.year+years)
    if ann > today:
        years -= 1
        ann = birthday.replace(year=birthday.year+years)
    months=0
    cur=ann
    while True:
        nxt=add_months(cur,1)
        if nxt <= today:
            cur=nxt
            months += 1
        else:
            break
    days=(today-cur).days
    return f"{years} years, {months} months, {days} days"

def graphql():
    q = "query($login:String!){user(login:$login){followers{totalCount} repositories(first:100,ownerAffiliations:OWNER){totalCount nodes{stargazerCount}} repositoriesContributedTo(first:1,contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){totalCount} contributionsCollection{totalCommitContributions}}}"
    payload=json.dumps({"query":q,"variables":{"login":USERNAME}}).encode()
    req=urllib.request.Request("https://api.github.com/graphql",data=payload,headers={"Authorization":f"Bearer {TOKEN}","Content-Type":"application/json","User-Agent":f"{USERNAME}-profile-readme"},method="POST")
    with urllib.request.urlopen(req,timeout=45) as r:
        data=json.load(r)
    user=data["data"]["user"]
    return {
        "repos":user["repositories"]["totalCount"],
        "contributed":user["repositoriesContributedTo"]["totalCount"],
        "stars":sum(x["stargazerCount"] for x in user["repositories"]["nodes"]),
        "commits":user["contributionsCollection"]["totalCommitContributions"],
        "followers":user["followers"]["totalCount"],
        "loc":"N/A","additions":"N/A","deletions":"N/A"
    }

def leader_dots(label):
    current=RIGHT_X+(2+len(label)+2)*9.6
    return "."*max(3,int((VALUE_X-current)/9.6))

def item(label,value,y):
    return f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan><tspan class="key">{escape(label)}</tspan>:<tspan class="cc"> {leader_dots(label)} </tspan><tspan x="{VALUE_X}" y="{y}" class="value">{escape(str(value))}</tspan>'

def render(theme,stats):
    C=DARK if theme=="dark" else LIGHT
    ascii_font=16.6
    ascii_line=14.15
    ascii_top=18
    ascii_h=len(LINES)*ascii_line
    if ascii_h>H-34:
        scale=(H-34)/ascii_h
        ascii_font*=scale; ascii_line*=scale
    max_cols=max(map(len,LINES)) if LINES else 1
    art_w=max_cols*ascii_font*0.60
    art_x=max(15,(RIGHT_X-art_w)/2)
    art="".join(f'<tspan x="{art_x:.2f}" y="{ascii_top+i*ascii_line:.2f}">{escape(line)}</tspan>' for i,line in enumerate(LINES))
    body=[]
    body.append(f'<tspan x="{RIGHT_X}" y="30">{escape(PROFILE["header"])}</tspan><tspan class="cc"> -{"—"*54}-</tspan>')
    y=50
    for label,value in PROFILE["system"]:
        body.append(item(label,age_text() if value=="__AGE__" else value,y)); y+=20
    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'); y+=20
    for label,value in PROFILE["stack"]:
        if isinstance(value,list):
            body.append(item(label,value[0],y)); y+=20
            for cont in value[1:]:
                body.append(f'<tspan x="{VALUE_X}" y="{y}" class="value">{escape(cont)}</tspan>'); y+=20
        else:
            body.append(item(label,value,y)); y+=20
    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'); y+=20
    for label,value in PROFILE["hobbies"]:
        body.append(item(label,value,y)); y+=20
    body.append(f'<tspan x="{RIGHT_X}" y="360">- Contact </tspan><tspan class="cc">{"—"*56}</tspan>')
    cy=380
    for label,value in PROFILE["contact"]:
        body.append(item(label,value,cy)); cy+=20
    # GitHub Stats: fixed-column layout.
    # Labels hug the left of each field, values are right-aligned,
    # dotted leaders fill the middle, and both pipes share the same x.
    STATS_PIPE_X = 775
    STATS_RIGHT_LABEL_X = 795
    STATS_RIGHT_VALUE_X = 970
    STATS_LEFT_VALUE_X = 745

    body.append(
        f'<tspan x="{RIGHT_X}" y="450">- GitHub Stats </tspan>'
        f'<tspan class="cc">{"—"*51}</tspan>'
    )

    def s(k):
        return str(stats.get(k, "N/A"))

    # Row 1: Repos / Contributed | Stars
    body.append(
        f'<tspan x="{RIGHT_X}" y="470" class="cc">. </tspan>'
        f'<tspan class="key">Repos</tspan>:'
        f'<tspan class="cc"> ........ </tspan>'
        f'<tspan class="value">{escape(s("repos"))}</tspan> '
        f'{{<tspan class="key">Contributed</tspan>: '
        f'<tspan class="value">{escape(s("contributed"))}</tspan>}}'
        f'<tspan x="{STATS_PIPE_X}" y="470" class="cc"> | </tspan>'
        f'<tspan x="{STATS_RIGHT_LABEL_X}" y="470" class="key">Stars</tspan>:'
        f'<tspan class="cc"> ............ </tspan>'
        f'<tspan x="{STATS_RIGHT_VALUE_X}" y="470" text-anchor="end" class="value">{escape(s("stars"))}</tspan>'
    )

    # Row 2: Commits | Followers
    body.append(
        f'<tspan x="{RIGHT_X}" y="490" class="cc">. </tspan>'
        f'<tspan class="key">Commits</tspan>:'
        f'<tspan class="cc"> ........................ </tspan>'
        f'<tspan x="{STATS_LEFT_VALUE_X}" y="490" text-anchor="end" class="value">{escape(s("commits"))}</tspan>'
        f'<tspan x="{STATS_PIPE_X}" y="490" class="cc"> | </tspan>'
        f'<tspan x="{STATS_RIGHT_LABEL_X}" y="490" class="key">Followers</tspan>:'
        f'<tspan class="cc"> ....... </tspan>'
        f'<tspan x="{STATS_RIGHT_VALUE_X}" y="490" text-anchor="end" class="value">{escape(s("followers"))}</tspan>'
    )

    # Row 3: full-width LOC, with the final value group ending at the right edge.
    body.append(
        f'<tspan x="{RIGHT_X}" y="510" class="cc">. </tspan>'
        f'<tspan class="key">Lines of Code on GitHub</tspan>:'
        f'<tspan class="cc"> ........ </tspan>'
        f'<tspan class="value">{escape(s("loc"))}</tspan>'
        f'<tspan class="cc"> ( </tspan>'
        f'<tspan class="addColor">{escape(s("additions"))}++</tspan>'
        f'<tspan class="cc">, </tspan>'
        f'<tspan class="delColor">{escape(s("deletions"))}--</tspan>'
        f'<tspan class="cc"> )</tspan>'
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{W}px" height="{H}px" font-size="{FONT_SIZE}px"><style>@font-face{{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;-webkit-size-adjust:109%;size-adjust:109%;}}.key{{fill:{C["key"]};}}.value{{fill:{C["value"]};}}.addColor{{fill:{C["add"]};}}.delColor{{fill:{C["delete"]};}}.cc{{fill:{C["cc"]};}}text,tspan{{white-space:pre;}}</style><rect width="{W}px" height="{H}px" fill="{C["bg"]}" rx="15"/><text x="15" y="30" fill="{C["main"]}" class="ascii" font-size="{ascii_font:.3f}px">{art}</text><text x="{RIGHT_X}" y="30" fill="{C["main"]}">{''.join(body)}</text></svg>'''

def main():
    stats=PROFILE["stats_preview"].copy()
    if TOKEN:
        try: stats.update(graphql())
        except Exception as e: print("Stats update failed:",e)
    for theme in ("dark","light"):
        (ROOT/"assets"/f"{theme}_mode.svg").write_text(render(theme,stats),encoding="utf-8")
    print("Uptime:",age_text())
    print("Stats:",stats)

if __name__=="__main__":
    main()
