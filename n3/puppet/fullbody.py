"""Full-body puppet outfits (Ye 11/29): casual and Myanmar traditional. Drawn in the same head coordinates as puppet.py
(head centre 0,0, chin y=134). Feet reach y~1040."""
import math
import puppet as P

LN = "stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round' stroke-linecap='round'"
PAT = """<defs>
<pattern id='plaid' width='44' height='44' patternUnits='userSpaceOnUse'>
 <rect width='44' height='44' fill='#5b2d3a'/><rect width='44' height='12' y='16' fill='#7a3d4c'/><rect width='12' height='44' x='16' fill='#7a3d4c' opacity='.8'/>
 <rect width='44' height='3' y='21' fill='#d9b66b' opacity='.8'/><rect width='3' height='44' x='21' fill='#d9b66b' opacity='.6'/></pattern>
<pattern id='acheik' width='60' height='36' patternUnits='userSpaceOnUse'>
 <rect width='60' height='36' fill='#2f6f73'/>
 <path d='M 0 18 q 15 -14 30 0 t 30 0' stroke='#f2d27a' stroke-width='5' fill='none'/>
 <path d='M 0 30 q 15 -14 30 0 t 30 0' stroke='#e98aa0' stroke-width='3' fill='none'/>
 <path d='M 0 6 q 15 -14 30 0 t 30 0' stroke='#e98aa0' stroke-width='3' fill='none'/></pattern>
</defs>"""


def arm_down(c, side, sleeve, t, swing=0):
    sx = 122 * side
    a = math.sin(t * 2.2) * 3 + swing
    hx, hy = sx + 22 * side + a, 540
    d = "M %d 230 Q %d 400 %d %d" % (sx, sx + 26 * side, hx, hy)
    s = "<path d='%s' fill='none' %s stroke-width='50'/>" % (d, LN)
    s += "<path d='%s' fill='none' stroke='%s' stroke-width='43' stroke-linecap='round'/>" % (d, sleeve)
    s += "<circle cx='%d' cy='%d' r='23' fill='%s' %s/>" % (hx, hy, c["skin"], LN)
    return s


def legs(c, pants, shoe, t, step=0):
    s = ""
    for side in (-1, 1):
        lift = max(0, math.sin(step + (0 if side < 0 else math.pi))) * 30 if step else 0
        x = 55 * side
        s += "<rect x='%d' y='560' width='86' height='%d' rx='30' fill='%s' %s/>" % (x - 43, 430 - lift, pants, LN)
        s += "<ellipse cx='%d' cy='%d' rx='56' ry='26' fill='%s' %s/>" % (x + 10 * side, 1010 - lift, shoe, LN)
    return s


