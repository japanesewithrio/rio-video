"""Learn with Rio - format E "Pattern Chain Teacher" (test, Ye 2026-11-03).
Rio alone, like a friendly teacher:
  hook -> まず、全部聞いてみて (the 4 lines at natural speed)
       -> じゃあ、一文ずつ見ていこう (each line again slowly: pattern + blue swap words + Burmese tip)
       -> 言葉を変えるだけで… (the same 4 patterns with new words, natural speed)
       -> your turn -> follow.
Reuses the Format D look (render_steps.py) unchanged: same cards, colours, animations and sound effects.

usage: python steps/render_teach.py lesson.json main.wav out.mp4   (main.bounds.json next to the wav)
"""
import json, math, os, sys, tempfile, wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_steps as RS  # noqa: E402
from render_steps import (Scene, ldraw, jfont, mfont, mm_block, kana_block, pattern_box, sentence_layers, step_label,  # noqa: E402
                          segments, plain, card, rows, avatar, STEP_COL, INK, SUB, GREY, BLUE, W, H, R)
import numpy as np  # noqa: E402

TEACH = {
    "listen": ("まず、全部聞いてみて。", "まず、ぜんぶ きいてみて。", "အရင်ဆုံး ၄ ကြောင်းလုံး နားထောင်ကြည့်။"),
    "slow": ("じゃあ、一文ずつ見ていこう。", "じゃあ、いちぶんずつ みていこう。", "ကဲ၊ တစ်ကြောင်းချင်း ဖြည်းဖြည်း ကြည့်ကြရအောင်။"),
    "swap": ("言葉を変えるだけで、別の話になるよ。", "ことばを かえるだけで、べつの はなしに なるよ。",
             "စကားလုံးလေး ပြောင်းရုံနဲ့ တခြားဇာတ်လမ်း ဖြစ်သွားတယ်။"),
}
TAIL = [("青いところを自分の話に変えて、言ってみて！", "あおいところを じぶんの はなしに かえて、いってみて！",
         "အပြာရောင် စကားလုံးတွေကို ကိုယ့်အကြောင်းနဲ့ ပြောင်းပြီး ပြောကြည့်နော်!"),
        ("リアルな日本語を話したいなら、Rioをフォローしてね！", "リアルなにほんごを はなしたいなら、Rioを フォローしてね！",
         "တကယ်သုံးတဲ့ ဂျပန်စကား ပြောချင်ရင် Rio ကို Follow လုပ်ထားနော်!")]
TIP_READ = 2.2      # extra silent seconds after each slow line, to read the Burmese tip
FINAL_PRACTICE = RS.FINAL_PRACTICE


# ---------------------------------------------------------------- spoken order
def main_turns(s):
    t = [dict(s["hook"], who="Rio", type="hook")]
    t.append({"who": "Rio", "jp": TEACH["listen"][0], "kana": TEACH["listen"][1], "type": "say", "key": "listen"})
    for k, st in enumerate(s["steps"]):
        t.append(dict(st["main"], who="Rio", jp=plain(st["main"]["jp"]), type="main", step=k))
    t.append({"who": "Rio", "jp": TEACH["slow"][0], "kana": TEACH["slow"][1], "type": "say", "key": "slow"})
    for k, st in enumerate(s["steps"]):
        t.append(dict(st["main"], who="Rio", jp=plain(st["main"]["jp"]), type="slow", step=k))
    t.append({"who": "Rio", "jp": TEACH["swap"][0], "kana": TEACH["swap"][1], "type": "say", "key": "swap"})
    for k, st in enumerate(s["steps"]):
        ex = st["ex"][0]
        t.append(dict(ex, who="Rio", jp=plain(ex["jp"]), type="ex", step=k))
    for i, (j, kana, mm) in enumerate(TAIL):
        t.append({"who": "Rio", "jp": j, "kana": kana, "mm": mm, "type": "tail", "step": i})
    return t


