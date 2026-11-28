"""Puppet anime episode (Ye 11/28): code-drawn Rio & Mio, voice-driven mouths, scripted emotions.
python n3/puppet/ep.py -> n3/puppet/out/puppet_ep1.mp4"""
import asyncio, math, os, re, subprocess, tempfile, wave
import numpy as np
from PIL import Image, ImageFilter
import puppet as P
import fullbody as FB

ROOT, HERE, FPS, SR = P.ROOT, P.HERE, 30, 24000
A = os.path.join(ROOT, "n3/cartoon/assets")
V = os.path.join(ROOT, "n3/gv/out")

HOOK = "ဂျပန်မှာ「月が綺麗ですね」ဆိုတာ<br>တကယ်က ဘာကိုဆိုလိုလဲ သိလား? 🌕"
# who, voice, inner?, shot, jp, mm, expressions {rio:{}, mio:{}} (start) , end-expressions, extra
EP = [
    dict(shot="moon", dur=2.2, mm="ညဘက်… မြစ်ကမ်းနားမှာ 🌙", sfx="twinkle"),
    dict(who="rio", v="pp_01", inner=1, shot="rio", jp="（心《こころ》の声《こえ》）今日《きょう》こそ……言《い》うぞ。",
         mm="(စိတ်ထဲက) ဒီနေ့တော့… ပြောကို ပြောမယ်။", ex={"rio": dict(blush=.6, brow=.2, smile=0, eye=1.05)}),
    dict(who="mio", v="pp_02", shot="two", jp="リオくん、どうしたの？ 顔《かお》、赤《あか》いよ。",
         mm="Rio… ဘာဖြစ်လို့လဲ? မျက်နှာ နီနေတယ်။",
         ex={"rio": dict(blush=1, look=-.2, smile=.1), "mio": dict(worry=.6, brow=.4, look=-.7, tilt=-4, smile=.3)}),
    dict(who="rio", v="pp_03", shot="rio", jp="え、えっと……ミオさん。[月《つき》が、綺麗《きれい》ですね]。",
         mm="အ… ဟို… Mio ရေ… လက… လှလိုက်တာနော်။", ex={"rio": dict(blush=1, sweat=1, look=.5, smile=.2)},
         end={"rio": dict(look=0, smile=.5)}),
    dict(who="mio", v="pp_04", shot="mio", jp="ほんとだ！ まんまるだね〜。", mm="ဟုတ်သားပဲ! ဝိုင်းစက်နေတာပဲ 🌕",
         ex={"mio": dict(lookup=1, smile=1, eye=1.1, tilt=4)}),
    dict(who="rio", v="pp_05", inner=1, shot="rio", jp="（心《こころ》の声《こえ》）……伝《つた》わってない！",
         mm="(စိတ်ထဲက) …နားမလည်ဘူး!", sfx="don",
         ex={"rio": dict(eye=1.25, brow=1, worry=1, wavy=1, sweat=1, blush=.4, shake=1)}),
    dict(who="rio", v="pp_06", shot="two", jp="い、いや、[そうじゃなくて]……ずっと前《まえ》から、その……",
         mm="မ… မဟုတ်ဘူး… ဟိုးအရင်ကတည်းက… အဲ့ဒါ…",
         ex={"rio": dict(blush=1, worry=.8, brow=.6, look=.6, sweat=1, tilt=3), "mio": dict(look=-.6, smile=.4, tilt=-3)}),
    dict(who="mio", v="pp_07", shot="mio", jp="うん？", mm="အင်း?", ex={"mio": dict(tilt=-9, brow=.5, smile=.4, look=-.3)}),
    dict(who="rio", v="pp_08", shot="rio", jp="……す、すき……", mm="…ချ… ချစ်…",
         ex={"rio": dict(blush=1.4, shut=1, worry=.6, brow=.5, tilt=-3)}, post=.3),
    dict(who="mio", v="pp_09", shot="mio", jp="[すき焼《や》き]？ いいね！ 今度《こんど》一緒《いっしょ》に食《た》べに行《い》こう！",
         mm="Sukiyaki လား? ကောင်းသားပဲ! နောက်တစ်ခါ အတူတူ သွားစားရအောင်! 🍲", ex={"mio": dict(happy=1, smile=1, blush=.5, bounce=1)}),
    dict(who="rio", v="pp_10", inner=1, shot="rio", jp="（心《こころ》の声《こえ》）……すき焼《や》きじゃない……。",
         mm="(စိတ်ထဲက) …Sukiyaki မဟုတ်ဘူးကွာ…", sfx="fall", ex={"rio": dict(droop=1, eye=.8, lookup=-.8, worry=1, brow=.3, nod=10, wavy=1, smile=0)}, post=.4),
    dict(who="mio", v="pp_11", shot="mio", jp="……でも、月《つき》、ほんとに綺麗《きれい》だね。",
         mm="…ဒါပေမဲ့ လက တကယ် လှတယ်နော်။", ex={"mio": dict(eye=.95, lookup=-.6, look=-.3, blush=1.1, smile=.8, tilt=-5)},
         end={"mio": dict(look=-.8, lookup=-.2, eye=1)}),
    dict(who="rio", v="pp_12", shot="rio", jp="……うん。", mm="…အင်း။", ex={"rio": dict(eye=1.2, brow=.8, blush=.6, smile=0)},
         end={"rio": dict(eye=.9, brow=0, blush=1.2, smile=1)}, post=.5),
    dict(shot="two_up", dur=3.0, mm="", ex={"rio": dict(lookup=1, smile=.9, blush=1), "mio": dict(lookup=1, smile=.9, blush=1)}),
]
RECAP = ("月《つき》が綺麗《きれい》ですね",
         [("月が綺麗ですね", "\"ချစ်တယ်\" ကို ကဗျာဆန်ဆန် ပြောတဲ့နည်း 🌕"),
          ("今日《きょう》こそ", "ဒီနေ့တော့ သေချာပေါက်"),
          ("〜じゃなくて", "…မဟုတ်ဘဲ"),
          ("食《た》べに行《い》こう", "သွားစားရအောင်")])


