#!/usr/bin/env python3
"""Desk-top chips: one animated SVG per tool, a monitor-label per row, and a
"field guide" card per row that explains every chip. Icons come from Simple
Icons; the README block between the Tech Garden markers is rewritten.

    python scripts/gen_chips.py
"""
import html
import random
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "chips"
ICON_URL = "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{}.svg"
FONT = ("Segoe UI, Microsoft YaHei, PingFang SC, Hiragino Sans GB, "
        "Noto Sans SC, Helvetica, Arial, sans-serif")
CHIP_COLOURS = ["#4C8DFF", "#F2A33C", "#37B59B", "#8A7CF5"]
GREY = "#8b949e"
GUIDE_WRAP = 118  # display units per line (a CJK glyph counts as 2)

# (row label, accent, deep accent, chips)
# chip = (file slug, Simple Icons slug or None, label, description)
STACK = [
    ("LANGUAGES", "#4C8DFF", "#2F6FE0", [
        ("python", "python", "Python",
         "My main source of productivity. Every framework learns to speak it first — so did I."),
        ("typescript", "typescript", "TypeScript",
         "Insurance for JavaScript — it blocks those late-night stupidities at compile time 🛡️"),
        ("javascript", "javascript", "JavaScript",
         "The lingua franca of the web. Writing it is like a mystery box: it runs, but you don't know why."),
        ("rust", "rust", "Rust",
         "A memory-safe systems language. I learned it because everyone said it was hard — then I found out everyone was right 🦀"),
        ("cplusplus", "cplusplus", "C++",
         "Performance and pain, together. Pointers taught me to respect memory."),
        ("git", "git", "Git",
         "My most honest skill — because every messy commit leaves evidence."),
    ]),
    ("AI / DATA", "#8A7CF5", "#6E5EE0", [
        ("langchain", "langchain", "LangChain",
         "The glue that strings models, tools and memory into chains. Once a chain grows long, you forget what you wrote 🧩"),
        ("rag", None, "RAG",
         "Look up sources before answering, so the model does less confident nonsense 📚"),
        ("prompt", None, "Prompt",
         "The craft of talking to models. Same model — the prompt decides whether it's a genius or an idiot ✍️"),
        ("numpy", "numpy", "NumPy",
         "The bedrock of matrix math, and the reason I break down debugging shapes."),
        ("pandas", "pandas", "Pandas",
         "The Swiss Army knife for tables. Out of memory? Switch chunks and go again."),
        ("openai", "openai", "OpenAI",
         "The second brain of modern programming, and the one I never thanked in my paper."),
        ("deepseek", "deepseek", "Deepseek",
         "Open-source pride: cheap and capable, the savior of my compute budget 🐋"),
    ]),
    ("ON MY DESK", "#37B59B", "#26897A", [
        ("apple", "apple", "Apple",
         "A sweet cage of ecosystem lock-in: once you're in, you never get out 🍎"),
        ("android", "android", "Android",
         "Backup phone, tinkering, flashing ROMs. The open other half of freedom."),
        ("raspberrypi", "raspberrypi", "Raspberry Pi",
         "The device that collects the most dust. The happiest moment is when you buy it."),
        ("arduino", "arduino", "Arduino",
         "It lets electronics newbies light things up. My first lit LED moved me more than my paper did."),
        ("nvidia", "nvidia", "NVIDIA",
         "The ultimate black hole for your wallet. CUDA will still be here; the money won't."),
        ("visualstudiocode", "visualstudiocode", "VS Code",
         "My second bed. 200 extensions installed, 3 actually used."),
        ("sony", "sony", "Sony",
         "Put on the noise-cancelling headphones and the world goes quiet — except my advisor's messages buzzing."),
    ]),
    ("OFF SCREEN", "#F2A33C", "#D98828", [
        ("nba", "nba", "Basketball",
         "The court is the only place honest with me — a miss is a miss 🏀"),
        ("nike", "nike", "Nike",
         "A gearhead's comfort: when the skill isn't enough, the shoes make up for it."),
        ("spotify", "spotify", "Spotify",
         "The BGM supplier for coding. My playlists get more care than my code."),
        ("steam", "steam", "Steam",
         "A digital museum where buying counts as playing. The games in my library are my digital inheritance."),
        ("bilibili", "bilibili", "Bilibili",
         "A cyber study room. Watch for three hours, learn for five minutes."),
        ("notion", "notion", "Notion",
         "Productivity laid out beautifully, output still zero."),
        ("youtube", "youtube", "YouTube",
         "From fixing pipes to writing papers, a gathering of cosmic-level mentors."),
    ]),
]

