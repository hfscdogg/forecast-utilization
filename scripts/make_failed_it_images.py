"""
Generate the staged "Failed it" banner illustrations for the Utilization
Actuals email (see nailed_it.py / FAILED_IT_IMAGE_IDS).

Original flat illustrations in Livewire colors, never real customer jobs.
Writes 1200x600 SVGs to assets/failed_it/. Render to JPEG with
scripts/render_failed_it_images.js.

    python3 scripts/make_failed_it_images.py
"""

import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "failed_it"
W, H = 1200, 600

INK = "#1A1A1A"
INK_SOFT = "#3A3A33"
GREY = "#85857A"
GREY_LT = "#B0B0A4"
WALL = "#ECE6D9"
WALL_DK = "#DFD7C5"
FLOOR = "#C9BFA8"
BONE = "#FAF8F2"
COPPER = "#F7941D"
COPPER_DK = "#D46C13"
CABLE_COLORS = ["#2F6FDE", "#E2412F", "#F7C21D", "#3BAA5C", "#F7941D", "#8E44AD",
                "#FAF8F2", "#1A1A1A", "#14A3B8", "#E86FA0"]


def svg(body, bg=WALL):
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' "
            f"viewBox='0 0 {W} {H}'><rect width='{W}' height='{H}' fill='{bg}'/>"
            f"{body}</svg>")


def floor(y=520):
    return (f"<rect x='0' y='{y}' width='{W}' height='{H - y}' fill='{FLOOR}'/>"
            f"<rect x='0' y='{y}' width='{W}' height='6' fill='{WALL_DK}'/>")


def spaghetti(rng, n, x0, y0, x1, y1, width=(5, 9)):
    """Random tangled bezier cables inside a box."""
    out = []
    for _ in range(n):
        pts = [(rng.uniform(x0, x1), rng.uniform(y0, y1)) for _ in range(4)]
        c = rng.choice(CABLE_COLORS)
        w = rng.uniform(*width)
        d = (f"M{pts[0][0]:.0f},{pts[0][1]:.0f} C{pts[1][0]:.0f},{pts[1][1]:.0f} "
             f"{pts[2][0]:.0f},{pts[2][1]:.0f} {pts[3][0]:.0f},{pts[3][1]:.0f}")
        out.append(f"<path d='{d}' stroke='{INK}' stroke-width='{w + 3:.1f}' fill='none' "
                   f"stroke-linecap='round' opacity='0.25'/>"
                   f"<path d='{d}' stroke='{c}' stroke-width='{w:.1f}' fill='none' "
                   f"stroke-linecap='round'/>")
    return "".join(out)


# 1. Rat's-nest network rack -------------------------------------------------

def rats_nest():
    rng = random.Random(7)
    body = floor()
    rx, ry, rw, rh = 430, 70, 340, 450
    body += f"<rect x='{rx - 14}' y='{ry - 14}' width='{rw + 28}' height='{rh + 28}' rx='10' fill='{INK}'/>"
    body += f"<rect x='{rx}' y='{ry}' width='{rw}' height='{rh}' fill='{INK_SOFT}'/>"
    # rack units: switches with ports
    for i in range(7):
        uy = ry + 20 + i * 60
        body += f"<rect x='{rx + 16}' y='{uy}' width='{rw - 32}' height='42' rx='4' fill='#2A2A24'/>"
        for p in range(12):
            px = rx + 34 + p * 23
            body += f"<rect x='{px}' y='{uy + 13}' width='14' height='14' rx='2' fill='{GREY}'/>"
            if rng.random() < 0.6:
                body += f"<circle cx='{px + 7}' cy='{uy + 6}' r='2.5' fill='#3BAA5C'/>"
    # the nest: in front of the rack and spilling everywhere
    body += spaghetti(rng, 70, rx - 40, ry + 10, rx + rw + 40, ry + rh + 20)
    body += spaghetti(rng, 25, rx - 160, ry + 300, rx + rw + 160, 590, width=(4, 7))
    # a few loose cables dangling to the floor
    for _ in range(9):
        x = rng.uniform(rx + 20, rx + rw - 20)
        c = rng.choice(CABLE_COLORS)
        body += (f"<path d='M{x:.0f},{ry + rh - 30} Q{x + rng.uniform(-80, 80):.0f},{ry + rh + 60} "
                 f"{x + rng.uniform(-160, 160):.0f},585' stroke='{c}' stroke-width='6' fill='none' "
                 f"stroke-linecap='round'/>")
    # zip tie bag, unopened, on the floor
    body += (f"<g transform='translate(860 470) rotate(-8)'><rect width='150' height='70' rx='8' "
             f"fill='{BONE}' stroke='{GREY}' stroke-width='3'/><text x='75' y='44' font-family='Arial, sans-serif' "
             f"font-size='20' font-weight='700' fill='{INK}' text-anchor='middle'>ZIP TIES</text>"
             f"<rect x='8' y='6' width='134' height='8' fill='{COPPER}'/></g>")
    return svg(body)


