"""Kinetic-typography explainer (Ye 11/14, reference: Burmese motion-graphics explainer).
One spoken phrase on screen at a time. Rio's Japanese appears word by word exactly as she says it,
the grammar part pops in big and green, the Burmese meaning follows word by word underneath,
and a small icon animation above illustrates each phrase.

Content (n3/kinetic_enc/NNN): {"no", "title", "beats": [{"jp", "mm", "icon": {...}, "part", "hold"?}], "quiz": {...}}
  jp : tokens split by spaces; [x] = key phrase (big green), {x} = red (ta/ba/nai form), 漢字《かんじ》 = furigana
  mm : Burmese, split by spaces; **x** = bold green
"""
import asyncio, os, re, wave, subprocess
import numpy as np
import render_explain as RX
from render_explain import c01, ease, back, inout, hl, plain, G, SR, FPS, usfx, trim, AV

PARTS = 6
TOP_TXT = 1030


def tokens(s):
    return re.findall(r"\[[^\]]*\][^\s\[]*|\S+", s)   # "[key]！" stays one token (no lonely punctuation)


def mm_tokens(s):
    return re.findall(r"\*\*.*?\*\*|\S+", s)


def weight(tok):
    t = re.sub(r"《.+?》", "", tok)
    t = re.sub(r"[\[\]{}、。！？!?,.「」『』＋+()（）・〜~\s]", "", t)
    w = 0.0
    for ch in t:
        w += 1.6 if "一" <= ch <= "鿿" else (0.35 if ch in "ゃゅょャュョっッー" else 1.0)
    return max(w, 0.6)


def spoken(jp):
    """the line Rio says (no markup, no spaces)"""
    return plain(jp).replace(" ", "")


def lines(k):
    keys = [("b%02d" % i, b.get("say") or spoken(b.get("jp") or "".join(plain(j) for j, m in b["lines"])))
            for i, b in enumerate(k["beats"]) if b.get("jp") or b.get("lines")]
    groups, g = [], []
    for kv in keys:          # at most 6 lines per TTS request
        g.append(kv)
        if len(g) == 6:
            groups.append(g); g = []
    if g:
        groups.append(g)
    return groups


# ---------- text ----------
def jp_html(b, lt, L):
    toks = tokens(b["jp"])
    ws = [weight(x) for x in toks]
    tot = sum(ws)
    a0 = 0.12
    out, acc = [], 0.0
    for tok, w in zip(toks, ws):
        ti = a0 + L * 0.94 * acc / tot
        acc += w
        e = c01((lt - ti) / 0.22)
        if e <= 0:
            if tok.startswith("["):
                key, suf = re.match(r"\[(.*?)\](.*)", tok).groups()
                out.append("<span style='white-space:nowrap;opacity:0'><span class='kk' style='font-size:%dpx'>%s</span>%s</span>"
                           % (92 if len(plain(key)) <= 6 else 76, hl(key), hl(suf)))
            else:
                out.append("<span style='opacity:0'>%s</span>" % hl(tok))
            continue
        ee = ease(e)
        if tok.startswith("["):
            key, suf = re.match(r"\[(.*?)\](.*)", tok).groups()
            bb = back(c01((lt - ti) / 0.4))
            sw = ease(c01((lt - ti - 0.1) / 0.35))
            fs = 92 if len(plain(key)) <= 6 else 76
            out.append("<span style='white-space:nowrap'><span class='kk' style='font-size:%dpx;opacity:%.2f;transform:scale(%.3f);filter:blur(%.1fpx);"
                       "background-size:%.0f%% 100%%'>%s</span>%s</span>" % (fs, ee, 1.35 - 0.35 * bb, (1 - ee) * 8, sw * 100, hl(key),
                                                                         "<span class='tk' style='opacity:%.2f'>%s</span>" % (ee, hl(suf)) if suf else ""))
        else:
            out.append("<span class='tk' style='opacity:%.2f;transform:translateY(%.0fpx);filter:blur(%.1fpx)'>%s</span>"
                       % (ee, (1 - ee) * 34, (1 - ee) * 8, hl(tok)))
    return "<div class='jp'>%s</div>" % " ".join(out)


def mm_html(b, lt, start):
    toks = mm_tokens(b.get("mm", ""))
    out = []
    for i, tok in enumerate(toks):
        ti = start + i * 0.09
        e = ease(c01((lt - ti) / 0.25))
        bold = tok.startswith("**")
        txt = tok[2:-2] if bold else tok
        out.append("<span class='%s' style='opacity:%.2f;transform:translateY(%.0fpx)'>%s</span>"
                   % ("mb" if bold else "mt", e, (1 - e) * 18, hl(txt)))
    return "<div class='mm'>%s</div>" % " ".join(out)