# Arial Bold advance widths (per 1000 em) — a safe upper bound for the Segoe/Helvetica stack
_W = {**{c: 722 for c in "ABCDHKNRU"}, "E": 667, "F": 611, "G": 778, "I": 278, "J": 556, "L": 611, "M": 833,
      "O": 778, "P": 667, "Q": 778, "S": 667, "T": 611, "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
      **{c: 556 for c in "acekssxyv"}, **{c: 611 for c in "bdghnopqu"}, "f": 333, "i": 278, "j": 278, "l": 278,
      "m": 889, "r": 389, "t": 333, "w": 778, "z": 500, " ": 278, ".": 278, "/": 278, "-": 333, "+": 584,
      "(": 333, ")": 333}


def text_width(s, size):
    return sum(_W.get(c, 611) for c in s) * size / 1000


def display_width(s):
    """CJK / full-width glyphs count as 2 units, the rest as 1."""
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def wrap_cjk(s, limit):
    lines, cur, w = [], "", 0
    for ch in s:
        cw = 2 if ord(ch) > 0x2E7F else 1
        if w + cw > limit and cur:
            lines.append(cur)
            cur, w = "", 0
        cur += ch
        w += cw
    if cur:
        lines.append(cur)
    return lines


_icons = {}


def icon_path(slug):
    if slug not in _icons:
        req = urllib.request.Request(ICON_URL.format(slug), headers={"User-Agent": "Mozilla/5.0"})
        last = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    svg = r.read().decode("utf-8")
                break
            except Exception as exc:
                last = exc
                time.sleep(1.0)
        else:
            raise SystemExit(f"could not fetch Simple Icons svg for {slug}: {last}")
        m = re.search(r'<path d="([^"]+)"', svg)
        if not m:
            raise SystemExit(f"no path in Simple Icons svg for {slug}")
        _icons[slug] = m.group(1)
    return _icons[slug]


def svg(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="{FONT}">'
            f'<title>{html.escape(title)}</title>{body}</svg>\n')


def monitor(x, y, accent, deep, dur):
    """A tiny monitor glyph with a pulsing power LED."""
    return (f'<g transform="translate({x},{y})">'
            f'<rect x="-9" y="-7" width="18" height="13" rx="2.2" fill="none" stroke="{accent}" stroke-width="1.4"/>'
            f'<path d="M-4 8 H4" stroke="{accent}" stroke-width="1.4" stroke-linecap="round"/>'
            f'<circle cx="0" cy="0" r="2.6" fill="{deep}">'
            f'<animate attributeName="opacity" values="1;0.25;1" dur="{dur}s" repeatCount="indefinite"/></circle></g>')


def chip(slug, icon, label, colour):
    rnd = random.Random(label)
    dur, beg = 3.5 + rnd.random(), -rnd.random() * 4
    tw = int(text_width(label, 12)) + 2
    if icon:
        w = 32 + tw + 13
        inner = (f'<g transform="translate(12,8) scale(0.5833)"><path d="{icon_path(icon)}" fill="{colour}"/></g>'
                 f'<text x="32" y="19" font-size="12" font-weight="600" fill="{colour}">{html.escape(label)}</text>')
    else:
        w = 12 + tw + 12
        inner = f'<text x="{w / 2:g}" y="19" text-anchor="middle" font-size="12" font-weight="600" fill="{colour}">{html.escape(label)}</text>'
    body = ('<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="0s" dur="0.5s" fill="freeze"/>'
            f'<g><animateTransform attributeName="transform" type="translate" values="0 1.2;0 -1.2;0 1.2" calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1" keyTimes="0;0.5;1" dur="{dur:.1f}s" begin="{beg:.1f}s" repeatCount="indefinite"/>'
            f'<rect x="1" y="4" width="{w - 2}" height="22" rx="11" fill="{colour}" fill-opacity="0.07" stroke="{colour}" stroke-width="1.3"/>'
            f'{inner}</g></g>')
    return svg(w, 30, label, body)


