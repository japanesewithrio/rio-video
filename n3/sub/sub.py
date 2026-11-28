"""Japanese + Burmese dual subtitles for a finished video (Ye 11/28, eJLS-style).

ONLY for our own videos, or for videos whose owner has given written permission.

Steps (python n3/sub/sub.py STEP NAME), job settings in n3/sub/jobs/NAME.json:
  asr     video -> Japanese lines with times (faster-whisper)        -> n3/sub/jobs/NAME.segs.json
  tr      Japanese lines -> fixed Japanese with furigana + Burmese     (Gemini; same file, adds jp/mm)
  render  burns the subtitles                                          -> n3/sub/out/NAME.mp4 (own) / Telegram
  all     asr + tr + render

Job JSON:
  {"src": "n3/out/x.mp4" | "url": "https://...",   # file in repo (own videos) or a direct download link
   "own": true,                 # false = licensed video: never committed to this public repo, sent by Telegram only
   "mode": "band" | "land",     # band = 9:16 reel, video in the middle; land = keep 16:9, subtitles at the bottom
   "title": "Burmese hook line (| = line break)", "credit": "原作：マリマリマリー（YouTube）",
   "names": {"かなめ": "Kaname"}, "context": "short story notes that help the translation",
   "model": "medium", "from": 0, "to": null}
segs.json can be edited by hand between steps (fix a Japanese word or a Burmese line, then run render).
"""
import asyncio, json, os, re, subprocess, sys, tempfile, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FONTS = os.path.join(ROOT, "fonts")
W, H = 1080, 1920
BT, BH = 560, 608           # band mode: picture top and height


def sh(*a):
    subprocess.run(a, check=True)


def job(name):
    j = json.load(open(os.path.join(HERE, "jobs", name + ".json"), encoding="utf-8"))
    j.setdefault("mode", "band")
    j.setdefault("own", True)
    return j


def segs_path(name):
    return os.path.join(HERE, "jobs", name + ".segs.json")


def source(j, tmp):
    if j.get("src"):
        return os.path.join(ROOT, j["src"])
    f = os.path.join(tmp, "src.mp4")
    with requests.get(j["url"], stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(f, "wb") as o:
            for ch in r.iter_content(1 << 20):
                o.write(ch)
    return f


def duration(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).decode().strip())