# ---------- icons ----------
def chip(t, a, html, cls="ic"):
    p = back(c01((t - a) / 0.45))
    o = c01((t - a) / 0.15)
    return "<div class='%s' style='opacity:%.2f;transform:translateY(%.0fpx) scale(%.3f)'>%s</div>" % (cls, o, (1 - p) * 60, 0.6 + 0.4 * p, html)


def icon(ic, lt, d, k):
    ty = ic.get("type")
    s = ""
    if ty == "title":
        g = ic["g"]
        n = len(plain(g))
        shown = int(c01((lt - 0.5) / 0.9) * n + 0.999) if lt > 0.5 else 0
        txt = plain(g)[:shown]
        cur = "<span style='opacity:%d'>|</span>" % (1 if int(lt * 2.5) % 2 == 0 else 0)
        s += chip(lt, 0.1, "<div class='tag'>%s</div>" % ic.get("tag", "今日の N3 文法 📘"))
        s += ("<div class='bigpill' style='font-size:%dpx;opacity:%.2f'>%s%s</div>" % (min(120, int(1500 / max(1, n))), c01((lt - 0.4) / 0.2), txt, cur if shown < n or lt < 2.5 else ""))
    elif ty == "chain":
        pats = k["chain"]
        act = ic.get("active", -1)
        s += "<div style='display:flex;flex-direction:column;align-items:center;gap:4px;transform:scale(.84)'>"
        for j, ptn in enumerate(pats):
            a = 0.15 + (j * 0.35 if act < 0 else 0)
            if j:
                s += "<div style='font-size:34px;color:#9bbfb0;opacity:%.2f;line-height:1'>↓</div>" % c01((lt - a) / 0.2)
            if act < 0 or j == act:
                sty = "background:%s;color:#fff;box-shadow:0 12px 26px rgba(31,138,91,.30)" % G
                sc = 1.0 + (0.06 * back(c01((lt - 0.2) / 0.4)) if j == act else 0)
            elif j < act:
                sty, sc = "background:#e3f5ec;color:%s" % G, 0.92
            else:
                sty, sc = "background:#fff;color:#9aa9a2", 0.92
            num = "✓" if 0 <= j < act else str(j + 1)
            mmc = k.get("chain_mm", [""] * len(pats))[j]
            s += chip(lt, a, "<div class='pc' style='%s;transform:scale(%.3f)'><span class='pn'>%s</span><div><div>%s</div>%s</div></div>"
                      % (sty, sc, num, hl(ptn), "<div class='pcm'>%s</div>" % mmc if mmc else ""), "ic2")
        s += "</div>"
    elif ty == "grow":
        cols = ic.get("labels", ["A", "B"])
        s += "<div style='display:flex;gap:120px;align-items:flex-end;height:360px'>"
        for ci, lab in enumerate(cols):
            s += "<div style='display:flex;flex-direction:column;align-items:center;gap:16px'><div style='display:flex;gap:14px;align-items:flex-end;height:300px'>"
            for j in range(4):
                h = 60 + j * 60
                p = back(c01((lt - 0.3 - j * 0.35 - ci * 0.12) / 0.4))
                s += "<div style='width:46px;height:%.0fpx;border-radius:14px;background:%s'></div>" % (h * p, G if ci else "#7fd3b2")
            s += "</div><div class='lab2'>%s</div></div>" % lab
        s += "</div>"
        s += chip(lt, 1.7, "<div style='font-size:64px'>📈</div>")
    elif ty == "formula":
        parts = ic["parts"]
        s += "<div style='display:flex;gap:14px;align-items:center;flex-wrap:nowrap;justify-content:center'>"
        for j, (txt, sub) in enumerate(parts):
            if j:
                s += chip(lt, 0.25 + j * 0.45 - 0.15, "<span class='plus'>+</span>", "ic2")
            on = j == len(parts) - 1 or ic.get("on") == j
            s += chip(lt, 0.25 + j * 0.45, "<div class='blk%s'><div class='one'>%s</div><div class='bs'>%s</div></div>" % (" on" if on else "", hl(txt), hl(sub)), "ic2")
        s += "</div>"
    elif ty == "emoji":
        es = ic["e"]
        s += "<div style='display:flex;gap:40px;align-items:center'>"
        for j, e in enumerate(es):
            if j:
                s += chip(lt, 0.2 + j * 0.6 - 0.25, "<span style='font-size:70px;color:#9bbfb0'>→</span>", "ic2")
            wig = 6 * np.sin(lt * 5 + j) * c01((lt - 0.8 - j * 0.6) / 0.3)
            s += chip(lt, 0.2 + j * 0.6, "<div style='font-size:170px;transform:rotate(%.1fdeg) translateY(%.0fpx)'>%s</div>"
                      % (wig, 8 * np.sin(lt * 3 + j), e), "ic2")
        s += "</div>"
    elif ty in ("cross", "check"):
        bad = ty == "cross"
        sh = 14 * np.sin(lt * 40) * c01((lt - 0.7) / 0.05) * (1 - c01((lt - 1.0) / 0.3)) if bad else 0
        s += chip(lt, 0.15, "<div class='card big' style='transform:translateX(%.0fpx);%s'>%s</div>"
                  % (sh, "text-decoration:line-through;text-decoration-color:#e0453a;text-decoration-thickness:6px" if bad and lt > 0.75 else "", hl(ic["text"])), "ic2")
        st = back(c01((lt - 0.6) / 0.35))
        s += "<div class='stamp' style='background:%s;transform:scale(%.2f) rotate(-12deg);opacity:%.2f'>%s</div>" % (
            "#e0453a" if bad else G, 1.8 - 0.8 * st, c01((lt - 0.6) / 0.1), "✕" if bad else "✓")
    elif ty == "warn":
        p = back(c01((lt - 0.1) / 0.45))
        s += "<div style='font-size:220px;transform:scale(%.2f) rotate(%.1fdeg)'>⚠️</div>" % (0.4 + 0.6 * p, 8 * np.sin(lt * 9) * (1 - c01((lt - 0.9) / 0.4)))
    elif ty == "quiz":
        q = k["quiz"]
        reveal = ic.get("reveal", False)
        s += "<div class='card qz'><div class='qt'>%s</div>" % (hl(q["full"]) if reveal and lt > 0.2 else hl(q["q"]).replace("（　）", "<span style='color:%s'>（　）</span>" % G))
        for j, o in enumerate(q["opts"], 1):
            okk = j == q["ans"]
            if reveal:
                sty = "background:#e3f5ec;border-color:%s;color:%s" % (G, G) if okk else "opacity:.35"
                lab = ("✓ " if okk else "✕ ") + hl(o)
            else:
                sty, lab = "", "%d. %s" % (j, hl(o))
            s += chip(lt if not reveal else 9, 0.2 + j * 0.15, "<div class='opt' style='%s'>%s</div>" % (sty, lab), "ic3")
        s += "</div>"
        if ic.get("countdown"):
            cd0 = ic["cd0"]
            if lt >= cd0:
                n = 3 - int((lt - cd0) / 1.0)
                if n >= 1:
                    f = (lt - cd0) % 1.0
                    s += "<div class='cd' style='transform:scale(%.2f);opacity:%.2f'>%d</div>" % (1.5 - 0.5 * back(c01(f / 0.4)), 1 - c01((f - 0.7) / 0.3), n)
    elif ty == "rio":
        b = abs(np.sin(lt * 4)) * 22 * (1 - c01((lt - 1.5) / 0.5))
        s += chip(lt, 0.1, "<img src='file://%s/rio.png' style='width:300px;height:300px;border-radius:50%%;border:10px solid #fff;"
                  "box-shadow:0 14px 34px rgba(0,0,0,.12);transform:translateY(%.0fpx)'>" % (AV, -b), "ic2")
        for j in range(5):
            y = (lt * 120 + j * 90) % 420
            s += "<div style='position:absolute;left:%dpx;top:%.0fpx;font-size:54px;opacity:%.2f;color:#e0607e'>♡</div>" % (380 + j * 70 - 140, 520 - y, 0.8 * (1 - y / 420) * c01(lt - 0.4))
    return "<div class='iz'>%s</div>" % s


