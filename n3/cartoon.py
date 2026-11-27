"""Cartoon-style dialogue videos (Ye 11/19, reference: "Useful English Cartoons").
A scene picture, two characters (Rio / Yui) who bounce when they talk, and subtitles (Japanese + furigana + Burmese).

Trigger n3/cartoon_trigger.txt:
  "ASSETS n"  -> only draw the missing pictures for content n (Gemini image model), push them for review
  "CT n"      -> draw what is missing, voice, render, send to the owner's Telegram DM
Content n3/cartoon_enc/NNN (encrypted like the others):
  {"no", "title", "tag", "assets": {name: {"prompt", "ref": "rio"|"yui"|None, "key": true for green-screen sprites}},
   "cast": {"Rio": {"img", "x", "y", "h", "flip"}, "Yui": {...}}, "bg": name,
   "lines": [{"who", "jp", "mm", "note"?, "emoji"?}], "recap": {"title", "items": [[jp, mm], ...], "say"}}
"""
import asyncio, base64, hashlib, io, json, os, re, shutil, subprocess, sys, tempfile, time, wave
import numpy as np
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import chat3 as C3
import render_explain as RX
from render_explain import c01, ease, back, hl, plain, G, SR, FPS, usfx, trim

D = C3.D
S = C3.S
ASSETS = os.path.join(HERE, "cartoon", "assets")
REFS = {"rio": os.path.join(ROOT, "steps", "rio.png"), "yui": os.path.join(ROOT, "steps", "yui.png")}
IMG_MODELS = ["gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-nano-banana-2.1", "gemini-3-pro-image", "nano-banana-pro-preview"]
STYLE = ("Clean modern 2D anime illustration style, soft pastel colors, simple flat shading, consistent thin outlines. "
         "No text, no letters, no logos, no watermark. ")


# ---------- pictures ----------
def ref_path(ref):
    """a reference picture: Rio / Yui, or an asset already drawn for an episode (keeps one look across pictures)"""
    return REFS.get(ref) or os.path.join(ASSETS, ref + ".png")


def local_cutout(png_bytes):
    """remove the background on the runner itself (rembg, CPU) - uses no image-service quota"""
    from rembg import remove
    from PIL import Image
    im = Image.open(io.BytesIO(remove(png_bytes))).convert("RGBA")
    bb = im.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
    if bb:
        im = im.crop(bb)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return buf.getvalue()


def gen_image(prompt, ref=None, aspect="9:16"):
    parts = [{"text": STYLE + prompt}]   # STYLE can be replaced per episode ("style" in the episode JSON)
    if ref:
        parts.append({"inline_data": {"mime_type": "image/png", "data": base64.b64encode(open(ref_path(ref), "rb").read()).decode()}})
    for model in IMG_MODELS:
        for cfg in ({"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": aspect}}, {"responseModalities": ["TEXT", "IMAGE"]}):
            try:
                r = requests.post(D.API % model, params={"key": D.GKEY}, json={"contents": [{"parts": parts}], "generationConfig": cfg}, timeout=180)
            except Exception as e:
                D.log("image", model, type(e).__name__)
                break
            if r.status_code == 400:
                D.log("image", model, 400, r.text[:200])
                continue
            if r.status_code != 200:
                D.log("image", model, r.status_code, r.text[:200])
                break
            for p in r.json().get("candidates", [{}])[0].get("content", {}).get("parts", []):
                if "inlineData" in p or "inline_data" in p:
                    d = p.get("inlineData") or p.get("inline_data")
                    D.log("image ok", model)
                    return base64.b64decode(d["data"])
            D.log("image", model, "no picture in answer")
            break
    return hf_image(prompt, ref, aspect)


def _read(res):
    """gradio_client results: a path, a dict with 'path'/'url', or a (image, seed) tuple"""
    if isinstance(res, (list, tuple)):
        res = res[0]
    if isinstance(res, dict):
        res = res.get("path") or res.get("url") or res.get("value")
        if isinstance(res, dict):
            res = res.get("path") or res.get("url")
    if isinstance(res, str) and res.startswith("http"):
        return requests.get(res, timeout=120).content
    return open(res, "rb").read()