def label_chip(text, accent, deep):
    w = round(30 + len(text) * 8.2 + 6)
    return svg(w, 30, text, monitor(13, 15, accent, deep, 2.4) +
               f'<text x="30" y="19" font-size="11" letter-spacing="1.5" fill="{GREY}">{html.escape(text)}</text>')


def guide(text, accent, chips):
    h = len(chips) * 62 + 48
    parts = [f'\n<rect x="1" y="1" width="858" height="{h - 2}" rx="14" fill="{accent}" fill-opacity="0.04" stroke="{accent}" stroke-opacity="0.35" stroke-width="1.2"/>\n',
             monitor(30, 24, accent, accent, 3) + "\n",
             f'<text x="48" y="30" font-size="11" letter-spacing="2" fill="{GREY}">{html.escape(text)}</text>\n']
    for i, (slug, icon, label, desc) in enumerate(chips):
        y, c = 50 + 62 * i, CHIP_COLOURS[i % 4]
        lines = wrap_cjk(desc, GUIDE_WRAP)
        if len(lines) > 2:
            raise SystemExit(f"{label}: description needs {len(lines)} lines, max 2")
        glyph = f'<g transform="translate(38,{y}) scale(0.8)"><path d="{icon_path(icon)}" fill="{c}"/></g>' if icon else ""
        body = "".join(f'<text x="76" y="{y + 25 + 16 * k}" font-size="12" fill="{GREY}">{html.escape(l)}</text>' for k, l in enumerate(lines))
        rule = f'<path d="M76 {y + 48} H 820" stroke="{c}" stroke-opacity="0.15" stroke-width="1"/>' if i < len(chips) - 1 else ""
        parts.append(f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{0.15 + 0.09 * i:.2f}s" dur="0.5s" fill="freeze"/>'
                     f'{glyph}<text x="76" y="{y + 8}" font-size="13" font-weight="700" fill="{c}">{html.escape(label)}</text>{body}{rule}</g>\n')
    return svg(860, h, f"{text} field guide", "".join(parts))


def readme_block():
    rows, guides = [], []
    for i, (text, accent, deep, chips) in enumerate(STACK):
        imgs = [f'<img src="chips/label-{i}.svg" alt="{html.escape(text)}" />']
        imgs += [f'<img src="chips/{slug}.svg" alt="{html.escape(label)}" />' for slug, _, label, _ in chips]
        rows.append("\n".join(imgs))
        guides.append(f'<img src="chips/guide-{i}.svg" alt="{html.escape(text)} field guide" /><br/>')
    return ('<!-- ============ Tech Garden ============ -->\n<div align="center">\n\n'
            + "\n\n".join(rows) + "\n\n<details>\n"
            '<summary>🖥️ &nbsp;<b>Field guide</b> — every chip, explained (click to see what each one does)</summary>\n<br/>\n<div align="center">\n'
            + "\n".join(guides) + "\n</div>\n</details>\n\n</div>\n")


def main():
    OUT.mkdir(exist_ok=True)
    keep = set()
    for i, (text, accent, deep, chips) in enumerate(STACK):
        for j, (slug, icon, label, desc) in enumerate(chips):
            (OUT / f"{slug}.svg").write_text(chip(slug, icon, label, CHIP_COLOURS[j % 4]), encoding="utf-8")
            keep.add(f"{slug}.svg")
        (OUT / f"label-{i}.svg").write_text(label_chip(text, accent, deep), encoding="utf-8")
        (OUT / f"guide-{i}.svg").write_text(guide(text, accent, chips), encoding="utf-8")
        keep |= {f"label-{i}.svg", f"guide-{i}.svg"}
    stale = [p for p in OUT.glob("*.svg") if p.name not in keep]
    for p in stale:
        p.unlink()

    readme = ROOT / "README.md"
    s = readme.read_text(encoding="utf-8")
    start = s.index("<!-- ============ Tech Garden ============ -->")
    end_marker = "</details>\n\n</div>\n"
    end = s.index(end_marker, start) + len(end_marker)
    readme.write_text(s[:start] + readme_block() + s[end:], encoding="utf-8")
    print(f"{len(keep)} svgs written, {len(stale)} stale removed: {', '.join(p.name for p in stale) or '-'}")


if __name__ == "__main__":
    main()