CSS = """
.iz{position:absolute;top:330px;left:0;right:0;height:620px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:34px}
.ic,.ic2,.ic3{display:inline-block}
.tag{display:inline-block;background:#fff;border-radius:30px;padding:10px 32px;font-family:Round;font-size:38px;color:%(G)s;box-shadow:0 8px 20px rgba(0,0,0,.06)}
.bigpill{background:%(G)s;color:#fff;border-radius:28px;padding:10px 40px;font-size:120px;font-weight:800;font-family:Round,My;min-height:150px}
.lab2{font-family:Round,My;font-size:44px;font-weight:700;color:#24493b}
.pc{display:flex;align-items:center;gap:20px;min-width:640px;border-radius:26px;padding:10px 34px;font-size:44px;text-align:left;font-weight:800;font-family:Round,My}
.pcm{font-family:My,Round;font-size:28px;font-weight:500;opacity:.9;margin-top:2px}
.pn{display:inline-flex;width:58px;height:58px;border-radius:50%%;background:rgba(255,255,255,.35);align-items:center;justify-content:center;font-size:34px}
.fl{font-size:40px;font-weight:700;color:#3a4a43;line-height:1.8;text-align:left;padding:10px 18px;border-radius:18px}
.fm{font-family:My,Round;font-size:28px;color:#5b6b64;line-height:1.6;text-align:left;padding:0 18px 6px}
.plus{font-size:70px;color:#e8a33d;font-weight:700}
.blk{background:#fff;border-radius:30px;padding:22px 0;width:250px;text-align:center;box-shadow:0 16px 34px rgba(20,60,45,.10);color:#173b2e}
.blk.on{background:%(G)s;color:#fff}
.blk .one{font-size:60px;font-weight:800;white-space:nowrap;padding:0 14px}
.blk .bs{font-family:My,Round;font-size:28px;opacity:.85;padding:0 10px}
.card.big{font-size:70px;font-weight:800;padding:34px 50px;color:#24493b}
.stamp{position:absolute;margin-left:440px;margin-top:-200px;width:150px;height:150px;border-radius:50%%;color:#fff;font-size:100px;font-weight:900;display:flex;align-items:center;justify-content:center}
.qz{width:900px;padding:34px 40px;text-align:left}
.qt{font-size:48px;font-weight:700;line-height:1.95;margin-bottom:14px}
.opt{width:820px;border:3px solid #dbe9e2;border-radius:22px;padding:12px 26px;margin-top:12px;font-size:42px;font-weight:700;background:#fff}
.cd{position:absolute;top:720px;left:0;right:0;text-align:center;font-family:Round;font-size:200px;font-weight:900;color:%(G)s}
.tx{position:absolute;top:%(T)dpx;left:70px;right:70px;display:flex;flex-direction:column;gap:34px}
.jp{text-align:center;font-size:58px;font-weight:700;color:#3a4a43;line-height:1.7}
.tk{display:inline-block}
.kk{display:inline-block;color:%(G)s;font-size:92px;font-weight:900;padding:0 14px;border-radius:18px;
    background-image:linear-gradient(rgba(43,181,130,.16),rgba(43,181,130,.16));background-repeat:no-repeat;background-position:left center}
.mm{padding:0 10px;text-align:center;font-family:My,Round;font-size:42px;color:#5b6b64;line-height:1.75}
.mt,.mb{display:inline-block}
.mb{color:%(G)s;font-weight:700}
"""