def hf_image(prompt, ref=None, aspect="9:16"):
    """Gemini image models have no free quota (429), so draw with free Hugging Face Spaces (ZeroGPU)."""
    from gradio_client import Client, handle_file
    tok = os.environ.get("HF_TOKEN") or None
    last = None
    for attempt in range(3):
        try:
            if ref:
                cl = Client("mcp-tools/FLUX.1-Kontext-Dev", **({"token": tok} if tok else {}))
                res = cl.predict(input_image=handle_file(ref_path(ref)), prompt=prompt[:600], guidance_scale=2.5, steps=24,
                                 randomize_seed=True, api_name="/infer")
            else:
                cl = Client("mcp-tools/Qwen-Image-Fast", **({"token": tok} if tok else {}))
                if attempt == 0:
                    D.log("qwen api:", str(cl.view_api(print_info=False, return_format="dict"))[:600])
                res = cl.predict(prompt=STYLE + prompt, aspect_ratio=aspect, randomize_seed=True, api_name="/generate_image")
            D.log("hf image ok", "kontext" if ref else "qwen")
            return _read(res)
        except Exception as e:
            last = e
            D.log("hf image", attempt, type(e).__name__, str(e)[:300])
            time.sleep(20)
    raise RuntimeError("no image service could draw (%s): %s" % (last, prompt[:60]))


def hf_cutout(png_bytes):
    """remove the background of a character picture (free Space), cropped to the character"""
    from gradio_client import Client, handle_file
    from PIL import Image
    tmp = tempfile.mktemp(suffix=".png")
    open(tmp, "wb").write(png_bytes)
    cl = Client("not-lain/background-removal")
    res = cl.predict(handle_file(tmp), api_name="/png")
    im = Image.open(io.BytesIO(_read(res))).convert("RGBA")
    bb = im.getbbox()
    if bb:
        im = im.crop(bb)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return buf.getvalue()


def key_green(png_bytes):
    """green-screen sprite -> transparent PNG, cropped to the character"""
    from PIL import Image
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    a = np.array(im).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green = (g > 120) & (g > r + 35) & (g > b + 35)
    edge = (g > r + 10) & (g > b + 10) & ~green
    a[..., 3] = np.where(green, 0, 255)
    a[..., 1] = np.where(edge, np.maximum(r, b), g)          # remove green spill on the outline
    out = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    bb = out.getbbox()
    if bb:
        out = out.crop(bb)
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def ensure_assets(c):
    global STYLE
    if c.get("style"):
        STYLE = c["style"]
    os.makedirs(ASSETS, exist_ok=True)
    made = []
    for name, a in c["assets"].items():
        p = os.path.join(ASSETS, name + ".png")
        if os.path.exists(p):
            continue
        if a.get("src"):           # cut out a picture that was already drawn
            data = open(ref_path(a["src"]), "rb").read()
        else:
            base = STYLE
            STYLE = a.get("style", STYLE)     # e.g. a background must not get the "cute characters" part of the style
            try:
                data = gen_image(a["prompt"], a.get("ref"), a.get("aspect", "9:16"))
            finally:
                STYLE = base
        if a.get("key"):
            try:
                data = local_cutout(data)
            except Exception as e:
                D.log("local cutout failed", type(e).__name__, str(e)[:200])
                try:
                    data = hf_cutout(data)
                except Exception as e:
                    D.log("cutout service failed, using green key", type(e).__name__, str(e)[:200])
                    data = key_green(data)
        open(p, "wb").write(data)
        made.append(name)
        cwd = os.getcwd(); os.chdir(ROOT)
        D.push("cartoon asset %s" % name, ["n3/cartoon"])   # keep each picture even if a later one fails
        os.chdir(cwd)
        time.sleep(4)
    return made


# ---------- voice ----------
VV = "http://localhost:50021"


def vv_voice(c, wav):
    """VOICEVOX (free, no daily limit; engine runs as a service container). c["voicevox"] = {who: speaker name}"""
    for _ in range(90):
        try:
            if requests.get(VV + "/version", timeout=5).ok:
                break
        except Exception:
            pass
        time.sleep(5)
    sp = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in requests.get(VV + "/speakers", timeout=30).json()}
    lines = c["lines"] + ([{"who": "Rio", "jp": c["recap"]["say"]}] if c.get("recap", {}).get("say") else [])
    out = {}
    for i, l in enumerate(lines):
        name = c["voicevox"][l["who"]]
        style = l.get("style") or "ノーマル"
        sid = sp[name].get(style) or list(sp[name].values())[0]
        q = requests.post(VV + "/audio_query", params={"text": l.get("say") or plain(l["jp"]).replace(" ", ""), "speaker": sid}, timeout=120).json()
        q["speedScale"] = c.get("vv_speed", 1.0)
        q["prePhonemeLength"] = 0.05; q["postPhonemeLength"] = 0.1
        f = wav + ".%02d.wav" % i
        open(f, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q, timeout=300).content)
        out["l%02d" % i] = S.RS.R.pcm(f, 24000)
    D.log("voicevox ok", len(out))
    return out


