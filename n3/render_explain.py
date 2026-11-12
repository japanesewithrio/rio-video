"""N3 explainer video (Ye 11/11 night): ONE narrator style, no two-person chat.
Title (Ye 11/12) -> timeline picture -> formula blocks -> 2 examples -> ⚠️ trap -> JLPT 問題 3-2-1 -> end.
Clean mint design, every element animated (pop / slide / word by word), self-made sound effects, Rio reads the Japanese.
Every frame is drawn as HTML and filmed with Chrome (playwright)."""
import asyncio, math, os, re, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.environ.get("RIO_FONTS", os.path.join(ROOT, "fonts"))
AV = os.path.join(ROOT, "steps")
SR, FPS = 24000, 30
G = "#1f8a5b"
PARTS = 6

CSS = """@font-face{font-family:My;src:url('file://%(F)s/NotoSansMyanmar.ttf')}@font-face{font-family:Round;src:url('file://%(F)s/MPLUSRounded1c-Bold.ttf')}
*{box-sizing:border-box}body{margin:0;width:1080px;height:1920px;overflow:hidden;background:linear-gradient(180deg,#f3faf7,#e3f1ea);
font-family:'Noto Sans CJK JP','Noto Sans JP',My,sans-serif;color:#173b2e}
.brand{position:absolute;top:150px;left:0;right:0;text-align:center;font-family:Round;font-size:30px;color:%(G)s;opacity:.85}
.w{display:inline-block;margin:0 4px}.pill{background:%(G)s;color:#fff;border-radius:18px;padding:0 16px}.ta{color:#e0453a;font-weight:800;border-bottom:6px solid #e0453a}.pill .ta{background:#fff;border-radius:14px;padding:0 8px;border:0}
.card{background:#fff;border-radius:34px;box-shadow:0 16px 36px rgba(31,90,70,.13)}
.lab{text-align:center;font-family:My;font-size:42px;color:%(G)s;font-weight:700}
.my{font-family:My}.g{color:%(G)s}"""


# ---------------------------------------------------------------- easing helpers
def c01(x):
    return max(0.0, min(1.0, x))


def ease(x):
    x = c01(x)
    return 1 - (1 - x) ** 3


def inout(x):
    x = c01(x)
    return x * x * (3 - 2 * x)


def back(x):
    x = c01(x)
    k = 1.6
    return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2


def P(t, a, d=0.45):
    return c01((t - a) / d)


def hl(s):
    s = re.sub(r"\{(.+?)\}", r"<span class='ta'>\1</span>", s)   # {た} = red: shows the ta-form
    return re.sub(r"\[(.+?)\]", r"<span class='pill'>\1</span>", s)


def plain(s):
    return re.sub(r"[\[\]{}]", "", s)


def pop(t, a, d=0.45):
    """style for an element that pops in at time a."""
    p = back(P(t, a, d))
    return "opacity:%.2f;transform:translateY(%.0fpx) scale(%.3f)" % (c01(P(t, a, d) * 2.2), (1 - p) * 60, 0.85 + 0.15 * p)


def words(chunks, t, a, size, font="Round", gap=0.32):
    """chunks: text split at spaces; [x] = green pill. Appear one by one from time a."""
    out = ""
    for i, w in enumerate(chunks):
        st = a + i * gap
        p = back(P(t, st, 0.32))
        out += "<span class='w' style='opacity:%.2f;transform:translateY(%.0fpx)'>%s</span>" % (c01(P(t, st, 0.18)), (1 - p) * 50, hl(w))
    return "<div style='text-align:center;font-family:%s;font-size:%dpx;line-height:1.45'>%s</div>" % (font, size, out)