def full_html(b, lt, L):
    """whole passage: every sentence fades in, the one Rio is reading now is highlighted"""
    ls = b["lines"]
    ws = [weight(plain(j)) for j, m in ls]
    tot = sum(ws)
    out, acc = "", 0.0
    for (j, m), w in zip(ls, ws):
        a = 0.12 + L * acc / tot
        e = L * (acc + w) / tot + 0.12
        acc += w
        on = a <= lt < e
        o = 0.45 + 0.55 * c01((lt - a + 0.3) / 0.3) if lt < e else 0.75
        out += ("<div style='opacity:%.2f;transform:translateX(%.0fpx)'><div class='fl' style='background:%s'>%s</div><div class='fm'>%s</div></div>"
                % (o, 0 if lt > a else 20, "rgba(43,181,130,.14)" if on else "transparent", hl(re.sub(r"\[(.+?)\]", r"<b style='color:%s'>\1</b>" % G, j)), m))
    return "<div class='card' style='position:absolute;top:300px;left:50px;right:50px;padding:26px 24px'>%s</div>" % out


def beat_fn(b, L, d, k):
    hasjp = bool(b.get("jp"))
    if b.get("lines"):
        def ff(lt):
            out_e = c01((lt - (d - 0.35)) / 0.35)
            return "<style>%s</style><div style='opacity:%.2f'>%s</div>" % (CSS % {"G": G, "T": TOP_TXT, "T2": 0}, 1 - out_e, full_html(b, lt, L))
        return ff
    def f(lt):
        out_e = c01((lt - (d - 0.35)) / 0.35)
        s = icon(b.get("icon", {}), lt, d, k)
        txt = ""
        if hasjp:
            txt += jp_html(b, lt, L)
        if b.get("mm"):
            txt += mm_html(b, lt, 0.25 + L * 0.35 if hasjp else 0.2)
        ic = b.get("icon", {})
        tfade = 1 - c01((lt - ic["cd0"]) / 0.3) if ic.get("countdown") else 1   # countdown takes the text's place
        txt = "<div class='tx' style='opacity:%.2f'>%s</div>" % (tfade, txt)
        s = ("<div style='opacity:%.2f;transform:translateY(%.0fpx);filter:blur(%.1fpx)'>%s%s</div>"
             % (1 - out_e, -40 * ease(out_e), 6 * out_e, s, txt))
        return "<style>%s</style>%s" % (CSS % {"G": G, "T": TOP_TXT, "T2": TOP_TXT + 330}, s)
    return f


