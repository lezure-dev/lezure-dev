#!/usr/bin/env python3
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
import base64
import calendar
import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
CACHE_PATH = ROOT / "stats_cache.json"

LINES = (ROOT / "ascii" / "helix.txt").read_text(
    encoding="utf-8", errors="ignore"
).splitlines()
while LINES and not LINES[0].strip():
    LINES.pop(0)
while LINES and not LINES[-1].strip():
    LINES.pop()
lead = min((len(x) - len(x.lstrip(" ")) for x in LINES if x.strip()), default=0)
LINES = [x[lead:].rstrip() for x in LINES]

DARK = {
    "bg": "#000000",
    "main": "#ffffff",
    "key": "#00ff41",
    "value": "#ffffff",
    "add": "#3fb950",
    "delete": "#f85149",
    "cc": "#ffffff",
    "dots": "#ffffff",
}
LIGHT = {
    "bg": "#ffffff",
    "main": "#000000",
    "key": "#d0006f",
    "value": "#000000",
    "add": "#1a7f37",
    "delete": "#cf222e",
    "cc": "#000000",
    "dots": "#000000",
}

W, H = 985, 530
RIGHT_X = 300
RIGHT_EDGE = 970
FONT_SIZE = 16
CHAR_W = 9.6
ROW = 20
PIPE_X = 775
LEFT_VALUE_X = 755
RIGHT_LABEL_X = 795
CODE_STATS_REFRESH_DAYS = 7


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