OUT = "puppet_ep1.mp4"
MUSIC = "n3/snd/out/bgm_wholesome.mp3"
SWAY = 0
AMB = None
TABLE = False
FULL = None          # e.g. {"rio": "myanmar", "mio": "myanmar"}: full-body figures
LEFT_ARM = {"wave", "clap"}
RIGHT_ARM = {"fan", "glass", "spoon", "scratch", "facepalm", "thumb", "point_self", "phone_ear", "shh", "phone_out", "clap", "point"}
BG = {"two": ("pp_bg_night.png", 4), "cu": ("pp_bg_night.png", 9), "moon": "pp_moon.png"}
LN = "stroke='#3b2a24' stroke-linejoin='round' stroke-linecap='round'"

SLEEVE = {("rio", "myanmar"): "#2c3550", ("mio", "myanmar"): "#f7c6d0"}
def arm(c, sh, el, hd, front=False, fist=None, osc=0):
    """sleeve from shoulder (sh) via elbow (el) to hand (hd); hand drawn on top."""
    cl = SLEEVE.get((c["kind"], (FULL or {}).get(c["kind"])), c["cloth"])
    hx, hy = hd[0], hd[1] + osc
    d = "M %d %d Q %d %d %d %d" % (sh[0], sh[1], el[0], el[1], hx, hy)
    s = "<path d='%s' fill='none' %s stroke-width='60'/>" % (d, LN)
    s += "<path d='%s' fill='none' stroke='%s' stroke-width='53' stroke-linecap='round'/>" % (d, cl)
    s += "<circle cx='%d' cy='%d' r='27' fill='%s' %s stroke-width='3.5'/>" % (hx, hy, c["skin"], LN)
    if fist == "thumb":
        s += "<rect x='%d' y='%d' width='16' height='34' rx='8' fill='%s' %s stroke-width='3.5'/>" % (hx - 8, hy - 52, c["skin"], LN)
    if fist == "point":
        s += "<rect x='%d' y='%d' width='40' height='14' rx='7' fill='%s' %s stroke-width='3'/>" % (hx - 54, hy - 10, c["skin"], LN)
    if fist == "palm":
        for k in range(4):
            s += "<rect x='%d' y='%d' width='13' height='40' rx='6' fill='%s' %s stroke-width='3'/>" % (hx - 28 + k * 14, hy - 56, c["skin"], LN)
    return s