# ---------------------------------------------------------------- scenes: each returns (html(t_local), duration, audio events, sfx events)
def scene_title(x, L):
    ti = x["title_card"]
    a_say = 1.2
    dur = max(7.5, a_say + L["t_say"] + 1.5)

    def f(t):
        s = "<div style='position:absolute;top:290px;left:60px;right:60px;text-align:center'>"
        s += "<div style='display:inline-block;background:#fff;border-radius:30px;padding:8px 30px;font-family:Round;font-size:34px;color:%s;%s'>今日の N3 文法 📘</div>" % (G, pop(t, 0.0))
        s += "<div style='font-family:Round;font-size:%dpx;margin-top:50px;%s'><span class='pill' style='padding:0 34px'>%s</span></div>" % (min(150, int(880 / max(1, len(plain(ti["g"]))))), pop(t, 0.3), hl(ti["g"]))
        s += "<div class='my' style='font-size:46px;margin-top:50px;%s'>%s</div>" % (pop(t, 0.6), hl(ti["mm"]))
        if ti.get("meaning"):
            s += ("<div class='card my' style='margin:34px 20px 0;padding:24px 34px;text-align:left;font-size:44px;line-height:1.6;border-left:10px solid %s;%s'>"
                  "<span style='font-size:32px;color:#4a6a5c'>📖 အဓိပ္ပာယ်</span><br><b>%s</b>" % (G, pop(t, 0.9), hl(ti["meaning"])))
            if ti.get("use"):
                s += ("<div style='margin-top:14px;padding-top:14px;border-top:3px dashed #d6e8df;font-size:36px;%s'>"
                      "<span style='font-size:32px;color:#c46a00'>💡 ဘယ်တော့ သုံးလဲ</span><br>%s</div>" % (pop(t, 1.6), hl(ti["use"])))
            s += "</div>"
        s += ("<div style='display:flex;justify-content:center;align-items:center;gap:24px;margin-top:60px;%s'><img src='file://%s/rio.png' style='width:130px;height:130px;"
              "border-radius:50%%;border:5px solid #fff;box-shadow:0 6px 16px rgba(0,0,0,.12)'><div class='card' style='padding:20px 30px;font-size:40px;font-weight:700;text-align:left'>%s</div></div>"
              % (pop(t, a_say), AV, ti["bubble"]))
        return s + "</div>"
    return f, dur, [(a_say, "t_say")], [(0, "pop"), (0.3, "ding"), (0.6, "swish"), (0.9, "tick"), (1.6, "tick")]


def form_chip(t, a, fm, name):
    """📌 立ち上がる → 立ち上がった  /  た形（たけい）· Ta-form.  Same word twice (nouns etc.) -> just the word."""
    arrow = hl(fm[1]) if plain(fm[0]) == plain(fm[1]) else "%s <span style='color:#e8a33d'>→</span> %s" % (fm[0], hl(fm[1]))
    return ("<div style='text-align:center;%s'><div style='display:inline-block;background:#eef5f1;border-radius:24px;padding:12px 26px'>"
            "<span style='font-size:40px;font-weight:700'>📌 %s</span>"
            "<div class='my' style='font-size:28px;color:#4a6a5c'>%s</div></div></div>" % (pop(t, a), arrow, hl(name)))


def why_card(t, a, txt):
    return ("<div class='card my' style='margin:26px 40px 0;padding:22px 30px;font-size:36px;line-height:1.65;border-left:10px solid #e8a33d;%s'>"
            "<b style='color:#c46a00'>💡 ဘာလို့?</b><br>%s</div>" % (pop(t, a), txt))


def blk(t, a, txt, sub, on=False, w=300):
    p = back(P(t, a, 0.45))
    return ("<div class='card' style='width:%dpx;padding:26px 0;text-align:center;background:%s;color:%s;opacity:%.2f;transform:translateY(%.0fpx) scale(%.2f)'>"
            "<div style='font-size:64px;font-weight:700'>%s</div><div class='my' style='font-size:28px;opacity:.85'>%s</div></div>"
            % (w, G if on else "#fff", "#fff" if on else "#173b2e", c01(P(t, a, 0.15)), (1 - p) * -120, 0.7 + 0.3 * p, hl(txt), plain(sub)))


def scene_formula(x, L):
    fm = x["formula"]
    a_ex = 2.6
    t_mm = a_ex + 1.0
    dur = max(t_mm + 3.0, a_ex + L["f_say"] + 2.5)

    def f(t):
        top = "<div style='font-size:60px;color:#e8a33d;opacity:%.2f'>+</div>" % c01(P(t, 1.2, 0.2))
        s = "<div style='position:absolute;top:360px;left:0;right:0'><div class='lab' style='%s'>ပုံသေနည်း</div>" % pop(t, 0.1)
        s += "<div style='display:flex;justify-content:center;align-items:center;gap:20px;margin-top:40px'>%s%s%s</div>" % (
            blk(t, 0.6, *fm["top"][0]), top, blk(t, 1.3, *fm["top"][1], on=True))
        s += "<div style='text-align:center;font-size:60px;margin-top:36px;opacity:%.2f'>⬇️</div>" % c01(P(t, 2.1, 0.3))
        s += "<div style='display:flex;justify-content:center;gap:20px;margin-top:30px'>%s%s</div>" % (
            blk(t, a_ex, *fm["ex"][0], w=270), blk(t, a_ex + 0.5, *fm["ex"][1], on=True, w=270))
        s += "<div class='my' style='text-align:center;font-size:30px;color:#4a6a5c;margin-top:18px;%s'>%s</div>" % (pop(t, a_ex + 0.8), hl(x["form_name"]))
        s += ("<div class='card my' style='margin:50px 90px 0;padding:28px;text-align:center;font-size:48px;font-weight:700;%s'>%s</div>"
              % (pop(t, t_mm), fm["mm"]))
        return s + "</div>"
    return f, dur, [(a_ex, "f_say")], [(0.1, "whoosh"), (0.6, "pop"), (1.3, "pop"), (a_ex, "tick"), (a_ex + 0.5, "tick"), (t_mm, "ding")]


