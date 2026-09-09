#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape
import datetime as dt
import json
import os
import urllib.request

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
LINES = (ROOT / "ascii" / "helix.txt").read_text(encoding="utf-8", errors="ignore").splitlines()

while LINES and not LINES[0].strip():
    LINES.pop(0)
while LINES and not LINES[-1].strip():
    LINES.pop()
_min_lead = min((len(line) - len(line.lstrip(" ")) for line in LINES if line.strip()), default=0)
LINES = [line[_min_lead:].rstrip() for line in LINES]

USERNAME = "fkpanni"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

DARK = {
    "bg": "#161b22", "main": "#c9d1d9", "key": "#ffa657",
    "value": "#a5d6ff", "add": "#3fb950", "delete": "#f85149", "cc": "#616e7f",
}
LIGHT = {
    "bg": "#f6f8fa", "main": "#24292f", "key": "#953800",
    "value": "#0a3069", "add": "#1a7f37", "delete": "#cf222e", "cc": "#c2cfde",
}

W, H = 985, 530
RIGHT_X = 330
FONT_SIZE = 16
ROW_STEP = 20

def graphql(query: str, variables: dict) -> dict:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required for dynamic stats.")
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{USERNAME}-profile-readme",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]

def basic_stats() -> dict:
    query = """
    query($login:String!) {
      user(login:$login) {
        followers { totalCount }
        repositories(first:100, ownerAffiliations:OWNER) {
          totalCount
          nodes { nameWithOwner stargazerCount }
        }
        repositoriesContributedTo(first:1, contributionTypes:[COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) {
          totalCount
        }
        contributionsCollection {
          totalCommitContributions
        }
      }
    }
    """
    user = graphql(query, {"login": USERNAME})["user"]
    return {
        "repos": user["repositories"]["totalCount"],
        "contributed": user["repositoriesContributedTo"]["totalCount"],
        "stars": sum(repo["stargazerCount"] for repo in user["repositories"]["nodes"]),
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "followers": user["followers"]["totalCount"],
    }

def owned_repositories():
    query = """
    query($login:String!, $cursor:String) {
      user(login:$login) {
        repositories(first:50, after:$cursor, ownerAffiliations:OWNER) {
          nodes {
            name
            nameWithOwner
            defaultBranchRef {
              target {
                ... on Commit { oid }
              }
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
    """
    cursor = None
    repos = []
    while True:
        data = graphql(query, {"login": USERNAME, "cursor": cursor})["user"]["repositories"]
        repos.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            return repos
        cursor = data["pageInfo"]["endCursor"]

def repo_loc(repo_name: str):
    query = """
    query($owner:String!, $name:String!, $cursor:String) {
      repository(owner:$owner, name:$name) {
        defaultBranchRef {
          target {
            ... on Commit {
              history(first:100, after:$cursor) {
                nodes {
                  additions
                  deletions
                  author { user { login } }
                }
                pageInfo { hasNextPage endCursor }
              }
            }
          }
        }
      }
    }
    """
    cursor = None
    additions = deletions = 0
    while True:
        result = graphql(query, {"owner": USERNAME, "name": repo_name, "cursor": cursor})["repository"]
        branch = result.get("defaultBranchRef")
        if not branch:
            return additions, deletions
        history = branch["target"]["history"]
        for commit in history["nodes"]:
            author = ((commit.get("author") or {}).get("user") or {}).get("login")
            if author and author.lower() == USERNAME.lower():
                additions += int(commit["additions"])
                deletions += int(commit["deletions"])
        if not history["pageInfo"]["hasNextPage"]:
            return additions, deletions
        cursor = history["pageInfo"]["endCursor"]

def lines_of_code():
    cache_path = ROOT / "stats_cache.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        cache = {}

    additions = deletions = 0
    repos = owned_repositories()
    new_cache = {}

    # Cache by default branch HEAD oid so unchanged repos cost no history queries.
    for repo in repos:
        branch = repo.get("defaultBranchRef")
        oid = branch["target"]["oid"] if branch else None
        key = repo["nameWithOwner"]
        prior = cache.get(key, {})
        if prior.get("oid") == oid:
            add = int(prior.get("additions", 0))
            delete = int(prior.get("deletions", 0))
        else:
            add, delete = repo_loc(repo["name"])
        new_cache[key] = {"oid": oid, "additions": add, "deletions": delete}
        additions += add
        deletions += delete

    cache_path.write_text(json.dumps(new_cache, indent=2), encoding="utf-8")
    return additions, deletions, additions - deletions

def fmt_num(value):
    return f"{value:,}" if isinstance(value, int) else str(value)

def dot_count(label, value, target=61):
    return max(3, target - len(label) - len(str(value)))