def voice(c, wav):
    if c.get("voicevox"):
        return vv_voice(c, wav)
    lines = c["lines"] + ([{"who": "Rio", "jp": c["recap"]["say"]}] if c.get("recap", {}).get("say") else [])
    items = [{"key": "l%02d" % i, "who": l["who"], "jp": plain(l["jp"]).replace(" ", ""), "kana": ""} for i, l in enumerate(lines)]
    groups = [items[i:i + 7] for i in range(0, len(items), 7)]
    keys = [t["key"] for t in items]
    texts = [t["jp"] for t in items]
    h = hashlib.sha1(json.dumps([[t["who"], t["jp"]] for t in items], ensure_ascii=False).encode()).hexdigest()
    cw = os.path.join(HERE, "out", "cartoon_test_%03d.wav" % c["no"])
    cm = cw[:-4] + ".meta.json"
    if os.path.exists(cw) and os.path.exists(cm) and json.load(open(cm)).get("hash") == h:
        shutil.copy(cw, wav)
        y = S.RS.R.pcm(wav, 24000)
        bounds = json.load(open(cm))["bounds"]
        D.log("voice cache hit")
        return {k: y[int(bounds[i] * 24000):int(bounds[i + 1] * 24000)] for i, k in enumerate(keys)}
    bad = []
    for attempt in (1, 2):
        bounds = S.build_audio(groups, C3.P_MULTI, C3.P_ONE, wav)
        y = S.RS.R.pcm(wav, 24000)
        bad = C3.bad_lines(keys, texts, bounds, y)
        D.log("sync check", attempt, bad or "ok")
        if not bad:
            break
    if bad:
        D.WARN.append("voice/text may not match: " + " | ".join(bad)[:300])
    else:
        os.makedirs(os.path.dirname(cm), exist_ok=True)
        shutil.copy(wav, cw)
        json.dump({"hash": h, "bounds": list(map(float, bounds))}, open(cm, "w"))
    return {k: y[int(bounds[i] * 24000):int(bounds[i + 1] * 24000)] for i, k in enumerate(keys)}


# ---------- frames ----------
CSS = """
@font-face{font-family:Round;src:url('file://%(F)s/MPLUSRounded1c-Bold.ttf')}
@font-face{font-family:My;src:url('file://%(F)s/NotoSansMyanmar.ttf')}
body{margin:0;width:1080px;height:1920px;overflow:hidden;font-family:Round,My;background:#222}
.bg{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}
.ch{position:absolute;transform-origin:50%% 100%%}
.top{position:absolute;top:70px;left:40px;right:40px;text-align:center}
.tag{display:inline-block;background:rgba(255,255,255,.92);border-radius:30px;padding:10px 34px;font-size:40px;color:%(G)s;box-shadow:0 8px 20px rgba(0,0,0,.15)}
.sub{position:absolute;left:40px;right:40px;bottom:120px;background:rgba(255,255,255,.95);border-radius:36px;padding:28px 36px 30px;
     box-shadow:0 18px 40px rgba(0,0,0,.18);text-align:center}
.who{position:absolute;top:-34px;left:40px;border-radius:22px;padding:6px 26px;font-size:34px;color:#fff}
.jp{font-size:62px;font-weight:800;color:#1f2d27;line-height:1.75}
.mm{font-family:My,Round;font-size:40px;color:#46574f;line-height:1.6;margin-top:6px}
.note{display:inline-block;margin-top:14px;background:#fff6df;border-radius:18px;padding:8px 22px;font-family:My,Round;font-size:32px;color:#7a5a12}
rt{font-size:.58em;color:#0f5a3e;font-weight:800;letter-spacing:.02em}
.jp{line-height:1.95 !important}
.pill{background:%(G)s;color:#fff;border-radius:16px;padding:0 12px;white-space:nowrap}
.ta{color:#e0453a}
.bub{position:absolute;font-size:110px;filter:drop-shadow(0 8px 12px rgba(0,0,0,.2))}
.card{position:absolute;left:60px;right:60px;top:380px;background:rgba(255,255,255,.96);border-radius:40px;padding:40px 44px;box-shadow:0 20px 44px rgba(0,0,0,.2)}
.ttl{font-size:110px;font-weight:900;color:#fff;text-shadow:0 6px 0 %(G)s,0 10px 24px rgba(0,0,0,.35);line-height:1.2}
"""
COL = {"Rio": "#2d7bd6", "Yui": "#e0607e"}