def arms(c, pose, t):
    o = math.sin(t * 14) * 10
    if pose == "scratch":      # hand scratching the side of the head
        return arm(c, (150, 230), (250, 120), (118, -70), osc=o)
    if pose == "facepalm":     # hand over the eyes
        return arm(c, (150, 230), (170, 140), (20, -5), fist="palm")
    if pose == "thumb":
        return arm(c, (150, 230), (215, 320), (110, 170), fist="thumb")
    if pose == "point_self":
        return arm(c, (150, 230), (170, 380), (50, 290), fist="point")
    if pose == "wave":
        return arm(c, (-150, 230), (-240, 150), (-210, 10), fist="palm", osc=o * .6)
    if pose == "fan":          # fanning the mouth (too spicy!)
        o2 = math.sin(t * 26) * 22
        return arm(c, (150, 230), (220, 230), (70 + o2, 90), fist="palm")
    if pose == "glass":        # holding out a glass of water
        a = arm(c, (150, 230), (230, 300), (180, 210))
        return a + ("<rect x='150' y='120' width='54' height='80' rx='8' fill='#cfe9ff' opacity='.9' %s stroke-width='3'/>"
                    "<rect x='154' y='150' width='46' height='46' rx='6' fill='#8fc8f5' opacity='.8'/>" % LN) + \
            "<circle cx='180' cy='210' r='27' fill='%s' %s stroke-width='3.5'/>" % (c["skin"], LN)
    if pose == "spoon":        # spoon up to the mouth
        a = arm(c, (150, 230), (200, 300), (60, 150))
        return a + "<path d='M 60 150 L 14 92' stroke='#b9bfc8' stroke-width='9' stroke-linecap='round'/><ellipse cx='10' cy='86' rx='16' ry='11' fill='#d7dce3' %s stroke-width='2'/>" % LN + \
            "<circle cx='60' cy='150' r='27' fill='%s' %s stroke-width='3.5'/>" % (c["skin"], LN)
    if pose == "point":        # pointing toward the viewer / the other person
        return arm(c, (150, 230), (230, 250), (190, 140), fist="point")
    if pose == "phone_ear":    # holding a phone to the right ear
        a = arm(c, (150, 230), (215, 170), (112, 20))
        return a + "<rect x='92' y='-62' width='34' height='70' rx='8' fill='#2f3440' %s stroke-width='3'/>" % LN + \
            "<circle cx='%d' cy='%d' r='27' fill='%s' %s stroke-width='3.5'/>" % (112, 20, c["skin"], LN)
    if pose == "shh":          # index finger on the lips
        a = arm(c, (150, 230), (150, 230), (24, 150))
        return a + "<rect x='14' y='62' width='16' height='70' rx='8' fill='%s' %s stroke-width='3'/>" % (c["skin"], LN)
    if pose == "phone_out":    # phone held up in front (panicking)
        o2 = math.sin(t * 30) * 4
        a = arm(c, (150, 230), (190, 330), (80 + o2, 190))
        return a + "<rect x='%d' y='120' width='46' height='82' rx='9' fill='#ff7aa8' %s stroke-width='3'/>" % (58 + o2, LN) + \
            "<circle cx='%d' cy='190' r='27' fill='%s' %s stroke-width='3.5'/>" % (80 + o2, c["skin"], LN)
    if pose == "clap":
        g = abs(math.sin(t * 12)) * 26
        return arm(c, (-150, 230), (-190, 300), (-24 - g, 150)) + arm(c, (150, 230), (190, 300), (24 + g, 150))
    return ""

DEF = dict(shut=0, mouth=0, wide=.5, smile=.4, eye=1, happy=0, look=0, lookup=0, brow=0, worry=0, blush=0, nod=0, tilt=0,
           sweat=0, wavy=0, droop=0, bounce=0, shake=0, bow=0, spark=0, spin=0, hearts=0)


