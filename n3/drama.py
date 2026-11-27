"""Story drama videos (Ye 11/27, reference: Korean web-animation stories dubbed in Burmese).

A 16:9 picture band in a 9:16 frame, a fixed hook title above it, Japanese subtitles (+ furigana) and Burmese
below it. Japanese lines are voiced with VOICEVOX; narration ("narr") and inner thoughts ("think") are
Burmese text only. Each line is a shot: background + characters + camera move + effects, or an
AI-animated clip (image-to-video) for the key moments.

Episode JSON (cartoon_enc/NNN):
  {"no", "title", "hook", "ep", "voicevox": {who: speaker}, "names": {who: display name}, "assets": {...},
   "lines": [{"who"|"narr"|"think", "jp"?, "mm", "note"?, "bg", "chars": [[img, cx, h, top?, flip?]],
              "cam": [z0, z1, fx, fy], "fx": ["sparkle"|"heart"|"sweat"|"lines"|"shake"], "clip"?}],
   "recap": {"title", "items": [[jp, mm]]}}
"""
import asyncio, os, re, subprocess, tempfile, time, wave
import numpy as np
import requests
import cartoon as CT
from cartoon import ASSETS, HERE, ROOT, D, S, C3, c01, ease, back, hl, plain, SR, FPS, usfx, trim

W, BH, BT = 1080, 608, 470          # picture band: width, height, top
COL = ["#e0607e", "#2d7bd6", "#c07a2a", "#5a9e4b"]


def voices(c, work):
    for _ in range(90):
        try:
            if requests.get(CT.VV + "/version", timeout=5).ok:
                break
        except Exception:
            pass
        time.sleep(5)
    sp = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in requests.get(CT.VV + "/speakers", timeout=30).json()}
    out = {}
    for i, l in enumerate(c["lines"]):
        if not l.get("who"):
            continue
        name = c["voicevox"][l["who"]]
        sid = sp[name].get(l.get("style") or "ノーマル") or list(sp[name].values())[0]
        q = requests.post(CT.VV + "/audio_query", params={"text": l.get("say") or plain(l["jp"]).replace(" ", ""), "speaker": sid}, timeout=120).json()
        q["speedScale"] = c.get("vv_speed", 1.0)
        q["prePhonemeLength"] = 0.05; q["postPhonemeLength"] = 0.1
        f = os.path.join(work, "dr_%02d.wav" % i)
        open(f, "wb").write(requests.post(CT.VV + "/synthesis", params={"speaker": sid}, json=q, timeout=300).content)
        out[i] = trim(S.RS.R.pcm(f, 24000))
    D.log("voicevox ok", len(out))
    return out


def plan(c, V):
    evs, t = [], 0.0
    for i, l in enumerate(c["lines"]):
        if i in V:
            L = len(V[i]) / SR
            d = max(L + 0.9, 2.2) + (1.0 if l.get("note") else 0)
        else:
            L = 0
            d = min(4.5, 1.6 + len(l.get("mm", "")) / 16.0)
        evs.append(dict(l, kind="line", st=t, d=d, L=L, i=i))
        t += d
    if c.get("recap"):
        d = 1.5 + 0.6 * len(c["recap"]["items"]) + 2.5
        evs.append({"kind": "recap", "st": t, "d": d})
        t += d
    return evs, t + 0.2


CSS = """
@font-face{font-family:Round;src:url('file://%(F)s/MPLUSRounded1c-Bold.ttf')}
@font-face{font-family:My;src:url('file://%(F)s/NotoSansMyanmar.ttf')}
body{margin:0;width:1080px;height:1920px;overflow:hidden;font-family:Round,My;background:#111}
.hook{position:absolute;top:170px;left:40px;right:40px;text-align:center;font-family:My,Round;color:#fff;font-size:50px;line-height:1.5}
.ep{display:inline-block;background:#e0607e;color:#fff;border-radius:14px;padding:2px 18px;font-family:Round;font-size:34px;margin-bottom:10px}
.band{position:absolute;left:0;top:%(BT)dpx;width:1080px;height:%(BH)dpx;overflow:hidden;background:#000}
.world{position:absolute;left:0;top:0;width:1080px;height:%(BH)dpx;transform-origin:0 0}
.bg{position:absolute;left:0;top:0;width:1080px;height:%(BH)dpx;object-fit:cover}
.ch{position:absolute;transform-origin:50%% 100%%}
.cap{position:absolute;left:26px;top:22px;max-width:760px;background:rgba(20,20,20,.78);color:#fff;border-radius:16px;padding:10px 24px;font-family:My;font-size:36px;line-height:1.55}
.think{position:absolute;left:60px;right:60px;bottom:26px;text-align:center}
.think span{display:inline-block;background:rgba(255,255,255,.93);border-radius:30px;padding:12px 30px;font-family:My;font-size:38px;line-height:1.55;color:#333;box-shadow:0 6px 16px rgba(0,0,0,.25)}
.fx{position:absolute;font-size:86px;filter:drop-shadow(0 6px 10px rgba(0,0,0,.25))}
.lines{position:absolute;inset:0;background:repeating-conic-gradient(from 0deg at 50%% 50%%,rgba(255,255,255,0) 0deg 5deg,rgba(255,255,255,.55) 5deg 6deg);
       -webkit-mask:radial-gradient(circle at 50%% 50%%,transparent 34%%,#000 70%%)}
.sub{position:absolute;left:40px;right:40px;top:%(SUBT)dpx;text-align:center;color:#fff}
.who{display:inline-block;border-radius:20px;padding:4px 24px;font-size:34px;color:#fff;margin-bottom:16px}
.jp{line-height:1.5}
.jp rt{font-size:.5em;color:#ffe08a}
.pill{background:#3fbf7f;color:#fff;border-radius:14px;padding:0 12px}
.ta{color:#ff6b6b}
.mm{font-family:My;font-size:40px;color:#d9d9d9;margin-top:14px;line-height:1.6}
.note{display:inline-block;margin-top:18px;background:#fff6df;border-radius:18px;padding:8px 22px;font-family:My,Round;font-size:32px;color:#7a5a12}
.recap{position:absolute;left:50px;right:50px;top:440px;background:#fff;border-radius:40px;padding:40px 46px;box-shadow:0 20px 50px rgba(0,0,0,.4)}
.recap h2{margin:0 0 26px;font-size:54px;color:#2a9d5f}
.ri{border-bottom:2px dashed #e5e5e5;padding:16px 0}
.ri .j{font-size:50px;color:#222}.ri .j rt{font-size:.5em;color:#888}
.ri .m{font-family:My;font-size:36px;color:#555;margin-top:4px}
"""