def scene_timeline(x, L):
    tl = x["timeline"]
    a_say = 2.0
    dur = max(8.5, a_say + L.get("tl_say", 0) + 5.5)

    def f(t):
        ln = inout(P(t, 0.4, 1.0))
        s = "<div style='position:absolute;top:360px;left:0;right:0'><div class='lab' style='%s'>အချိန်နဲ့ ကြည့်ရင်</div>" % pop(t, 0.1)
        s += "<div style='position:relative;height:440px;margin-top:30px'>"
        s += "<div style='position:absolute;top:250px;left:100px;width:%.0fpx;height:10px;border-radius:5px;background:#cfe3d9'></div>" % (ln * 880)
        for (e, lab), x0, a in ((tl["a"], 300, 1.4), (tl["b"], 470, 2.2)):
            s += "<div style='position:absolute;top:110px;left:%dpx;text-align:center;%s'><div style='font-size:100px'>%s</div><div style='font-size:38px;font-weight:700'>%s</div></div>" % (x0, pop(t, a), e, hl(lab))
        s += "<div style='position:absolute;top:330px;left:300px;width:300px;text-align:center;font-family:Round;font-size:44px;color:#d9534f;%s'>%s</div>" % (pop(t, 2.9), tl["gap"])
        s += "</div>"
        s += ("<div class='card my' style='margin:0 90px;padding:26px 32px;font-size:42px;line-height:1.6;%s'>%s<br><span style='font-size:36px;color:#4a5a52'>%s</span></div>"
              % (pop(t, 3.8), tl["mm"], tl["sub"]))
        s += "<div style='display:flex;justify-content:center;gap:30px;margin-top:40px'>"
        s += "<div class='my' style='font-size:36px;background:#eaf7f0;border-radius:24px;padding:16px 28px;%s'>%s</div>" % (pop(t, 5.4), tl["ok"])
        s += "<div class='my' style='font-size:36px;background:%s;border-radius:24px;padding:16px 28px;%s'>%s</div>" % ("#eaf7f0" if tl.get("both_ok") else "#fdecec", pop(t, 6.2), tl["ng"])
        return s + "</div></div>"
    return f, dur, ([(a_say, "tl_say")] if "tl_say" in L else []), [(0.1, "whoosh"), (1.4, "pop"), (2.2, "pop"), (2.9, "ding"), (3.8, "swish"), (5.4, "tick"), (6.2, "tick")]


def scene_example(x, L, k):
    e = x["examples"][k]
    a_jp = 1.6
    t_mm = a_jp + min(1.2, L["e%d" % k])
    t_why = max(t_mm + 1.2, a_jp + L["e%d" % k] + 0.5)
    dur = t_why + 5.0

    def f(t):
        s = "<div style='position:absolute;top:300px;left:40px;right:40px'><div class='lab' style='%s'>ဥပမာ %d</div>" % (pop(t, 0.1), k + 1)
        s += "<div style='text-align:center;font-size:120px;margin-top:16px;%s'>%s</div>" % (pop(t, 0.4), e["emoji"])
        s += "<div style='margin-top:16px'>%s</div>" % form_chip(t, 0.9, e["form"], e.get("form_name", x["form_name"]))
        s += "<div class='card' style='margin:26px 40px 0;padding:30px 30px;%s'>%s" % (pop(t, a_jp - 0.2), words(e["jp"].split(" "), t, a_jp, 64, "Noto Sans CJK JP", 0.28))
        s += "<div class='my' style='text-align:center;font-size:40px;color:#4a5a52;margin-top:16px;%s'>%s</div></div>" % (pop(t, t_mm), e["mm"])
        s += why_card(t, t_why, e["why"])
        return s + "</div>"
    return f, dur, [(a_jp, "e%d" % k)], [(0.1, "whoosh"), (0.4, "pop"), (0.9, "tick"), (t_mm, "swish"), (t_why, "ding")]


