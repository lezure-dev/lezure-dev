from pathlib import Path
import re

path = Path("generate_profile.py")
s = path.read_text(encoding="utf-8")

pattern = re.compile(r'def left_stat\(label, value, y\):.*?\n\ndef render\(theme, stats\):', re.S)
replacement = r'''def stats_geometry(stats):
    added = fmt_stat(stats.get("additions"))
    deleted = fmt_stat(stats.get("deletions"))

    open_text = "( "
    added_text = f"{added}++"
    middle_text = ", "
    deleted_text = f"{deleted}--"
    close_text = " )"

    close_start = RIGHT_EDGE - len(close_text) * CHAR_W
    deleted_x = close_start - len(deleted_text) * CHAR_W
    middle_x = deleted_x - len(middle_text) * CHAR_W
    added_x = middle_x - len(added_text) * CHAR_W
    split_x = added_x - len(open_text) * CHAR_W

    return {
        "split_x": split_x,
        "right_label_x": split_x + 20,
        "left_value_x": split_x - 20,
        "open_text": open_text,
        "added_text": added_text,
        "middle_text": middle_text,
        "deleted_text": deleted_text,
        "close_text": close_text,
        "added_x": added_x,
        "middle_x": middle_x,
        "deleted_x": deleted_x,
    }


def left_stat(label, value, y, stats):
    value = fmt_stat(value)
    geometry = stats_geometry(stats)
    split_x = geometry["split_x"]
    value_end = geometry["left_value_x"]
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = value_end - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(3, int(gap / CHAR_W))
    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{escape(label)}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{value_end:.1f}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
        f'<tspan x="{split_x:.1f}" y="{y}" class="cc">|</tspan>'
    )


def repo_stat_row(stats, y):
    label = "Repos"
    repos = fmt_stat(stats.get("repos"))
    contributed = fmt_stat(stats.get("contributed", 0))
    contrib_prefix = "{Contributed: "
    contrib_suffix = "}"
    contrib_text = contrib_prefix + contributed + contrib_suffix

    geometry = stats_geometry(stats)
    split_x = geometry["split_x"]
    contrib_end = split_x - 14
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
        f'<tspan x="{repo_end:.1f}" y="{y}" text-anchor="end" class="value">{escape(repos)}</tspan>'
        f'<tspan x="{contrib_start:.1f}" y="{y}" class="key">{escape(contrib_prefix)}</tspan>'
        f'<tspan x="{number_x:.1f}" y="{y}" class="value">{escape(contributed)}</tspan>'
        f'<tspan x="{suffix_x:.1f}" y="{y}" class="key">{escape(contrib_suffix)}</tspan>'
        f'<tspan x="{split_x:.1f}" y="{y}" class="cc">|</tspan>'
    )


def right_stat(label, value, y, stats):
    value = fmt_stat(value)
    geometry = stats_geometry(stats)
    label_x = geometry["right_label_x"]
    label_end = label_x + (len(label) + 2) * CHAR_W
    value_start = RIGHT_EDGE - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(2, int(gap / CHAR_W))
    return (
        f'<tspan x="{label_x:.1f}" y="{y}" class="key">{escape(label)}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="value">'
        f"{escape(value)}</tspan>"
    )


def code_stat_row(stats, y):
    label = "Lines of Code on GitHub"
    value = fmt_stat(stats.get("loc"))
    geometry = stats_geometry(stats)
    split_x = geometry["split_x"]
    value_end = split_x - 14
    label_end = RIGHT_X + (2 + len(label) + 2) * CHAR_W
    value_start = value_end - len(value) * CHAR_W
    gap = value_start - label_end
    dots = "." * max(2, int(gap / CHAR_W))

    return (
        f'<tspan x="{RIGHT_X}" y="{y}" class="dots">. </tspan>'
        f'<tspan class="key">{label}</tspan>:'
        f'<tspan class="dots"> {dots} </tspan>'
        f'<tspan x="{value_end:.1f}" y="{y}" text-anchor="end" class="value">{escape(value)}</tspan>'
        f'<tspan x="{split_x:.1f}" y="{y}" class="cc">{escape(geometry["open_text"])}</tspan>'
        f'<tspan x="{geometry["added_x"]:.1f}" y="{y}" class="addColor">{escape(geometry["added_text"])}</tspan>'
        f'<tspan x="{geometry["middle_x"]:.1f}" y="{y}" class="cc">{escape(geometry["middle_text"])}</tspan>'
        f'<tspan x="{geometry["deleted_x"]:.1f}" y="{y}" class="delColor">{escape(geometry["deleted_text"])}</tspan>'
        f'<tspan x="{RIGHT_EDGE}" y="{y}" text-anchor="end" class="cc">{escape(geometry["close_text"])}</tspan>'
    )


def render(theme, stats):'''

s, count = pattern.subn(replacement, s, count=1)
if count != 1:
    raise SystemExit(f"stats renderer replacement count={count}")

s = s.replace(
    '    body.append(repo_stat_row(stats, 470))\n'
    '    body.append(right_stat("Stars", stats.get("stars"), 470))\n'
    '    body.append(left_stat("Commits", stats.get("commits"), 490))\n'
    '    body.append(right_stat("Followers", stats.get("followers"), 490))\n'
    '    body.append(code_stat_row(stats, 510))',
    '    body.append(repo_stat_row(stats, 470))\n'
    '    body.append(right_stat("Stars", stats.get("stars"), 470, stats))\n'
    '    body.append(left_stat("Commits", stats.get("commits"), 490, stats))\n'
    '    body.append(right_stat("Followers", stats.get("followers"), 490, stats))\n'
    '    body.append(code_stat_row(stats, 510))',
    1,
)

path.write_text(s, encoding="utf-8")
print("Pinned LOC closing parenthesis to the right edge and aligned stats columns dynamically.")
