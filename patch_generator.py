from pathlib import Path

path = Path("generate_profile.py")
s = path.read_text(encoding="utf-8")

# Give dot leaders/markers their own explicit palette key.
if '"dots": "#ffffff"' not in s:
    s = s.replace('    "cc": "#ffffff",\n}', '    "cc": "#ffffff",\n    "dots": "#ffffff",\n}', 1)
if '"dots": "#000000"' not in s:
    s = s.replace('    "cc": "#000000",\n}', '    "cc": "#000000",\n    "dots": "#000000",\n}', 1)

# Shorten every calculated leader by exactly one dot.
old = 'int(gap / CHAR_W) + 1'
count = s.count(old)
if count:
    s = s.replace(old, 'int(gap / CHAR_W)')

# Left-side row dots and leader runs use the dedicated dots class.
s = s.replace('class="cc">. </tspan>', 'class="dots">. </tspan>')
s = s.replace('class="cc"> {dots} </tspan>', 'class="dots"> {dots} </tspan>')

# Emit the dedicated SVG class.
old_style = '.delColor{{fill:{C["delete"]};}} .cc{{fill:{C["cc"]};}}'
new_style = '.delColor{{fill:{C["delete"]};}} .cc{{fill:{C["cc"]};}} .dots{{fill:{C["dots"]};}}'
if old_style in s:
    s = s.replace(old_style, new_style, 1)

path.write_text(s, encoding="utf-8")
print(f"Patched generator; shortened {count} leader calculations.")