# ---- small additions to the puppet drawing: look up, wavy panic mouth, droop ----
_eye, _mouth = P.eye, P.mouth
def eye(x, side, c, openv, happy, look, lookup=0, shut=0):
    if shut:     # > <  tightly shut (shy / embarrassed)
        d = 1 if side < 0 else -1
        return ("<path d='M %d -12 L %d 2 L %d 14' stroke='#2a1a14' stroke-width='7' fill='none' stroke-linecap='round' stroke-linejoin='round'/>"
                % (x - 22 * d, x + 18 * d, x - 22 * d))
    s = _eye(x, side, c, openv, happy, look)
    return s if not lookup or happy > .5 else s.replace("cy='3' rx='19'", "cy='%.1f' rx='19'" % (3 - 9 * lookup)).replace(
        "cy='5' rx='8'", "cy='%.1f' rx='8'" % (5 - 9 * lookup))
def mouth(openv, wide, smile, c, wavy=0):
    if wavy and openv < .1:
        return "<path d='M -20 0 q 5 -6 10 0 t 10 0 t 10 0 t 10 0' stroke='#7a3b32' stroke-width='5' fill='none' stroke-linecap='round'/>"
    return _mouth(openv, wide, smile, c)


def head(c, p):
    s = P.head(c, p)
    # re-draw eyes with look-up, and mouth variants, by replacing the generated pieces
    s = s.replace(_eye(-50, -1, c, p["eye"], p["happy"], p["look"]), eye(-50, -1, c, p["eye"], p["happy"], p["look"], p["lookup"], p.get("shut", 0)))
    s = s.replace(_eye(50, 1, c, p["eye"], p["happy"], p["look"]), eye(50, 1, c, p["eye"], p["happy"], p["look"], p["lookup"], p.get("shut", 0)))
    s = s.replace(_mouth(p["mouth"], p["wide"], p["smile"], c), mouth(p["mouth"], p["wide"], p["smile"], c, p["wavy"]))
    if FULL and FULL.get(c["kind"]) == "myanmar" and c["kind"] == "mio":
        s += FB.padauk(-88, -96)
    if p["droop"]:      # gloomy vertical lines on the forehead
        s += "".join("<line x1='%d' y1='-50' x2='%d' y2='-26' stroke='#5b6aa8' stroke-width='4' opacity='.7'/>" % (x, x) for x in (-70, -56, -42, 42, 56, 70))
    return s


def char(c, x, y, sc, p, t, pose=""):
    bob = math.sin(t * 2.1 + x) * 2.5 + p["bounce"] * abs(math.sin(t * 9)) * 7
    sx = p["shake"] * math.sin(t * 60) * 4
    rot = p["tilt"] + math.sin(t * .9 + x) * 1.2
    bow = p.get("bow", 0)
    s = "<g transform='translate(%.1f %.1f) scale(%.3f)'>" % (x + sx, y + bob + bow * 70, sc)
    s += "<g transform='rotate(%.2f 0 460)'>" % (bow * 8)
    if p.get("spin"):                      # twirl: squash horizontally through a half turn
        s += "<g transform='scale(%.3f 1)'>" % (math.cos(p["spin"] * math.pi * 2))
    if FULL:
        st = FULL[c["kind"]]
        walk = p.get("walk", 0)
        s += FB.outfit(c, st, t + walk, arms=(pose not in LEFT_ARM, pose not in RIGHT_ARM))
    else:
        s += P.body(c)
    s += "<g transform='rotate(%.2f 0 120) translate(0 %.1f)'>%s</g>" % (rot + bow * 4, p["nod"] + bow * 45, head(c, p))
    s += arms(c, pose, t)
    if p.get("spin"):
        s += "</g>"
    if p.get("hearts"):
        for k, hx in enumerate((-150, 150, -110)):
            hy = -150 - ((t * 60 + k * 50) % 120)
            s += ("<path d='M %d %d c -14 -18 -40 -2 -20 18 l 20 18 l 20 -18 c 20 -20 -6 -36 -20 -18 Z' fill='#ff7d9c' opacity='.85' %s stroke-width='2'/>"
                  % (hx, hy, LN))
    if p.get("spark"):
        for k, (sx2, sy2) in enumerate(((-170, -120), (175, -90), (-150, 40), (160, 60))):
            a2 = .5 + .5 * math.sin(t * 8 + k * 1.7)
            s += ("<path d='M %d %d l 6 -16 l 6 16 l 16 6 l -16 6 l -6 16 l -6 -16 l -16 -6 Z' fill='#ffe066' opacity='%.2f'/>"
                  % (sx2, sy2, .35 + .65 * a2))
    return s + "</g></g>"


