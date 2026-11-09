"""N3 chat-style grammar video (Ye 11/09): Rio & Yui talk -> short 📝 notes -> なる vs する -> ⚠️ cautions -> 📖 word note
-> JLPT 問題 (3-2-1) -> answer + why the other 3 are wrong (one example each) -> follow outro.
Frames are HTML pages screenshotted with Chrome (playwright); the newest element slides in over 5 frames."""
import asyncio, json, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.environ.get("RIO_FONTS", os.path.join(ROOT, "fonts"))
AV = os.path.join(ROOT, "steps")
SR, FPS, W, H = 24000, 30, 1080, 1920
B = "#2558b8"
SFX_GAIN = 0.5
ANIM = [0.25, 0.5, 0.75, 0.92]          # progress of the newest element in the first frames of a beat

CSS = """@font-face{font-family:My;src:url('file://%(F)s/NotoSansMyanmar.ttf')}
@font-face{font-family:Round;src:url('file://%(F)s/MPLUSRounded1c-Bold.ttf')}
*{box-sizing:border-box} body{margin:0;width:1080px;height:1920px;font-family:'Noto Sans CJK JP','Noto Sans JP',My,sans-serif;
background:linear-gradient(180deg,#eef4ff,#fff 55%%,#fff2f7);color:#17202c;overflow:hidden;position:relative}
.top{position:absolute;top:150px;left:60px;right:150px;display:flex;justify-content:space-between;align-items:center;font-family:Round,My;color:%(B)s;font-size:34px}
.chip{background:%(B)s;color:#fff;border-radius:40px;padding:4px 22px;font-size:28px}
.bar{position:absolute;top:212px;left:60px;right:150px;height:10px;background:#e3e9f3;border-radius:6px} .bar i{display:block;height:100%%;background:#3bbf6b;border-radius:6px}
.wrap{position:absolute;top:250px;left:60px;right:150px}
.row{display:flex;gap:22px;margin-bottom:24px;align-items:flex-start} .row.r{flex-direction:row-reverse}
.av{width:120px;height:120px;border-radius:50%%;object-fit:cover;border:5px solid #fff;box-shadow:0 4px 14px rgba(0,0,0,.12);flex:none}
.bub{background:#fff;border-radius:34px;padding:24px 32px;box-shadow:0 8px 30px rgba(37,88,184,.12);max-width:740px}
.r .bub{background:#fff0f6}
.nm{font-family:Round,My;font-size:26px;color:%(B)s} .r .nm{color:#d6336c}
.jp{font-size:50px;font-weight:700;line-height:1.55} .kana{font-size:27px;color:#7c8798} .my{font-family:My,sans-serif;font-size:33px;color:#4a5568;line-height:1.7}
.my b,.note b{font-family:'Noto Sans CJK JP',My}
.hl{background:linear-gradient(transparent 55%%,#ffe27a 55%%)}
s.bad{color:#c92a2a}
.dim{opacity:.4}
.note{display:flex;gap:16px;align-items:center;background:#fffbe6;border:3px dashed #f0c419;border-radius:26px;padding:16px 24px;margin:0 0 20px 142px;font-family:My;font-size:31px;line-height:1.6}
.r + .note, .note.rn{margin:0 142px 20px 0}
.tag{background:#e6f6f3;color:#0f7a6c;border-radius:14px;padding:2px 14px;font-size:27px;font-family:'Noto Sans CJK JP';white-space:nowrap}
.card{background:#fff;border-radius:36px;box-shadow:0 10px 40px rgba(37,88,184,.13);padding:32px 40px;margin-bottom:26px}
.tt{font-family:Round,My;font-size:44px;color:#17305e;margin-bottom:6px} .en{font-family:Round,My;font-size:34px;color:%(B)s}
.flow{display:grid;grid-template-columns:auto auto auto;justify-content:start;align-items:center;gap:12px 18px;font-size:44px;font-weight:700;margin-top:12px}
.flow span.a{color:#f08c00} .pill{background:#eef4ff;border-radius:18px;padding:6px 20px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px} .grid div{background:#eef4ff;border-radius:18px;padding:10px 18px;font-size:40px;font-weight:700}
.grid small{display:block;font-family:My;font-size:26px;color:#4a5568;font-weight:400}
.vs{display:flex;gap:24px} .vs .card{flex:1;text-align:center;padding:30px 20px}
.big{font-size:90px}
.warn{background:#fff7ea} .warn .tt{color:#c46a00;font-size:38px}
.opt{border:4px solid #cfdcf2;border-radius:24px;padding:12px 26px;font-size:44px;font-weight:700;margin:12px 0;background:#fff}
.opt.ok{border-color:#2b8a3e;background:#f0faf2;color:#2b8a3e} .opt.ng{opacity:.4}
.ok2{background:#f0faf2;border-radius:20px;padding:12px 22px;margin-top:10px}
.cnt{font-family:Round;text-align:center;color:#e8590c;font-size:150px;line-height:1.1}
.hook{font-family:Round,My;text-align:center;font-size:64px;color:#17305e;line-height:1.35;margin:20px 0 30px}
.badge{display:inline-block;background:#e8590c;color:#fff;font-family:Round,My;border-radius:30px;padding:6px 30px;font-size:40px}
.outro{text-align:center;margin-top:140px} .outro .av{width:260px;height:260px;margin:0 20px}
.outro .tt{font-size:66px;margin-top:50px} .outro .pink{color:#d6336c}
.new{opacity:var(--p,1);transform:translateY(calc((1 - var(--p,1)) * 50px))}
"""