def timeline(k, L):
    tl, t = [], 0.0
    for i, b in enumerate(k["beats"]):
        key = "b%02d" % i
        Lb = L.get(key, 0.0)
        n_mm = len(mm_tokens(b.get("mm", "")))
        d = max(Lb + 0.7, 0.6 + n_mm * 0.3, 1.6) + b.get("hold", k.get("hold", 0.0))
        ic = b.get("icon", {})
        if ic.get("countdown"):
            ic["cd0"] = Lb + 0.4
            d = Lb + 0.4 + 3.2
        fx = [(0.0, "swish"), (0.1, "tick")]
        if "[" in b.get("jp", ""):
            toks = tokens(b["jp"]); ws = [weight(x) for x in toks]; tot = sum(ws); acc = 0
            for tok, w in zip(toks, ws):
                if tok.startswith("["):
                    fx.append((0.12 + Lb * 0.94 * acc / tot, "pop"))
                acc += w
        if ic.get("type") in ("cross", "check"):
            fx.append((0.6, "pop"))
        if ic.get("reveal"):
            fx.append((0.15, "ding"))
        if ic.get("countdown"):
            fx += [(ic["cd0"] + j, "tick") for j in range(3)]
        au = [(0.12, key)] if Lb else []
        tl.append((t, d, beat_fn(b, Lb, d, k), au, fx, b.get("part", 0)))
        t += d
    return tl, t + 0.3


async def _film(tl, total, tmp):
    from playwright.async_api import async_playwright
    exe = next((p for p in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(p)), None)
    async with async_playwright() as p:
        b = await (p.chromium.launch(executable_path=exe, args=["--allow-file-access-from-files"]) if exe else p.chromium.launch())
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        f = os.path.join(tmp, "f.html")
        n = int(round(total * FPS))
        shots = {min(n - 1, int((st + d - 0.5) * FPS)) for st, d, fn, au, fx, pt in tl}
        RX.QA["frames"].clear(); RX.QA["dom"].clear()
        for i in range(n):
            t = i / FPS
            idx = max(j for j, s in enumerate(tl) if s[0] <= t + 1e-9)
            st, d, fn, au, fx, pt = tl[idx]
            lt = min(t - st, d)
            open(f, "w", encoding="utf-8").write(RX.page(fn(lt), pt, 1.0, lt, t, 1080))
            await pg.goto("file://" + f)
            if i == 0:
                await pg.evaluate("document.fonts.ready")
            bad = await pg.evaluate(RX.FIT_JS)
            if bad:
                RX.QA["dom"].append((round(t, 1), bad))
            if i in shots:
                RX.QA["frames"].append(os.path.join(tmp, "%05d.jpg" % i))
            await pg.screenshot(path=os.path.join(tmp, "%05d.jpg" % i), type="jpeg", quality=90)
        await b.close()


def render(k, clips, out_path, tmp):
    clips = {kk: trim(v) for kk, v in clips.items()}
    L = {kk: len(v) / SR for kk, v in clips.items()}
    tl, total = timeline(k, L)
    total = round(total * FPS) / FPS
    y = np.zeros(int(total * SR) + SR, np.float32)
    for st, d, fn, au, fx, pt in tl:
        for a, kk in au:
            i = int((st + a) * SR)
            v = clips[kk][:len(y) - i]
            y[i:i + len(v)] += v
        for a, nm in fx:
            e = usfx(nm) * (0.6 if nm == "swish" else 1.0)
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
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
                    "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out_path)
    return total