def lerp(a, b, k):
    return {key: a.get(key, 0) + (b.get(key, a.get(key, 0)) - a.get(key, 0)) * k for key in set(a) | set(b)}


def ruby(s):
    s = re.sub(r"([一-龯々]+)《(.+?)》", r"<ruby>\1<rt>\2</rt></ruby>", s)
    return re.sub(r"\[(.+?)\]", r"<span class='pill'>\1</span>", s)


def env_of(path, n):
    e, x, sr = P.rms_env(path, n)
    return e, x


def plan():
    t, evs = 0.2, []
    for L in EP:
        d = L.get("dur") or (wave.open(os.path.join(V, L["v"] + ".wav")).getnframes() / SR + 0.45)
        d += L.get("post", 0)
        evs.append(dict(L, st=t, d=d)); t += d
    rec = dict(shot="recap", st=t, d=5.5); evs.append(rec)
    return evs, t + 5.7


def params(ev, who, t, env, i):
    lt = t - ev["st"]; k = min(1, lt / max(ev["d"], .1))
    base = dict(DEF); base["smile"] = .45 if who == "rio" else .6
    ex = ev.get("ex", {}).get(who, {}); en = ev.get("end", {}).get(who)
    base.update(lerp(ex, en, k) if en else ex)
    talking = ev.get("who") == who and not ev.get("inner")
    if talking:
        base["mouth"] = env[who][i]
        if base["mouth"] > .6: base["nod"] = base["nod"] + 3
        base["wide"] = .5 + .5 * math.sin(i * .9)
    if base.get("happy"): base["mouth"] = max(base["mouth"], .3)
    blink = (t + (0 if who == "rio" else 1.3)) % 3.6
    if blink < .14 and base["eye"] > .3:
        base["eye"] *= abs(blink - .07) / .07
    if ev.get("shot") == "two" and who != ev.get("who"):
        base["look"] = base.get("look", 0)   # listener keeps eye contact
    return base