def hl(s):
    s = re.sub(r"\[(.+?)\]", r"<span class='hl'>\1</span>", s)
    return re.sub(r"\{(.+?)\}", r"<s class='bad'>\1</s>", s)


def plain(s):
    return re.sub(r"[\[\]{}]", "", s)


def page(body, tag, prog):
    return ("<html><head><meta charset='utf-8'><style>%s</style></head><body><div class='top'><span>Learn with Rio ♡</span>"
            "<span class='chip'>%s</span></div><div class='bar'><i style='width:%d%%'></i></div><div class='wrap'>%s</div></body></html>"
            % (CSS % {"F": FONTS, "B": B}, tag, round(prog * 100), body))


def bubble(l, cls=""):
    r = l["who"] == "Yui"
    return ("<div class='row%s %s'><img class='av' src='file://%s/%s.png'><div class='bub'><div class='nm'>%s</div><div class='jp'>%s</div>"
            "<div class='kana'>%s</div><div class='my'>%s</div></div></div>"
            % (" r" if r else "", cls, AV, "yui" if r else "rio", l["who"], hl(l["jp"]), l.get("kana", ""), l.get("mm", "")))


def note(t, l, cls=""):
    return "<div class='note %s%s'>📝 <div>%s</div></div>" % ("rn " if l["who"] == "Yui" else "", cls, t)


