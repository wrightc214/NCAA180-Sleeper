"""
bracket.py -- reusable single-elimination bracket component (Chris, 2026-11-20, task 5.13).

One data model, four renderings:
  model(...)          -> plain dict: rounds of games, each game two sides (or TBD), quads, champion
  desktop_html(B)     -> the whole bracket, one-sided, rounds left to right, absolutely positioned
  phone_html(B)       -> one round in focus + the next round peeking (laid out by assets/bracket.js)
  export_templates(B) -> <template>s the Save image menu draws with NCAASnap (assets/snapshot.js)

The Playoff uses it today (postseason_page.py). NIT / CCG brackets can feed it the same way: build a
model from ordered rounds and call the renderers (nothing here knows about the Playoff except the
optional quad / bowl / champion fields, which are simply left empty).

Look (Chris's approved mockup): every team row in its own colours (site_common.team_colors pair),
seed . logo . name (conference on a second line) . score; losers dimmed (opacity + grayscale from
config postseason.display.bracket) only once their game is final; connector lines in the colour of
the team that advanced; Elite 8 / Final Four bowls named and shown with their logo; champion card
after the final.
"""
import datetime as dt
import html
import json
import re
from zoneinfo import ZoneInfo

e = html.escape

# ---------------------------------------------------------------- geometry (desktop, from the mockup)
RW, RH, RG = 292, 42, 2            # row width / height / gap between a game's two rows
GH = 2 * RH + RG                   # game height (86)
PITCH = 104                        # first-round game pitch inside a quad
CGAP = 52                          # gap between round columns
CP = RW + CGAP                     # column pitch (344)
X0 = 48                            # left / right margin
QH, QGAP = 34, 40                  # quad header block, extra space between quads
TOP_ROUNDS = 168                   # round headers
TOP_GAMES = 249                    # first quad header (or first game when there are no quads)
BOWL_LOGO, NC_LOGO = 84, 110       # bowl logo heights above Elite 8 / Final Four / title game
CHAMP_W = 258
STUB = 26                          # connector stub length


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def fmt(p):
    return "" if p is None else f"{p:.2f}"


def gray_mix(hexc, g):
    """CSS grayscale(g) applied to a colour (same matrix the browser uses), as #rrggbb. html2canvas
    can't draw CSS filter, so exports use these precomputed colours for dimmed losers."""
    try:
        h = hexc.lstrip("#")
        r, gg, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except (AttributeError, ValueError):
        return hexc
    a = 1 - g
    m = [[0.2126 + 0.7874 * a, 0.7152 - 0.7152 * a, 0.0722 - 0.0722 * a],
         [0.2126 - 0.2126 * a, 0.7152 + 0.2848 * a, 0.0722 - 0.0722 * a],
         [0.2126 - 0.2126 * a, 0.7152 - 0.7152 * a, 0.0722 + 0.9278 * a]]
    out = [max(0, min(255, round(row[0] * r + row[1] * gg + row[2] * b))) for row in m]
    return "#" + "".join(f"{v:02x}" for v in out)


def now_et():
    t = dt.datetime.now(ZoneInfo("America/New_York"))
    return t.strftime("%a %b %-d, %-I:%M %p ET")


# ---------------------------------------------------------------- model
def order_rounds(games, seed_of):
    """Knockout games -> rounds in bracket order (lists; None = a game not drawn yet).
    games: dicts with 'round_key' (sortable), 'teams' (two team dicts with 'Team'). The order comes
    from the results themselves: a game's feeders are the earlier games its teams played; the half
    holding the best seed goes on top; a first round alone is ordered by standard bracket position.
    Returns [] when the games aren't a clean knockout (each round half the one before)."""
    keys = sorted({g["round_key"] for g in games})
    R = [[g for g in games if g["round_key"] == k] for k in keys]
    if not R or any(len(R[i + 1]) * 2 != len(R[i]) for i in range(len(R) - 1)):
        return []
    names = lambda g: {t["Team"] for t in g["teams"]}  # noqa: E731
    by_pos = _by_position(R, seed_of, names)
    if by_pos:
        return _pad(by_pos)
    if len(R) == 1 and all(seed_of(t) < 99 for g in R[0] for t in g["teams"]):
        pos = {s_: i for i, s_ in enumerate(bracket_order(2 * len(R[0])))}
        R[-1].sort(key=lambda g: min(pos.get(seed_of(t), 99) for t in g["teams"]))
    else:
        R[-1].sort(key=lambda g: min(seed_of(t) for t in g["teams"]))
    feed = {}
    for j in range(len(R) - 1, 0, -1):
        for g in R[j]:
            feed[id(g)] = [x for x in R[j - 1] if names(x) & names(g)]
    best = {}

    def low(g):
        if id(g) not in best:
            best[id(g)] = min([seed_of(t) for t in g["teams"]] + [low(f) for f in feed.get(id(g), [])])
        return best[id(g)]
    if len(R) > 1:
        R[-1].sort(key=low)
    for j in range(len(R) - 1, 0, -1):
        out, used = [], set()
        for g in R[j]:
            for f in sorted(feed[id(g)], key=low):
                if id(f) not in used:
                    used.add(id(f))
                    out.append(f)
        R[j - 1] = out + [x for x in R[j - 1] if id(x) not in used]
    return _pad(R)


def _pad(R):
    n = len(R[-1])
    while n > 1:  # rounds still to play
        n //= 2
        R.append([None] * n)
    return R


