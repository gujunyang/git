#!/usr/bin/env python3
"""Living desk: a Hong-Kong-weather-synced animated header + footer.

The sky follows the real forecast (Open-Meteo, no API key), the desk follows
the season, and a cat lives in the footer. Pure Python, zero dependencies.

    python scripts/gen_scene.py

Outputs (repo root, both day and night variants for prefers-color-scheme):
    desk.svg            desk-night.svg
    desk-footer.svg     desk-footer-night.svg
    .github/scene-state.json

Optional pins via environment (used by the GitHub Action):
    SCENE_WEATHER  clear|clouds|drizzle|rain|snow|fog|storm
    SCENE_SEASON   spring|summer|autumn|winter
"""
import json
import math
import os
import random
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".github" / "scene-state.json"

LAT, LON = 22.3193, 114.1694          # Hong Kong
TZ = "Asia%2FHong_Kong"
PLACE = "Hong Kong"
FONT = ("Segoe UI, Microsoft YaHei, PingFang SC, Hiragino Sans GB, "
        "Noto Sans SC, Helvetica, Arial, sans-serif")

W, H = 900, 300                        # header canvas
FW, FH = 900, 170                      # footer canvas

CONDITIONS = ("clear", "clouds", "drizzle", "rain", "snow", "fog", "storm")
COND_EN = {"clear": "Clear", "clouds": "Cloudy", "drizzle": "Drizzle", "rain": "Rain",
           "snow": "Snow", "fog": "Fog", "storm": "Thunder"}
SEASONS = ("spring", "summer", "autumn", "winter")

# ---------------------------------------------------------------- palette


class Pal:
    def __init__(self, sky1, sky2, wall, desk1, desk2, edge, device, screen,
                 ink, sub, glow, sun, sun2, cloud, cloud2, plant, plant2,
                 cat, cat2):
        self.sky1, self.sky2 = sky1, sky2
        self.wall = wall
        self.desk1, self.desk2, self.edge = desk1, desk2, edge
        self.device, self.screen = device, screen
        self.ink, self.sub = ink, sub
        self.glow = glow
        self.sun, self.sun2 = sun, sun2
        self.cloud, self.cloud2 = cloud, cloud2
        self.plant, self.plant2 = plant, plant2
        self.cat, self.cat2 = cat, cat2


DAY = Pal(sky1="#BFE0FF", sky2="#EAF4FF", wall="#F3F7FC",
          desk1="#EADCC3", desk2="#CDB48C", edge="#B79B70",
          device="#CBD5E1", screen="#12202E",
          ink="#1F2A37", sub="#5B6B7C", glow="#FFD27A",
          sun="#FFC94D", sun2="#FFE9B8", cloud="#FFFFFF", cloud2="#DCE6F2",
          plant="#5FA86B", plant2="#8FCB97",
          cat="#F0B27A", cat2="#D19A66")

NIGHT = Pal(sky1="#0A1020", sky2="#141E36", wall="#0D1117",
            desk1="#2A2D36", desk2="#1A1C22", edge="#3A3E49",
            device="#37404E", screen="#0B1A2A",
            ink="#E6EDF3", sub="#9AA7B4", glow="#FFD98A",
            sun="#E8EEF7", sun2="#FBFDFF", cloud="#2A3550", cloud2="#1C2438",
            plant="#3F7A52", plant2="#5C9B6C",
            cat="#B98A5E", cat2="#8A6440")


# ---------------------------------------------------------------- weather


def weather_code_to_condition(code):
    if code in (0, 1):
        return "clear"
    if code in (2, 3):
        return "clouds"
    if code in (45, 48):
        return "fog"
    if 51 <= code <= 57:
        return "drizzle"
    if 61 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "snow"
    if code >= 95:
        return "storm"
    return "clouds"


def current_season(now):
    m = now.month
    if 3 <= m <= 5:
        return "spring"
    if 6 <= m <= 8:
        return "summer"
    if 9 <= m <= 11:
        return "autumn"
    return "winter"


def fetch_weather():
    """Return (condition, is_day, temp) or None if the network is unreachable."""
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={LAT}&longitude={LON}"
           "&current=weather_code,temperature_2m,is_day"
           f"&timezone={TZ}")
    with urllib.request.urlopen(url, timeout=30) as r:
        data = json.load(r)
    cur = data["current"]
    return (weather_code_to_condition(int(cur["weather_code"])),
            int(cur.get("is_day", 1)),
            round(float(cur["temperature_2m"])))