def frame(evs, t, env, bgs):
    ev = next((e for e in reversed(evs) if e["st"] <= t + 1e-9), evs[0])
    lt = t - ev["st"]; i = int(round(t * FPS))
    F = os.path.join(ROOT, "fonts")
    css = """@font-face{font-family:Round;src:url('file://%s/MPLUSRounded1c-Bold.ttf')}
@font-face{font-family:My;src:url('file://%s/NotoSansMyanmar.ttf')}
body{margin:0;width:1080px;height:1920px;background:#111;overflow:hidden}
.band{position:absolute;top:560px;left:0;width:1080px;height:608px;overflow:hidden}
.band img{position:absolute;left:0;top:0;width:1080px;height:608px;object-fit:cover}
.band svg{position:absolute;left:0;top:0}
.hook{position:absolute;top:190px;left:40px;right:40px;text-align:center;font-family:My,Round;color:#fff;font-size:46px;line-height:1.5}
.ep{display:inline-block;background:#e0607e;color:#fff;border-radius:14px;padding:2px 18px;font-family:Round;font-size:34px;margin-bottom:10px}
.ej{position:absolute;left:30px;right:30px;top:1218px;text-align:center}
.m2{font-family:My;font-size:42px;color:#fff;line-height:1.6;text-shadow:0 0 6px #000,2px 2px 0 #000}
.j2{font-family:Round,My;color:#fff;line-height:1.45;margin-top:18px;-webkit-text-stroke:10px #000;paint-order:stroke fill}
.j2 rt{font-size:.45em;color:#ffe08a;-webkit-text-stroke:5px #000}
.pill{background:#3fbf7f;border-radius:14px;padding:0 10px;white-space:nowrap}
.cap{position:absolute;left:26px;top:22px;background:rgba(20,20,20,.75);color:#fff;border-radius:16px;padding:10px 24px;font-family:My;font-size:36px}
.recap{position:absolute;left:50px;right:50px;top:440px;background:#fff;border-radius:40px;padding:40px 46px}
.recap h2{margin:0 0 26px;font-family:Round;font-size:54px;color:#2a9d5f}
.ri{border-bottom:2px dashed #e5e5e5;padding:16px 0}.ri .j{font-family:Round;font-size:48px;color:#222}.ri .j rt{font-size:.5em;color:#888}
.ri .m{font-family:My;font-size:34px;color:#555;margin-top:4px}
""" % (F, F)
    body = "<div class='hook'><div class='ep'>Rio &amp; Mio</div><br>%s</div>" % HOOK
    if ev["shot"] == "recap":
        e = P.c01 if hasattr(P, "c01") else None
        a = min(1, lt / .4)
        body += "<div class='recap' style='opacity:%.2f'><h2>%s</h2>" % (a, ruby(RECAP[0]))
        for kk, (j, m) in enumerate(RECAP[1]):
            body += "<div class='ri' style='opacity:%.2f'><div class='j'>%s</div><div class='m'>%s</div></div>" % (
                max(0, min(1, (lt - .4 - kk * .5) / .3)), ruby(j), m)
        return "<html><head><meta charset='utf-8'><style>%s</style></head><body>%s</div></body></html>" % (css, body)
    zoom = 1 + .025 * lt
    if ev.get("zoom"):
        z0, z1 = ev["zoom"]; k2 = min(1, lt / .35)
        zoom = z0 + (z1 - z0) * (1 - (1 - k2) ** 3)
    sway = math.sin(t * 1.9) * 5 if ev.get("sway", SWAY) else 0
    if ev["shot"] == "moon":
        body += "<div class='band'><img src='file://%s' style='transform:scale(%.3f)'><div class='cap'>%s</div></div>" % (bgs["moon"], 1 + .04 * lt, ev["mm"])
    else:
        if ev["shot"] in ("two", "two_up"):
            po = ev.get("pose", {})
            pr, pm = params(ev, "rio", t, env, i), params(ev, "mio", t, env, i)
            if FULL:
                xs = {"rio": 350, "mio": 730}; ys, sc = 112, .6
                for who, (x0, dur0) in ev.get("enter", {}).items():     # walk in from x0
                    k3 = min(1, lt / dur0); xs[who] = x0 + (xs[who] - x0) * (1 - (1 - k3) ** 2)
                    if k3 < 1:
                        (pr if who == "rio" else pm)["bounce"] = .6
                for who, (t0, d0) in ev.get("twirl", {}).items():
                    k4 = (lt - t0) / d0
                    if 0 <= k4 <= 1:
                        (pr if who == "rio" else pm)["spin"] = k4
                chars = char(P.RIO, xs["rio"], ys, sc, pr, t, po.get("rio", "")) + char(P.MIO, xs["mio"], ys + 6, sc * .97, pm, t, po.get("mio", ""))
            else:
                chars = char(P.RIO, 330, 250, .95, pr, t, po.get("rio", "")) + char(P.MIO, 750, 262, .92, pm, t, po.get("mio", ""))
        elif ev["shot"] == "rio":
            chars = char(P.RIO, 540, 300, 1.3, params(ev, "rio", t, env, i), t, ev.get("pose", {}).get("rio", ""))
        else:
            chars = char(P.MIO, 540, 305, 1.27, params(ev, "mio", t, env, i), t, ev.get("pose", {}).get("mio", ""))
        if TABLE:
            tb = ("<rect x='-60' y='520' width='1200' height='120' fill='#b9875a' stroke='#3b2a24' stroke-width='4'/>"
                  "<rect x='-60' y='512' width='1200' height='16' fill='#d6a674' stroke='#3b2a24' stroke-width='3'/>")
            if ev["shot"] in ("two", "two_up"):
                for bx in (330, 750):
                    tb += ("<ellipse cx='%d' cy='520' rx='86' ry='22' fill='#f3efe6' stroke='#3b2a24' stroke-width='3'/>"
                           "<path d='M %d 520 q 86 70 172 0' fill='#e9e2d2' stroke='#3b2a24' stroke-width='3'/>"
                           "<ellipse cx='%d' cy='516' rx='70' ry='14' fill='#e0a640'/>" % (bx, bx - 86, bx))
            chars += tb
        svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='608' viewBox='0 0 1080 608'>%s"
               "<g transform='translate(%.1f 0) translate(540 304) scale(%.4f) translate(-540 -304)'>%s</g></svg>" % (P.DEFS + FB.PAT, sway, zoom, chars))
        body += "<div class='band'><img src='file://%s' style='transform:translate(%.1fpx,0) scale(1.02)'>%s</div>" % (bgs["two" if ev["shot"] in ("two", "two_up") else "cu"], sway * .6, svg)
    if ev.get("jp") and lt <= ev["d"]:
        n = len(re.sub(r"《.+?》|[\[\]]", "", ev["jp"]))
        px = 66 if n <= 15 else max(int(66 * 15 / n), 42)
        body += "<div class='ej'><div class='m2'>%s</div><div class='j2' style='font-size:%dpx'>%s</div></div>" % (ev["mm"], px, ruby(ev["jp"]))
    return "<html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>" % (css, body)