def load_cache():
    try:
        data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(data):
    CACHE_PATH.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def api_json(url, token=None, payload=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-readme-generator",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    method = "GET"
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def paginated_repos(url, token=None):
    repos = []
    page = 1
    separator = "&" if "?" in url else "?"
    while True:
        batch = api_json(f"{url}{separator}per_page=100&page={page}", token)
        if not isinstance(batch, list):
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def contributed_repo_count(username, token):
    if not token:
        return 0
    query = '''
    query($login: String!) {
      user(login: $login) {
        repositoriesContributedTo(
          first: 1
          includeUserRepositories: false
          contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, PULL_REQUEST_REVIEW]
        ) {
          totalCount
        }
      }
    }
    '''
    data = api_json(
        "https://api.github.com/graphql",
        token,
        {"query": query, "variables": {"login": username}},
    )
    if data.get("errors"):
        return None
    user = data.get("data", {}).get("user") or {}
    connection = user.get("repositoriesContributedTo") or {}
    return connection.get("totalCount")


def github_username():
    owner = os.getenv("GITHUB_REPOSITORY_OWNER")
    if owner:
        return owner
    for label, value in PROFILE.get("contact", []):
        if label == "GitHub":
            return str(value)
    return PROFILE["header"].split("@", 1)[0]


def clone_auth_env(token):
    env = os.environ.copy()
    if not token:
        return env
    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.https://github.com/.extraheader"
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {basic}"
    return env


def code_stats(owned_repos, token):
    if not owned_repos or not shutil.which("cloc") or not shutil.which("git"):
        return None

    total_loc = 0
    total_additions = 0
    total_deletions = 0
    counted = 0

    with tempfile.TemporaryDirectory(prefix="profile-code-stats-") as temp:
        temp_root = Path(temp)
        git_env = clone_auth_env(token)

        for index, repo in enumerate(owned_repos):
            if repo.get("fork") or repo.get("size", 0) == 0:
                continue
            full_name = repo.get("full_name")
            if not full_name:
                continue

            dest = temp_root / f"repo-{index}"
            try:
                clone = subprocess.run(
                    [
                        "git", "clone", "--quiet", "--filter=blob:none",
                        "--single-branch",
                        f"https://github.com/{full_name}.git", str(dest),
                    ],
                    env=git_env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=300,
                    check=False,
                )
                if clone.returncode != 0:
                    continue

                cloc = subprocess.run(
                    [
                        "cloc", "--json", "--quiet",
                        "--exclude-dir=.git,node_modules,dist,build,.next,coverage,vendor",
                        str(dest),
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=240,
                    check=False,
                )
                if cloc.returncode == 0:
                    data = json.loads(cloc.stdout)
                    total_loc += int((data.get("SUM") or {}).get("code", 0))

                history = subprocess.run(
                    [
                        "git", "-C", str(dest), "log",
                        "--no-merges", "--numstat", "--format=",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=300,
                    check=False,
                )
                if history.returncode == 0:
                    for line in history.stdout.splitlines():
                        parts = line.split("\t", 2)
                        if len(parts) < 2:
                            continue
                        added, deleted = parts[0], parts[1]
                        if added.isdigit():
                            total_additions += int(added)
                        if deleted.isdigit():
                            total_deletions += int(deleted)

                counted += 1
            except (
                subprocess.TimeoutExpired,
                json.JSONDecodeError,
                ValueError,
                OSError,
            ):
                pass
            finally:
                shutil.rmtree(dest, ignore_errors=True)

    if not counted:
        return None
    return {
        "loc": total_loc,
        "additions": total_additions,
        "deletions": total_deletions,
    }


def code_stats_are_stale(cache, username):
    if cache.get("username") != username:
        return True
    if any(cache.get(key) is None for key in ("loc", "additions", "deletions")):
        return True
    stamp = cache.get("code_stats_updated_at") or cache.get("loc_updated_at")
    if not stamp:
        return True
    try:
        previous = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return True
    now = dt.datetime.now(dt.timezone.utc)
    return now - previous >= dt.timedelta(days=CODE_STATS_REFRESH_DAYS)


def fetch_stats():
    cache = load_cache()
    username = github_username()
    token = os.getenv("PROFILE_GITHUB_TOKEN", "").strip() or None
    now = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    stats = dict(cache)
    stats["username"] = username
    owned_repos = []

    try:
        user = api_json(
            f"https://api.github.com/users/{urllib.parse.quote(username)}", token
        )
        stats["followers"] = int(user.get("followers", 0))

        if token:
            repos = paginated_repos(
                "https://api.github.com/user/repos?"
                "visibility=all&affiliation=owner,collaborator,organization_member",
                token,
            )
        else:
            repos = paginated_repos(
                f"https://api.github.com/users/{urllib.parse.quote(username)}/repos?type=owner"
            )

        owned_repos = [
            repo
            for repo in repos
            if str((repo.get("owner") or {}).get("login", "")).lower()
            == username.lower()
        ]
        stats["repos"] = len(owned_repos)
        stats["stars"] = sum(
            int(repo.get("stargazers_count", 0) or 0) for repo in owned_repos
        )

        contributed = contributed_repo_count(username, token)
        if contributed is not None:
            stats["contributed"] = int(contributed)
        elif stats.get("contributed") in (None, ""):
            stats["contributed"] = 0

        stats["updated_at"] = now
    except Exception as exc:
        print(
            "GitHub stats fetch failed; using cache where available: "
            f"{type(exc).__name__}: {exc}"
        )
        if stats.get("contributed") in (None, ""):
            stats["contributed"] = 0

    force_code_stats = (
        os.getenv("PROFILE_FORCE_CODE_STATS") == "1"
        or os.getenv("PROFILE_FORCE_LOC") == "1"
    )
    if owned_repos and (
        force_code_stats or code_stats_are_stale(stats, username)
    ):
        fresh = code_stats(owned_repos, token)
        if fresh:
            stats.update(fresh)
            stats["code_stats_updated_at"] = now
            stats["loc_updated_at"] = now

    save_cache(stats)
    return stats


def fmt_stat(value):
    if value is None or value == "":
        return "..."
    if isinstance(value, int):
        return f"{value:,}"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def compact_stat(value):
    if value is None or value == "":
        return "..."
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if n < 0 else ""
    n = abs(n)
    for divisor, suffix in (
        (1_000_000_000, "B"),
        (1_000_000, "M"),
        (1_000, "K"),
    ):
        if n >= divisor:
            scaled = n / divisor
            text = f"{scaled:.1f}".rstrip("0").rstrip(".")
            return f"{sign}{text}{suffix}"
    return f"{sign}{n}"


def dots_between(label, value, min_dots=3):
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = RIGHT_EDGE - len(str(value)) * CHAR_W
    gap = value_start - label_end
    return "." * max(min_dots, int(gap / CHAR_W))


def item(label, value, y):
    value = str(value)
    dots = dots_between(label, value)
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
    )


def continuation(value, y):
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="value">'
        f"{escape(str(value))}</tspan>"
    )


def left_stat(label, value, y):
    value = fmt_stat(value)
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = LEFT_VALUE_X - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(3, int(gap / CHAR_W))
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{LEFT_VALUE_X}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
        f'<tspan x="{PIPE_X}" y="{y}" class="cc">|</tspan>'
    )