def outfit(c, style, t):
    k = c["kind"]; s = ""
    if style == "casual" and k == "rio":
        s += legs(c, "#3d5a80", "#f4f4f4", t)
        s += "<path d='M -150 590 C -150 300 -110 182 -40 160 L 40 160 C 110 182 150 300 150 590 Z' fill='%s' %s/>" % (c["cloth"], LN)
        s += "<path d='M -70 168 C -40 210 40 210 70 168 C 50 200 -50 200 -70 168 Z' fill='%s'/>" % c["cloth2"]
        s += "<path d='M -22 196 L -26 290 M 22 196 L 26 290' stroke='#f4f4f4' stroke-width='5' stroke-linecap='round'/>"
        s += "<path d='M -90 440 L 90 440 L 82 520 L -82 520 Z' fill='%s' opacity='.4'/>" % c["cloth2"]
        s += arm_down(c, -1, c["cloth"], t) + arm_down(c, 1, c["cloth"], t)
    elif style == "casual" and k == "mio":
        s += "<path d='M -150 520 L 150 520 L 190 980 L -190 980 Z' fill='#a9c8e8' %s/>" % LN            # long skirt
        for side in (-1, 1):
            s += "<ellipse cx='%d' cy='1010' rx='46' ry='22' fill='#f4f4f4' %s/>" % (60 * side, LN)
        s += "<path d='M -60 160 L 60 160 L 70 530 L -70 530 Z' fill='#fbfbfb' %s/>" % LN
        s += "<path d='M -140 540 C -140 260 -104 184 -46 162 L -8 250 L -20 540 Z' fill='%s' %s/>" % (c["cloth"], LN)
        s += "<path d='M 140 540 C 140 260 104 184 46 162 L 8 250 L 20 540 Z' fill='%s' %s/>" % (c["cloth"], LN)
        s += arm_down(c, -1, c["cloth"], t) + arm_down(c, 1, c["cloth"], t)
    elif style == "myanmar" and k == "rio":      # white taikpon jacket over shirt + plaid longyi with front knot, velvet slippers
        s += "<path d='M -120 455 L 120 455 L 138 1000 L -138 1000 Z' fill='url(#plaid)' %s/>" % LN
        s += "<path d='M -34 462 q 34 44 68 0 q -12 34 -34 58 q -22 -24 -34 -58 Z' fill='#7a3d4c' %s/>" % LN   # paso knot
        for side in (-1, 1):
            s += "<ellipse cx='%d' cy='1018' rx='50' ry='18' fill='#2a2a2a' %s/>" % (60 * side, LN)
        s += "<path d='M -140 470 C -140 290 -104 182 -40 160 L 40 160 C 104 182 140 290 140 470 Z' fill='#fbfaf5' %s/>" % LN
        s += "<path d='M 0 170 L 0 470' stroke='#d8d4c6' stroke-width='4'/>"
        for yy in (230, 300, 370, 435):
            s += "<circle cx='0' cy='%d' r='6' fill='#e0c36a' %s stroke-width='2'/>" % (yy, LN)
        s += "<path d='M -40 160 Q 0 185 40 160' fill='none' %s/>" % LN      # mandarin collar
        s += arm_down(c, -1, "#fbfaf5", t) + arm_down(c, 1, "#fbfaf5", t)
    elif style == "myanmar" and k == "mio":      # fitted yinphone blouse with side fastening + acheik htamein, sandals, padauk flowers
        s += "<path d='M -100 420 L 100 420 L 128 1005 L -128 1005 Z' fill='url(#acheik)' %s/>" % LN
        for side in (-1, 1):
            s += "<ellipse cx='%d' cy='1018' rx='40' ry='15' fill='#c9a36a' %s/>" % (45 * side, LN)
        s += "<path d='M -122 430 C -128 290 -100 182 -40 160 L 40 160 C 100 182 128 290 122 430 Z' fill='#f7c6d0' %s/>" % LN
        s += "<path d='M -40 165 Q 20 230 70 300 L 86 430' fill='none' stroke='#d58fa0' stroke-width='5'/>"
        for yy, xx in ((215, 18), (255, 44), (295, 66)):
            s += "<circle cx='%d' cy='%d' r='6' fill='#f2d27a' %s stroke-width='2'/>" % (xx, yy, LN)
        s += arm_down(c, -1, "#f7c6d0", t) + arm_down(c, 1, "#f7c6d0", t)
    s += "<rect x='-34' y='110' width='68' height='60' fill='%s' %s/>" % (c["skin"], LN)    # neck
    return s


def padauk(x, y):
    s = ""
    for k in range(7):
        a = k * 0.9
        s += "<circle cx='%.1f' cy='%.1f' r='9' fill='#f6c21c' stroke='#c9930a' stroke-width='2'/>" % (x + 18 * math.cos(a), y + 12 * math.sin(a))
    return s


def figure(c, style, x, y, sc, p, t=0.0):
    s = "<g transform='translate(%.1f %.1f) scale(%.3f)'>" % (x, y, sc)
    s += outfit(c, style, t)
    hd = P.head(c, p)
    if style == "myanmar" and c["kind"] == "mio":
        hd += padauk(-88, -96)
    s += "<g transform='rotate(%.2f 0 120)'>%s</g>" % (p.get("tilt", 0), hd)
    return s + "</g>"
