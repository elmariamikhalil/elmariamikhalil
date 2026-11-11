#!/usr/bin/env python3
"""Generate retro arcade-style SVG cards for a GitHub profile README.

Run by .github/workflows/profile-summary-cards.yml. Needs GH_TOKEN in the
environment (a personal access token). Writes SVG files into ./assets.

    python scripts/retro_cards.py            # real data
    python scripts/retro_cards.py --mock     # sample data, for previewing
"""
import base64, datetime as dt, io, json, os, sys, urllib.request
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

USERNAME = os.environ.get("USERNAME", "elmariamikhalil")
DISPLAY_NAME = os.environ.get("DISPLAY_NAME", "Khalil Elmariami")
TAGLINE = os.environ.get("TAGLINE", "Full stack web developer")
TIME_ZONE = os.environ.get("TIME_ZONE", "Africa/Casablanca")
EXCLUDE_REPOS = {r.strip().lower() for r in os.environ.get("EXCLUDE_REPOS", "").split(",") if r.strip()}
EXCLUDE_LANGS = {l.strip().lower() for l in os.environ.get("EXCLUDE_LANGS", "").split(",") if l.strip()}
OUT = os.environ.get("OUT_DIR", "assets")

# Palette taken from the profile picture: CRT bezels, night-blue room,
# arcade orange/yellow lettering, red hearts and terminal green.
BEZEL, BEZEL_HI, BEZEL_SHADE = "#D8CFB2", "#EFE8D2", "#9F9678"
SCREEN, SCREEN_EDGE = "#151B48", "#0A0E2A"
INK, INK_DIM = "#F2E9CF", "#7D88D6"
GREEN, GREEN_DIM = "#3DFF7A", "#1E7A45"
YELLOW, ORANGE, RED = "#FFE14D", "#FF8A1F", "#E8363C"
EMPTY = "#252C66"

FONT_URLS = {
    "Press Start 2P": "https://raw.githubusercontent.com/google/fonts/main/ofl/pressstart2p/PressStart2P-Regular.ttf",
    "VT323": "https://raw.githubusercontent.com/google/fonts/main/ofl/vt323/VT323-Regular.ttf",
}
PIXEL, TERM = "'Press Start 2P', 'Courier New', monospace", "'VT323', 'Courier New', monospace"


# ---------------------------------------------------------------- helpers
def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "retro-cards", **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def font_css():
    """Download both fonts, subset them to the characters we use, inline as base64."""
    css = []
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
    except ImportError:
        return ""
    chars = "".join(chr(c) for c in range(32, 127)) + "×–—’…"
    for family, url in FONT_URLS.items():
        try:
            font = TTFont(io.BytesIO(http(url)))
            opts = subset.Options(); opts.flavor = "woff"; opts.drop_tables += ["DSIG"]
            sub = subset.Subsetter(opts); sub.populate(text=chars); sub.subset(font)
            buf = io.BytesIO(); font.flavor = "woff"; font.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            css.append(f"@font-face{{font-family:'{family}';src:url(data:font/woff;base64,{b64}) format('woff');}}")
        except Exception as e:  # fall back to the monospace stack
            print(f"warning: could not load {family}: {e}", file=sys.stderr)
    return "".join(css)


def stepped(x, y, w, h, s):
    """Rectangle with pixel-stepped corners (two steps of size s)."""
    p = [(x + 2*s, y), (x + w - 2*s, y), (x + w - 2*s, y + s), (x + w - s, y + s), (x + w - s, y + 2*s),
         (x + w, y + 2*s), (x + w, y + h - 2*s), (x + w - s, y + h - 2*s), (x + w - s, y + h - s),
         (x + w - 2*s, y + h - s), (x + w - 2*s, y + h), (x + 2*s, y + h), (x + 2*s, y + h - s),
         (x + s, y + h - s), (x + s, y + h - 2*s), (x, y + h - 2*s), (x, y + 2*s), (x + s, y + 2*s),
         (x + s, y + s), (x + 2*s, y + s)]
    return "M" + " L".join(f"{a},{b}" for a, b in p) + " Z"


def sprite(rows, x, y, px, colors):
    out = []
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in colors:
                out.append(f'<rect x="{x+i*px}" y="{y+j*px}" width="{px}" height="{px}" fill="{colors[ch]}"/>')
    return "".join(out)