def est_h(l, notes):
    """rough pixel height of a line bubble + n notes (to decide what still fits on the screen)."""
    jl = -(-len(plain(l["jp"])) // 13)
    ml = -(-len(l.get("mm", "")) // 26)
    return 120 + jl * 78 + 40 + ml * 56 + 24 + notes * 128


def chat_beats(c):
    """One beat per line, then one per note. Returns list of (html_body, tag, voice_key or None, hold, sfx)."""
    out, lines = [], c["chat"]
    for i, l in enumerate(lines):
        # older lines that still fit stay above (dimmed); the current one is full
        keep, hsum = [], est_h(l, len(l["notes"]))
        for k in range(i - 1, -1, -1):
            h = est_h(lines[k], len(lines[k]["notes"]) if k == i - 1 else 0)
            if hsum + h > 1250:
                break
            keep.insert(0, k); hsum += h
        def old():
            s = ""
            for k in keep:
                s += bubble(lines[k], "dim" if k < i - 1 or not lines[k]["notes"] else "")
                if k == i - 1 and lines[k]["notes"]:
                    s += "".join(note(t, lines[k]) for t in lines[k]["notes"])
            return s
        base = old()
        out.append((base + bubble(l, "new"), l["tag"], "c%d" % i, 0.35, [(0.0, "pop" if l["who"] == "Yui" else "whoosh")]))
        for j in range(len(l["notes"])):
            body = base + bubble(l) + "".join(note(t, l, "new" if q == j else "") for q, t in enumerate(l["notes"][:j + 1]))
            out.append((body, l["tag"], None, 2.4, [(0.0, "swish")]))
    return out


def compare_beats(c):
    cp, out = c["compare"], []
    def cards(n, new):
        s = "<div class='vs' style='margin-top:30px'>"
        for k, it in enumerate(cp["items"][:n]):
            s += ("<div class='card%s'><div class='big'>%s</div><div class='tt'>%s</div><div class='my'>%s</div>"
                  "<div class='jp' style='font-size:38px;margin-top:10px'>%s</div></div>" % (" new" if k == new else "", it["icon"], it["g"], it["mm"], hl(it["ex"])))
        return s + "</div>"
    for k in range(len(cp["items"])):
        out.append((cards(k + 1, k), cp["tag"], "v%d" % k, 1.2, [(0.0, "pop")]))
    return out


def caution_beats(c):
    out, tag = [], c["compare"]["tag"] if c.get("compare") else "⚠️ 注意"
    cv = ""
    if c.get("compare"):
        cv = "".join("<div class='card' style='padding:16px 30px;margin-bottom:16px'><span class='tt' style='font-size:36px'>%s %s</span> "
                     "<span class='my' style='font-size:28px'>%s</span></div>" % (it["icon"], it["g"], re.sub("<br>", " ", it["mm"])) for it in c["compare"]["items"])
    for k, w in enumerate(c["cautions"]):
        body = cv
        for q, x in enumerate(c["cautions"][:k + 1]):
            body += ("<div class='card warn%s'><div class='tt'>⚠️ သတိ! %s</div><div class='jp' style='font-size:42px'>%s ❌</div>"
                     "<div class='jp' style='font-size:42px'>%s ✅</div><div class='my'>%s</div></div>"
                     % (" new" if q == k else "", x["g"], hl(x["bad"]), hl(x["good"]), x["mm"]))
        out.append((body, tag, "w%d" % k, 2.2, [(0.0, "whoosh")]))
    return out


def word_card(w, cls=""):
    if w.get("grid"):
        inner = "<div class='grid'>%s</div>" % "".join("<div>%s<small>%s</small></div>" % (a, b) for a, b in w["grid"])
    else:
        inner = "<div class='flow'>%s</div>" % "".join("<span class='pill'>%s</span><span class='a'>→</span><span class='pill'>%s</span>" % (a, b) for a, b in w["pairs"])
    return ("<div class='card %s'><div class='tt'>%s <span class='kana'>%s</span></div><div class='en'>%s</div><div class='my'>%s</div>%s</div>"
            % (cls, w["term"], w["kana"], w["en"], w["mm"], inner))


def word_beats(c):
    out, head = [], "<div class='tt' style='font-size:54px;margin:10px 0 24px'>📖 ဒါတွေ ဘာလဲ?</div>"
    ws = c.get("words", [])
    for pg in range(0, len(ws), 2):
        chunk = ws[pg:pg + 2]
        for k in range(len(chunk)):
            body = head + "".join(word_card(w, "new" if q == k else "") for q, w in enumerate(chunk[:k + 1]))
            out.append((body, "📖 Word note", "d%d" % (pg + k), 2.6, [(0.0, "pop")]))
    return out


def q_card(m, mark=None, blank=True):
    s = "<div class='card'><div class='jp' style='font-size:46px'>%s</div>" % (
        m["q"].replace("（　）", "<span style='color:#e8590c'>（　）</span>") if blank else hl(m["full"]))
    s += "<div class='kana'>%s</div>" % m["kana"] if blank else "<div class='my'>%s</div>" % m["full_mm"]
    for i, o in enumerate(m["opts"], 1):
        if mark is None:
            s += "<div class='opt'>%d. %s</div>" % (i, o)
        else:
            s += "<div class='opt %s'>%s %s</div>" % ("ok" if i == m["ans"] else "ng", "✓" if i == m["ans"] else "✕", o)
    return s + "</div>"


def hook_beat(c):
    m = c["mondai"]
    body = "<div class='hook'>JLPT N3 に出る！<br>わかる？👇</div>" + q_card(m) + "<div style='text-align:center'><span class='badge'>答えは最後！</span></div>"
    return [(body, "N3文法 No.%d" % c["no"], "h0", 0.6, [(0.0, "ding")])]


def mondai_beats(c):
    m, out = c["mondai"], []
    head = "<div class='tt' style='text-align:center;font-size:56px;margin:10px 0 20px'>JLPT 問題 ✍️</div>"
    out.append((head + q_card(m), "JLPT 問題", "q0", 0.2, [(0.0, "whoosh")]))
    for n in (3, 2, 1):
        out.append((head + q_card(m) + "<div class='cnt'>%d</div>" % n, "JLPT 問題", None, 1.0, [(0.0, "tick")]))
    out.append((q_card(m, mark=True, blank=False), "JLPT 答え", "q1", 0.5, [(0.0, "ding")]))
    out.append((q_card(m, mark=True, blank=False) + "<div class='note new' style='margin-left:0'>💭 <div>%s</div></div>" % m["think"],
                "JLPT 答え", None, 3.0, [(0.0, "swish")]))
    head2 = "<div class='tt' style='font-size:48px;margin:0 0 20px'>ဒီ %d ခု ဘာလို့ မှားလဲ?</div>" % len(m["wrong"])
    out.append((head2, "JLPT 答え", "q2", 0.2, [(0.0, "whoosh")]))
    for k in range(len(m["wrong"])):
        body = head2
        for q, w in enumerate(m["wrong"][:k + 1]):
            body += ("<div class='card%s' style='padding:24px 34px;margin-bottom:20px'><div class='tt' style='font-size:40px;color:#c92a2a'>✕ %s</div>"
                     "<div class='my'>%s</div><div class='ok2'><div class='jp' style='font-size:38px'>✅ %s</div><div class='kana'>%s</div>"
                     "<div class='my' style='font-size:30px'>%s</div></div></div>" % (" new" if q == k else "", w["g"], w["mm"], hl(w["ex"]), w["kana"], w["exmm"]))
        out.append((body, "JLPT 答え", "x%d" % k, 1.8, [(0.0, "pop")]))
    return out


def outro_beats(c):
    body = ("<div class='outro'><img class='av' src='file://%s/rio.png'><img class='av' src='file://%s/yui.png'>"
            "<div class='tt'>Follow <span class='pink'>Rio</span> ♡</div><div class='my' style='font-size:38px;margin-top:20px'>"
            "JLPT N3 まで、いっしょにがんばろう！</div></div>" % (AV, AV))
    return [(body, "Learn with Rio ♡", "o0", 0.2, [(0.0, "pop"), (0.2, "ding")]), (body, "Learn with Rio ♡", "o1", 0.8, [])]


def beats(c):
    b = hook_beat(c) + chat_beats(c)
    if c.get("compare"):
        b += compare_beats(c)
    if c.get("cautions"):
        b += caution_beats(c)
    if c.get("words"):
        b += word_beats(c)
    return b + mondai_beats(c) + outro_beats(c)


def lines(c):
    """Every spoken line: key -> (who, jp). Grouped into 3 TTS requests."""
    m = c["mondai"]
    g1 = [("c%d" % i, l["who"], plain(l["jp"])) for i, l in enumerate(c["chat"])]
    g1 += [("o0", "Rio", "リアルな日本語を話したいなら、Rioをフォローしてね！"), ("o1", "Yui", "バイバーイ！")]
    g2 = [("h0", "Rio", "この問題、わかる？答えは最後！")]
    g2 += [("v%d" % k, "Rio", it["say"]) for k, it in enumerate(c.get("compare", {}).get("items", []))]
    g2 += [("w%d" % k, "Rio", w["say"]) for k, w in enumerate(c.get("cautions", []))]
    g2 += [("d%d" % k, "Rio", w["say"]) for k, w in enumerate(c.get("words", []))]
    g3 = [("q0", "Rio", "じゃあ、問題！どれが入ると思う？"), ("q1", "Rio", m["full_say"]), ("q2", "Rio", "ほかの%sは、こう使うよ。" % ["一つ", "二つ", "三つ"][max(1, min(3, len(m["wrong"]))) - 1])]
    g3 += [("x%d" % k, "Rio", plain(w["ex"])) for k, w in enumerate(m["wrong"])]
    return [g1, g2, g3]


# ---------------------------------------------------------------- render
async def _shots(pages, tmp):
    from playwright.async_api import async_playwright
    exe = next((p for p in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium") if os.path.exists(p)), None)
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path=exe, args=["--allow-file-access-from-files"]) if exe else await p.chromium.launch()
        pg = await b.new_page(viewport={"width": W, "height": H})
        out = []
        for i, (html, prog) in enumerate(pages):
            f = os.path.join(tmp, "p%04d.html" % i)
            open(f, "w", encoding="utf-8").write(html.replace("<body>", "<body style='--p:%s'>" % prog, 1))
            await pg.goto("file://" + f)
            await pg.evaluate("document.fonts.ready")
            j = os.path.join(tmp, "p%04d.jpg" % i)
            await pg.screenshot(path=j, type="jpeg", quality=92)
            out.append(j)
        await b.close()
    return out


def trim(x, thr=0.015, tail=0.18):
    """cut the silence at the end of a voice clip (keeps a short natural tail)."""
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x
    a = max(0, idx[0] - int(0.03 * SR))
    return x[a:min(len(x), idx[-1] + int(tail * SR))]


def render(c, clips, out_path, tmp):
    """clips: key -> float32 mono 24 kHz voice. Returns seconds."""
    sys.path.insert(0, os.path.join(ROOT, "steps"))
    import render_steps as RS
    bt = beats(c)
    n = len(bt)
    pages, plan = [], []   # plan: (page index, seconds)
    audio, sfx_at, t = [], [], 0.0
    for i, (body, tag, key, hold, sfx) in enumerate(bt):
        html = page(body, tag, (i + 1) / n)
        v = trim(clips[key]) if key else np.zeros(0, np.float32)
        dur = max(len(v) / SR + hold, 0.5)
        nf = int(round(dur * FPS))
        dur = nf / FPS
        seg = np.zeros(int(round(dur * SR)), np.float32)
        isnew = bool(re.search(r"class='[^']*\bnew\b", body))
        lead = 0.12 if isnew else 0.0     # the voice starts as the card lands
        a0 = int(lead * SR)
        seg[a0:a0 + len(v)] = v[:len(seg) - a0]
        audio.append(seg)
        for w, name in sfx:
            sfx_at.append((t + w, name))
        if isnew:
            for p in ANIM:
                pages.append((html, p)); plan.append((len(pages) - 1, 1 / FPS))
            nf -= len(ANIM)
        pages.append((html, 1)); plan.append((len(pages) - 1, nf / FPS))
        t += dur
    shots = asyncio.run(_shots(pages, tmp))
    lst = os.path.join(tmp, "list.txt")
    with open(lst, "w") as f:
        for pi, d in plan:
            f.write("file '%s'\nduration %.5f\n" % (shots[pi], d))
        f.write("file '%s'\n" % shots[plan[-1][0]])
    y = np.concatenate(audio)
    for at, name in sfx_at:
        e = RS.sfx(name)
        a = int(at * SR)
        m = min(len(e), len(y) - a)
        if m > 0:
            y[a:a + m] += e[:m] * SFX_GAIN
    wav = os.path.join(tmp, "mix.wav")
    import wave
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    part = out_path[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", wav,
                    "-vf", "fps=%d,format=yuv420p" % FPS, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out_path)
    return len(y) / SR