def sfx(kind):
    n = int(SR * 1.6); t = np.arange(n) / SR; x = np.zeros(n, np.float32)
    if kind == "don":
        x += (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 5) * .8 + np.sin(2 * np.pi * np.cumsum(520 * np.exp(-t * 2.2)) / SR) * np.exp(-t * 3) * .25).astype(np.float32)
    elif kind == "twinkle":
        for k, f in enumerate((1568, 2093, 2637, 3136)):
            m = t >= k * .12; tt = t[m] - k * .12
            x[m] += (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 4) * .12).astype(np.float32)
    elif kind == "fall":    # comic descending slide whistle
        f = 900 * np.exp(-t * 1.4)
        x += (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.2) * .18).astype(np.float32)
    elif kind == "heart":    # soft "kyun" bell
        for k, f in enumerate((1319, 1760)):
            m = t >= k * .09; tt = t[m] - k * .09
            x[m] += (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3) * .16).astype(np.float32)
    elif kind == "ring":     # simple phone ring (marimba-like)
        for k in range(6):
            for j2, f in enumerate((880, 1175)):
                st2 = k * .26 + j2 * .12; m = t >= st2; tt = t[m] - st2
                x[m] += (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 9) * .22).astype(np.float32)
    elif kind == "ring2":    # loud silly ringtone
        notes = (784, 988, 1175, 1568, 1175, 988, 784, 1568)
        for k, f in enumerate(notes):
            st2 = k * .16; m = (t >= st2) & (t < st2 + .15); tt = t[m] - st2
            x[m] += (np.sign(np.sin(2 * np.pi * f * tt)) * .1).astype(np.float32)
    return x


def train_amb(n):
    rng = np.random.default_rng(3); t = np.arange(n) / SR
    rum = np.convolve(rng.standard_normal(n).astype(np.float32), np.ones(400) / 400, "same") * 2.5
    clack = np.zeros(n, np.float32)
    for k in np.arange(0.3, n / SR, 1.15):
        for d2 in (0, .14):
            i2 = int((k + d2) * SR); m = min(int(.05 * SR), n - i2)
            if m > 0:
                clack[i2:i2 + m] += rng.standard_normal(m).astype(np.float32) * np.exp(-np.arange(m) / 300) * .25
    return (rum + clack) * .35


