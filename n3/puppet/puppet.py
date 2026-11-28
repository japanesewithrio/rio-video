"""Puppet anime test (Ye 11/28): characters drawn in code (SVG parts), so every shot is the same character.
Mouth follows the voice loudness, eyes blink, head sways, brows react, laugh = closed happy eyes + shoulder bounce.
python n3/puppet/puppet.py  -> n3/puppet/out/puppet_test.mp4"""
import asyncio, math, os, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
FPS, SR = 30, 24000
W, H, BT, BH = 1080, 1920, 560, 608

RIO = dict(skin="#e9b994", shade="#d39b74", hair="#1d1e29", hair2="#3a3d52", iris1="#2b1a12", iris2="#7a5236",
           brow="#1d1e29", cloth="#cdd1d8", cloth2="#a9aeb8", kind="rio")
MIO = dict(skin="#fbe3d2", shade="#f0c4ad", hair="#6a4331", hair2="#93624a", iris1="#4a2a1c", iris2="#b0784f",
           brow="#5a3626", cloth="#f0e3c6", cloth2="#d7c6a2", kind="mio")


def eye(x, side, c, openv, happy, look):
    if happy > 0.5:     # ^ ^ laughing eyes
        return ("<path d='M %d 6 Q %d -18 %d 6' stroke='#2a1a14' stroke-width='7' fill='none' stroke-linecap='round'/>"
                % (x - 26, x, x + 26))
    o = max(0.06, openv)
    lx = look * 6
    g = "<g transform='translate(%d 0) scale(1 %.3f)'>" % (x, o)
    g += "<ellipse cx='0' cy='0' rx='27' ry='31' fill='#fff'/>"
    g += "<ellipse cx='%.1f' cy='3' rx='19' ry='25' fill='url(#ir_%s)'/>" % (lx, c["kind"])
    g += "<ellipse cx='%.1f' cy='5' rx='8' ry='11' fill='#140c0a'/>" % lx
    g += "<circle cx='%.1f' cy='-8' r='6.5' fill='#fff'/><circle cx='%.1f' cy='11' r='3' fill='#fff' opacity='.85'/>" % (lx - 7, lx + 7)
    g += "</g>"
    # upper lash line (thick) + small outer flick
    g += ("<path d='M %d %.1f Q %d %.1f %d %.1f' stroke='#1b1210' stroke-width='7' fill='none' stroke-linecap='round'/>"
          % (x - 30, -18 * o + 2, x, -36 * o, x + 30, -20 * o + 2))
    fl = 1 if side > 0 else -1
    g += "<path d='M %d %.1f l %d -8' stroke='#1b1210' stroke-width='5' stroke-linecap='round'/>" % (x + 30 * fl, -20 * o + 2, 8 * fl)
    return g


def mouth(openv, wide, smile, c):
    if openv < 0.08:
        d = 6 + 10 * smile
        return ("<path d='M -17 0 Q 0 %.1f 17 0' stroke='#7a3b32' stroke-width='5' fill='none' stroke-linecap='round'/>" % d)
    h = 8 + 34 * openv; w = 14 + 10 * wide + 6 * smile
    s = ("<path d='M %.1f 0 Q 0 %.1f %.1f 0 Q 0 %.1f %.1f 0 Z' fill='#7d2f30' stroke='#5a2020' stroke-width='3'/>"
         % (-w, -6 - 4 * smile, w, h * 1.25, -w))
    s += "<ellipse cx='0' cy='%.1f' rx='%.1f' ry='%.1f' fill='#e98a8a'/>" % (h * 0.75, w * 0.55, h * 0.28)
    return s