# ---------------------------------------------------------------- drawing helpers


def led(x, y, colour, dur=2.4, r=2.6):
    return (f'<circle cx="{x}" cy="{y}" r="{r}" fill="{colour}">'
            f'<animate attributeName="opacity" values="1;0.25;1" dur="{dur}s" repeatCount="indefinite"/></circle>')


def sun(cx, cy, p):
    return (f'<g transform="translate({cx},{cy})">'
            f'<circle r="30" fill="{p.sun}" opacity="0.14"><animate attributeName="opacity" values="0.08;0.2;0.08" keyTimes="0;0.5;1" dur="6s" repeatCount="indefinite"/></circle>'
            f'<circle r="19" fill="{p.sun}" opacity="0.30"><animate attributeName="opacity" values="0.2;0.36;0.2" keyTimes="0;0.5;1" dur="6s" repeatCount="indefinite"/></circle>'
            f'<circle r="15" fill="{p.sun}"/>'
            f'<circle r="15" fill="{p.sun2}" opacity="0.55"/></g>')


def moon(cx, cy, p):
    return (f'<g transform="translate({cx},{cy})">'
            f'<circle r="28" fill="{p.sun}" opacity="0.10"><animate attributeName="opacity" values="0.06;0.16;0.06" keyTimes="0;0.5;1" dur="7s" repeatCount="indefinite"/></circle>'
            f'<circle r="16" fill="{p.sun}"/>'
            f'<circle cx="-5" cy="-4" r="3" fill="{p.sun2}" opacity="0.5"/>'
            f'<circle cx="4" cy="5" r="2.2" fill="{p.sun2}" opacity="0.4"/>'
            f'<circle cx="6" cy="-6" r="1.6" fill="{p.sun2}" opacity="0.35"/></g>')


def cloud(cx, cy, s, p, opacity, dur, begin, dark=False):
    fill = p.cloud2 if dark else p.cloud
    return (f'<g transform="translate({cx},{cy})"><g opacity="{opacity}">'
            f'<animateTransform attributeName="transform" type="translate" values="-{20 + cx * 0.02:.0f} 0;{20 + cx * 0.02:.0f} 3;-{20 + cx * 0.02:.0f} 0" '
            f'calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1" keyTimes="0;0.5;1" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>'
            f'<g transform="scale({s})" fill="{fill}">'
            f'<rect x="-52" y="-8" width="104" height="22" rx="11"/>'
            f'<circle cx="-24" cy="-10" r="17"/><circle cx="2" cy="-20" r="23"/><circle cx="27" cy="-9" r="18"/>'
            f'<ellipse cx="0" cy="10" rx="46" ry="4" fill="{p.cloud2}" opacity="0.4"/></g></g></g>')


def rain_layer(p, seed, n=46):
    rnd = random.Random(seed)
    parts = [f'<g stroke="#8FB8FF" stroke-width="1.6" stroke-linecap="round" opacity="0.55">']
    for _ in range(n):
        x = rnd.uniform(30, W - 30)
        delay = round(rnd.uniform(0, 1.6), 2)
        dur = round(rnd.uniform(0.7, 1.1), 2)
        length = rnd.randint(8, 15)
        parts.append(
            f'<line x1="{x:.0f}" y1="0" x2="{x - 3:.0f}" y2="{length}">'
            f'<animateTransform attributeName="transform" type="translate" values="0 -20;0 230" dur="{dur}s" begin="-{delay}s" repeatCount="indefinite"/></line>')
    parts.append('</g>')
    return "".join(parts)


def snow_layer(p, seed, n=40):
    rnd = random.Random(seed)
    parts = ['<g fill="#FFFFFF" opacity="0.85">']
    for _ in range(n):
        x = rnd.uniform(30, W - 30)
        r = round(rnd.uniform(1.4, 2.6), 1)
        delay = round(rnd.uniform(0, 6), 2)
        dur = round(rnd.uniform(6, 10), 2)
        drift = rnd.randint(-14, 14)
        parts.append(
            f'<circle cx="{x:.0f}" cy="0" r="{r}">'
            f'<animateTransform attributeName="transform" type="translate" values="0 -10;{drift} 230" dur="{dur}s" begin="-{delay}s" repeatCount="indefinite"/></circle>')
    parts.append('</g>')
    return "".join(parts)