def scene_trap(x, L):
    tr = x["trap"]
    a_good = 3.2
    t_mm = a_good + min(1.0, L["trap"])
    t_why = max(t_mm + 1.2, a_good + L["trap"] + 0.5)
    dur = t_why + 5.0

    def f(t):
        st = inout(P(t, 2.3, 0.5))
        s = "<div style='position:absolute;top:300px;left:30px;right:30px;text-align:center'>"
        s += "<div style='font-size:120px;%s'><span style='display:inline-block;transform:rotate(%.0fdeg)'>⚠️</span></div>" % (pop(t, 0.1), math.sin(t * 14) * 6 * (t < 1.2))
        s += "<div class='my' style='font-size:48px;font-weight:700;color:#c46a00;%s'>ဒီလို မပြောနဲ့!</div>" % pop(t, 0.5)
        s += ("<div style='position:relative;display:inline-block;font-size:58px;font-weight:700;margin-top:44px;%s'>%s ❌"
              "<div style='position:absolute;left:0;top:50%%;height:8px;width:%.0f%%;background:#d9534f;border-radius:4px'></div></div>" % (pop(t, 1.2), tr["bad"], st * 100))
        s += "<div style='font-size:58px;font-weight:700;margin-top:34px;%s'>%s ✅</div>" % (pop(t, a_good), hl(tr["good"]))
        s += "<div class='card my' style='margin:44px 40px 0;padding:24px;font-size:38px;%s'>%s</div>" % (pop(t, t_mm), tr["mm"])
        s += "<div style='text-align:left'>%s</div>" % why_card(t, t_why, tr["why"])
        return s + "</div>"
    return f, dur, [(a_good, "trap")], [(0.1, "pop"), (1.2, "whoosh"), (2.3, "swish"), (a_good, "ding"), (t_mm, "swish"), (t_why, "ding")]


def scene_quiz(x, L):
    q = x["quiz"]
    a_cd = 0.3 + L["q0"] + 0.6
    a_ans = a_cd + 3.0
    t_th = a_ans + L["q1"] + 0.5
    dur = t_th + 3.6

    def card(t, mark):
        s = "<div class='card' style='margin:0 40px;padding:30px 36px;%s'>" % pop(t, 0.5)
        s += "<div style='font-size:50px;font-weight:700;line-height:1.5'>%s</div>" % (
            hl(q["full"]) if mark else q["q"].replace("（　）", "<span style='color:%s'>（　）</span>" % G))
        if mark:
            s += "<div class='my' style='font-size:34px;color:#4a5a52'>%s</div>" % q["full_mm"]
        for i, o in enumerate(q["opts"], 1):
            ok = i == q["ans"]
            if mark:
                sty = "border-color:%s;background:#eaf7f0;color:%s" % (G, G) if ok else "opacity:.3"
                lab = ("✓ " if ok else "✕ ") + o
            else:
                sty, lab = "", "%d. %s" % (i, o)
            s += "<div style='border:4px solid #d6e8df;border-radius:24px;padding:12px 26px;font-size:46px;font-weight:700;margin:14px 0;%s'>%s</div>" % (sty, lab)
        return s + "</div>"

    def f(t):
        s = "<div style='position:absolute;top:330px;left:0;right:0'>"
        s += "<div style='text-align:center;font-family:Round;font-size:60px;%s'>JLPT 問題 ✍️</div>" % pop(t, 0.1)
        s += "<div style='margin-top:30px'>%s</div>" % card(t, t >= a_ans)
        if a_cd <= t < a_ans:
            n = 3 - int(t - a_cd)
            s += "<div style='text-align:center;font-family:Round;font-size:170px;color:%s;%s'>%d</div>" % (G, pop(t, a_cd + (3 - n)), n)
        if t >= a_ans + 0.6 and q.get("form"):
            s += "<div style='margin-top:20px'>%s</div>" % form_chip(t, a_ans + 0.6, q["form"], q.get("form_name", x["form_name"]))
        if t >= t_th:
            s += "<div class='card my' style='margin:30px 40px 0;padding:22px 30px;font-size:36px;border-left:10px solid %s;%s'>💭 %s</div>" % (G, pop(t, t_th), q["think"])
        return s + "</div>"
    return f, dur, [(0.3, "q0"), (a_ans, "q1")], [(0.1, "whoosh"), (a_cd, "tick"), (a_cd + 1, "tick"), (a_cd + 2, "tick"), (a_ans, "ding"), (t_th, "swish")]