# ---------------------------------------------------------------- 1. speech -> Japanese lines
def asr(name, tmp):
    from faster_whisper import WhisperModel
    j = job(name)
    src = source(j, tmp)
    wav = os.path.join(tmp, "a.wav")
    cut = ["-ss", str(j.get("from", 0))] + (["-to", str(j["to"])] if j.get("to") else [])
    sh("ffmpeg", "-v", "error", "-y", *cut, "-i", src, "-ac", "1", "-ar", "16000", wav)
    m = WhisperModel(j.get("model", "medium"), device="cpu", compute_type="int8")
    out = []
    import wave, numpy as np        # numpy input: faster-whisper's own decoder breaks with new PyAV
    w = wave.open(wav)
    audio = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    segs, _ = m.transcribe(audio, language="ja", vad_filter=True, word_timestamps=True,
                           initial_prompt="、。！？を使った自然な日本語の会話。")
    for s in segs:
        # split long segments at 。！？ so each subtitle stays short
        cur, st = "", None
        for w in s.words:
            if st is None:
                st = w.start
            cur += w.word
            if re.search(r"[。！？!?]$", w.word.strip()) and len(cur) >= 6:
                out.append({"st": round(st, 2), "en": round(w.end, 2), "asr": cur.strip()})
                cur, st = "", None
        if cur.strip():
            out.append({"st": round(st, 2), "en": round(s.words[-1].end, 2), "asr": cur.strip()})
    json.dump(out, open(segs_path(name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("asr lines:", len(out))
    for s in out:
        print("%6.2f %6.2f %s" % (s["st"], s["en"], s["asr"]))


# ---------------------------------------------------------------- 2. fix + furigana + Burmese
PROMPT = """You subtitle a Japanese comedy anime for Burmese learners of Japanese (channel: Learn with Rio).
Below are speech-recognition lines (may contain mistakes) with times. Context: %s
Character names: %s

For EVERY line return an object {"i": index, "who": speaker name or "", "jp": ..., "mm": ...}:
- jp: the corrected Japanese line exactly as spoken (fix recognition mistakes from context; keep it natural,
  don't add words). Add furigana after every kanji word in this format: 漢字《かんじ》, e.g. 部長《ぶちょう》、今日《きょう》.
- mm: natural, spoken, funny Burmese (Myanmar Unicode) that a young Burmese person would really say,
  not word-for-word. Keep jokes and tone. Short enough to read in the line's time.
Return only a JSON array.

LINES:
%s"""


def gemini(prompt):
    key = os.environ["GEMINI_API_KEY"]
    for model in ["gemini-2.5-pro", "gemini-2.5-flash"]:
        for _ in range(3):
            r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model,
                              params={"key": key}, timeout=600,
                              json={"contents": [{"parts": [{"text": prompt}]}],
                                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}})
            if r.ok:
                return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"])
            print(model, r.status_code, r.text[:200])
            time.sleep(20)
    raise RuntimeError("gemini failed")


def tr(name):
    j = job(name)
    segs = json.load(open(segs_path(name), encoding="utf-8"))
    for a in range(0, len(segs), 60):       # 60 lines per call keeps the JSON reliable
        part = segs[a:a + 60]
        lines = "\n".join("%d [%.1f-%.1f] %s" % (a + k, s["st"], s["en"], s["asr"]) for k, s in enumerate(part))
        res = gemini(PROMPT % (j.get("context", ""), json.dumps(j.get("names", {}), ensure_ascii=False), lines))
        for r in res:
            i = int(r["i"])
            if a <= i < a + len(part):
                segs[i].update(jp=r.get("jp", segs[i]["asr"]), mm=r.get("mm", ""), who=r.get("who", ""))
    json.dump(segs, open(segs_path(name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for s in segs:
        print("%6.2f %s | %s" % (s["st"], s.get("jp"), s.get("mm")))


# ---------------------------------------------------------------- 3. burn the subtitles
def ruby(s):
    s = s.replace("<", "&lt;")
    return re.sub(r"([一-龯々〆ヶ]+)《(.+?)》", r"<ruby>\1<rt>\2</rt></ruby>", s)


CSS = """@font-face{font-family:Round;src:url('file://%(F)s/MPLUSRounded1c-Bold.ttf')}
@font-face{font-family:My;src:url('file://%(F)s/NotoSansMyanmar.ttf')}
html,body{margin:0;background:transparent}
body{width:%(w)dpx;height:%(h)dpx;position:relative;overflow:hidden;font-family:Round,My}
.box{position:absolute;left:30px;right:30px;text-align:center}
.mm{font-family:My;color:#fff;line-height:1.6;text-shadow:0 0 6px #000,0 0 3px #000,2px 2px 0 #000;text-wrap:balance}
.jp{font-family:Round;color:#fff;line-height:1.45;-webkit-text-stroke:%(stroke)dpx #000;paint-order:stroke fill;text-wrap:balance}
.jp rt{font-size:.45em;color:#ffe08a;-webkit-text-stroke:%(rstroke)dpx #000}
.title{position:absolute;top:200px;left:40px;right:40px;text-align:center;font-family:My,Round;color:#fff;font-size:48px;line-height:1.5;text-wrap:balance}
.title span{white-space:nowrap}
.credit{position:absolute;left:0;right:0;text-align:center;font-family:Round,My;color:#aaa;font-size:30px}
"""


def jp_px(jp, base):
    n = len(re.sub(r"《.+?》", "", jp))
    return base if n <= 14 else max(int(base * 14 / n), int(base * 0.62))


def sub_html(j, s):
    if j["mode"] == "band":
        css = CSS % {"F": FONTS, "w": W, "h": H, "stroke": 10, "rstroke": 5}
        top = BT + BH + 50
        body = "<div class='box' style='top:%dpx'>" % top
        if s:
            body += "<div class='mm' style='font-size:42px'>%s</div>" % s.get("mm", "")
            body += "<div class='jp' style='font-size:%dpx;margin-top:18px'>%s</div>" % (jp_px(s["jp"], 70), ruby(s["jp"]))
        body += "</div>"
        return "<html><head><style>%s</style></head><body>%s</body></html>" % (css, body)
    css = CSS % {"F": FONTS, "w": 1920, "h": 1080, "stroke": 9, "rstroke": 4}
    body = "<div class='box' style='bottom:40px'>"
    if s:
        body += "<div class='mm' style='font-size:40px'>%s</div>" % s.get("mm", "")
        body += "<div class='jp' style='font-size:%dpx;margin-top:8px'>%s</div>" % (jp_px(s["jp"], 66), ruby(s["jp"]))
    body += "</div>"
    return "<html><head><style>%s</style></head><body>%s</body></html>" % (css, body)


def frame_html(j):
    """band mode: the still parts (title above the picture, credit at the bottom)."""
    css = CSS % {"F": FONTS, "w": W, "h": H, "stroke": 10, "rstroke": 5}
    t = "<br>".join("<span>%s</span>" % x for x in j.get("title", "").split("|"))
    return ("<html><head><style>%s body{background:#111}</style></head><body><div class='title'>%s</div>"
            "<div class='credit' style='top:1840px'>%s</div></body></html>" % (css, t, j.get("credit", "")))


async def shots(j, segs, tmp):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        exe = next((x for x in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable") if os.path.exists(x)), None)
        b = await p.chromium.launch(**({"executable_path": exe} if exe else {}), args=["--allow-file-access-from-files"])
        vw, vh = (W, H) if j["mode"] == "band" else (1920, 1080)
        pg = await b.new_page(viewport={"width": vw, "height": vh})
        f = os.path.join(tmp, "s.html")
        todo = [("blank", None)] + [("%04d" % i, s) for i, s in enumerate(segs)]
        for name, s in todo:
            open(f, "w", encoding="utf-8").write(sub_html(j, s))
            await pg.goto("file://" + f)
            await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, name + ".png"), omit_background=True)
        if j["mode"] == "band":
            open(f, "w", encoding="utf-8").write(frame_html(j))
            await pg.goto("file://" + f)
            await pg.evaluate("document.fonts.ready")
            await pg.screenshot(path=os.path.join(tmp, "frame.png"))
        await b.close()


def render(name, tmp):
    j = job(name)
    segs = [s for s in json.load(open(segs_path(name), encoding="utf-8")) if s.get("jp")]
    src = source(j, tmp)
    a0 = float(j.get("from", 0))
    total = (float(j["to"]) if j.get("to") else duration(src)) - a0
    asyncio.run(shots(j, segs, tmp))
    # subtitle track: blank / line / blank ... as an image list with durations (alpha kept)
    lst, t = [], 0.0
    for i, s in enumerate(segs):
        st = max(s["st"], t)
        en = s["en"] + 0.25
        if i + 1 < len(segs):
            en = min(en, segs[i + 1]["st"])
        if st - t > 0.01:
            lst.append(("blank", st - t))
        lst.append(("%04d" % i, max(en - st, 0.3)))
        t = st + max(en - st, 0.3)
    if total - t > 0.01:
        lst.append(("blank", total - t))
    with open(os.path.join(tmp, "subs.txt"), "w") as o:
        for n, d in lst:
            o.write("file '%s'\nduration %.3f\n" % (os.path.join(tmp, n + ".png"), d))
        o.write("file '%s'\n" % os.path.join(tmp, lst[-1][0] + ".png"))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out = os.path.join(HERE, "out", name + ".mp4") if j["own"] else os.path.join(tmp, name + ".mp4")
    cut = ["-ss", str(a0), "-t", "%.3f" % total]
    if j["mode"] == "band":
        fg = ("[0:v]scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=black[v];"
              "[2:v][v]overlay=0:%d[b];[b][1:v]overlay=0:0:eof_action=pass,format=yuv420p[o]" % (W, BH, W, BH, BT))
        ins = [*cut, "-i", src, "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "subs.txt"),
               "-loop", "1", "-i", os.path.join(tmp, "frame.png")]
    else:
        fg = "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2[v];[v][1:v]overlay=0:0:eof_action=pass,format=yuv420p[o]"
        ins = [*cut, "-i", src, "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "subs.txt")]
    sh("ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", fg, "-map", "[o]", "-map", "0:a?",
       "-t", "%.3f" % total, "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
       "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out)
    print("rendered", out, "%.1fs" % total)
    tg = os.environ.get("TG_TOKEN")
    if tg and os.environ.get("TG_CHAT"):
        cap = "🎬 subtitles: %s (%d lines)" % (name, len(segs))
        r = requests.post("https://api.telegram.org/bot%s/sendVideo" % tg, timeout=600,
                          data={"chat_id": os.environ["TG_CHAT"], "caption": cap, "supports_streaming": "true"},
                          files={"video": open(out, "rb")})
        print("telegram", r.status_code)


if __name__ == "__main__":
    step, name = sys.argv[1], sys.argv[2]
    with tempfile.TemporaryDirectory() as tmp:
        if step in ("asr", "all"):
            asr(name, tmp)
        if step in ("tr", "all"):
            tr(name)
        if step in ("render", "all"):
            render(name, tmp)