def jp_size(jp):
    n = len(plain(jp).replace(" ", ""))
    return 62 if n <= 11 else 54 if n <= 14 else 46


def frame(c, ev, t, total):
    """ev: the event (line) active at time t"""
    F = os.path.join(ROOT, "fonts")
    s = "<img class='bg' src='file://%s/%s.png'>" % (ASSETS, c["bg"])
    kind = ev["kind"]
    lt = t - ev["st"]
    # characters
    for who, cfg in c["cast"].items():
        talk = kind == "line" and ev["who"] == who and lt < ev["L"] + 0.1
        bob = abs(np.sin(lt * 9)) * 14 if talk else 3 * np.sin(t * 2 + (0 if who == "Rio" else 1.5))
        et = cfg.get("_et", 0.2)            # a character can walk in later (cast "enter": line index)
        if t < et:
            continue
        enter = ease(c01((t - et) / 0.6))
        if t < et + 0.6:
            bob += abs(np.sin((t - et) * 16)) * 22   # running in
        dx = (1 - enter) * (-500 if cfg["x"] < 540 else 500)
        sc = 1.0 + (0.025 if talk else 0)
        s += ("<img class='ch' src='file://%s/%s.png' style='left:%dpx;top:%dpx;height:%dpx;transform:translate(%.0fpx,%.0fpx) scale(%s%.3f,%.3f);"
              "filter:brightness(%.2f)'>" % (ASSETS, cfg["img"], cfg["x"], cfg["y"], cfg["h"], dx, -bob, "-" if cfg.get("flip") else "", sc, sc,
                                               1.0 if talk or kind != "line" else 0.93))
    if kind == "title":
        p = back(c01((lt - 0.2) / 0.5))
        s += "<div class='top'><div class='tag' style='opacity:%.2f'>%s</div></div>" % (c01(lt / 0.3), c["tag"])
        s += ("<div style='position:absolute;top:300px;left:40px;right:40px;text-align:center;transform:scale(%.2f);opacity:%.2f'>"
              "<div class='ttl'>%s</div></div>" % (0.6 + 0.4 * p, c01((lt - 0.2) / 0.2), c["title_big"]))
    elif kind == "line":
        s += "<div class='top'><div class='tag'>%s</div></div>" % c["tag"]
        cfg = c["cast"][ev["who"]]
        if ev.get("emoji"):
            p = back(c01((lt - 0.3) / 0.4))
            bx = cfg["x"] + (cfg.get("bw", 300)) - 60
            s += "<div class='bub' style='left:%dpx;top:%dpx;transform:scale(%.2f);opacity:%.2f'>%s</div>" % (
                bx, cfg["y"] - 90, p, c01((lt - 0.3) / 0.15), ev["emoji"])
        e = ease(c01(lt / 0.25))
        note = ""
        if ev.get("note"):
            note = "<div class='note' style='opacity:%.2f'>💡 %s</div>" % (c01((lt - ev["L"] * 0.6 - 0.3) / 0.3), ev["note"])
        s += ("<div class='sub' style='opacity:%.2f;transform:translateY(%.0fpx)'><div class='who' style='background:%s'>%s</div>"
              "<div class='jp' style='font-size:%dpx'>%s</div><div class='mm' style='opacity:%.2f'>%s</div>%s</div>"
              % (e, (1 - e) * 40, COL[ev["who"]], c["cast"].get(ev["who"], {}).get("name", ev["who"]), jp_size(ev["jp"]), hl(ev["jp"]), c01((lt - 0.35) / 0.3), ev["mm"], note))
    elif kind == "recap":
        r = c["recap"]
        s += "<div style='position:absolute;inset:0;background:rgba(20,40,32,.35)'></div>"
        rows = ""
        for i, (j, m) in enumerate(r["items"]):
            o = c01((lt - 0.4 - i * 0.45) / 0.3)
            rows += ("<div style='opacity:%.2f;transform:translateX(%.0fpx);padding:14px 0;border-bottom:3px dashed #dcebe4'>"
                     "<div style='font-size:52px;font-weight:800;color:#1f2d27;line-height:1.7'>%s</div>"
                     "<div style='font-family:My,Round;font-size:34px;color:#46574f'>%s</div></div>" % (o, (1 - o) * 40, hl(j), m))
        s += ("<div class='card'><div style='font-size:48px;color:%s;font-weight:800;margin-bottom:10px'>%s</div>%s</div>"
              % (G, r["title"], rows))
    return "<html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>" % (CSS % {"F": F, "G": G}, s)