def scene_end(x, L):
    dur = 0.4 + L["out"] + 1.4

    def f(t):
        s = "<div style='position:absolute;top:520px;left:0;right:0;text-align:center'>"
        s += "<div style='%s'><img src='file://%s/rio.png' style='width:280px;height:280px;border-radius:50%%;border:8px solid #fff;box-shadow:0 10px 30px rgba(0,0,0,.12)'></div>" % (pop(t, 0.1), AV)
        s += "<div style='font-family:Round;font-size:70px;margin-top:50px;%s'>Follow <span style='color:%s'>Rio</span> ♡</div>" % (pop(t, 0.5), G)
        s += "<div class='my' style='font-size:40px;margin-top:24px;color:#4a5a52;%s'>JLPT N3 まで いっしょに がんばろう！</div>" % pop(t, 0.9)
        return s + "</div>"
    return f, dur, [(0.4, "out")], [(0.1, "pop"), (0.5, "ding")]


def lines(x):
    """Every spoken line (all Rio). Two TTS requests."""
    g1 = [("t_say", x["title_card"]["say"]), ("tl_say", x["timeline"]["say"]), ("f_say", x["formula"]["say"]),
          ("e0", plain(x["examples"][0]["jp"]).replace(" ", "")), ("e1", plain(x["examples"][1]["jp"]).replace(" ", ""))]
    g2 = [("trap", plain(x["trap"]["good"])), ("q0", "じゃあ、問題！どれが入ると思う？"), ("q1", plain(x["quiz"]["full"])),
          ("out", "JLPTまで、いっしょにがんばろう！")]
    return [g1, g2]


def timeline(x, L):
    sc = [scene_title(x, L), scene_timeline(x, L), scene_formula(x, L), scene_example(x, L, 0), scene_example(x, L, 1),
          scene_trap(x, L), scene_quiz(x, L), scene_end(x, L)]
    part = [0, 1, 2, 3, 3, 4, 5, 5]
    out, t = [], 0.0
    for (f, d, au, fx), pt in zip(sc, part):
        out.append((t, d, f, au, fx, pt))
        t += d
    return out, t


def page(inner, part, fade):
    dots = "".join("<i style='width:%dpx;height:12px;border-radius:6px;background:%s;display:inline-block'></i>"
                   % (60 if i == part else 18, G if i <= part else "#cfe3d9") for i in range(PARTS))
    return ("<html><head><meta charset='utf-8'><style>%s</style></head><body><div class='brand'>Learn with Rio ♡</div>"
            "<div style='position:absolute;top:205px;left:0;right:0;display:flex;justify-content:center;gap:14px'>%s</div>"
            "<div style='opacity:%.2f'>%s</div></body></html>" % (CSS % {"F": FONTS, "G": G}, dots, fade, inner))


async def _film(tl, total, tmp):
    from playwright.async_api import async_playwright
    exe = next((p for p in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(p)), None)
    async with async_playwright() as p:
        b = await (p.chromium.launch(executable_path=exe, args=["--allow-file-access-from-files"]) if exe else p.chromium.launch())
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        f = os.path.join(tmp, "f.html")
        n = int(round(total * FPS))
        for i in range(n):
            t = i / FPS
            st, d, fn, au, fx, pt = next(s for s in reversed(tl) if s[0] <= t + 1e-9)
            lt = t - st
            fade = min(c01(lt / 0.25), c01((d - lt) / 0.25)) if st > 0 else c01((d - lt) / 0.25)
            open(f, "w", encoding="utf-8").write(page(fn(lt), pt, fade))
            await pg.goto("file://" + f)
            if i == 0:
                await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, "%05d.jpg" % i), type="jpeg", quality=90)
        await b.close()
    return n


def trim(v, thr=0.015, tail=0.18):
    idx = np.where(np.abs(v) > thr)[0]
    if not len(idx):
        return v
    return v[max(0, idx[0] - int(0.03 * SR)):min(len(v), idx[-1] + int(tail * SR))]


def render(x, clips, out_path, tmp):
    sys.path.insert(0, os.path.join(ROOT, "steps"))
    import render_steps as RS
    clips = {k: trim(v) for k, v in clips.items()}
    L = {k: len(v) / SR for k, v in clips.items()}
    tl, total = timeline(x, L)
    total = round(total * FPS) / FPS
    y = np.zeros(int(total * SR) + SR, np.float32)
    for st, d, fn, au, fx, pt in tl:
        for a, k in au:
            i = int((st + a) * SR)
            v = clips[k][:len(y) - i]
            y[i:i + len(v)] += v
        for a, nm in fx:
            e = RS.sfx(nm) * 0.5
            i = int((st + a) * SR)
            m = min(len(e), len(y) - i)
            if m > 0:
                y[i:i + m] += e[:m]
    y = y[:int(total * SR)]
    asyncio.run(_film(tl, total, tmp))
    wav = os.path.join(tmp, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    part = out_path[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%05d.jpg"), "-i", wav,
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out_path)
    return total