def fog_layer(p, seed):
    rnd = random.Random(seed)
    parts = [f'<g fill="{p.cloud}" opacity="0.28">']
    for i in range(5):
        y = 130 + i * 16
        dur = round(rnd.uniform(18, 30), 1)
        parts.append(
            f'<ellipse cx="{rnd.uniform(150, 750):.0f}" cy="{y}" rx="{rnd.uniform(150, 260):.0f}" ry="9">'
            f'<animateTransform attributeName="transform" type="translate" values="-60 0;60 0;-60 0" dur="{dur}s" repeatCount="indefinite"/></ellipse>')
    parts.append('</g>')
    return "".join(parts)


def lightning(seed):
    rnd = random.Random(seed)
    x = rnd.uniform(520, 760)
    return (f'<g opacity="0"><path d="M{x:.0f} 18 L{x - 16:.0f} 74 L{x - 2:.0f} 74 L{x - 20:.0f} 132" '
            f'stroke="#FFE9A8" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round">'
            f'<animate attributeName="opacity" values="0;0;0.95;0;0.6;0;0" keyTimes="0;0.42;0.45;0.5;0.55;0.6;1" dur="7s" repeatCount="indefinite"/></path></g>')


# ---------------------------------------------------------------- desk items


def plant(season, x=120, y=210, scale=1.0):
    """A small potted plant; the season changes its mood."""
    out = [f'<g transform="translate({x},{y}) scale({scale})">']
    # pot
    out.append('<path d="M-20 0 H20 L15 30 H-15 Z" fill="#C98A63"/>'
               '<rect x="-22" y="-4" width="44" height="8" rx="3" fill="#B87A54"/>')
    # stem
    out.append('<path d="M0 0 C-2 -18 2 -34 0 -50" stroke="#4E8B57" stroke-width="2.6" fill="none" stroke-linecap="round"/>')
    if season == "winter":
        out.append('<path d="M0 -50 L-10 -62 M0 -44 L11 -56 M0 -34 L-9 -46" stroke="#7A8A93" stroke-width="2" '
                   'fill="none" stroke-linecap="round" opacity="0.8"/>')
        out.append('<circle cx="0" cy="-64" r="3" fill="#FFFFFF" opacity="0.9"/>')
    elif season == "autumn":
        for dx, dy, rot in [(-9, -46, -35), (10, -52, 25), (-2, -60, 0)]:
            out.append(f'<ellipse cx="{dx}" cy="{dy}" rx="9" ry="5" fill="#E0913F" transform="rotate({rot} {dx} {dy})"/>')
    elif season == "spring":
        for dx, dy in [(-9, -46), (10, -52), (-2, -60), (6, -38)]:
            out.append(f'<circle cx="{dx}" cy="{dy}" r="6" fill="#F3A6C4"/>'
                       f'<circle cx="{dx}" cy="{dy}" r="2.4" fill="#FFE1EC"/>')
    else:  # summer
        for dx, dy, rot in [(-10, -42, -40), (11, -50, 30), (-2, -58, 0), (7, -34, 20)]:
            out.append(f'<ellipse cx="{dx}" cy="{dy}" rx="10" ry="6" fill="#5FA86B" transform="rotate({rot} {dx} {dy})"/>')
    out.append('</g>')
    return "".join(out)


def monitor(p):
    return (
        '<g transform="translate(272,210)">'
        f'<rect x="-72" y="-96" width="144" height="88" rx="7" fill="{p.device}" stroke="{p.edge}" stroke-width="1.4"/>'
        f'<rect x="-65" y="-89" width="130" height="74" rx="4" fill="{p.screen}"/>'
        '<g font-family="Consolas, Menlo, monospace" font-size="9">'
        '<text x="-58" y="-72" fill="#7EE787">def</text><text x="-40" y="-72" fill="#79C0FF">hello</text><text x="-18" y="-72" fill="#E6EDF3">():</text>'
        '<text x="-52" y="-58" fill="#FFA657">print</text><text x="-30" y="-58" fill="#E6EDF3">(</text><text x="-25" y="-58" fill="#A5D6FF">"hi, world"</text><text x="35" y="-58" fill="#E6EDF3">)</text>'
        '<text x="-58" y="-44" fill="#8B949E"># TODO: sleep early</text>'
        '</g>'
        f'<rect x="-56" y="-32" width="6" height="10" fill="#E6EDF3"><animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.45;0.5;0.95;1" dur="1.1s" repeatCount="indefinite"/></rect>'
        f'<rect x="-10" y="-8" width="20" height="6" rx="2" fill="{p.edge}"/>'
        f'<rect x="-30" y="-2" width="60" height="4" rx="2" fill="{p.device}"/>'
        f'{led(66, -90, "#7EE787", 2.2, 2.2)}'
        '</g>')