def plan(c, L):
    evs, t = [{"kind": "title", "st": 0.0, "d": 2.6}], 2.6
    for i, l in enumerate(c["lines"]):
        Li = L.get("l%02d" % i, 1.5)
        d = max(Li + 1.1, 2.4) + (1.2 if l.get("note") else 0)
        evs.append(dict(l, kind="line", st=t, d=d, L=Li, key="l%02d" % i))
        t += d
    for who, cfg in c["cast"].items():
        if cfg.get("enter") is not None:
            cfg["_et"] = evs[cfg["enter"] + 1]["st"]
    if c.get("recap"):
        n = len(c["lines"])
        Lr = L.get("l%02d" % n, 0)
        d = max(Lr + 1.5, 1.0 + 0.45 * len(c["recap"]["items"]) + 2.5)
        evs.append({"kind": "recap", "st": t, "d": d, "L": Lr, "key": "l%02d" % n if Lr else None})
        t += d
    return evs, t + 0.3


async def film(c, evs, total, tmp):
    from playwright.async_api import async_playwright
    exe = next((p for p in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(p)), None)
    async with async_playwright() as p:
        b = await (p.chromium.launch(executable_path=exe, args=["--allow-file-access-from-files"]) if exe else p.chromium.launch())
        pg = await b.new_page(viewport={"width": 1080, "height": 1920})
        f = os.path.join(tmp, "f.html")
        n = int(round(total * FPS))
        for i in range(n):
            t = i / FPS if i else 2.0          # cover frame = finished title
            ev = next(e for e in reversed(evs) if e["st"] <= t + 1e-9)
            open(f, "w", encoding="utf-8").write(frame(c, ev, t, total))
            await pg.goto("file://" + f)
            if i == 0:
                await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, "%05d.jpg" % i), type="jpeg", quality=90)
        await b.close()


def render(c, clips, out, tmp):
    clips = {k: trim(v) for k, v in clips.items()}
    L = {k: len(v) / SR for k, v in clips.items()}
    evs, total = plan(c, L)
    total = round(total * FPS) / FPS
    y = np.zeros(int(total * SR) + SR, np.float32)
    def put(at, v):
        i = int(at * SR); m = min(len(v), len(y) - i)
        if m > 0:
            y[i:i + m] += v[:m]
    put(0.2, usfx("wipe")); put(0.5, usfx("ding"))
    for e in evs:
        if e.get("key") in clips:
            put(e["st"] + 0.15, clips[e["key"]])
        if e["kind"] == "line":
            put(e["st"], usfx("tick") * 0.8)
            if e.get("emoji"):
                put(e["st"] + 0.3, usfx("pop"))
        if e["kind"] == "recap":
            put(e["st"], usfx("swish"))
            for i in range(len(c["recap"]["items"])):
                put(e["st"] + 0.4 + i * 0.45, usfx("pop") * 0.8)
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


def main():
    trig = open(os.path.join(HERE, "cartoon_trigger.txt"), encoding="utf-8").read()
    no = int(re.search(r"\d+", trig).group(0))
    c = C3.decrypt("cartoon_enc", no)
    made = ensure_assets(c)
    os.chdir(ROOT)
    if trig.startswith("ASSETS"):
        D.log("assets only", made)
        return
    if not c.get("voicevox"):
        C3.setup_voices()
    work = os.path.join(ROOT, "work", "n3"); os.makedirs(work, exist_ok=True)
    clips = voice(c, os.path.join(work, "ct_%03d.wav" % no))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out = os.path.join(HERE, "out", "cartoon_test_%03d.mp4" % no)
    secs = render(c, clips, out, tempfile.mkdtemp())
    D.push("n3 cartoon test %03d" % no, ["n3/out", "n3/cartoon"])
    import explain as EX
    cap = "🧪 cartoon test No.%d %s (%ds)" % (no, c["title"], secs)
    if c.get("voicevox"):
        cap += "\n" + " / ".join("VOICEVOX:" + v for v in dict.fromkeys(c["voicevox"].values()))
    if D.WARN:
        cap += "\n⚠️ " + " / ".join(D.WARN)[:300]
    EX.send(out, cap)
    D.log(cap, D.WARN)


if __name__ == "__main__":
    main()