def build_svg(theme, stats):
    C = DARK if theme == "dark" else LIGHT

    ascii_top = 27
    ascii_line = 14.15
    ascii_font = 15.5
    ascii_h = len(LINES) * ascii_line
    max_h = H - 42
    if ascii_h > max_h:
        scale = max_h / ascii_h
        ascii_line *= scale
        ascii_font *= scale
        ascii_h = len(LINES) * ascii_line

    max_cols = max((len(line) for line in LINES), default=1)
    art_w = max_cols * ascii_font * 0.60
    art_x = max(15, (RIGHT_X - art_w) / 2)

    tspans = "".join(
        f'<tspan x="{art_x:.2f}" y="{ascii_top + i*ascii_line:.2f}">{escape(line)}</tspan>'
        for i, line in enumerate(LINES)
    )

    body = []
    y = 30
    body.append(
        f'<tspan x="{RIGHT_X}" y="{y}">{escape(PROFILE["header"])}</tspan>'
        f' -{"—"*44}-'
    )

    def item(label, value, y):
        dots = "." * dot_count(label, value)
        return (
            f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">{escape(label)}</tspan>:'
            f'<tspan class="cc"> {dots} </tspan>'
            f'<tspan class="value">{escape(str(value))}</tspan>'
        )

    y += ROW_STEP
    for label, value in PROFILE["system"]:
        body.append(item(label, value, y)); y += ROW_STEP

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'); y += ROW_STEP

    for label, value in PROFILE["stack"]:
        body.append(item(label, value, y)); y += ROW_STEP

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'); y += ROW_STEP

    for label, value in PROFILE["hobbies"]:
        body.append(item(label, value, y)); y += ROW_STEP

    y += ROW_STEP
    body.append(f'<tspan x="{RIGHT_X}" y="{y}">- Contact {"—"*39}</tspan>'); y += ROW_STEP
    for label, value in PROFILE["contact"]:
        body.append(item(label, value, y)); y += ROW_STEP

    y += ROW_STEP
    body.append(f'<tspan x="{RIGHT_X}" y="{y}">- GitHub Stats {"—"*35}</tspan>'); y += ROW_STEP

    repos = fmt_num(stats["repos"])
    contributed = fmt_num(stats["contributed"])
    stars = fmt_num(stats["stars"])
    commits = fmt_num(stats["commits"])
    followers = fmt_num(stats["followers"])
    loc = fmt_num(stats["loc"])
    additions = fmt_num(stats["additions"])
    deletions = fmt_num(stats["deletions"])

    body.append(
        f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
        f'<tspan class="key">Repos</tspan>:<tspan class="cc"> .... </tspan>'
        f'<tspan class="value">{repos}</tspan> '
        f'{{<tspan class="key">Contributed</tspan>: <tspan class="value">{contributed}</tspan>}}'
        f' | <tspan class="key">Stars</tspan>:<tspan class="cc"> .... </tspan>'
        f'<tspan class="value">{stars}</tspan>'
    ); y += ROW_STEP

    body.append(
        f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
        f'<tspan class="key">Commits</tspan>:<tspan class="cc"> .............. </tspan>'
        f'<tspan class="value">{commits}</tspan>'
        f' | <tspan class="key">Followers</tspan>:<tspan class="cc"> .... </tspan>'
        f'<tspan class="value">{followers}</tspan>'
    ); y += ROW_STEP

    body.append(
        f'<tspan x="{RIGHT_X}" y="{y}" class="cc">. </tspan>'
        f'<tspan class="key">Lines of Code on GitHub</tspan>:<tspan class="cc"> . </tspan>'
        f'<tspan class="value">{loc}</tspan> ( '
        f'<tspan class="addColor">{additions}</tspan><tspan class="addColor">++</tspan>, '
        f'<tspan class="delColor">{deletions}</tspan><tspan class="delColor">--</tspan> )'
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     font-family="ConsolasFallback,Consolas,monospace"
     width="{W}px" height="{H}px" font-size="{FONT_SIZE}px">
<style>
@font-face {{
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  -webkit-size-adjust: 109%;
  size-adjust: 109%;
}}
.key {{ fill: {C["key"]}; }}
.value {{ fill: {C["value"]}; }}
.addColor {{ fill: {C["add"]}; }}
.delColor {{ fill: {C["delete"]}; }}
.cc {{ fill: {C["cc"]}; }}
text, tspan {{ white-space: pre; }}
</style>
<rect width="{W}px" height="{H}px" fill="{C["bg"]}" rx="15"/>
<text x="15" y="30" fill="{C["main"]}" class="ascii" font-size="{ascii_font:.3f}px">
{tspans}
</text>
<text x="{RIGHT_X}" y="30" fill="{C["main"]}">
{''.join(body)}
</text>
</svg>"""

def main():
    stats = basic_stats()
    additions, deletions, loc = lines_of_code()
    stats.update({"additions": additions, "deletions": deletions, "loc": loc})

    for theme in ("dark", "light"):
        (ASSETS / f"{theme}_mode.svg").write_text(build_svg(theme, stats), encoding="utf-8")

    print("Updated profile stats:", stats)

if __name__ == "__main__":
    main()