def _by_position(R, seed_of, names):
    """Standard bracket order (1 v 32 on top, then 16 v 17, 8 v 25 ...) when every first-round team
    is seeded 1..2n and later games pair adjacent feeders; else None (results-based order instead).
    Gives the right quad order from the moment the bracket is drawn."""
    n = len(R[0])
    seeds = [seed_of(t) for g in R[0] for t in g["teams"]]
    if sorted(seeds) != list(range(1, 2 * n + 1)) or n & (n - 1):
        return None
    pos = {s_: i for i, s_ in enumerate(bracket_order(2 * n))}
    out = [sorted(R[0], key=lambda g: min(pos[seed_of(t)] for t in g["teams"]))]
    for j in range(1, len(R)):
        prev, row = out[-1], []
        for i in range(len(prev) // 2):
            pair = names(prev[2 * i]) | names(prev[2 * i + 1])
            hit = [g for g in R[j] if names(g) <= pair]
            if len(hit) > 1:
                return None
            row.append(hit[0] if hit else None)
        if sum(g is not None for g in row) != len(R[j]):
            return None  # a game doesn't sit on two adjacent feeders: not a standard bracket
        out.append(row)
    return out


def bracket_order(n):
    order = [1, 2]
    while len(order) < n:
        size = len(order) * 2
        order = [x for s in order for x in (s, size + 1 - s)]
    return order


def model(R, *, year, title, eyebrow, round_names, weeks, side, href=None, bowls=None, quad_bowls=None,
          quad_round=None, e8_round=None, quad_label="{bowl} Quad", bowl_src=None, site="", champion_trophy="",
          champion_title="", foot="", slug_name="playoff", file_prefix="ncaa180"):
    """Bracket model from ordered rounds R (order_rounds output).
    side(team_dict) -> {'name','seed','conf','bg','fg','logo','logo_alt'?}: display fields for a team.
    href(game) -> Scoreboard link or None. bowls: {round index: [bowl per game]} for rounds not
    played yet (played games carry their own 'bowl'). quad_bowls: [bowl per quad] (quad = the
    teams feeding one game of round quad_round). weeks: [week per round]."""
    nR = len(R)

    def seed_key(t):
        try:
            return int(float(t.get("Seed")))
        except (TypeError, ValueError):
            return 99

    def winner_side(g):
        if g is None or not g.get("final"):
            return None
        w = [t for t in g["teams"] if t.get("Win")]
        return w[0] if len(w) == 1 else None

    rounds = []
    adv = None  # per game of the previous round: the team that advanced (None until it's final)
    for j in range(nR):
        games = []
        for i, g in enumerate(R[j]):
            if j == 0:
                slots = sorted(g["teams"], key=seed_key) if g else [None, None]
            elif g:
                # order a game's two teams by the feeder they came from (top feeder on top)
                by = {t["Team"]: t for t in g["teams"]}
                slots = [by.pop(a["Team"], None) if a else None for a in (adv[2 * i], adv[2 * i + 1])]
                rest = list(by.values())
                slots = [s if s is not None else (rest.pop(0) if rest else None) for s in slots]
            else:  # not drawn yet: a finished feeder's winner already holds its slot
                slots = [adv[2 * i], adv[2 * i + 1]]
            final = bool(g and g.get("final"))
            live = bool(g and not final and any(t.get("Points") for t in g["teams"]))
            known = all(s is not None for s in slots)
            state = "final" if final else "live" if live else ("upcoming" if known else "tbd")
            win = winner_side(g)
            sides = []
            for s in slots:
                if s is None:
                    sides.append(None)
                    continue
                d = dict(side(s))
                d["score"] = fmt(s.get("Points")) if (g and (final or live)) else ""
                d["win"] = bool(final and win is s)
                d["lose"] = bool(final and win is not None and win is not s)
                sides.append(d)
            planned = ((bowls or {}).get(j) or [])
            bowl = (g.get("bowl") if g else "") or (planned[i] if i < len(planned) else "")
            games.append({"r": j, "i": i, "state": state, "sides": sides,
                          "winner": next((k for k, s in enumerate(sides) if s and s["win"]), None),
                          "bowl": bowl or "", "bowl_logo": bowl_src(bowl) if (bowl and bowl_src) else "",
                          "href": (href(g) if (g and href) else None)})
        rounds.append({"name": round_names[j] if j < len(round_names) else f"Round {j + 1}",
                       "week": weeks[j] if j < len(weeks) else None, "games": games})
        adv = [winner_side(g) for g in R[j]]

    last = rounds[-1]["games"][0]
    if bowl_src and not last["bowl_logo"]:  # the title game shows the National Championship logo
        last["bowl_logo"] = bowl_src("National Championship")
    quads = []
    if quad_round is not None and quad_round < nR:
        nq = len(rounds[quad_round]["games"])
        for k in range(nq):
            b = rounds[quad_round]["games"][k]["bowl"] or ((quad_bowls or [""] * nq)[k] if quad_bowls else "")
            nm = quad_label.replace("{bowl}", re.sub(r"\s*Bowl$", "", b)) if b else ""
            quads.append({"k": k, "bowl": b, "name": nm, "logo": bowl_src(b) if (b and bowl_src) else ""})
    champ = None
    if last["state"] == "final" and last["winner"] is not None:
        w = last["sides"][last["winner"]]
        lo = last["sides"][1 - last["winner"]]
        # path: everyone the champion beat, round by round
        beat = []
        for rd in rounds:
            for gm in rd["games"]:
                names_ = [s["name"] if s else None for s in gm["sides"]]
                if w["name"] in names_ and gm["state"] == "final":
                    o = gm["sides"][1 - names_.index(w["name"])]
                    if o:
                        beat.append(o["name"])
        champ = {**w, "opp": lo["name"], "opp_score": lo["score"], "path": beat, "year": year,
                 "trophy": champion_trophy, "title": champion_title or f"{year} National Champion"}
    states = [gm["state"] for rd in rounds for gm in rd["games"]]
    if champ:
        status = "Final"
    elif "live" in states:
        status = f"Live · updated {now_et()}"
    else:
        status = f"Updated {now_et()}"
    return {"year": year, "title": title, "eyebrow": eyebrow, "site": site, "status": status, "rounds": rounds,
            "quads": quads, "quad_round": quad_round if quads else None, "e8_round": e8_round, "champion": champ, "foot": foot,
            "slug": slug_name, "prefix": file_prefix, "nc_logo": last["bowl_logo"]}


# ---------------------------------------------------------------- shared pieces
def row_html(s, dim=None, cls=""):
    """One team row (or a neutral TBD row). dim = (opacity, grayscale) for the export colours."""
    if s is None:
        return f'<div class="bk-row tbd {cls}"><span class="bk-sd"></span><span class="bk-nm"><b>TBD</b></span><span class="bk-pt"></span></div>'
    c = "bk-row" + (" win" if s["win"] else "") + (" lose" if s["lose"] else "") + (f" {cls}" if cls else "")
    x = f' data-xbg="{gray_mix(s["bg"], dim[1])}" data-xfg="{gray_mix(s["fg"], dim[1])}"' if (s["lose"] and dim) else ""
    return (f'<div class="{c}" style="background:{s["bg"]};color:{s["fg"]}"{x}>'
            f'<span class="bk-sd">{e(str(s.get("seed") or ""))}</span>{s["logo"]}'
            f'<span class="bk-nm"><b>{e(s["name"])}</b><small>{e(s.get("conf") or "")}</small></span>'
            f'<span class="bk-pt">{e(s["score"])}</span></div>')


def game_label(gm, B):
    nm = B["rounds"][gm["r"]]["name"]
    a, b = [(s["name"] if s else "TBD") for s in gm["sides"]]
    return f'{nm}{" · " + gm["bowl"] if gm["bowl"] else ""}: {a} vs {b} — open in Scoreboard'


def game_open(gm, B, cls, style=""):
    st = f' style="{style}"' if style else ""
    attrs = f'class="{cls} st-{gm["state"]}" data-r="{gm["r"]}" data-i="{gm["i"]}"{st}'
    if gm["href"]:
        return f'<a {attrs} href="{e(gm["href"])}" aria-label="{e(game_label(gm, B))}">', "</a>"
    return f"<div {attrs}>", "</div>"


def live_tag(gm):
    return '<span class="bk-live" aria-label="Live">LIVE</span>' if gm["state"] == "live" else ""


def champ_html(B, cls=""):
    c = B["champion"]
    if not c:
        return f'<div class="bk-champ empty {cls}"><span>Champion</span></div>'
    seed = f'{c["seed"]} seed · ' if c.get("seed") else ""
    path = f'{seed}beat {", ".join(c["path"])}' if c["path"] else ""
    # engraved trophy (task 5.1, scripts/trophies.py) when the ledger has it; else the plain art
    th = c.get("trophy_html_big" if "bk-big" in cls else "trophy_html")
    trophy = th or (f'<img class="bk-ct" src="{e(c["trophy"])}" alt="National Championship trophy">' if c["trophy"] else "")
    big = re.sub(r'class="[^"]*"', "", c["logo"], count=1).replace("<img", '<img class="bk-cl"', 1)
    return (f'<div class="bk-champ {cls}" style="background:{c["bg"]};color:{c["fg"]};--ring:{c["fg"]}">'
            f'{big}<div class="bk-ce">{e(c["title"])}</div><div class="bk-cn">{e(c["name"])}</div>'
            f'<div class="bk-cs">{e(c["score"])} – {e(c["opp_score"])} over {e(c["opp"])}</div>'
            f'<div class="bk-cp">{e(path)}</div>{trophy}</div>')


def head_html(B, title=None, status=None, logo=""):
    site = f'<div>National Championship · {e(B["site"])}</div>' if B["site"] else ""
    lg = f'<img class="bk-hl" src="{e(logo)}" alt="">' if logo else ""
    return (f'<div class="bk-head">{lg}<div class="bk-ht"><div class="bk-eb">{e(B["eyebrow"])}</div>'
            f'<div class="bk-h1">{e(title or B["title"])}</div></div>'
            f'<div class="bk-hs">{site}<div class="bk-st">{e(status or B["status"])}</div></div></div>')


def wk_span(rd):
    return f'<span>Week {rd["week"]}</span>' if rd["week"] else ""


def img(src, extra=""):
    return f'<img src="{e(src)}" alt=""{extra}>' if src else ""


def dim_vars(dim):
    return f"--bk-dim:{dim[0]};--bk-gray:{dim[1]}"


# ---------------------------------------------------------------- desktop
def _centres(B, quads_only=None):
    """{(r, i): centre y} for every game; quads_only = quad index to lay out alone (quad export)."""
    R = B["rounds"]
    nq = len(B["quads"]) if B["quad_round"] is not None else 0
    per = len(R[0]["games"]) // nq if nq else len(R[0]["games"])
    qh, qgap = (QH, QGAP) if nq else (0, 0)
    C = {}
    first = range(len(R[0]["games"])) if quads_only is None else range(quads_only * per, (quads_only + 1) * per)
    for n, i in enumerate(first):
        k, m = divmod(n, per)
        top = TOP_GAMES + k * (qh + per * PITCH - (PITCH - GH) + qgap) + qh + m * PITCH
        C[(0, i)] = top + GH / 2
    last_r = len(R) - 1 if quads_only is None else B["quad_round"]
    for j in range(1, last_r + 1):
        for i in range(len(R[j]["games"])):
            a, b = C.get((j - 1, 2 * i)), C.get((j - 1, 2 * i + 1))
            if a is not None and b is not None:
                C[(j, i)] = (a + b) / 2
    return C, per


def _line(x, y, w, h, color):
    return (f'<div class="bk-ln" style="left:{x:.1f}px;top:{y:.1f}px;width:{w:.1f}px;height:{h:.1f}px;'
            f'background:{color or "var(--line)"}"></div>')


def _row_centre(gm_c, slot):
    return gm_c - GH / 2 + slot * (RH + RG) + RH / 2


def desktop_board(B, dim, quad=None, export=False):
    """The whole bracket (quad=None) or one quad's First Round -> Elite 8 (quad export)."""
    R = B["rounds"]
    C, per = _centres(B, quad)
    last_r = len(R) - 1 if quad is None else B["quad_round"]
    out = []
    # round headers
    for j in range(last_r + 1):
        out.append(f'<div class="bk-rh" style="left:{X0 + j * CP}px;top:{TOP_ROUNDS}px"><b>{e(R[j]["name"])}</b>{wk_span(R[j])}</div>')
    # quad headers
    if B["quad_round"] is not None and quad is None:  # a quad image carries its name in the header
        qs = range(len(B["quads"]))
        span = (B["quad_round"] + 1) * CP - CGAP
        for k in qs:
            q = B["quads"][k]
            top = C[(0, k * per)] - GH / 2 - QH
            lg = f'<img src="{e(q["logo"])}" alt="">' if q["logo"] else ""
            out.append(f'<div class="bk-qh" style="left:{X0}px;top:{top:.0f}px;width:{span}px">{lg}<span>{e(q["name"])}</span></div>')
    # games, bowls, connectors
    for j in range(last_r + 1):
        x = X0 + j * CP
        for gm in R[j]["games"]:
            c = C.get((j, gm["i"]))
            if c is None:
                continue
            top = c - GH / 2
            big = j == len(R) - 1
            if gm["bowl_logo"] and (gm["bowl"] or big) and j > 0:
                h = NC_LOGO if big else BOWL_LOGO
                label = "National Championship" if big else gm["bowl"]
                out.append(f'<div class="bk-bowl{" nc" if big else ""}" style="left:{x}px;top:{top - h - 35:.0f}px">'
                           f'<img src="{e(gm["bowl_logo"])}" alt="" style="height:{h}px"><span>{e(label)}</span></div>')
            o, cl = game_open(gm, B, "bk-g", f"left:{x}px;top:{top:.0f}px")
            out.append(o + "".join(row_html(s, dim) for s in gm["sides"]) + live_tag(gm) + cl)
            # connector to the slot this game's winner fills in the next round
            if j < last_r and (j + 1, gm["i"] // 2) in C:
                nc = C[(j + 1, gm["i"] // 2)]
                ty = _row_centre(nc, gm["i"] % 2)
                w = gm["sides"][gm["winner"]] if gm["winner"] is not None else None
                col = w["bg"] if w else None
                xm = x + RW + STUB - 1.5
                y0, y1 = sorted((c, ty))
                out.append(_line(x + RW, c - 1.5, STUB, 3, col) + _line(xm, y0 - 1.5, 3, y1 - y0 + 3, col)
                           + _line(xm + 1.5, ty - 1.5, CGAP - STUB, 3, col))
    if quad is None:
        nx = X0 + len(R) * CP - CGAP + 28
        nc = C[(len(R) - 1, 0)]
        w = R[-1]["games"][0]
        if w["winner"] is not None:  # line from the title game into the champion card
            out.append(_line(X0 + (len(R) - 1) * CP + RW, nc - 1.5, 28, 3, w["sides"][w["winner"]]["bg"]))
        out.append(f'<div class="bk-cw" style="left:{nx}px;top:{nc:.0f}px;width:{CHAMP_W}px">{champ_html(B)}</div>')
        width = nx + CHAMP_W + X0 - 24
    else:
        width = X0 * 2 + (last_r + 1) * CP - CGAP
    bottom = max(C.values()) + GH / 2
    height = int(bottom + (90 if quad is None and not export else 40))
    foot = ""
    if quad is None and not export:
        foot = (f'<div class="bk-foot"><span>Winners in full team colours · eliminated teams dimmed'
                f'{" · tap a game for the Scoreboard" if any(g["href"] for rd in R for g in rd["games"]) else ""}</span>'
                f'<span>{e(B["foot"])}</span></div>')
    if quad is None:
        hd = head_html(B)
    else:  # a quad image: its own name + bowl logo, and the state of the games in it
        q = B["quads"][quad]
        hd = head_html(B, title=q["name"], logo=q["logo"], status=_status_for(B, [R[j]["games"][i] for j, i in C]))
    return (f'<div class="bk-board" style="width:{width}px;height:{height}px;{dim_vars(dim)}">{hd}{"".join(out)}{foot}</div>',
            width, height)


def _status_for(B, games):
    """Header state for an image that shows only these games."""
    if games is None:
        return None
    st = [g["state"] for g in games]
    if "live" in st:
        return f"Live · updated {now_et()}"
    if st and all(s == "final" for s in st):
        return "Final"
    return f"Updated {now_et()}"


def desktop_html(B, dim):
    board, w, h = desktop_board(B, dim)
    return f'<div class="bk-desk"><div class="bk-scroll" tabindex="0" aria-label="Bracket (scrolls sideways)">{board}</div></div>'


# ---------------------------------------------------------------- phone (positions set by assets/bracket.js)
def card_html(gm, B, dim, big_bowl=False):
    o, cl = game_open(gm, B, "bk-card")
    rd = B["rounds"][gm["r"]]
    last = gm["r"] == len(B["rounds"]) - 1
    st = {"final": "Final", "live": "", "upcoming": "Upcoming", "tbd": ""}[gm["state"]]
    label = "National Championship" if last else gm["bowl"]
    logo = gm["bowl_logo"] if (gm["bowl"] or last) else ""
    if big_bowl and logo:
        top = f'<div class="bk-cbowl"><img src="{e(logo)}" alt=""><span>{e(label)}</span></div>'
        foot_b = ""
    else:
        top = ""
        foot_b = f'<span class="bk-fb">{img(logo)}{e(label)}</span>' if label else ""
    foot = f'<div class="bk-cf"><span class="bk-fs">{live_tag(gm)}{e(st)}</span>{foot_b}</div>'
    return o + top + "".join(row_html(s, dim) for s in gm["sides"]) + foot + cl


def phone_html(B, dim):
    R = B["rounds"]
    tabs = "".join(f'<button type="button" class="bk-tab" data-r="{j}"><b>{e(rd["name"])}</b>{wk_span(rd)}</button>'
                   for j, rd in enumerate(R))
    cols = []
    for j, rd in enumerate(R):
        inner = "".join(card_html(gm, B, dim) for gm in rd["games"])
        if j == len(R) - 1:
            inner = champ_html(B, "bk-pchamp") + inner
        cols.append(f'<div class="bk-col" data-r="{j}">{inner}</div>')
    qh = "".join(f'<div class="bk-pq" data-q="{q["k"]}">{img(q["logo"])}<span>{e(q["name"])}</span></div>' for q in B["quads"])
    return (f'<div class="bk-phone" data-quad-round="{B["quad_round"] if B["quad_round"] is not None else -1}" '
            f'data-quads="{len(B["quads"])}" style="{dim_vars(dim)}">'
            f'<div class="bk-phead"><div class="bk-eb">{e(B["eyebrow"])}</div><div class="bk-h1">{e(B["title"])}</div>'
            f'<div class="bk-st">{e(B["status"])}</div></div>'
            f'<div class="bk-tabs"><div class="bk-tabtrack">{tabs}</div></div>'
            f'<div class="bk-view" tabindex="0" aria-label="Bracket: swipe or use the left and right arrow keys to change round">'
            f'<div class="bk-track">{qh}{"".join(cols)}</div></div></div>')


# ---------------------------------------------------------------- exports (Save image)
def _tpl(key, label, fname, width, html_, live, group="", disabled_note="", scale=2):
    return (f'<template class="bk-x" data-key="{e(key)}" data-label="{e(label)}" data-file="{e(fname)}" data-w="{width}" '
            f'data-live="{1 if live else 0}" data-group="{e(group)}" data-note="{e(disabled_note)}" data-scale="{scale}">'
            f'{html_}</template>')


def round_export(B, j, dim):
    R = B["rounds"]
    rd = R[j]
    last = j == len(R) - 1
    title = f'{B["year"]} {B["slug"].title()} · {rd["name"]}' + (f' · Week {rd["week"]}' if rd["week"] else "")
    parts = []
    qr = B["quad_round"]
    per = (len(rd["games"]) // len(B["quads"])) if (qr is not None and j <= qr) else 0
    if last:
        parts.append(champ_html(B, "bk-xchamp"))
    for gm in rd["games"]:
        if per and gm["i"] % per == 0:
            q = B["quads"][gm["i"] // per]
            parts.append(f'<div class="bk-xq">{img(q["logo"])}<span>{e(q["name"])}</span></div>')
        parts.append(card_html(gm, B, dim, big_bowl=bool(gm["bowl"]) or last))
    st = _status_for(B, rd["games"])
    body = (f'<div class="bk-x1" style="{dim_vars(dim)}"><div class="bk-xh"><div class="bk-eb">{e(B["eyebrow"])}</div>'
            f'<div class="bk-h1">{e(title)}</div><div class="bk-st">{e(st)}</div></div>{"".join(parts)}</div>')
    return _tpl(f"round-{j}", "This round", f'{B["prefix"]}-{B["year"]}-{B["slug"]}-{slug(rd["name"])}', 400, body,
                any(g["state"] == "live" for g in rd["games"]), group="round")


def quad_export(B, k, dim):
    board, w, h = desktop_board(B, dim, quad=k, export=True)
    q = B["quads"][k]
    C, per = _centres(B, k)
    games = [B["rounds"][j]["games"][i] for (j, i) in C]
    short = slug(re.sub(r"(?i)\s*bowl$", "", q["bowl"]))
    return _tpl(f"quad-{k}", q["name"], f'{B["prefix"]}-{B["year"]}-{B["slug"]}-{short}-quad',
                w, board, any(g["state"] == "live" for g in games), group="quad")


def elite_export(B, dim):
    """Elite 8 -> Final Four -> Championship -> champion (Chris's old Excel layout): each game a tall
    block, team A on top, the bowl logo large in the middle, team B at the bottom; each next-round
    block's rows sit at the midpoints of its two feeder blocks."""
    R = B["rounds"]
    E = R[B["e8_round"]:]
    BW, BH, BP, LGAP = 300, 240, 280, 96   # block width / first-column block height / pitch / column gap
    top0 = 230
    X = lambda c: X0 + c * (BW + LGAP)  # noqa: E731
    out = []
    rows = {}  # (c, i) -> (top row centre, bottom row centre)
    for c, rd in enumerate(E):
        out.append(f'<div class="bk-rh" style="left:{X(c)}px;top:{TOP_ROUNDS}px;width:{BW}px"><b>{e(rd["name"])}</b>{wk_span(rd)}</div>')
        for gm in rd["games"]:
            i = gm["i"]
            if c == 0:
                t = top0 + i * BP
                a, b = t + RH / 2 + 1, t + BH - RH / 2 + 1
            else:
                pa, pb = rows[(c - 1, 2 * i)], rows[(c - 1, 2 * i + 1)]
                a, b = (pa[0] + pa[1]) / 2, (pb[0] + pb[1]) / 2
            rows[(c, i)] = (a, b)
            last = c == len(E) - 1
            o, cl = game_open(gm, B, "bk-xb", f"left:{X(c)}px;top:{a - RH / 2:.0f}px;width:{BW}px;height:{b - a + RH:.0f}px")
            s0, s1 = gm["sides"]
            logo = gm["bowl_logo"]
            label = "National Championship" if last else gm["bowl"]
            mid = (f'<div class="bk-xbl"><img src="{e(logo)}" alt="" style="max-height:{min(130, b - a - RH - 40):.0f}px">'
                   f'<span>{e(label)}</span></div>') if logo or label else '<div class="bk-xbl"></div>'
            out.append(o + row_html(s0, dim) + mid + row_html(s1, dim) + live_tag(gm) + cl)
            w = gm["sides"][gm["winner"]] if gm["winner"] is not None else None
            col = w["bg"] if w else None
            xr = X(c) + BW
            out.append(_line(xr, a - 1.5, 22, 3, col) + _line(xr, b - 1.5, 22, 3, col) + _line(xr + 20.5, a - 1.5, 3, b - a + 3, col))
            out.append(_line(xr + 22, (a + b) / 2 - 1.5, LGAP - 22 if not last else 40, 3, col))
    nc = rows[(len(E) - 1, 0)]
    cx = X(len(E)) - LGAP + 40
    out.append(f'<div class="bk-cw" style="left:{cx}px;top:{(nc[0] + nc[1]) / 2:.0f}px;width:{CHAMP_W + 30}px">{champ_html(B)}</div>')
    width = cx + CHAMP_W + 30 + X0
    height = int(top0 + len(E[0]["games"]) * BP + 20)
    games = [g for rd in E for g in rd["games"]]
    body = (f'<div class="bk-board bk-e8" style="width:{width}px;height:{height}px;{dim_vars(dim)}">'
            f'{head_html(B, title="Elite 8 & Beyond", status=_status_for(B, games))}{"".join(out)}</div>')
    ready = all(s is not None for g in E[0]["games"] for s in g["sides"])
    return _tpl("e8", "Elite 8 & beyond", f'{B["prefix"]}-{B["year"]}-{B["slug"]}-elite-8-and-beyond', width, body,
                any(g["state"] == "live" for g in games), group="e8",
                disabled_note="" if ready else "Available once the Elite 8 is set")


def champion_export(B):
    c = B["champion"]
    body = (f'<div class="bk-xc"><div class="bk-xch"><div class="bk-eb">{e(B["eyebrow"])}</div>'
            f'<div class="bk-h1">{e(c["title"])}</div></div>{champ_html(B, "bk-big")}</div>')
    return _tpl("champ", "Champion", f'{B["prefix"]}-{B["year"]}-national-champion', 540, body, False, group="champ")


def export_templates(B, dim):
    R = B["rounds"]
    t = [round_export(B, j, dim) for j in range(len(R))]
    if B["quad_round"] is not None:
        t += [quad_export(B, k, dim) for k in range(len(B["quads"]))]
    if B["e8_round"] is not None and B["e8_round"] < len(R) - 1:
        t.append(elite_export(B, dim))
    if B["champion"]:
        t.append(champion_export(B))
    full_live = any(g["state"] == "live" for rd in R for g in rd["games"])
    meta = {"full": f'{B["prefix"]}-{B["year"]}-{B["slug"]}-bracket', "live": full_live}
    return f'<div class="bk-xs" hidden data-meta="{e(json.dumps(meta))}">{"".join(t)}</div>'


def html_(B, dim):
    """Desktop + phone + export templates, for a page section."""
    foot = f'{B["eyebrow"]} · {B["foot"]}' if B["foot"] else B["eyebrow"]
    return (f'<div class="bk" data-year="{B["year"]}" data-slug="{e(B["slug"])}" data-foot="{e(foot)}">{desktop_html(B, dim)}{phone_html(B, dim)}'
            f'{export_templates(B, dim)}</div><script src="assets/bracket.js"></script>')


# ---------------------------------------------------------------- styles
CSS = """
.bk{--bk-ink:var(--ink);position:relative}
.bk .bk-eb{font:600 13px var(--num);letter-spacing:.16em;text-transform:uppercase;color:var(--mute)}
.bk .bk-h1{font:900 44px/1 var(--disp);text-transform:uppercase;letter-spacing:.01em;color:var(--ink)}
.bk .bk-st{color:var(--mute);font-size:13px}
.bk-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;margin:0 -16px;padding:0 0 6px;overscroll-behavior-x:contain}
.bk-scroll:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.bk-board{position:relative;box-sizing:border-box;color:var(--ink)}
.bk-head{position:absolute;left:48px;right:48px;top:40px;display:flex;align-items:flex-end;justify-content:space-between;gap:16px;border-bottom:1px solid var(--line);padding-bottom:18px}
.bk-head .bk-ht{display:flex;flex-direction:column;gap:6px;flex:1}
.bk-hl{height:72px;max-width:180px;object-fit:contain;flex:none}
.bk-hs{text-align:right;font-size:13px;line-height:1.6;color:var(--ink)}
.bk-rh{position:absolute;width:292px;text-align:center;display:flex;flex-direction:column}
.bk-rh b{font:700 19px var(--disp);letter-spacing:.06em;text-transform:uppercase}
.bk-rh span{font-size:12px;color:var(--mute)}
.bk-qh{position:absolute;height:26px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--line)}
.bk-qh img{height:22px;max-width:60px;object-fit:contain}
.bk-qh span,.bk-pq span,.bk-xq span{font:700 17px var(--disp);letter-spacing:.1em;text-transform:uppercase;color:var(--ink)}
.bk-g{position:absolute;width:292px;display:flex;flex-direction:column;gap:2px;text-decoration:none;color:inherit;border-radius:7px}
a.bk-g:hover,a.bk-card:hover,a.bk-xb:hover{outline:2px solid var(--ink);outline-offset:2px}
a.bk-g:focus-visible,a.bk-card:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.bk-row{display:flex;align-items:center;gap:8px;min-height:42px;box-sizing:border-box;padding:3px 10px 3px 8px;border-radius:6px}
.bk-row.lose{opacity:var(--bk-dim,.35);filter:grayscale(var(--bk-gray,.6))}
.bk-row.tbd{background:transparent;border:1px dashed var(--line);color:var(--mute)}
.bk-row.tbd b{font-weight:600}
.bk-sd{width:18px;flex:none;text-align:right;font:600 13px var(--num)}
.bk-row img{width:26px;height:26px;object-fit:contain;flex:none}
.bk-nm{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}
.bk-nm b{font:600 14px/1.15 var(--body);white-space:nowrap}
.bk-row.win .bk-nm b{font-weight:700}
.bk-nm small{font:600 9.5px/1.1 var(--body);letter-spacing:.06em;text-transform:uppercase;color:inherit;white-space:nowrap}
.bk-pt{flex:none;min-width:46px;text-align:right;font:600 16px var(--num);font-variant-numeric:tabular-nums}
.bk-live{display:inline-block;font:700 10px/1 var(--num);letter-spacing:.08em;color:#fff;background:#b42318;border-radius:3px;padding:3px 5px 2px}
.bk-live::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:#fff;margin:0 4px 1px 0;vertical-align:middle}
.bk-g>.bk-live{position:absolute;right:-6px;top:-9px}
.bk-bowl{position:absolute;width:292px;display:flex;flex-direction:column;align-items:center;gap:4px}
.bk-bowl img{max-width:292px;object-fit:contain}
.bk-bowl span,.bk-xbl span,.bk-cbowl span{font:700 13px var(--num);letter-spacing:.1em;text-transform:uppercase;color:var(--mute)}
.bk-ln{position:absolute;border-radius:2px}
.bk-cw{position:absolute;transform:translateY(-50%)}
.bk-champ{box-sizing:border-box;padding:22px 18px 20px;border-radius:14px;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;box-shadow:0 0 0 3px color-mix(in srgb,var(--ring) 22%,transparent),0 18px 40px rgba(0,0,0,.25)}
.bk-champ.empty{min-height:180px;justify-content:center;border:2px dashed var(--line);box-shadow:none;color:var(--mute);font:700 18px var(--disp);letter-spacing:.1em;text-transform:uppercase}
.bk-cl{width:120px;height:120px;object-fit:contain}
.bk-ce{font:600 13px var(--num);letter-spacing:.14em;text-transform:uppercase}
.bk-cn{font:900 34px/1.02 var(--disp);text-transform:uppercase}
.bk-cs{font:600 18px var(--num)}
.bk-cp{font-size:12px;line-height:1.45}
.bk-ct{height:110px;object-fit:contain}
.bk-foot{position:absolute;left:48px;right:48px;bottom:24px;display:flex;justify-content:space-between;color:var(--mute);font-size:12px}
/* phone: ESPN bracket-app model (positions from assets/bracket.js) */
.bk-phone{display:none;margin:0 -16px}
.bk-phead{padding:0 16px 8px}.bk-phead .bk-h1{font-size:30px}
.bk-tabs{overflow-x:auto;scrollbar-width:none;border-bottom:1px solid var(--line);position:relative;overscroll-behavior-x:contain}
.bk-tabs::-webkit-scrollbar{display:none}
.bk-tabtrack{display:flex;width:max-content}
.bk-tab{flex:none;min-width:120px;padding:9px 12px 7px;border:0;border-bottom:3px solid transparent;background:transparent;color:var(--mute);cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:1px;font:inherit}
.bk-tab b{font:700 15px var(--disp);letter-spacing:.05em;text-transform:uppercase;white-space:nowrap}
.bk-tab span{font-size:11px}
.bk-tab[aria-current="true"]{color:var(--ink);border-bottom-color:var(--accent)}
.bk-tab:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.bk-view{position:relative;overflow:hidden;touch-action:pan-y;user-select:none;-webkit-user-select:none;transition:height .35s ease}
.bk-view:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.bk-track{position:relative;transition:transform .35s ease}
.bk-col{position:absolute;top:0;transition:opacity .35s ease}
.bk-col>*{position:absolute;left:0;transition:top .35s ease}
.bk-card,.bk-x1 .bk-card{display:flex;flex-direction:column;gap:4px;padding:8px;box-sizing:border-box;border-radius:10px;background:var(--bg);border:1px solid var(--line);text-decoration:none;color:inherit}
.bk-phone .bk-nm b,.bk-x1 .bk-nm b{white-space:normal}
.bk-phone .bk-card{padding:6px}.bk-phone .bk-row{gap:5px;padding:3px 8px 3px 6px}
.bk-phone .bk-nm b{overflow-wrap:anywhere}
@media (max-width:359px){.bk-phone .bk-sd{width:16px}.bk-phone .bk-row img{width:22px;height:22px}.bk-phone .bk-pt{min-width:40px;font-size:15px}}
.bk-cf{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:22px;padding:0 4px;font-size:11px;color:var(--mute)}
.bk-fs{font-weight:600}
.bk-fb{display:flex;align-items:center;gap:6px;text-align:right}
.bk-fb img{height:18px;max-width:40px;object-fit:contain}
.bk-pq{position:absolute;display:flex;align-items:center;gap:8px;height:24px;transition:top .35s ease,opacity .35s ease}
.bk-pq img{height:20px;max-width:50px;object-fit:contain}
.bk-pchamp{width:100%}
@media (max-width:719px){.bk-desk{display:none}.bk-phone{display:block}}
@media (prefers-reduced-motion:reduce){.bk-view,.bk-track,.bk-col,.bk-col>*,.bk-pq{transition:none!important}}
/* exports */
.bk-x1{display:flex;flex-direction:column;gap:12px;width:376px}
.bk-xh .bk-h1{font-size:22px;line-height:1.1}.bk-xch .bk-h1{font-size:28px}
.bk-xq{display:flex;align-items:center;gap:8px;border-bottom:1px solid var(--line);padding:6px 0 4px;margin-top:4px}
.bk-xq img{height:24px;max-width:60px;object-fit:contain}
.bk-cbowl{display:flex;flex-direction:column;align-items:center;gap:4px;padding:6px 0 8px}
.bk-cbowl img{height:84px;max-width:280px;object-fit:contain}
.bk-xb{position:absolute;display:flex;flex-direction:column;text-decoration:none;color:inherit}
.bk-xb>.bk-live{position:absolute;right:-6px;top:-9px}
.bk-xbl{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;min-height:0}
.bk-xbl img{max-width:260px;object-fit:contain}
.bk-xc{width:500px;display:flex;flex-direction:column;gap:14px}
.bk-champ.bk-big .bk-cl{width:220px;height:220px}
.bk-champ.bk-big .bk-cn{font-size:52px}
.bk-champ.bk-big .bk-ct{height:200px}
.bk-champ.bk-big{padding:32px 24px 28px;gap:14px}
.bk-champ.bk-big .bk-cs{font-size:24px}.bk-champ.bk-big .bk-cp{font-size:15px}.bk-champ.bk-big .bk-ce{font-size:16px}
/* save-image menu */
.bk-menu{position:absolute;right:12px;top:44px;z-index:30;width:min(320px,calc(100vw - 32px));background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 32px rgba(0,0,0,.25);padding:12px}
.bk-menu fieldset{border:0;margin:0 0 8px;padding:0}
.bk-menu legend{font:600 11px var(--num);letter-spacing:.12em;text-transform:uppercase;color:var(--mute);margin-bottom:4px}
.bk-menu label{display:flex;align-items:center;gap:8px;padding:5px 2px;font-size:14px;cursor:pointer}
.bk-menu label.off{color:var(--mute);cursor:not-allowed}
.bk-menu label small{display:block;font-size:11px}
.bk-menu .bk-sz{margin:2px 0 4px 26px}
.bk-menu svg{flex:none}
.bk-menu .bk-do{display:flex;gap:8px;justify-content:flex-end;margin-top:6px}
.bk-menu button{font:600 14px var(--body);border-radius:6px;padding:7px 14px;cursor:pointer;border:1px solid var(--line);background:var(--bg);color:var(--ink)}
.bk-menu button.go{background:var(--accent);border-color:var(--accent);color:#fff}
.bk-menu .bk-err{color:var(--bad);font-size:12px;margin:6px 0 0}
"""