def head(c, p):
    k = c["kind"]
    s = ""
    # back hair
    if k == "mio":
        s += ("<path d='M -128 -60 C -150 -170 150 -170 128 -60 C 140 10 132 90 112 118 C 80 124 60 100 60 60 L -60 60 "
              "C -60 100 -80 124 -112 118 C -132 90 -140 10 -128 -60 Z' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["hair"])
    else:
        s += "<path d='M -118 -20 C -130 -160 130 -160 118 -20 L 104 10 L -104 10 Z' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["hair"]
    # ears + face
    s += "<ellipse cx='-104' cy='12' rx='16' ry='24' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/><ellipse cx='104' cy='12' rx='16' ry='24' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % (c["skin"], c["skin"])
    s += ("<path d='M -104 -40 C -106 -128 106 -128 104 -40 L 100 30 C 92 92 42 126 0 134 C -42 126 -92 92 -100 30 Z' "
          "fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["skin"])
    s += "<path d='M -100 30 C -92 92 -42 126 0 134 C -30 120 -70 96 -88 40 Z' fill='%s' opacity='.35'/>" % c["shade"]
    # blush
    b = 0.28 + 0.25 * p["blush"]
    s += "<ellipse cx='-62' cy='52' rx='22' ry='11' fill='#ff8f8f' opacity='%.2f'/><ellipse cx='62' cy='52' rx='22' ry='11' fill='#ff8f8f' opacity='%.2f'/>" % (b, b)
    # eyes, brows, nose, mouth
    s += eye(-50, -1, c, p["eye"], p["happy"], p["look"]) + eye(50, 1, c, p["eye"], p["happy"], p["look"])
    br = -60 - 10 * p["brow"]
    bw = 7 if k == "rio" else 5
    tilt = 6 * p.get("worry", 0)
    s += ("<path d='M -78 %.1f Q -52 %.1f -26 %.1f' stroke='%s' stroke-width='%d' fill='none' stroke-linecap='round'/>"
          % (br + 4 - tilt, br - 8, br + 2 + tilt, c["brow"], bw))
    s += ("<path d='M 26 %.1f Q 52 %.1f 78 %.1f' stroke='%s' stroke-width='%d' fill='none' stroke-linecap='round'/>"
          % (br + 2 + tilt, br - 8, br + 4 - tilt, c["brow"], bw))
    s += "<path d='M 4 34 l -5 9' stroke='%s' stroke-width='3' stroke-linecap='round'/>" % c["shade"]
    s += "<g transform='translate(0 78)'>%s</g>" % mouth(p["mouth"], p["wide"], p["smile"], c)
    # front hair
    if k == "mio":
        s += ("<path d='M -116 -40 C -120 -150 120 -150 116 -40 C 100 -70 70 -62 52 -84 C 40 -58 0 -60 -16 -88 "
              "C -30 -58 -80 -60 -116 -40 Z' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["hair"])
        s += "<path d='M -70 -104 C -40 -118 10 -120 40 -108' stroke='%s' stroke-width='9' fill='none' stroke-linecap='round' opacity='.75'/>" % c["hair2"]
        # flower clip
        fx, fy = 82, -96
        for a in range(5):
            ang = a * 72 * math.pi / 180
            s += "<ellipse cx='%.1f' cy='%.1f' rx='10' ry='7' fill='#fff' transform='rotate(%d %.1f %.1f)'/>" % (
                fx + 11 * math.cos(ang), fy + 11 * math.sin(ang), a * 72, fx + 11 * math.cos(ang), fy + 11 * math.sin(ang))
        s += "<circle cx='%d' cy='%d' r='6' fill='#f5c542'/>" % (fx, fy)
    else:
        fr = ("M -122 -10 C -130 -100 -90 -150 0 -152 C 90 -150 130 -100 122 -10 L 112 -30 C 108 -60 96 -66 88 -60 "
              "C 84 -80 70 -96 52 -92 C 50 -74 40 -62 30 -58 C 30 -80 18 -96 0 -100 C -6 -78 -18 -64 -30 -58 "
              "C -36 -82 -54 -96 -70 -92 C -70 -72 -80 -62 -92 -58 C -100 -66 -110 -50 -112 -30 Z")
        s += "<path d='%s' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % (fr, c["hair"])
        s += "<path d='M -60 -122 C -30 -136 20 -138 50 -124' stroke='%s' stroke-width='9' fill='none' stroke-linecap='round' opacity='.8'/>" % c["hair2"]
    if p.get("sweat"):
        s += "<path d='M 118 -50 q 10 18 0 26 q -10 -8 0 -26 Z' fill='#9fd8ff' stroke='#5aa9d6' stroke-width='2'/>"
    return s


def body(c):
    k = c["kind"]
    s = "<rect x='-34' y='110' width='68' height='60' fill='%s'/>" % c["skin"]
    s += "<path d='M -34 128 Q 0 150 34 128 L 34 150 L -34 150 Z' fill='%s' opacity='.5'/>" % c["shade"]
    if k == "rio":
        s += ("<path d='M -190 460 C -186 250 -120 182 -40 160 L 40 160 C 120 182 186 250 190 460 Z' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["cloth"])
        s += "<path d='M -70 168 C -40 210 40 210 70 168 C 50 200 -50 200 -70 168 Z' fill='%s'/>" % c["cloth2"]   # hood collar
        s += "<path d='M -22 196 L -26 290 M 22 196 L 26 290' stroke='#f4f4f4' stroke-width='5' stroke-linecap='round'/>"
        s += "<path d='M -120 330 L 120 330 L 110 420 L -110 420 Z' fill='%s' opacity='.35'/>" % c["cloth2"]       # pocket
    else:
        s += "<path d='M -60 160 L 60 160 L 70 460 L -70 460 Z' fill='#fbfbfb' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>"
        s += ("<path d='M -186 460 C -182 250 -118 184 -46 162 L -8 250 L -20 460 Z' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["cloth"])
        s += ("<path d='M 186 460 C 182 250 118 184 46 162 L 8 250 L 20 460 Z' fill='%s' stroke='#3b2a24' stroke-width='3.5' stroke-linejoin='round'/>" % c["cloth"])
        s += "<circle cx='-14' cy='300' r='5' fill='%s'/><circle cx='-16' cy='350' r='5' fill='%s'/>" % (c["cloth2"], c["cloth2"])
    return s


def char(c, x, y, sc, p, t):
    bob = math.sin(t * 2.1 + x) * 2.5 + p.get("bounce", 0)
    rot = p.get("tilt", 0) + math.sin(t * 0.9 + x) * 1.4
    s = "<g transform='translate(%.1f %.1f) scale(%.3f)'>" % (x, y + bob, sc)
    s += "<g transform='translate(0 %.1f)'>%s</g>" % (p.get("bounce", 0) * 0.6, body(c))
    s += "<g transform='rotate(%.2f 0 120) translate(0 %.1f)'>%s</g>" % (rot, p.get("nod", 0), head(c, p))
    s += "</g>"
    return s


DEFS = """<defs>
<radialGradient id='ir_rio' cx='50%%' cy='35%%' r='70%%'><stop offset='0' stop-color='%s'/><stop offset='1' stop-color='%s'/></radialGradient>
<radialGradient id='ir_mio' cx='50%%' cy='35%%' r='70%%'><stop offset='0' stop-color='%s'/><stop offset='1' stop-color='%s'/></radialGradient>
</defs>""" % (RIO["iris2"], RIO["iris1"], MIO["iris2"], MIO["iris1"])


def rms_env(path, n):
    w = wave.open(path); sr = w.getframerate()
    x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    hop = sr // FPS
    e = np.array([np.sqrt(np.mean(x[i * hop:(i + 1) * hop] ** 2)) if i * hop < len(x) else 0 for i in range(n)])
    e = e / (np.percentile(e[e > 0], 95) + 1e-6) if (e > 0).any() else e
    sm = np.convolve(e, [0.25, 0.5, 0.25], "same")
    return np.clip((sm - 0.12) / 0.75, 0, 1), x, sr


LINES = [  # (who, wav, jp, mm, shot)
    ("mio", "n3/gv/out/rm_04.wav", "ほら、入口《いりぐち》に機械《きかい》あるでしょ。あれで買《か》ってから座《すわ》るんだよ。",
     "ဟော… တံခါးဝမှာ စက်ရှိတယ်လေ။ အဲ့မှာ ဝယ်ပြီးမှ ထိုင်ရတာ။", "two"),
    ("rio", "n3/gv/out/rm_05.wav", "えっ、先《さき》に言《い》ってくれればいいのに！", "ဟာ… စောစောက ပြောပြပါလားကွာ!", "rio"),
    ("mio", "n3/gv/out/rm_06.wav", "だって、面白《おもしろ》そうだったから。", "ဘာလို့လဲဆို ရယ်ရမယ့်ပုံ ပေါက်နေလို့ 😆", "mio"),
]


def ruby(s):
    import re
    return re.sub(r"([一-龯々]+)《(.+?)》", r"<ruby>\1<rt>\2</rt></ruby>", s)


def plan():
    evs, t = [], 0.3
    for who, wav, jp, mm, shot in LINES:
        d = wave.open(os.path.join(ROOT, wav)).getnframes() / 24000
        evs.append(dict(who=who, wav=wav, jp=jp, mm=mm, shot=shot, st=t, d=d))
        t += d + 0.45
    return evs, t + 0.4


def frame_html(evs, t, env, bg):
    ev = next((e for e in reversed(evs) if e["st"] - 0.3 <= t), evs[0])
    lt = t - ev["st"]
    i = int(round(t * FPS))
    def params(who):
        talking = ev["who"] == who and 0 <= lt <= ev["d"]
        m = env[who][i] if talking else 0.0
        blink_t = (t + (0.0 if who == "rio" else 1.3)) % 3.7
        eyev = 1.0 if blink_t > 0.14 else abs(blink_t - 0.07) / 0.07
        p = dict(mouth=m, wide=0.5 + 0.5 * math.sin(i * 0.9), smile=0.4, eye=eyev, happy=0, look=0, brow=0, blush=0, nod=0, tilt=0)
        if who == "mio":
            p["smile"] = 0.8; p["look"] = -0.6 if ev["shot"] == "two" else 0
        if who == "rio":
            p["look"] = 0.6 if ev["shot"] == "two" else 0
        if ev["shot"] == "rio" and who == "rio":            # complaining: raised worried brows, sweat
            p.update(brow=0.8 + 0.3 * m, worry=1, smile=0, sweat=True, tilt=-4)
        if ev["shot"] == "mio" and who == "mio":            # laughing
            p.update(happy=1, smile=1, blush=1, bounce=abs(math.sin(t * 9)) * 6 * (1 if lt > 0.1 else 0), tilt=5)
            p["mouth"] = max(p["mouth"], 0.35)
        if talking and m > 0.6:
            p["nod"] = 3
        return p
    if ev["shot"] == "two":
        chars = char(RIO, 330, 250, 0.95, params("rio"), t) + char(MIO, 750, 262, 0.92, params("mio"), t)
        zoom = 1.0 + 0.02 * lt
    elif ev["shot"] == "rio":
        chars = char(RIO, 540, 300, 1.3, params("rio"), t); zoom = 1.0 + 0.015 * lt
    else:
        chars = char(MIO, 540, 305, 1.27, params("mio"), t); zoom = 1.0 + 0.015 * lt
    counter = ("<rect x='-50' y='540' width='1180' height='80' fill='#b07a4a'/><rect x='-50' y='534' width='1180' height='14' fill='#d39a63'/>"
               if ev["shot"] == "two" else "")
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='608' viewBox='0 0 1080 608'>%s"
           "<g transform='translate(540 304) scale(%.4f) translate(-540 -304)'>%s%s</g></svg>" % (DEFS, zoom, chars, counter))
    show = 0 <= lt <= ev["d"] + 0.45
    sub = ""
    if show:
        n = len(ev["jp"]) - ev["jp"].count("《") * 3
        px = 66 if n <= 16 else max(int(66 * 16 / n), 44)
        sub = ("<div class='ej'><div class='m2'>%s</div><div class='j2' style='font-size:%dpx'>%s</div></div>"
               % (ev["mm"], px, ruby(ev["jp"])))
    F = os.path.join(ROOT, "fonts")
    return ("""<html><head><meta charset='utf-8'><style>
@font-face{font-family:Round;src:url('file://%s/MPLUSRounded1c-Bold.ttf')}
@font-face{font-family:My;src:url('file://%s/NotoSansMyanmar.ttf')}
body{margin:0;width:1080px;height:1920px;background:#111;overflow:hidden}
.band{position:absolute;top:%dpx;left:0;width:1080px;height:%dpx;overflow:hidden}
.band img{position:absolute;left:0;top:0;width:1080px;height:%dpx;object-fit:cover}
.band svg{position:absolute;left:0;top:0}
.hook{position:absolute;top:200px;left:40px;right:40px;text-align:center;font-family:My,Round;color:#fff;font-size:46px;line-height:1.5}
.ej{position:absolute;left:30px;right:30px;top:%dpx;text-align:center}
.m2{font-family:My;font-size:42px;color:#fff;line-height:1.6;text-shadow:0 0 6px #000,2px 2px 0 #000}
.j2{font-family:Round;color:#fff;line-height:1.45;margin-top:18px;-webkit-text-stroke:10px #000;paint-order:stroke fill}
.j2 rt{font-size:.45em;color:#ffe08a;-webkit-text-stroke:5px #000}
</style></head><body><div class='hook'>🧪 puppet anime test</div>
<div class='band'><img src='file://%s'>%s</div>%s</body></html>"""
            % (F, F, BT, BH, BH, BT + BH + 50, bg, svg, sub))


async def shoot(evs, total, env, bg, tmp):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": W, "height": H})
        f = os.path.join(tmp, "f.html")
        for i in range(int(total * FPS)):
            open(f, "w", encoding="utf-8").write(frame_html(evs, i / FPS, env, bg))
            await pg.goto("file://" + f)
            if i == 0:
                await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, "%05d.jpg" % i), type="jpeg", quality=90)
        await b.close()


def main():
    evs, total = plan()
    n = int(total * FPS) + 2
    env = {"rio": np.zeros(n), "mio": np.zeros(n)}
    mix = np.zeros(int(total * SR) + SR, np.float32)
    for e in evs:
        en, x, sr = rms_env(os.path.join(ROOT, e["wav"]), int(e["d"] * FPS) + 2)
        a = int(e["st"] * FPS); env[e["who"]][a:a + len(en)] = en[:n - a]
        i = int(e["st"] * SR); mix[i:i + len(x)] += x[:len(mix) - i]
    tmp = tempfile.mkdtemp()
    bg = os.path.join(tmp, "bg.jpg")      # shop seen from the kitchen, softly blurred (depth of field)
    im = Image.open(os.path.join(ROOT, "n3/cartoon/assets/rm_bg_seats.png")).convert("RGB")
    w, h = im.size
    im.crop((0, int(h * 0.12), int(w * 0.6), int(h * 0.12 + w * 0.6 * 608 / 1080))).resize((1080, 608)).filter(ImageFilter.GaussianBlur(5)).save(bg, quality=92)
    asyncio.run(shoot(evs, total, env, bg, tmp))
    wv = os.path.join(tmp, "a.wav")
    with wave.open(wv, "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out = os.path.join(HERE, "out", "puppet_test.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%05d.jpg"), "-i", wv,
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], check=True)
    print(out, total)


if __name__ == "__main__":
    main()
