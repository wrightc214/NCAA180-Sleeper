"""
color_literal_check.py -- guard: no hard-coded good/bad (red/green) colours in page code (5.12.2).

Every colour that means something (good/bad, up/down, win/loss, odds, clinched/out, grades, ...)
must come from the shared tokens (docs/color-tokens.md): CSS var(--good) / var(--bad) / var(--neutral)
and the -soft / -fill variants, or NCAA180.colors.scale() in JS. This check fails when a red or green
colour literal -- hex, rgb(), hsl(), a computed hsl()/rgb() string, or a named colour in a CSS
declaration -- appears in page CSS/JS/HTML sources outside the token definitions and ALLOW below.

A literal used as the fallback of a token (var(--good,#1a7f37)) is fine and is not reported.

Scanned: scripts/ (*.py, *.js), templates/, reports/assets/ (*.js, *.css; not vendor/).
Not scanned: archived generated pages under reports/*.html (the kept --up/--dn aliases cover them),
config/*.json (owner palette settings), data/, tests/.

  python3 scripts/color_literal_check.py     list offenders; exit 1 if any (tests/test_color_literals.py)
"""
import colorsys
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = [("scripts", (".py", ".js")), ("templates", (".html", ".js", ".css")),
        ("reports/assets", (".js", ".css"))]
SKIP_DIRS = {"vendor", "__pycache__"}
SELF = "scripts/color_literal_check.py"  # this file names the patterns it looks for

# ---- Allowlist -------------------------------------------------------------------------------
# (path, pattern, reason). `pattern` is a regex searched in the 200 characters before each literal
# plus the literal itself; patterns ending in [^{}]* stay inside one CSS rule. "*" allows the whole file. Every entry must still match at least one literal
# (tests/test_color_literals.py), so a stale entry fails instead of silently widening the allowlist.
ALLOW = [
    # -- Token definitions: the one place good/bad colours are spelled out.
    ("templates/accessibility.js", "*", "token definitions + preset palettes (Standard/rg/by/none defaults)"),
    ("reports/assets/menu.js", "*", "generated from templates/menu.js + templates/accessibility.js + config"),
    ("scripts/accessibility_config.py", "*", "Python copy of the owner palette defaults (validates config)"),
    ("templates/access.html", r'type="color" id="(good|bad)" value="$',
     "custom-colour pickers start at the Standard token values"),

    # -- Brand colour (site accent, not a meaning). Red by brand, unchanged by colour mode.
    ("templates/weekly_report.html", r"--accent:$", "site brand accent (header rule, titles, links)"),
    ("reports/assets/app.js", r"var\(--accent,$", "brand accent fallback on the app setup button"),

    # -- Category colours (positions), not good/bad.
    ("reports/assets/scoreboard.css", r"\.s-(QB|RB|WR|TE|FLEX|K|DEF)\{[^{}]*$", "position category colours"),

    # -- Status badges: LIVE / FINAL / upcoming and the Games lead/underdog tag. To be redesigned
    #    separately (5.12.2 "leave alone"); don't restyle them here.
    ("reports/assets/scoreboard-overview.css", r"(\.wk-live|\.wk-live b:first-child|\.match-status\.is-live)\{[^{}]*$", "LIVE status (overview)"),
    ("reports/assets/scoreboard.css", r"\.(pill|lv)\{[^{}]*$", "LIVE / FINAL pill and per-player live tag"),
    ("reports/assets/snapshot.js", r"\.snap-lab\.live b\{[^{}]*$", "saved-image LIVE label"),
    ("scripts/bracket.py", r"\.bk-live\{[^{}]*$", "bracket LIVE badge"),

    # -- PNG renderers: Discord/post images have no viewer and stay hard-coded Standard.
    ("reports/assets/snapshot.js", r"getImageData\([^\n]*return `$", "canvas pixel read-back (copies whatever colour the page drew)"),
    ("scripts/poll_bot_cards.py", r'return f"$', "shade(): Standard green->red for the Discord PNG cards only (shoot())"),
]