HEART = [".XX.XX.", "XWXXXXX", "XXXXXXX", ".XXXXX.", "..XXX..", "...X..."]
FLAME = ["..O...", "..OO..", ".OOO.O", ".OOOOO", "OOYYOO", "OYYYYO", "OYYYYO", ".OYYO."]
FLAME2 = ["...O..", "..OO..", "O.OOO.", "OOOOO.", "OOYYOO", "OYYYYO", "OYYYYO", ".OYYO."]


def t(x, y, text, size, color, font=TERM, anchor="start", extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}" '
            f'text-anchor="{anchor}" {extra}>{escape(str(text))}</text>')


def shadow_t(x, y, text, size, color, shade, off=3, font=PIXEL, anchor="start"):
    return t(x + off, y + off, text, size, shade, font, anchor) + t(x, y, text, size, color, font, anchor)


def crt(w, h, body, fonts, title=None, led=GREEN, style=""):
    """Wrap card content in a beige CRT monitor bezel with a scanlined screen."""
    b, sx, sy, sw, sh = 12, 12, 12, w - 24, h - 24
    title_svg = f"<title>{escape(title)}</title>" if title else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">{title_svg}
<style>{fonts}{style}text{{-webkit-font-smoothing:none;}}</style>
<defs>
<pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".28"/></pattern>
<radialGradient id="glow" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="{SCREEN}"/><stop offset="1" stop-color="{SCREEN_EDGE}"/></radialGradient>
<clipPath id="scr"><path d="{stepped(sx, sy, sw, sh, 4)}"/></clipPath>
</defs>
<path d="{stepped(0, 0, w, h, 4)}" fill="{BEZEL_SHADE}"/>
<path d="{stepped(0, 0, w, h - 4, 4)}" fill="{BEZEL}"/>
<path d="{stepped(4, 4, w - 8, h - 14, 4)}" fill="none" stroke="{BEZEL_HI}" stroke-width="2" opacity=".7"/>
<rect x="{w - 30}" y="{h - 9}" width="8" height="4" fill="{led}"/>
<path d="{stepped(sx - 2, sy - 2, sw + 4, sh + 4, 4)}" fill="{BEZEL_SHADE}"/>
<g clip-path="url(#scr)">
<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#glow)"/>
{body}
<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#scan)"/>
</g>
</svg>'''


# ---------------------------------------------------------------- data
def gql(token, query):
    data = json.dumps({"query": query}).encode()
    res = json.loads(http("https://api.github.com/graphql", data, {"Authorization": f"bearer {token}"}))
    if "errors" in res:
        raise SystemExit(f"GraphQL error: {res['errors']}")
    return res["data"]


def fetch(token):
    cal = "contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }"
    base = gql(token, f'''{{ user(login: "{USERNAME}") {{
        name createdAt avatarUrl(size: 200)
        contributionsCollection {{ contributionYears {cal} }}
    }} }}''')["user"]

    years = base["contributionsCollection"]["contributionYears"]
    aliases = " ".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
        f'{{ totalCommitContributions restrictedContributionsCount totalPullRequestContributions '
        f'totalIssueContributions {cal} }}' for y in years)
    per_year = gql(token, f'{{ user(login: "{USERNAME}") {{ {aliases} }} }}')["user"]

    repos, cursor = [], None
    while True:
        after = f', after: "{cursor}"' if cursor else ""
        page = gql(token, f'''{{ user(login: "{USERNAME}") {{
            repositories(first: 100, ownerAffiliations: OWNER, isFork: false{after}) {{
              totalCount pageInfo {{ hasNextPage endCursor }}
              nodes {{ name stargazerCount
                languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{ edges {{ size node {{ name color }} }} }} }}
            }} }} }}''')["user"]["repositories"]
        repos += page["nodes"]; total_repos = page["totalCount"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    days = {}
    totals = dict(score=0, commits=0, prs=0, issues=0)
    for y in per_year.values():
        totals["score"] += y["contributionCalendar"]["totalContributions"]
        totals["commits"] += y["totalCommitContributions"] + y["restrictedContributionsCount"]
        totals["prs"] += y["totalPullRequestContributions"]
        totals["issues"] += y["totalIssueContributions"]
        for w in y["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]

    langs = {}
    for r in repos:
        if r["name"].lower() in EXCLUDE_REPOS:
            continue
        for e in r["languages"]["edges"]:
            n = e["node"]["name"]
            if n.lower() in EXCLUDE_LANGS:
                continue
            size, color = langs.get(n, (0, e["node"]["color"]))
            langs[n] = (size + e["size"], color or INK_DIM)

    last_year = [[d["contributionCount"] for d in w["contributionDays"]]
                 for w in base["contributionsCollection"]["contributionCalendar"]["weeks"]]
    first_day = base["contributionsCollection"]["contributionCalendar"]["weeks"][0]["contributionDays"][0]["date"]

    return dict(
        name=base["name"] or DISPLAY_NAME, created=base["createdAt"][:10],
        avatar=http(base["avatarUrl"]), stars=sum(r["stargazerCount"] for r in repos),
        repos=total_repos, days=days, langs=langs, last_year=last_year, first_day=first_day,
        last_year_total=base["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        **totals)


def mock():
    import random
    random.seed(7)
    today = dt.date.today()
    days = {}
    for i in range(2200):
        d = today - dt.timedelta(days=i)
        days[d.isoformat()] = 0 if i > 16 and random.random() < .45 else random.choice([1, 2, 3, 5, 8, 12])
    start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    weeks, d = [], start
    while d <= today:
        weeks.append([days.get((d + dt.timedelta(k)).isoformat(), 0) for k in range(7) if d + dt.timedelta(k) <= today])
        d += dt.timedelta(7)
    avatar = open(os.environ["MOCK_AVATAR"], "rb").read() if os.environ.get("MOCK_AVATAR") else b""
    return dict(name=DISPLAY_NAME, created="2019-11-25", avatar=avatar, stars=4, repos=22, days=days,
                langs={"JavaScript": (900, "#f1e05a"), "TypeScript": (420, "#3178c6"), "CSS": (160, "#663399"),
                       "HTML": (90, "#e34c26"), "Liquid": (60, "#67b8de"), "Python": (20, "#3572A5")},
                last_year=weeks, first_day=start.isoformat(), last_year_total=sum(map(sum, weeks)),
                score=5217, commits=3480, prs=41, issues=12)


def streaks(days, today):
    dates = sorted(dt.date.fromisoformat(k) for k, v in days.items() if v > 0)
    longest, best_range, run, run_start, prev = 0, None, 0, None, None
    for d in dates:
        run = run + 1 if prev and (d - prev).days == 1 else 1
        run_start = d if run == 1 else run_start
        if run > longest:
            longest, best_range = run, (run_start, d)
        prev = d
    current, cur_start = 0, None
    d = today if days.get(today.isoformat(), 0) > 0 else today - dt.timedelta(1)
    while days.get(d.isoformat(), 0) > 0:
        current, cur_start = current + 1, d
        d -= dt.timedelta(1)
    return current, cur_start, longest, best_range


def fmt_range(a, b):
    if not a:
        return "Start a new combo today"
    f = lambda d, y: d.strftime("%b %-d" + (" %Y" if y else ""))
    same_year = a.year == b.year == dt.date.today().year
    return f"{f(a, not same_year)} – {f(b, not same_year)}"


# ---------------------------------------------------------------- cards
def player_card(d, fonts, today):
    w, h = 840, 300
    img = ""
    if d["avatar"]:
        mime = "image/png" if d["avatar"][:4] == b"\x89PNG" else "image/jpeg"
        b64 = base64.b64encode(d["avatar"]).decode()
        img = (f'<rect x="44" y="52" width="196" height="196" fill="#000" opacity=".45"/>'
               f'<rect x="36" y="44" width="196" height="196" fill="{YELLOW}"/>'
               f'<rect x="40" y="48" width="188" height="188" fill="{SCREEN_EDGE}"/>'
               f'<image x="44" y="52" width="180" height="180" preserveAspectRatio="xMidYMid slice" '
               f'style="image-rendering:pixelated" href="data:{mime};base64,{b64}"/>')

    # One heart per week, for the last five weeks: full if you contributed that week.
    hearts = ""
    for i in range(5):
        week_end = today - dt.timedelta(days=7 * (4 - i))
        active = any(d["days"].get((week_end - dt.timedelta(k)).isoformat(), 0) for k in range(7))
        hearts += sprite(HEART, 652 + i * 32, 38, 4, {"X": RED, "W": "#FFC2C2"} if active else {"X": EMPTY, "W": EMPTY})

    level = max(1, today.year - int(d["created"][:4]) + (1 if today.strftime("%m-%d") >= d["created"][5:] else 0))
    score = f'{d["score"]:06d}'
    sx = 268
    stats = [("COMMITS", d["commits"]), ("PULL REQS", d["prs"]), ("ISSUES", d["issues"]),
             ("STARS", d["stars"]), ("REPOS", d["repos"]), ("LEVEL", level)]
    grid = ""
    for i, (label, val) in enumerate(stats):
        cx, cy = sx + (i % 3) * 182, 222 + (i // 3) * 34
        grid += t(cx, cy, label, 20, GREEN_DIM) + t(cx + 96, cy, f"{val:,}", 24, GREEN)

    body = (img
            + shadow_t(sx, 74, "PLAYER 1", 24, ORANGE, "#6B2300")
            + hearts
            + t(sx, 112, d["name"], 34, INK)
            + t(sx, 138, TAGLINE, 22, INK_DIM)
            + t(sx, 178, "SCORE", 12, YELLOW, PIXEL)
            + t(sx + 80, 182, score, 26, "#FF3B5C", PIXEL, extra='opacity=".75"')
            + t(sx + 84, 182, score, 26, "#38E8FF", PIXEL, extra='opacity=".75"')
            + t(sx + 82, 182, score, 26, "#F4F1FF", PIXEL)
            + t(sx + 252, 182, "contributions", 20, INK_DIM)
            + grid)
    title = f'Player 1: {d["name"]}. Score {d["score"]:,} contributions, {d["commits"]:,} commits, level {level}.'
    return crt(w, h, body, fonts, title)


def combo_card(d, fonts, today):
    w, h = 414, 220
    cur, cur_start, best, best_range = streaks(d["days"], today)
    flicker = (".f1{animation:f 0.6s steps(1) infinite}.f2{animation:f 0.6s steps(1) infinite reverse;opacity:0}"
               "@keyframes f{0%{opacity:1}50%{opacity:0}}"
               "@media (prefers-reduced-motion:reduce){.f1,.f2{animation:none}.f2{opacity:0}}")
    flame_colors = {"O": ORANGE, "Y": YELLOW}
    num = f"×{cur}"
    num_w = len(num) * 40
    fx = 207 - (num_w + 44) // 2
    body = (shadow_t(32, 50, "COMBO", 14, ORANGE, "#6B2300", 2)
            + f'<g class="f1">{sprite(FLAME, fx, 72, 6, flame_colors)}</g>'
            + f'<g class="f2">{sprite(FLAME2, fx, 72, 6, flame_colors)}</g>'
            + shadow_t(fx + 48, 118, num, 40, YELLOW, "#6B4A00", 4)
            + t(207, 146, "day streak" if cur != 1 else "day streak", 22, GREEN, anchor="middle")
            + t(207, 166, fmt_range(cur_start, today if cur else None) if cur else "Start a new combo today",
                18, INK_DIM, anchor="middle")
            + f'<rect x="32" y="178" width="350" height="2" fill="{EMPTY}"/>'
            + t(32, 200, "BEST", 10, YELLOW, PIXEL) + t(82, 201, f"×{best}", 22, INK)
            + t(382, 200, fmt_range(*best_range) if best_range else "", 18, INK_DIM, anchor="end"))
    return crt(w, h, body, fonts, f"Current streak {cur} days, best {best} days.", style=flicker)


def inventory_card(d, fonts):
    w, h = 414, 220
    total = sum(s for s, _ in d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1][0])[:5]
    rows = ""
    for i, (name, (size, color)) in enumerate(top):
        y = 82 + i * 27
        pct = size / total * 100
        filled = max(1, round(pct / 10)) if pct > 0 else 0
        rows += t(32, y, name, 22, INK)
        for k in range(10):
            rows += f'<rect x="{170 + k * 15}" y="{y - 14}" width="12" height="14" fill="{color if k < filled else EMPTY}"/>'
        rows += t(382, y, f"{pct:.0f}%", 10, YELLOW, PIXEL, "end")
    body = shadow_t(32, 50, "INVENTORY", 14, ORANGE, "#6B2300", 2) + rows
    title = "Top languages: " + ", ".join(f"{n} {s / total * 100:.0f}%" for n, (s, _) in top)
    return crt(w, h, body, fonts, title)


def level_map(d, fonts):
    w, h = 840, 196
    weeks = d["last_year"]
    cell, gap = 11, 3
    gx = 12 + (816 - len(weeks) * (cell + gap) + gap) // 2
    gy = 78
    ramp = [EMPTY, "#1B5E3A", "#24A152", "#3DFF7A", "#C8FFB0"]
    peak = max((c for wk in weeks for c in wk), default=1) or 1
    cells, months, start = "", "", dt.date.fromisoformat(d["first_day"])
    last_month = None
    for i, wk in enumerate(weeks):
        wd = start + dt.timedelta(weeks=i)
        if wd.month != last_month and i < len(weeks) - 2:
            months += t(gx + i * (cell + gap), gy - 8, wd.strftime("%b"), 18, INK_DIM)
            last_month = wd.month
        for j, c in enumerate(wk):
            lvl = 0 if c == 0 else min(4, 1 + int(3 * c / peak))
            cells += f'<rect x="{gx + i * (cell + gap)}" y="{gy + j * (cell + gap)}" width="{cell}" height="{cell}" fill="{ramp[lvl]}"/>'
    body = (shadow_t(32, 46, "LEVEL MAP", 14, ORANGE, "#6B2300", 2)
            + t(808, 46, f'{d["last_year_total"]:,} contributions in the last year', 22, GREEN, anchor="end")
            + months + cells)
    return crt(w, h, body, fonts, f'{d["last_year_total"]:,} contributions in the last year.')


def title_bar(text, fonts):
    w, h = 840, 52
    tri = "".join(f'<rect x="{14 + i * 4}" y="{14 + i * 4}" width="4" height="{24 - i * 8}" fill="{YELLOW}"/>' for i in range(3))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{escape(text)}</title>
<style>{fonts}</style>
<path d="{stepped(0, 0, w, h, 4)}" fill="{SCREEN}"/>
<rect x="0" y="{h - 4}" width="{w}" height="4" fill="{ORANGE}" opacity=".9"/>
{tri}
{shadow_t(40, 35, text, 16, YELLOW, "#6B4A00", 2)}
</svg>'''