def jp_size(s):
    n = len(plain(s))
    return 64 if n <= 14 else 56 if n <= 20 else 48


def frame(c, ev, t, total):
    F = os.path.join(ROOT, "fonts")
    css = CSS % {"F": F, "BT": BT, "BH": BH, "SUBT": BT + BH + 70}
    s = "<html><head><meta charset='utf-8'><style>%s</style></head><body>" % css
    s += "<div class='hook'><div class='ep'>%s</div><br>%s</div>" % (c.get("ep", ""), c["hook"])
    lt = t - ev["st"]
    if ev["kind"] == "recap":
        r = c["recap"]
        p = back(c01(lt / 0.5))
        s += "<div class='recap' style='transform:scale(%.3f);opacity:%.2f'><h2>%s</h2>" % (0.7 + 0.3 * p, c01(lt / 0.25), r["title"])
        for k, (j, m) in enumerate(r["items"]):
            e = ease(c01((lt - 0.5 - k * 0.6) / 0.35))
            s += "<div class='ri' style='opacity:%.2f;transform:translateX(%.0fpx)'><div class='j'>%s</div><div class='m'>%s</div></div>" % (e, (1 - e) * 60, hl(j), m)
        return s + "</div></body></html>"
    # ----- picture band -----
    s += "<div class='band'>"
    cf = ev.get("_cf")
    if cf:
        s += "<img class='bg' src='file://%s'>" % cf[min(int(lt * FPS), len(cf) - 1)]
    else:
        z0, z1, fx, fy = ev.get("cam") or [1.0, 1.06, 0.5, 0.5]
        k = ease(c01(lt / max(ev["d"], 0.1)))
        z = z0 + (z1 - z0) * k
        ox, oy = fx * W * (1 - z), fy * BH * (1 - z)
        if "shake" in ev.get("fx", []) and lt < 0.6:
            ox += np.sin(lt * 70) * 14 * (1 - lt / 0.6)
            oy += np.cos(lt * 63) * 8 * (1 - lt / 0.6)
        s += "<div class='world' style='transform:translate(%.1fpx,%.1fpx) scale(%.4f)'>" % (ox, oy, z)
        s += "<img class='bg' src='file://%s/%s.png'>" % (ASSETS, ev["bg"])
        talker = ev.get("who")
        for n, ch in enumerate(ev.get("chars", [])):
            img, cx, h = ch[0], ch[1], ch[2]
            top = ch[3] if len(ch) > 3 else 0.06
            flip = len(ch) > 4 and ch[4]
            hp = h * BH
            breathe = 1 + 0.008 * np.sin(t * 2.2 + n)
            ent = ease(c01(lt / 0.35)) if ev.get("pop") else 1
            s += ("<img class='ch' src='file://%s/%s.png' style='height:%.0fpx;top:%.0fpx;left:%.0fpx;"
                  "transform:translateX(-50%%) translateY(%.0fpx) scale(%s%.4f,%.4f);opacity:%.2f'>"
                  % (ASSETS, img, hp, top * BH, cx * W, (1 - ent) * 40, "-" if flip else "", breathe, breathe, ent))
        s += "</div>"
        for f in ev.get("fx", []):
            if f == "lines":
                s += "<div class='lines' style='opacity:%.2f'></div>" % (0.9 * c01(lt / 0.15) * (1 - c01((lt - 1.2) / 0.4)))
            elif f in ("sparkle", "heart", "sweat"):
                em = {"sparkle": "✨", "heart": "💗", "sweat": "💦"}[f]
                pts = [(0.18, 0.22), (0.8, 0.18), (0.72, 0.62), (0.28, 0.66)] if f != "sweat" else [(0.64, 0.2)]
                for q, (px, py) in enumerate(pts):
                    a = c01((lt - 0.15 * q) / 0.3)
                    dy = -20 * lt if f == "heart" else 0
                    sc = 0.8 + 0.25 * np.sin(lt * 6 + q)
                    s += "<div class='fx' style='left:%.0fpx;top:%.0fpx;opacity:%.2f;transform:scale(%.2f)'>%s</div>" % (px * W, py * BH + dy, a, sc, em)
    if ev.get("narr"):
        s += "<div class='cap' style='opacity:%.2f'>%s</div>" % (c01(lt / 0.25), ev["mm"])
    if ev.get("think"):
        e = ease(c01(lt / 0.3))
        s += "<div class='think' style='opacity:%.2f;transform:translateY(%.0fpx)'><span>%s</span></div>" % (e, (1 - e) * 20, ev["mm"])
    s += "</div>"
    # ----- subtitles under the band (spoken lines) -----
    if ev.get("who"):
        who = ev["who"]
        col = COL[list(c["voicevox"]).index(who) % len(COL)]
        e = ease(c01(lt / 0.25))
        note = ""
        if ev.get("note"):
            note = "<br><div class='note' style='opacity:%.2f'>💡 %s</div>" % (c01((lt - ev["L"] * 0.6 - 0.3) / 0.3), ev["note"])
        s += ("<div class='sub' style='opacity:%.2f;transform:translateY(%.0fpx)'><div class='who' style='background:%s'>%s</div>"
              "<div class='jp' style='font-size:%dpx'>%s</div><div class='mm' style='opacity:%.2f'>%s</div>%s</div>"
              % (e, (1 - e) * 30, col, c.get("names", {}).get(who, who), jp_size(ev["jp"]), hl(ev["jp"]),
                 c01((lt - 0.35) / 0.3), ev["mm"], note))
    return s + "</body></html>"