# 2. Crooked TV mount ---------------------------------------------------------

def crooked_tv():
    body = floor(540)
    # straight picture frame for contrast
    body += (f"<rect x='90' y='150' width='170' height='130' fill='{BONE}' stroke='{INK}' stroke-width='10'/>"
             f"<path d='M110,260 L160,200 L195,240 L215,220 L245,260 Z' fill='{GREY_LT}'/>"
             f"<circle cx='215' cy='190' r='14' fill='{COPPER}'/>")
    # crooked TV
    body += (f"<g transform='rotate(-9 640 270)'>"
             f"<rect x='380' y='120' width='520' height='300' rx='10' fill='{INK}'/>"
             f"<rect x='396' y='136' width='488' height='268' fill='#24303A'/>"
             f"<path d='M396,136 L560,136 L470,404 L396,404 Z' fill='#FFFFFF' opacity='0.06'/>"
             f"</g>")
    # extra screw holes from earlier attempts
    for x, y in [(470, 455), (505, 470), (790, 95), (830, 108), (865, 92), (455, 480), (900, 130)]:
        body += f"<circle cx='{x}' cy='{y}' r='6' fill='{INK_SOFT}'/><circle cx='{x}' cy='{y}' r='9' fill='none' stroke='{WALL_DK}' stroke-width='3'/>"
    # visible cords hanging below
    body += (f"<path d='M600,440 C590,480 640,500 620,540' stroke='{INK}' stroke-width='7' fill='none'/>"
             f"<path d='M640,436 C660,490 600,500 650,540' stroke='{BONE}' stroke-width='7' fill='none'/>"
             f"<path d='M680,432 C700,470 720,500 700,540' stroke='{INK_SOFT}' stroke-width='7' fill='none'/>")
    # level held against it, bubble pinned to one end
    body += (f"<g transform='rotate(-9 640 470)'>"
             f"<rect x='470' y='452' width='340' height='40' rx='6' fill='{COPPER}'/>"
             f"<rect x='610' y='460' width='70' height='24' rx='12' fill='#D9F2B4' stroke='{INK}' stroke-width='3'/>"
             f"<line x1='635' y1='460' x2='635' y2='484' stroke='{INK}' stroke-width='2'/>"
             f"<line x1='655' y1='460' x2='655' y2='484' stroke='{INK}' stroke-width='2'/>"
             f"<circle cx='668' cy='472' r='8' fill='#FFFFFF'/></g>")
    return svg(body)


# 3. Switch plates at random heights ------------------------------------------

def switch_plates():
    rng = random.Random(3)
    body = floor(540)
    # doorway on the left
    body += (f"<rect x='60' y='90' width='230' height='450' fill='{WALL_DK}'/>"
             f"<rect x='75' y='105' width='200' height='435' fill='#B39B78'/>"
             f"<circle cx='250' cy='330' r='10' fill='{COPPER}'/>")
    # a row of plates that should line up and don't
    base_y = 250
    for i in range(6):
        x = 380 + i * 125
        y = base_y + rng.choice([-70, -40, -15, 10, 35, 60])
        a = rng.choice([-14, -8, -4, 0, 6, 11, 17])
        gangs = rng.choice([1, 1, 2])
        pw = 70 + (gangs - 1) * 44
        body += f"<g transform='rotate({a} {x + pw / 2} {y + 55})'>"
        body += f"<rect x='{x}' y='{y}' width='{pw}' height='110' rx='8' fill='{BONE}' stroke='{GREY}' stroke-width='3'/>"
        for g in range(gangs):
            gx = x + 22 + g * 44
            body += f"<rect x='{gx}' y='{y + 30}' width='26' height='50' rx='4' fill='{GREY_LT}' stroke='{GREY}' stroke-width='2'/>"
        body += f"<circle cx='{x + pw / 2}' cy='{y + 14}' r='3' fill='{GREY}'/><circle cx='{x + pw / 2}' cy='{y + 96}' r='3' fill='{GREY}'/>"
        body += "</g>"
    # the chalk line everyone ignored
    body += (f"<line x1='360' y1='{base_y + 55}' x2='1150' y2='{base_y + 55}' stroke='{COPPER}' "
             f"stroke-width='3' stroke-dasharray='14 10' opacity='0.9'/>")
    # one plate missing entirely: open box with wires
    body += (f"<rect x='1080' y='400' width='60' height='90' fill='{INK_SOFT}'/>"
             f"<path d='M1095,420 q-30,40 -10,80' stroke='#E2412F' stroke-width='5' fill='none'/>"
             f"<path d='M1115,420 q20,50 -5,85' stroke='{INK}' stroke-width='5' fill='none'/>"
             f"<path d='M1125,425 q35,30 15,75' stroke='{BONE}' stroke-width='5' fill='none'/>")
    return svg(body)