async def shoot(evs, total, env, bgs, tmp):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        f = os.path.join(tmp, "f.html")
        for i in range(int(total * FPS)):
            open(f, "w", encoding="utf-8").write(frame(evs, i / FPS, env, bgs))
            await pg.goto("file://" + f)
            if i == 0:
                await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, "%05d.jpg" % i), type="jpeg", quality=90)
        await b.close()


def main():
    evs, total = plan()
    n = int(total * FPS) + 2
    env = {"rio": np.zeros(n), "mio": np.zeros(n)}
    y = np.zeros(int(total * SR) + SR, np.float32); vm = np.zeros_like(y)
    for e in evs:
        if e.get("v"):
            path = os.path.join(V, e["v"] + ".wav")
            en, x = env_of(path, int(e["d"] * FPS) + 2)
            act = x[np.abs(x) > .01]                     # even out loudness: every line to the same speech level
            if len(act):
                x = x * min(6.0, .09 / (np.sqrt(np.mean(act ** 2)) + 1e-6))
            a = int((e["st"] + .15) * FPS); env[e["who"]][a:a + len(en)] = en[:max(0, n - a)]
            s = int((e["st"] + .15) * SR); m = min(len(x), len(y) - s)
            y[s:s + m] += x[:m] * (.8 if e.get("inner") else 1.0); vm[s:s + m] = 1
        if e.get("sfx"):
            z = sfx(e["sfx"]) * e.get("sfxv", 1); s = int((e["st"] + e.get("sfxat", 0)) * SR); m = min(len(z), len(y) - s); y[s:s + m] += z[:m]
    if AMB == "train":
        y += train_amb(len(y)) * .5
    # music bed (CC BY Kevin MacLeod), ducked under voices
    mus = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(ROOT, MUSIC), "-t", "%.2f" % total,
                          "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    mus = np.frombuffer(mus, np.float32).copy()[:len(y)]
    duck = 1 - .7 * np.convolve(vm[:len(mus)], np.ones(SR // 4) / (SR // 4), "same")
    fade = np.minimum(1, np.arange(len(mus)) / SR) * np.minimum(1, (len(mus) - np.arange(len(mus))) / (1.5 * SR))
    y[:len(mus)] += mus * .06 * duck * fade
    tmp = tempfile.mkdtemp()
    bgs = {}
    im = Image.open(os.path.join(A, BG["two"][0])).convert("RGB").resize((1080, 608))
    im.filter(ImageFilter.GaussianBlur(BG["two"][1])).save(os.path.join(tmp, "two.jpg")); bgs["two"] = os.path.join(tmp, "two.jpg")
    im = Image.open(os.path.join(A, BG["cu"][0])).convert("RGB").resize((1080, 608))
    im.crop((180, 60, 900, 465)).resize((1080, 608)).filter(ImageFilter.GaussianBlur(BG["cu"][1])).save(os.path.join(tmp, "cu.jpg")); bgs["cu"] = os.path.join(tmp, "cu.jpg")
    if BG.get("moon"):
        Image.open(os.path.join(A, BG["moon"])).convert("RGB").resize((1080, 608)).save(os.path.join(tmp, "moon.jpg")); bgs["moon"] = os.path.join(tmp, "moon.jpg")
    asyncio.run(shoot(evs, total, env, bgs, tmp))
    wv = os.path.join(tmp, "a.wav")
    with wave.open(wv, "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    out = os.path.join(HERE, "out", OUT); os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%05d.jpg"), "-i", wv,
                    "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5", "-ar", "48000",
                    "-c:a", "aac", "-shortest", "-movflags", "+faststart", out], check=True)
    print(out, "%.1fs" % total)


if __name__ == "__main__":
    import sys, importlib
    if len(sys.argv) > 1:          # python ep.py script_ep2  -> use EP/RECAP/HOOK/BG/OUT/MUSIC from that module
        m = importlib.import_module(sys.argv[1])
        for k in ("EP", "RECAP", "HOOK", "BG", "OUT", "MUSIC", "SWAY", "AMB", "FULL", "TABLE"):
            if hasattr(m, k):
                globals()[k] = getattr(m, k)
    main()
