from pathlib import Path
import re

path = Path("generate_profile.py")
s = path.read_text(encoding="utf-8")

# Andrew-style split: the first two rows use | at the same x as the LOC opening parenthesis.
s = s.replace(
    "PIPE_X = 775\nLEFT_VALUE_X = 755\nRIGHT_LABEL_X = 795",
    "PIPE_X = 640\nLEFT_VALUE_X = PIPE_X - 20\nRIGHT_LABEL_X = PIPE_X + 20",
)

# Track commit count alongside LOC/churn while full history is already cloned.
s = s.replace(
    "    total_deletions = 0\n    counted = 0",
    "    total_deletions = 0\n    total_commits = 0\n    counted = 0",
)

history_tail = '''                if history.returncode == 0:\n                    for line in history.stdout.splitlines():\n                        parts = line.split("\\t", 2)\n                        if len(parts) < 2:\n                            continue\n                        added, deleted = parts[0], parts[1]\n                        if added.isdigit():\n                            total_additions += int(added)\n                        if deleted.isdigit():\n                            total_deletions += int(deleted)\n\n                counted += 1'''
replacement_tail = '''                if history.returncode == 0:\n                    for line in history.stdout.splitlines():\n                        parts = line.split("\\t", 2)\n                        if len(parts) < 2:\n                            continue\n                        added, deleted = parts[0], parts[1]\n                        if added.isdigit():\n                            total_additions += int(added)\n                        if deleted.isdigit():\n                            total_deletions += int(deleted)\n\n                commits = subprocess.run(\n                    [\n                        "git", "-C", str(dest), "rev-list",\n                        "--count", "--no-merges", "HEAD",\n                    ],\n                    stdout=subprocess.PIPE,\n                    stderr=subprocess.DEVNULL,\n                    text=True,\n                    timeout=120,\n                    check=False,\n                )\n                if commits.returncode == 0:\n                    try:\n                        total_commits += int(commits.stdout.strip() or 0)\n                    except ValueError:\n                        pass\n\n                counted += 1'''
if history_tail not in s:
    raise SystemExit("history block not found")
s = s.replace(history_tail, replacement_tail, 1)

s = s.replace(
    '        "deletions": total_deletions,\n    }',
    '        "deletions": total_deletions,\n        "commits": total_commits,\n    }',
    1,
)
s = s.replace(
    'if any(cache.get(key) is None for key in ("loc", "additions", "deletions")):',
    'if any(cache.get(key) is None for key in ("loc", "additions", "deletions", "commits")):',
    1,
)

# Replace the stats-row renderers with Andrew-style geometry.
pattern = re.compile(r'def left_stat\(label, value, y\):.*?\n\ndef render\(theme, stats\):', re.S)
replacement = r'''def left_stat(label, value, y):
    value = fmt_stat(value)
    value_end = LEFT_VALUE_X
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = value_end - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(3, int(gap / CHAR_W))
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{value_end}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
        f'<tspan x="{PIPE_X}" y="{y}" class="cc">|</tspan>'
    )


def repo_stat_row(stats, y):
    label = "Repos"
    repos = fmt_stat(stats.get("repos"))
    contributed = fmt_stat(stats.get("contributed", 0))
    contrib_prefix = "{Contributed: "
    contrib_suffix = "}"
    contrib_text = contrib_prefix + contributed + contrib_suffix

    contrib_end = PIPE_X - 14
    contrib_start = contrib_end - len(contrib_text) * CHAR_W
    repo_end = contrib_start - CHAR_W
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    repo_start = repo_end - len(repos) * CHAR_W
    gap = repo_start - label_end
    dots = "." * max(2, int(gap / CHAR_W))

    number_x = contrib_start + len(contrib_prefix) * CHAR_W
    suffix_x = number_x + len(contributed) * CHAR_W

    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{label}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{repo_end}" y="{y}" text-anchor="end" class="value">{escape(repos)}</tspan>'
        f'<tspan x="{contrib_start:.1f}" y="{y}" class="key">{escape(contrib_prefix)}</tspan>'
        f'<tspan x="{number_x:.1f}" y="{y}" class="value">{escape(contributed)}</tspan>'
        f'<tspan x="{suffix_x:.1f}" y="{y}" class="key">{escape(contrib_suffix)}</tspan>'
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
    value_end = PIPE_X - 14
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = value_end - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(2, int(gap / CHAR_W))

    added = fmt_stat(stats.get("additions"))
    deleted = fmt_stat(stats.get("deletions"))

    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{label}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{value_end}" y="{y}" text-anchor="end" class="value">{escape(value)}</tspan>'
        f'<tspan x="{PIPE_X}" y="{y}" class="cc">( </tspan>'
        f'<tspan class="addColor">{escape(added)}++</tspan>'
        f'<tspan class="cc">, </tspan>'
        f'<tspan class="delColor">{escape(deleted)}--</tspan>'
        f'<tspan class="cc"> )</tspan>'
    )


def render(theme, stats):'''

s, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit(f"stats renderer block replacement count={count}")

s = s.replace(
    '    body.append(left_stat("Repos", stats.get("repos"), 470))\n'
    '    body.append(right_stat("Stars", stats.get("stars"), 470))\n'
    '    body.append(left_stat("Contrib", stats.get("contributed", 0), 490))\n'
    '    body.append(right_stat("Followers", stats.get("followers"), 490))\n'
    '    body.append(code_stat_row(stats, 510))',
    '    body.append(repo_stat_row(stats, 470))\n'
    '    body.append(right_stat("Stars", stats.get("stars"), 470))\n'
    '    body.append(left_stat("Commits", stats.get("commits"), 490))\n'
    '    body.append(right_stat("Followers", stats.get("followers"), 490))\n'
    '    body.append(code_stat_row(stats, 510))',
    1,
)

s = s.replace(
    '        f"followers={fmt_stat(stats.get(\'followers\'))},",\n'
    '        f"loc={fmt_stat(stats.get(\'loc\'))},",',
    '        f"followers={fmt_stat(stats.get(\'followers\'))},",\n'
    '        f"commits={fmt_stat(stats.get(\'commits\'))},",\n'
    '        f"loc={fmt_stat(stats.get(\'loc\'))},",',
    1,
)

path.write_text(s, encoding="utf-8")
print("Patched GitHub stats layout, full churn numbers, contributed tag, and commits.")