def audio_groups(s):
    """5 TTS calls. Returns list of (style, turns); style 'slow' = the one-line-at-a-time part."""
    mt = main_turns(s)
    g = [("normal", mt[0:1]), ("normal", mt[1:6]), ("slow", mt[6:11]), ("normal", mt[11:16]), ("normal", mt[16:18])]
    assert sum(len(x) for _, x in g) == len(mt)
    return g


# ---------------------------------------------------------------- frames
def rio(sc, y, size=200, delay=0.0, bounce=True):
    a = avatar("Rio", size, 9, 1.0)
    sc.layer("bounce" if bounce else "static", delay).alpha_composite(a, (W // 2 - size // 2, int(y)))
    return y + size


def title_frame(s, prog):
    sc = Scene("PATTERN CHAIN", prog)
    rio(sc, 330, 220, 0.15)
    d = ldraw(sc.layer("pop", 0.0))
    y = 640
    for part in [x for x in __import__("re").split(r"(?<=[、，])", s["hook"]["jp"]) if x]:
        y = R.block(d, y, part, jfont(88), INK, maxw=940, gap=30)
    if s["hook"].get("kana"):
        y = kana_block(d, y + 6, s["hook"]["kana"], 34, GREY, 900)
    y = mm_block(ldraw(sc.layer("fade", 0.3)), y + 40, s["hook"].get("mm", ""), 46, SUB, weight=600)
    R.block(ldraw(sc.layer("pop", 0.5)), max(y + 80, 1400), s["title"], jfont(54), (222, 98, 150), maxw=920)
    sc.sfx += [(0.0, "pop"), (0.15, "whoosh"), (0.5, "pop")]
    return sc


def say_frame(key, prog, sub=None):
    """Rio's short teacher line, big, with Burmese under it."""
    jp, kana, mm = TEACH[key]
    sc = Scene({"listen": "LISTEN FIRST", "slow": "ONE BY ONE", "swap": "NEW WORDS"}[key], prog)
    rio(sc, 470, 240, 0.0)
    d = ldraw(sc.layer("pop", 0.1))
    y = R.block(d, 820, jp, jfont(76), INK, maxw=920, gap=26)
    y = kana_block(d, y + 6, kana, 34, GREY, 900)
    y = mm_block(ldraw(sc.layer("fade", 0.35)), y + 36, mm, 48, SUB, weight=600)
    if sub:
        cd = ldraw(sc.layer("pop", 0.5))
        f = jfont(44)
        tw = cd.textlength(sub, font=f)
        cd.rounded_rectangle([W / 2 - tw / 2 - 40, y + 50, W / 2 + tw / 2 + 40, y + 140], 45, fill=(234, 242, 253))
        cd.text((W / 2, y + 95), sub, font=f, fill=BLUE, anchor="mm")
    sc.sfx += [(0.0, "whoosh"), (0.1, "pop")]
    return sc


def listen_frame(s, cur, prog, lines="main"):
    """All 4 lines stacked; the spoken one is outlined. lines='ex' shows the new-words version."""
    s2 = s if lines == "main" else dict(s, steps=[dict(st, main=st["ex"][0]) for st in s["steps"]])
    sc = Scene("LISTEN FIRST" if lines == "main" else "NEW WORDS · SAME PATTERNS", prog)
    d = ldraw(sc.layer("pop", 0.0) if cur == 0 else sc.layer())
    head = "まず、全部聞いてみて" if lines == "main" else "言葉を変えると…"
    d.text((W / 2, 250), head, font=jfont(60), fill=INK, anchor="mt")
    sub = "ပုံမှန်အမြန်နှုန်းနဲ့ ၄ ကြောင်း ဆက်ပြောတာ" if lines == "main" else \
        "Pattern က အတူတူပဲ၊ အပြာစကားလုံး ပြောင်းရုံပဲ (%s)" % s.get("swap_tag", "")
    y = mm_block(d, 345, sub, 38, SUB) + 24
    rows(sc, s2, y, cur, H - 180)
    sc.sfx.append((0.0, "whoosh" if cur == 0 else "tick"))
    return sc


def tip_box(img, y, text):
    d = ImageDraw.Draw(img)
    f = mfont(38, 550)
    alt = jfont(34, False)
    n = len(R.wrap(d, text, f, 820, alt))
    h = n * 68 + 110
    card(img, y, h, outline=(246, 214, 120), width=4, fill=(255, 251, 236), x0=80, x1=W - 80)
    d.ellipse([118, y + 34, 158, y + 74], fill=(240, 180, 40))
    d.text((138, y + 54), "!", font=jfont(30), fill=(255, 255, 255), anchor="mm")
    d.text((176, y + 26), "ဘာကြောင့် ဒီလိုဆက်လဲ", font=mfont(36, 700), fill=(176, 120, 20))
    R.lblock(d, 120, y + 96, text, f, INK, 840)
    return y + h


def slow_frame(s, k, prog):
    st, col = s["steps"][k], STEP_COL[k]
    sc = Scene("ONE BY ONE · SLOWLY", prog)
    d = ldraw(sc.layer("fade", 0.0))
    y = step_label(d, 240, "STEP %d / 4" % (k + 1), col)
    y = pattern_box(sc.layer("pop", 0.05), y, st["pattern"], col, size=60) + 18
    y = mm_block(ldraw(sc.layer("fade", 0.2)), y, st.get("pattern_mm", ""), 38, SUB, weight=500) + 30
    y = sentence_layers(sc, y, segments(st["main"]["jp"]), st["main"].get("kana", ""), col, True, 58, 0.3) + 24
    y = mm_block(ldraw(sc.layer("in", 0.45)), y, st["main"].get("mm", ""), 42, INK, weight=600) + 34
    if st.get("tip"):
        tip_box(sc.layer("in", 1.2), y, st["tip"])
    sc.sfx += [(0.0, "ding"), (0.05, "pop"), (0.3, "whoosh"), (1.2, "pop")]
    return sc


def final_frame(s, cur, prog):
    sc = Scene("YOUR TURN", prog)
    d = ldraw(sc.layer("pop", 0.0) if cur is None else sc.layer())
    y = mm_block(d, 240, TAIL[0][2], 44, INK, weight=650) + 24
    rows(sc, s, y, cur, H - 250)
    ldraw(sc.layer("pop", 0.25) if cur is None else sc.layer()).text(
        (W / 2, H - 205), "SWAP THE BLUE WORDS!", font=jfont(40), fill=BLUE, anchor="mm")
    sc.sfx.append((0.0, "sparkle") if cur is None else (0.0, "tick"))
    return sc


def outro_frame(prog):
    sc = Scene("FOLLOW", prog)
    rio(sc, 520, 230, 0.0, bounce=False)
    for l in sc.layers:
        l["kind"], l["delay"] = "pop", 0.0
    d = ldraw(sc.layer("in", 0.2))
    d.text((W / 2, 860), "Follow", font=jfont(62), fill=(222, 98, 150), anchor="mt")
    d.text((W / 2, 960), "Learn with Rio ♡", font=jfont(88), fill=INK, anchor="mt")
    d = ldraw(sc.layer("fade", 0.45))
    y = R.block(d, 1150, "リアルな日本語を話したいなら、", jfont(46), SUB, maxw=900, gap=14)
    y = R.block(d, y, "Rioをフォローしてね！", jfont(46), SUB, maxw=900, gap=14)
    mm_block(d, y + 26, TAIL[1][2], 40, GREY)
    sc.sfx += [(0.0, "pop"), (0.2, "ding")]
    return sc


from PIL import ImageDraw  # noqa: E402


def timeline(s, mb):
    mt = main_turns(s)
    at = {}
    for i, t in enumerate(mt):
        at[(t["type"], t.get("step"), t.get("key"))] = i
    seg = lambda i, pad: (mb[i], mb[i + 1], pad)  # noqa: E731
    tl = [(lambda p: title_frame(s, p), seg(0, 0.4))]
    tl.append((lambda p: say_frame("listen", p), seg(at[("say", None, "listen")], 0.3)))
    for k in range(4):
        tl.append((lambda p, k=k: listen_frame(s, k, p), seg(at[("main", k, None)], 0.3 if k < 3 else 0.9)))
    tl.append((lambda p: say_frame("slow", p), seg(at[("say", None, "slow")], 0.4)))
    for k in range(4):
        tl.append((lambda p, k=k: slow_frame(s, k, p), seg(at[("slow", k, None)], TIP_READ)))
    tl.append((lambda p: say_frame("swap", p, sub=s.get("swap_tag")), seg(at[("say", None, "swap")], 0.4)))
    for k in range(4):
        tl.append((lambda p, k=k: listen_frame(s, k, p, lines="ex"), seg(at[("ex", k, None)], 0.3 if k < 3 else 0.9)))
    tl.append((lambda p: final_frame(s, None, p), seg(at[("tail", 0, None)], 0.4)))
    for k in range(4):
        tl.append((lambda p, k=k: final_frame(s, k, p), ("silence", FINAL_PRACTICE)))
    tl.append((lambda p: outro_frame(p), (mb[at[("tail", 1, None)]], mb[-1], 1.2)))
    return tl


def render(lesson_path, wav, out_path):
    s = json.load(open(lesson_path, encoding="utf-8"))
    mt = main_turns(s)
    mb, _ = RS.bounds(wav, mt)
    tl = timeline(s, mb)
    voice = RS.load_wav(wav)
    tmp = tempfile.mkdtemp()
    pieces, audio, sfx_at, t0, n = [], [], [], 0, len(tl)
    SR, FPS = RS.SR, RS.FPS
    for i, (fn, spec) in enumerate(tl):
        x = np.zeros(int(spec[1] * SR), np.float32) if spec[0] == "silence" else RS.clip_audio(voice, *spec)
        nf = max(1, int(round(len(x) / SR * FPS)))
        x = np.concatenate([x, np.zeros(max(0, nf * SR // FPS - len(x)), np.float32)])[:nf * SR // FPS]
        audio.append(x)
        sc = fn((i + 1) / n)
        na = min(nf, int(math.ceil(sc.anim_len() * FPS)) + 1)
        if na:
            f = os.path.join(tmp, "v%03da.mp4" % i)
            RS.encode_frames((sc.at(k / FPS) for k in range(na)), na, f)
            pieces.append(f)
        if nf - na > 0:
            f = os.path.join(tmp, "v%03db.mp4" % i)
            RS.encode_still(sc.flat(), nf - na, f, tmp)
            pieces.append(f)
        for when, name in sc.sfx:
            sfx_at.append((t0 + int(when * SR), name))
        t0 += len(x)
    y = np.concatenate(audio)
    for a, name in sfx_at:
        e = RS.sfx(name)
        m = min(len(e), len(y) - a)
        if m > 0:
            y[a:a + m] += e[:m] * RS.SFX_GAIN
    y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    aud = os.path.join(tmp, "all.wav")
    with wave.open(aud, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
    lst = os.path.join(tmp, "v.txt")
    with open(lst, "w") as fv:
        fv.writelines("file '%s'\n" % f for f in pieces)
    import subprocess
    vcat = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vcat], check=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = out_path[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vcat, "-i", aud, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out_path)
    secs = len(y) / SR
    print("rendered teach", out_path, len(pieces), "pieces", round(secs, 1), "s")
    return secs


if __name__ == "__main__":
    render(*sys.argv[1:4])
