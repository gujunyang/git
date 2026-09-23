#!/usr/bin/env python3
"""Desk-top chips: one animated SVG per tool, a monitor-label per row, and a
"field guide" card per row that explains every chip. Icons come from Simple
Icons; the README block between the Tech Garden markers is rewritten.

    python scripts/gen_chips.py
"""
import html
import random
import re
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
         "主要生产力。所有框架都先学会说它，我也是。"),
        ("typescript", "typescript", "TypeScript",
         "给 JavaScript 上保险——编译期就拦住那些深夜的愚蠢 🛡️"),
        ("javascript", "javascript", "JavaScript",
         "一切网页的通用语。写它像开盲盒：能跑，但不知道为什么。"),
        ("rust", "rust", "Rust",
         "内存安全的系统语言。我学它是因为大家都说它难，后来我发现大家是对的 🦀"),
        ("cplusplus", "cplusplus", "C++",
         "性能与痛苦并存。指针教会我对内存保持敬畏。"),
        ("git", "git", "Git",
         "我最诚实的一项技能——因为每一次乱提交都留下了证据。"),
    ]),
    ("AI / DATA", "#8A7CF5", "#6E5EE0", [
        ("langchain", "langchain", "LangChain",
         "把大模型、工具和记忆串成链的胶水。链一长，就不知道自己写了啥 🧩"),
        ("rag", None, "RAG",
         "先检索资料再回答，让模型少一本正经地胡说八道 📚"),
        ("prompt", None, "Prompt",
         "和模型对话的手艺。同一个模型，提示词决定它是天才还是人工智障 ✍️"),
        ("numpy", "numpy", "NumPy",
         "矩阵运算的地基，也是我调 shape 调到崩溃的元凶。"),
        ("pandas", "pandas", "Pandas",
         "处理表格的瑞士军刀。内存爆了？换个 chunk 再来。"),
        ("openai", "openai", "OpenAI",
         "现代编程的第二个大脑，也是我论文致谢里没写的那位。"),
        ("deepseek", "deepseek", "Deepseek",
         "国产开源之光：便宜、能打，是我算力预算的救星 🐋"),
    ]),
    ("ON MY DESK", "#37B59B", "#26897A", [
        ("apple", "apple", "Apple",
         "生态绑架的甜蜜牢笼：一旦进去，就再也没出来过 🍎"),
        ("android", "android", "Android",
         "备机、折腾、刷机。开放的另一半自由。"),
        ("raspberrypi", "raspberrypi", "Raspberry Pi",
         "吃灰率最高的设备。买它的那一刻最快乐。"),
        ("arduino", "arduino", "Arduino",
         "让电子小白也能点灯。我点亮的第一个 LED，比论文还让我感动。"),
        ("nvidia", "nvidia", "NVIDIA",
         "钱包的终极黑洞。CUDA 会在，钱不会。"),
        ("visualstudiocode", "visualstudiocode", "VS Code",
         "我的第二张床。插件装了 200 个，常用的只有 3 个。"),
        ("sony", "sony", "Sony",
         "降噪耳机一戴，全世界安静，只剩导师的消息在震。"),
    ]),
    ("OFF SCREEN", "#F2A33C", "#D98828", [
        ("nba", "nba", "Basketball",
         "球场是唯一对我诚实的地方——投不进，就是投不进 🏀"),
        ("nike", "nike", "Nike",
         "装备党的自我安慰：技术不够，鞋来凑。"),
        ("spotify", "spotify", "Spotify",
         "写代码的 BGM 供应商。歌单比代码更用心。"),
        ("steam", "steam", "Steam",
         "买了等于玩过的电子收藏馆。库里的游戏是我的数字遗产。"),
        ("bilibili", "bilibili", "Bilibili",
         "赛博自习室。看了三小时，学了五分钟。"),
        ("notion", "notion", "Notion",
         "生产力布置得很漂亮，产出依旧为零。"),
        ("youtube", "youtube", "YouTube",
         "从修水管到写论文，宇宙级导师集合。"),
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
        with urllib.request.urlopen(req, timeout=20) as r:
            svg = r.read().decode("utf-8")
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
            '<summary>🖥️ &nbsp;<b>Field guide</b> — every chip, explained (点开看看每个都在干嘛)</summary>\n<br/>\n<div align="center">\n'
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