def right_stat(label, value, y):
    value = fmt_stat(value)
    label_end = RIGHT_LABEL_X + (len(label) + 2) * CHAR_W
    value_start = RIGHT_EDGE - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(3, int(gap / CHAR_W))
    return (
        f'<tspan x="{RIGHT_LABEL_X}" y="{y}" class="key">{escape(label)}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
    )


def code_stat_row(stats, y):
    label = "Lines of Code on GitHub"
    value = fmt_stat(stats.get("loc"))
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = LEFT_VALUE_X - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(3, int(gap / CHAR_W))

    added = compact_stat(stats.get("additions"))
    deleted = compact_stat(stats.get("deletions"))

    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{label}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{LEFT_VALUE_X}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
        f'<tspan x="{PIPE_X}" y="{y}" class="cc">|</tspan>'
        f'<tspan x="{RIGHT_LABEL_X}" y="{y}" class="cc">(</tspan>'
        f'<tspan class="addColor">{escape(added)}++</tspan>'
        f'<tspan class="cc">, </tspan>'
        f'<tspan class="delColor">{escape(deleted)}--</tspan>'
        f'<tspan class="cc">)</tspan>'
    )


def render(theme, stats):
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
        f'<tspan x="{art_x:.2f}" y="{ascii_top + i * ascii_line:.2f}">'
        f"{escape(line)}</tspan>"
        for i, line in enumerate(LINES)
    )

    body = [
        f'<tspan x="{RIGHT_X}" y="30">{escape(PROFILE["header"])}</tspan>'
        f'<tspan class="cc"> -{"—" * 56}-</tspan>'
    ]

    y = 50
    for label, value in PROFILE["system"]:
        body.append(item(label, age_text() if value == "__AGE__" else value, y))
        y += ROW

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>')
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

    body.append(f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>')
    y += ROW

    for label, value in PROFILE["hobbies"]:
        body.append(item(label, value, y))
        y += ROW

    body.append(
        f'<tspan x="{RIGHT_X}" y="360">- Contact </tspan>'
        f'<tspan class="cc">{"—" * 58}</tspan>'
    )
    cy = 380
    for label, value in PROFILE["contact"]:
        body.append(item(label, value, cy))
        cy += ROW

    body.append(
        f'<tspan x="{RIGHT_X}" y="450">- GitHub Stats </tspan>'
        f'<tspan class="cc">{"—" * 53}</tspan>'
    )

    body.append(left_stat("Repos", stats.get("repos"), 470))
    body.append(right_stat("Stars", stats.get("stars"), 470))
    body.append(left_stat("Contrib", stats.get("contributed", 0), 490))
    body.append(right_stat("Followers", stats.get("followers"), 490))
    body.append(code_stat_row(stats, 510))

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="{W}px" height="{H}px" font-size="{FONT_SIZE}px">
<style>
@font-face{{src:local('Consolas'),local('Consolas Bold');font-family:'ConsolasFallback';font-display:swap;-webkit-size-adjust:109%;size-adjust:109%;}}
.key{{fill:{C["key"]};}} .value{{fill:{C["value"]};}} .addColor{{fill:{C["add"]};}} .delColor{{fill:{C["delete"]};}} .cc{{fill:{C["cc"]};}} .dots{{fill:{C["dots"]};}}
text,tspan{{white-space:pre;}}
</style>
<rect width="{W}px" height="{H}px" fill="{C["bg"]}" rx="15"/>
<text x="15" y="30" fill="{C["main"]}" class="ascii" font-size="{ascii_font:.3f}px">{art}</text>
<text x="{RIGHT_X}" y="30" fill="{C["main"]}">{''.join(body)}</text>
</svg>'''


def main():
    stats = fetch_stats()
    for theme in ("dark", "light"):
        (ROOT / "assets" / f"{theme}_mode.svg").write_text(
            render(theme, stats), encoding="utf-8"
        )
    print("Uptime:", age_text())
    print(
        "GitHub stats:",
        f"repos={fmt_stat(stats.get('repos'))},",
        f"contrib={fmt_stat(stats.get('contributed', 0))},",
        f"stars={fmt_stat(stats.get('stars'))},",
        f"followers={fmt_stat(stats.get('followers'))},",
        f"loc={fmt_stat(stats.get('loc'))},",
        f"added={fmt_stat(stats.get('additions'))},",
        f"deleted={fmt_stat(stats.get('deletions'))}",
    )


if __name__ == "__main__":
    main()