# 4. Ceiling speakers and extra holes -----------------------------------------

def ceiling_holes():
    rng = random.Random(11)
    body = ""
    # ceiling seen from below, with a light grid of drywall seams
    body += f"<rect width='{W}' height='{H}' fill='#F1ECE2'/>"
    for x in (300, 600, 900):
        body += f"<line x1='{x}' y1='0' x2='{x}' y2='{H}' stroke='{WALL_DK}' stroke-width='3'/>"
    # the speakers: different sizes, not in a line
    for cx, cy, r in [(250, 220, 78), (560, 330, 62), (870, 190, 88), (1010, 440, 54)]:
        body += (f"<circle cx='{cx}' cy='{cy}' r='{r + 10}' fill='{BONE}' stroke='{GREY_LT}' stroke-width='3'/>"
                 f"<circle cx='{cx}' cy='{cy}' r='{r}' fill='{GREY_LT}'/>")
        for k in range(0, r, 9):
            body += f"<circle cx='{cx}' cy='{cy}' r='{k}' fill='none' stroke='{GREY}' stroke-width='1.2' opacity='0.5'/>"
    # abandoned holes, some patched badly
    for _ in range(9):
        cx, cy, r = rng.uniform(80, 1120), rng.uniform(60, 560), rng.uniform(22, 48)
        if rng.random() < 0.5:
            body += f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='{r:.0f}' fill='{INK}'/>"
        else:
            body += (f"<rect x='{cx - r * 1.3:.0f}' y='{cy - r * 1.2:.0f}' width='{r * 2.6:.0f}' height='{r * 2.4:.0f}' "
                     f"fill='#FFFFFF' stroke='{WALL_DK}' stroke-width='6' transform='rotate({rng.uniform(-20, 20):.0f} {cx:.0f} {cy:.0f})'/>")
    # a crack and a cable poking out of one hole
    body += (f"<path d='M640,40 l25,60 l-30,50 l40,70 l-15,60' stroke='{GREY}' stroke-width='3' fill='none'/>"
             f"<path d='M420,470 c40,-30 80,40 130,0 s60,40 90,20' stroke='{COPPER}' stroke-width='8' fill='none' stroke-linecap='round'/>")
    return svg(body, bg="#F1ECE2")


# 5. Power strip daisy chain --------------------------------------------------