def mug(p, x=470, y=210):
    return (
        f'<g transform="translate({x},{y})">'
        f'<path d="M-22 -46 H22 V-4 A16 16 0 0 1 -22 -4 Z" fill="{p.device}" stroke="{p.edge}" stroke-width="1.2"/>'
        f'<path d="M-22 -40 H22 V-32 H-22 Z" fill="#C98A63" opacity="0.9"/>'
        f'<path d="M22 -36 q14 0 14 12 q0 12 -14 12" fill="none" stroke="{p.edge}" stroke-width="3"/>'
        '<g stroke="#CBD5E1" stroke-width="2" fill="none" opacity="0.7" stroke-linecap="round">'
        '<path d="M-8 -52 q6 -8 0 -16 q-6 -8 0 -16"><animate attributeName="opacity" values="0.1;0.7;0.1" dur="3.4s" repeatCount="indefinite"/></path>'
        '<path d="M6 -52 q6 -8 0 -16 q-6 -8 0 -16"><animate attributeName="opacity" values="0.4;0.1;0.4" dur="3.4s" repeatCount="indefinite"/></path>'
        '</g></g>')


def headphones(p):
    return (
        '<g transform="translate(566,210)">'
        f'<path d="M-26 -30 A30 30 0 0 1 26 -30" fill="none" stroke="{p.edge}" stroke-width="5" stroke-linecap="round"/>'
        f'<rect x="-33" y="-32" width="14" height="26" rx="7" fill="{p.device}" stroke="{p.edge}" stroke-width="1.2"/>'
        f'<rect x="19" y="-32" width="14" height="26" rx="7" fill="{p.device}" stroke="{p.edge}" stroke-width="1.2"/>'
        f'{led(-26, -18, "#4C8DFF", 2.6, 2)}'
        '</g>')


def phone(p):
    return (
        '<g transform="translate(658,210) rotate(-6)">'
        f'<rect x="-16" y="-62" width="32" height="58" rx="7" fill="{p.device}" stroke="{p.edge}" stroke-width="1.3"/>'
        f'<rect x="-13" y="-58" width="26" height="46" rx="3" fill="{p.screen}"/>'
        '<circle cx="0" cy="-4" r="2" fill="#8b949e"/>'
        f'{led(16, -66, "#F2A33C", 1.6, 2)}'
        '</g>')


def lamp(p, is_day):
    glow_op = 0.18 if is_day else 0.5
    return (
        '<g transform="translate(806,210)">'
        f'<rect x="-26" y="-6" width="52" height="6" rx="3" fill="{p.edge}"/>'
        f'<path d="M0 -6 L-30 -74" stroke="{p.edge}" stroke-width="4" stroke-linecap="round"/>'
        f'<path d="M-30 -74 l-16 12 l22 14 z" fill="{p.device}" stroke="{p.edge}" stroke-width="1.2"/>'
        f'<circle cx="-34" cy="-64" r="5" fill="{p.glow}"/>'
        f'<path d="M-34 -60 L-72 20 L4 20 Z" fill="{p.glow}" opacity="{glow_op}">'
        f'<animate attributeName="opacity" values="{glow_op};{glow_op + 0.06};{glow_op}" dur="4s" repeatCount="indefinite"/></path>'
        '</g>')


def hud(text, ink, sub, sub_colour):
    """small caption, top-left under the name"""
    return (f'<g><circle cx="62" cy="{sub_colour[0]}" r="3.5" fill="{sub_colour[1]}">'
            f'<animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite"/></circle>'
            f'<text x="74" y="{sub_colour[0] + 4}" font-size="13" fill="{ink}" font-family="{FONT}">{text}</text></g>')


# ---------------------------------------------------------------- compose


def scene_defs(p, is_day):
    return (
        '<defs>'
        f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{p.sky1}"/><stop offset="1" stop-color="{p.sky2}"/></linearGradient>'
        f'<linearGradient id="desk" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{p.desk1}"/><stop offset="1" stop-color="{p.desk2}"/></linearGradient>'
        '</defs>')