HEX = re.compile(r"(?<![\w&])#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F\w])")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*[, ]\s*(\d{1,3})\s*[, ]\s*(\d{1,3})")
HSL = re.compile(r"hsla?\(\s*(-?\d+(?:\.\d+)?)(?:deg)?\s*[, ]\s*(\d+(?:\.\d+)?)%\s*[, ]\s*(\d+(?:\.\d+)?)%")
COMPUTED = re.compile(r"(?:hsla?|rgba?)\(\s*(?:\{|\$\{|\"\s*\+|'\s*\+)")  # hsl({hue}..), `hsl(${h}..)`, "hsl(" + h
NAMED = re.compile(r"(?:color|background(?:-color)?|border(?:-[a-z]+)*|fill|stroke|outline(?:-color)?|"
                   r"box-shadow|text-decoration-color|accent-color)\s*:\s*[^;{}\"']*?(?<![\w-])"
                   r"(red|green|darkred|darkgreen|lime|limegreen|forestgreen|seagreen|crimson|firebrick|maroon|"
                   r"tomato|indianred|orangered|lightgreen|palegreen|springgreen|olivedrab)(?![\w-])", re.I)
TOKEN_FALLBACK = re.compile(r"var\(\s*--(good|bad|neutral|up|dn)(-soft|-fill)?\s*,\s*$")
SAFE_FILL = re.compile(r"var\(\s*--on-fill\s*,\s*$")


def classify_rgb(r, g, b):
    """'red' / 'green' for a colour a reader would call red or green; None otherwise (greys, oranges,
    ambers, blues, very dark/light). Hue bands: red < 15 or >= 340, green 80..165."""
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    if s < 0.25 or l < 0.12 or l > 0.95:
        return None
    h *= 360
    if h < 15 or h >= 340:
        return "red"
    if 80 <= h <= 165:
        return "green"
    return None


def classify_hsl(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l / 100, s / 100)
    return classify_rgb(round(r * 255), round(g * 255), round(b * 255))


def files():
    for d, exts in SCAN:
        for dp, dn, fn in os.walk(os.path.join(ROOT, d)):
            dn[:] = [x for x in dn if x not in SKIP_DIRS]
            for f in sorted(fn):
                rel = os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")
                if f.endswith(exts) and rel != SELF:
                    yield os.path.relpath(os.path.join(dp, f), ROOT).replace(os.sep, "/")


def literals(text):
    """Yield (offset, literal, kind) for every red/green literal in text."""
    for m in HEX.finditer(text):
        x = m.group(1)
        x = "".join(c * 2 for c in x) if len(x) == 3 else x
        k = classify_rgb(int(x[:2], 16), int(x[2:4], 16), int(x[4:], 16))
        if k:
            yield m.start(), m.group(0), k
    for m in RGB.finditer(text):
        k = classify_rgb(*(min(255, int(v)) for v in m.groups()))
        if k:
            yield m.start(), m.group(0), k
    for m in HSL.finditer(text):
        k = classify_hsl(float(m.group(1)), float(m.group(2)), float(m.group(3)))
        if k:
            yield m.start(), m.group(0), k
    for m in COMPUTED.finditer(text):
        yield m.start(), m.group(0), "computed"
    for m in NAMED.finditer(text):
        yield m.start(1), m.group(1), "named"


def scan(root=ROOT):
    """[(path, line, literal, kind, allow_index or None)] for every literal found."""
    out = []
    for path in files():
        text = open(os.path.join(root, path), encoding="utf-8", errors="replace").read()
        for off, lit, kind in literals(text):
            before = text[max(0, off - 80):off]
            if TOKEN_FALLBACK.search(before) or (kind != "computed" and SAFE_FILL.search(before)):
                continue  # var(--good,#1a7f37): fallback of a token
            ctx = text[max(0, off - 200):off]
            hit = None
            for i, (p, pat, _) in enumerate(ALLOW):
                if p == path and (pat == "*" or re.search(pat, ctx)):
                    hit = i
                    break
            out.append((path, text.count("\n", 0, off) + 1, lit, kind, hit))
    return out


def offenders(results=None):
    return [r for r in (results if results is not None else scan()) if r[4] is None]


if __name__ == "__main__":
    res = scan()
    bad = offenders(res)
    for path, line, lit, kind, _ in bad:
        print(f"{path}:{line}: {lit} ({kind}) -- use var(--good)/var(--bad)/var(--neutral) or "
              f"NCAA180.colors.scale(); see docs/color-tokens.md")
    unused = [a for i, a in enumerate(ALLOW) if not any(r[4] == i for r in res)]
    for p, pat, why in unused:
        print(f"stale allowlist entry: {p} {pat!r} ({why})")
    print(f"{len(res) - len(bad)} allowlisted, {len(bad)} offending, {len(unused)} stale allowlist entries")
    sys.exit(1 if bad or unused else 0)