async def film(c, evs, total, tmp):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        exe = next((x for x in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(x)), None)
        b = await p.chromium.launch(**({"executable_path": exe} if exe else {}), args=["--allow-file-access-from-files"])
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        f = os.path.join(tmp, "f.html")
        n = int(round(total * FPS))
        for i in range(n):
            t = i / FPS
            ev = next(e for e in reversed(evs) if e["st"] <= t + 1e-9)
            open(f, "w", encoding="utf-8").write(frame(c, ev, t, total))
            await pg.goto("file://" + f)
            if i == 0:
                await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, "%05d.jpg" % i), type="jpeg", quality=90)
        await b.close()


def render(c, V, out, tmp):
    evs, total = plan(c, V)
    total = round(total * FPS) / FPS
    y = np.zeros(int(total * SR) + SR, np.float32)

    def put(at, v):
        i = int(at * SR); m = min(len(v), len(y) - i)
        if m > 0:
            y[i:i + m] += v[:m]
    put(0.1, usfx("whoosh") * 0.7)
    for e in evs:
        if e["kind"] == "recap":
            put(e["st"], usfx("swish"))
            for k in range(len(c["recap"]["items"])):
                put(e["st"] + 0.5 + k * 0.6, usfx("pop") * 0.8)
            continue
        if e["i"] in V:
            put(e["st"] + 0.15, V[e["i"]])
        fx = e.get("fx", [])
        if "lines" in fx or "shake" in fx:
            put(e["st"], usfx("whoosh") * 0.9)
        elif "sparkle" in fx or "heart" in fx:
            put(e["st"] + 0.15, usfx("ding") * 0.6)
        elif e.get("narr"):
            put(e["st"], usfx("wipe") * 0.5)
        if e.get("clip"):
            d = os.path.join(tmp, "clip_%02d" % e["i"]); os.makedirs(d, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(HERE, "i2v", "out", e["clip"]), "-vf",
                            "fps=%d,scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,unsharp=5:5:0.6" % (FPS, W, BH, W, BH),
                            "-q:v", "2", os.path.join(d, "%04d.jpg")], check=True)
            e["_cf"] = sorted(os.path.join(d, f) for f in os.listdir(d))
    y = y[:int(total * SR)]
    asyncio.run(film(c, evs, total, tmp))
    wv = os.path.join(tmp, "mix.wav")
    with wave.open(wv, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%05d.jpg"), "-i", wv,
                    "-c:v", "libx264", "-crf", "20", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out],
                   check=True)
    return total


def main(c):
    no = c["no"]
    work = os.path.join(ROOT, "work", "n3"); os.makedirs(work, exist_ok=True)
    V = voices(c, work)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out = os.path.join(HERE, "out", "drama_test_%03d.mp4" % no)
    secs = render(c, V, out, tempfile.mkdtemp())
    D.push("n3 drama test %03d" % no, ["n3/out"])
    import explain as EX
    cap = "🧪 drama test No.%d %s (%ds)\n%s" % (no, c["title"], secs, " / ".join("VOICEVOX:" + v for v in dict.fromkeys(c["voicevox"].values())))
    EX.send(out, cap)
    D.log(cap)