def header(cond, season, is_day):
    p = DAY if is_day else NIGHT
    body = [scene_defs(p, is_day)]
    # sky
    body.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="url(#sky)"/>')
    # celestial
    if is_day:
        body.append(sun(812, 58, p))
    else:
        body.append(moon(812, 56, p))
        body.append('<g fill="#E8EEF7" opacity="0.7">' +
                    "".join(f'<circle cx="{x}" cy="{y}" r="{r:.1f}"/>'
                            for x, y, r in [(120, 40, 1.2), (220, 70, 1.0), (330, 34, 1.3), (520, 52, 1.0), (660, 30, 1.2)])
                    + '</g>')
    # clouds
    heavy = cond in ("clouds", "rain", "drizzle", "storm", "snow", "fog")
    body.append(cloud(520, 54, 0.85, p, 0.95 if heavy else 0.55, 40, -8, dark=not is_day))
    body.append(cloud(662, 42, 0.7, p, 0.9 if heavy else 0.4, 52, -22, dark=not is_day))
    if cond in ("clouds", "rain", "drizzle", "storm", "snow"):
        body.append(cloud(778, 74, 0.55, p, 0.8, 34, -3, dark=not is_day))
    # weather
    if cond in ("rain", "drizzle"):
        body.append(rain_layer(p, f"rain-{season}", 30 if cond == "drizzle" else 46))
    elif cond == "snow":
        body.append(snow_layer(p, f"snow-{season}", 46))
    elif cond == "fog":
        body.append(fog_layer(p, f"fog-{season}"))
    elif cond == "storm":
        body.append(cloud(430, 40, 1.1, p, 0.95, 30, -4, dark=not is_day))
        body.append(rain_layer(p, f"storm-{season}", 54))
        body.append(lightning(season))
    # desk
    body.append(f'<rect x="0" y="210" width="{W}" height="{H - 210}" fill="url(#desk)"/>')
    body.append(f'<rect x="0" y="210" width="{W}" height="3" fill="{p.edge}" opacity="0.8"/>')
    body.append(f'<rect x="0" y="211" width="{W}" height="1.5" fill="#FFFFFF" opacity="{0.25 if is_day else 0.06}"/>')
    # items (back to front)
    body.append(lamp(p, is_day))
    body.append(plant(season))
    body.append(monitor(p))
    body.append(mug(p))
    body.append(headphones(p))
    body.append(phone(p))
    # text
    ink, sub = p.ink, p.sub
    cond_en = COND_EN[cond]
    body.append(
        f'<g><text x="56" y="58" font-size="46" font-weight="700" letter-spacing="2" fill="{ink}">J4ckG</text>'
        f'<text x="58" y="86" font-size="15" letter-spacing="1" fill="{sub}">Half code, half court.</text>'
        + hud(f'{PLACE} · {cond_en} · {season}', ink, sub, (104, p.glow))
        + '</g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
            f'font-family="{FONT}">'
            f'<title>J4ckG — desk ({PLACE} {cond_en} {season})</title>'
            + "".join(body) + '</svg>\n')


# ---- footer: a cat asleep on the keyboard -------------------------------


def cat(p, x, y):
    return (
        f'<g transform="translate({x},{y})">'
        # body
        f'<ellipse cx="0" cy="0" rx="42" ry="22" fill="{p.cat}"/>'
        # tail
        f'<path d="M36 6 q26 4 22 -20 q-2 -14 -14 -8" fill="none" stroke="{p.cat2}" stroke-width="6" stroke-linecap="round">'
        f'<animateTransform attributeName="transform" type="rotate" values="0 36 6;-8 36 6;0 36 6" dur="3.2s" repeatCount="indefinite"/></path>'
        # stripes
        f'<path d="M-14 -18 q6 6 0 12 M4 -19 q6 6 0 12" stroke="{p.cat2}" stroke-width="3" fill="none" stroke-linecap="round" opacity="0.8"/>'
        # head
        f'<circle cx="-34" cy="-6" r="18" fill="{p.cat}"/>'
        f'<path d="M-48 -18 l-3 -12 l11 5 z" fill="{p.cat}"/>'
        f'<path d="M-22 -18 l3 -12 l-11 5 z" fill="{p.cat}"/>'
        # closed, content eyes
        f'<path d="M-42 -6 q4 4 8 0" stroke="{p.ink}" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        f'<path d="M-30 -6 q4 4 8 0" stroke="{p.ink}" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        f'<path d="M-36 -1 q3 3 6 0" stroke="#E98AA0" stroke-width="1.6" fill="none" stroke-linecap="round"/>'
        # breathing chest
        f'<ellipse cx="-8" cy="4" rx="14" ry="9" fill="{p.cat2}" opacity="0.45">'
        f'<animate attributeName="ry" values="9;11;9" dur="2.6s" repeatCount="indefinite"/></ellipse>'
        # Zzz
        '<g fill="' + p.sub + '" font-family="' + FONT + '" font-weight="700">'
        '<text x="-64" y="-30" font-size="13" opacity="0"><animate attributeName="opacity" values="0;1;0" dur="3.6s" begin="0s" repeatCount="indefinite"/>Z</text>'
        '<text x="-78" y="-46" font-size="16" opacity="0"><animate attributeName="opacity" values="0;1;0" dur="3.6s" begin="1.2s" repeatCount="indefinite"/>Z</text>'
        '<text x="-94" y="-64" font-size="19" opacity="0"><animate attributeName="opacity" values="0;1;0" dur="3.6s" begin="2.4s" repeatCount="indefinite"/>Z</text>'
        '</g></g>')