def daisy_chain():
    body = floor(450)
    def strip(x, y, a):
        g = f"<g transform='rotate({a} {x + 110} {y + 22})'>"
        g += f"<rect x='{x}' y='{y}' width='220' height='44' rx='10' fill='{BONE}' stroke='{GREY}' stroke-width='3'/>"
        for i in range(5):
            ox = x + 20 + i * 38
            g += (f"<rect x='{ox}' y='{y + 12}' width='24' height='20' rx='4' fill='{GREY_LT}'/>"
                  f"<rect x='{ox + 6}' y='{y + 16}' width='3' height='9' fill='{INK}'/>"
                  f"<rect x='{ox + 15}' y='{y + 16}' width='3' height='9' fill='{INK}'/>")
        g += f"<rect x='{x + 196}' y='{y + 14}' width='16' height='16' rx='3' fill='#E2412F'/>"
        return g + "</g>"
    # wall outlet
    body += (f"<rect x='60' y='300' width='80' height='120' rx='8' fill='{BONE}' stroke='{GREY}' stroke-width='3'/>"
             f"<rect x='86' y='322' width='28' height='30' rx='6' fill='{GREY_LT}'/>"
             f"<rect x='86' y='368' width='28' height='30' rx='6' fill='{GREY_LT}'/>")
    strips = [(180, 470, -4), (450, 500, 6), (700, 460, -10), (930, 515, 3)]
    prev = (100, 337)
    for (x, y, a) in strips:
        body += (f"<path d='M{prev[0]},{prev[1]} C{prev[0] + 60},{prev[1] + 120} {x - 60},{y - 40} {x + 10},{y + 22}' "
                 f"stroke='{INK}' stroke-width='9' fill='none' stroke-linecap='round'/>")
        body += strip(x, y, a)
        prev = (x + 200, y + 10)
    # every outlet used, plugs everywhere going up and off frame
    rng = random.Random(5)
    for (x, y, a) in strips:
        for i in range(5):
            px = x + 32 + i * 38
            c = rng.choice([INK, INK_SOFT, BONE, GREY])
            body += (f"<rect x='{px - 12}' y='{y - 26}' width='24' height='30' rx='4' fill='{c}' stroke='{INK}' stroke-width='2'/>"
                     f"<path d='M{px},{y - 26} C{px + rng.uniform(-40, 40):.0f},{y - 140} "
                     f"{px + rng.uniform(-200, 200):.0f},{y - 260} {px + rng.uniform(-300, 300):.0f},-10' "
                     f"stroke='{c}' stroke-width='6' fill='none'/>")
    # a little smoke curl over the last strip
    body += (f"<path d='M1050,480 c-20,-30 20,-50 0,-80 s20,-50 0,-80' stroke='{GREY_LT}' stroke-width='10' "
             f"fill='none' stroke-linecap='round' opacity='0.8'/>")
    return svg(body)


# 6. Labels that don't help ---------------------------------------------------

def bad_labels():
    rng = random.Random(9)
    body = floor(560)
    # patch panel
    body += f"<rect x='120' y='130' width='960' height='120' rx='8' fill='{INK}'/>"
    for i in range(24):
        px = 150 + i * 38
        body += f"<rect x='{px}' y='175' width='26' height='22' rx='3' fill='{GREY}'/>"
    labels = ["CABLE", "?", "THIS ONE", "OLD", "DONT", "idk", "NEW?", "MAYBE TV", "??", "BOB", "X", "GOOD ONE"]
    for i, lab in enumerate(labels):
        px = 150 + i * 2 * 38 + 13
        c = rng.choice(CABLE_COLORS[:6])
        sway = rng.uniform(-70, 70)
        end_y = rng.uniform(380, 520)
        body += (f"<path d='M{px},197 C{px},300 {px + sway:.0f},320 {px + sway * 1.2:.0f},{end_y:.0f}' "
                 f"stroke='{c}' stroke-width='9' fill='none' stroke-linecap='round'/>")
        # Alternate tag rows so neighbouring tags don't overlap.
        tx, ty = px + sway * 0.3, 290 + (i % 2) * 85
        tw = 22 + len(lab) * 13
        a = rng.uniform(-14, 14)
        body += (f"<g transform='rotate({a:.0f} {tx:.0f} {ty:.0f})'>"
                 f"<rect x='{tx - tw / 2:.0f}' y='{ty - 18:.0f}' width='{tw}' height='36' rx='4' fill='{BONE}' stroke='{GREY}' stroke-width='2'/>"
                 f"<text x='{tx:.0f}' y='{ty + 7:.0f}' font-family='Comic Sans MS, Marker Felt, cursive' font-size='20' "
                 f"font-weight='700' fill='{INK}' text-anchor='middle'>{lab}</text></g>")
    # a strip of masking tape on the panel reading "LABEL LATER"
    body += (f"<g transform='rotate(-3 600 95)'><rect x='470' y='72' width='260' height='42' fill='#F3E3B5'/>"
             f"<text x='600' y='102' font-family='Comic Sans MS, Marker Felt, cursive' font-size='24' "
             f"font-weight='700' fill='{COPPER_DK}' text-anchor='middle'>LABEL LATER</text></g>")
    return svg(body)


SCENES = {
    "failed_it_01_rats_nest": rats_nest,
    "failed_it_02_crooked_tv": crooked_tv,
    "failed_it_03_switch_plates": switch_plates,
    "failed_it_04_ceiling_holes": ceiling_holes,
    "failed_it_05_daisy_chain": daisy_chain,
    "failed_it_06_bad_labels": bad_labels,
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in SCENES.items():
        (OUT / f"{name}.svg").write_text(fn())
        print(OUT / f"{name}.svg")