def send_ideas(fonts, email):
    w, h = 840, 120
    cursor = ".c{animation:b 1s steps(1) infinite}@keyframes b{50%{opacity:0}}@media (prefers-reduced-motion:reduce){.c{animation:none}}"
    body = (shadow_t(420, 72, "SEND IDEAS", 34, YELLOW, "#6B4A00", 4, anchor="middle")
            + t(420, 100, email, 24, GREEN, anchor="middle")
            + f'<rect class="c" x="{420 + len(email) * 5 + 8}" y="84" width="10" height="18" fill="{GREEN}"/>')
    return crt(w, h, body, fonts, f"Send ideas: {email}", style=cursor)


# ---------------------------------------------------------------- main
def main():
    os.makedirs(OUT, exist_ok=True)
    today = dt.datetime.now(ZoneInfo(TIME_ZONE)).date()
    if "--mock" in sys.argv:
        d = mock()
    else:
        token = os.environ.get("GH_TOKEN")
        if not token:
            raise SystemExit("GH_TOKEN is not set. Add the SUMMARY_GITHUB_TOKEN secret to the repo.")
        d = fetch(token)
    fonts = font_css()
    files = {
        "player.svg": player_card(d, fonts, today),
        "combo.svg": combo_card(d, fonts, today),
        "inventory.svg": inventory_card(d, fonts),
        "level-map.svg": level_map(d, fonts),
        "send-ideas.svg": send_ideas(fonts, os.environ.get("EMAIL", "elmariamikhalil@gmail.com")),
    }
    for slug, label in [("about", "ABOUT ME"), ("stack", "TECH STACK"), ("what", "WHAT I DO"),
                        ("stats", "STATS"), ("projects", "FEATURED PROJECTS")]:
        files[f"title-{slug}.svg"] = title_bar(label, fonts)
    for name, svg in files.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote {OUT}/{name} ({len(svg) // 1024} KB)")


if __name__ == "__main__":
    main()