def keyboard(p, x, y):
    keys = []
    for r in range(2):
        for c in range(6):
            keys.append(f'<rect x="{x + 8 + c * 13}" y="{y + 6 + r * 11}" width="11" height="9" rx="2" fill="{p.edge}" opacity="0.85"/>')
    return (f'<rect x="{x}" y="{y}" width="94" height="30" rx="6" fill="{p.device}" stroke="{p.edge}" stroke-width="1.2"/>'
            + "".join(keys))


def footer(is_day):
    p = DAY if is_day else NIGHT
    body = [scene_defs(p, is_day)]
    body.append(f'<rect x="0" y="0" width="{FW}" height="{FH}" fill="{p.wall}"/>')
    # soft spotlight
    body.append(f'<ellipse cx="330" cy="96" rx="300" ry="70" fill="{p.glow}" opacity="{0.10 if is_day else 0.16}"/>')
    # desk strip
    body.append(f'<rect x="0" y="120" width="{FW}" height="{FH - 120}" fill="url(#desk)"/>')
    body.append(f'<rect x="0" y="120" width="{FW}" height="3" fill="{p.edge}" opacity="0.8"/>')
    # scene
    # scene: keyboard + sleeping cat + mug + desk plant
    body.append(keyboard(p, 270, 108))
    body.append(cat(p, 330, 104))
    body.append(mug(p, 560, 150))
    body.append(plant("summer", 690, 150, 0.8))
    # caption
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FW} {FH}" width="{FW}" height="{FH}" '
            f'font-family="{FONT}">'
            f'<title>gujunyang — footer (the cat stays)</title>'
            + "".join(body)
            + f'<text x="60" y="62" font-size="20" font-weight="700" fill="{p.ink}">still running…</text>'
            + f'<text x="60" y="86" font-size="13" fill="{p.sub}">Still on the road · cat asleep · code still running</text>'
            + '</svg>\n')


# ---------------------------------------------------------------- main


def load_prev():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def main():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)

    season = os.environ.get("SCENE_SEASON") or None
    weather = os.environ.get("SCENE_WEATHER") or None

    prev = load_prev()
    temp = None
    is_day = 1
    try:
        cond, is_day, temp = fetch_weather()
    except Exception as exc:  # offline / rate-limited → keep the previous scene
        print(f"! weather fetch failed ({exc}); using previous state")
        cond = (prev or {}).get("condition", "clear")
        is_day = (prev or {}).get("is_day", 1)
    if not season:
        season = current_season(now)
    if not weather:
        weather = cond
    cond = weather

    if season not in SEASONS:
        season = current_season(now)
    if cond not in CONDITIONS:
        cond = "clouds"

    outputs = {
        "desk.svg": header(cond, season, True),
        "desk-night.svg": header(cond, season, False),
        "desk-footer.svg": footer(True),
        "desk-footer-night.svg": footer(False),
    }
    for name, svg in outputs.items():
        (ROOT / name).write_text(svg, encoding="utf-8")

    prev_state = prev or {}
    # note: no timestamp here — the state only changes when the scene does, so
    # the Action commits only on a real change (weather / season / day-night).
    state = {"condition": cond, "season": season, "is_day": is_day, "place": PLACE}
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = f"{season} {cond} {'day' if is_day else 'night'}" + (f" {temp}°C" if temp is not None else "")
    updated = now.strftime("%Y-%m-%d %H:%M")
    changed = any(prev_state.get(k) != state[k] for k in ("condition", "season", "is_day"))
    print(f"scene: {summary} (updated {updated}, changed={changed})")


if __name__ == "__main__":
    main()
