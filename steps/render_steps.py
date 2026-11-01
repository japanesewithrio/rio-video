"""Learn with Rio - "4 Steps" video (format D, daily since 2026-11).
Rio tells a tiny story in 4 chained sentence patterns (前は〜 → でも〜てみたら → それから〜 → 今では〜).
Each step: pattern intro -> pattern highlighted (blue underline = words you can swap) -> 2 examples with swapped words.
Then つなげて話すと… (the 4 lines in a row) -> your turn (swap the blue words) -> follow outro.

usage: python steps/render_steps.py lesson.json main.wav out.mp4
  lesson.json : see steps/sample.json  (sentences mark swappable words with [brackets])
  main.wav    : hook, then per step [main (Rio), example 1 (Yui), example 2 (Rio)], then tail (Yui, Rio, Yui)
  optional main.bounds.json next to the wav (exact line bounds, written by steps.py)
"""
import json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import render as R  # noqa: E402  (render.py in the repo root, gunzipped by the workflow)
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

W, H = R.W, R.H
INK = (40, 44, 58)
SUB = (96, 100, 118)
GREY = (150, 152, 166)
BLUE = (37, 110, 214)          # swappable words (underlined)
STEP_COL = [(232, 112, 40), (222, 74, 128), (28, 150, 104), (134, 92, 214)]
SPK_COL = {"Rio": (52, 120, 200), "Yui": (222, 98, 150)}
GREEN = (40, 160, 120)

TAIL = [("Yui", "青いところを自分の話に変えて、言ってみて！", "あおいところを じぶんの はなしに かえて、いってみて！",
         "အပြာရောင် စကားလုံးတွေကို ကိုယ့်အကြောင်းနဲ့ ပြောင်းပြီး ပြောကြည့်နော်!"),
        ("Rio", "リアルな日本語を話したいなら、Rioをフォローしてね！", "リアルなにほんごをはなしたいなら、Rioをフォローしてね！",
         "တကယ်သုံးတဲ့ ဂျပန်စကား ပြောချင်ရင် Rio ကို Follow လုပ်ထားနော်!"),
        ("Yui", "バイバーイ！", "", "Bye bye!")]
FINAL_PRACTICE = 4.0  # silent seconds per line on the "your turn" card
_AV = {}

# ---------------------------------------------------------------- text helpers
PARTICLES = ("よね", "んだ", "よ", "ね", "な", "の", "わ")


def plain(s):
    return s.replace("[", "").replace("]", "")


def segments(sentence):
    """'前は、[人前で話すの]が苦手だった。' -> [('前は、','p'), ('人前で話すの','s'), ('が苦手だった。','p')]"""
    out = []
    for part in re.split(r"(\[[^\]]*\])", sentence):
        if not part:
            continue
        if part.startswith("["):
            out.append((part[1:-1], "s"))
        else:
            out.append((part, "p"))
    return out


def jfont(size, bold=True):
    return R.font(R.JP_BOLD if bold else R.JP_MED, size)


def mfont(size, weight=500):
    return R.font(R.MM, size, weight)


NO_START = set("、。！？!?ー」』）)ぁぃぅぇぉっゃゅょァィゥェォッャュョ…")


def rich_lines(d, segs, fnt, maxw):
    """Wrap styled Japanese text char by char -> list of lines, each a list of (char, kind)."""
    chars = [(c, k) for t, k in segs for c in t]
    lines, cur, w = [], [], 0.0
    for c, k in chars:
        cw = d.textlength(c, font=fnt)
        if cur and w + cw > maxw and c not in NO_START:
            lines.append(cur)
            cur, w = [], 0.0
        cur.append((c, k))
        w += cw
    if cur:
        lines.append(cur)
    return lines


def rich_block(d, cx, y, segs, fnt, maxw, pcol, ncol=INK, hl=True, center=True, x0=None):
    """Draw styled text. kinds: p = pattern part (pcol), s = swappable (blue + underline), n = normal.
    hl=False draws everything in ncol (plain sentence)."""
    lh = int(fnt.size * 1.42)
    for ln in rich_lines(d, segs, fnt, maxw):
        tw = sum(d.textlength(c, font=fnt) for c, _ in ln)
        x = cx - tw / 2 if center else x0
        i = 0
        while i < len(ln):
            k = ln[i][1]
            j = i
            while j < len(ln) and ln[j][1] == k:
                j += 1
            run = "".join(c for c, _ in ln[i:j])
            col = ncol if not hl else (BLUE if k == "s" else pcol if k == "p" else ncol)
            d.text((x, y), run, font=fnt, fill=col)
            rw = d.textlength(run, font=fnt)
            if hl and k == "s":
                uy = y + int(fnt.size * 1.18)
                d.line([(x + 2, uy), (x + rw - 2, uy)], fill=BLUE, width=max(3, fnt.size // 14))
            x += rw
            i = j
        y += lh
    return y


def rich_height(d, segs, fnt, maxw):
    return len(rich_lines(d, segs, fnt, maxw)) * int(fnt.size * 1.42)


def mm_block(d, y, text, size=44, fill=INK, maxw=900, weight=500):
    if not text:
        return y
    return R.block(d, y, text, mfont(size, weight), fill, maxw=maxw, gap=22)


def kana_lines(d, text, fnt, maxw):
    """Kana is written with spaces between words: wrap at the spaces (never inside a word)."""
    out, cur = [], ""
    for w in text.split():
        t = (cur + " " + w) if cur else w
        if cur and d.textlength(t, font=fnt) > maxw:
            out.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        out.append(cur)
    return out


def kana_block(d, y, text, size=32, fill=GREY, maxw=860, cx=None, x0=None):
    if not text:
        return y
    f = jfont(size, False)
    for ln in kana_lines(d, text, f, maxw):
        if x0 is None:
            d.text(((cx or W / 2), y), ln, font=f, fill=fill, anchor="mt")
        else:
            d.text((x0, y), ln, font=f, fill=fill)
        y += int(size * 1.45)
    return y


# ---------------------------------------------------------------- base frame
def base(tag, prog):
    if "bg" not in _AV:
        bg = Image.new("RGB", (W, H), (248, 250, 253))
        bd = ImageDraw.Draw(bg)
        bd.ellipse([-420, -380, 700, 520], fill=(224, 237, 252))
        bd.ellipse([700, 1380, 1500, 2200], fill=(252, 228, 237))
        _AV["bg"] = bg.filter(ImageFilter.GaussianBlur(3)).convert("RGBA")
    img = _AV["bg"].copy()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([46, 38, W - 46, 182], 44, fill=(255, 255, 255), outline=(228, 232, 240), width=3)
    d.text((90, 110), "Learn with Rio ♡", font=jfont(46), fill=(222, 98, 150), anchor="lm")
    if tag:
        f = jfont(24, False)
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle([W - 96 - tw - 40, 78, W - 96, 142], 22, fill=(234, 243, 252))
        d.text((W - 96 - tw / 2 - 20, 110), tag, font=f, fill=(70, 120, 170), anchor="mm")
    d.rounded_rectangle([84, H - 140, W - 84, H - 124], 8, fill=(232, 236, 242))
    d.rounded_rectangle([84, H - 140, 84 + max(16, int((W - 168) * min(1.0, prog))), H - 124], 8, fill=GREEN)
    d.line([(66, H - 96), (W - 66, H - 96)], fill=(228, 232, 240), width=2)
    d.text((W / 2, H - 52), "話せるようになろう  ・  LET'S SPEAK", font=jfont(30, False), fill=(120, 126, 142), anchor="mm")
    return img


def avatar(name, size, ring, alpha=1.0):
    key = (name, size, ring, alpha)
    if key in _AV:
        return _AV[key]
    p = os.path.join(HERE, name.lower() + ".png")
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    od = ImageDraw.Draw(out)
    od.ellipse([0, 0, size - 1, size - 1], fill=SPK_COL.get(name, GREY))
    inner = size - 2 * ring
    if os.path.exists(p):
        face = Image.open(p).convert("RGBA").resize((inner, inner), Image.LANCZOS)
    else:
        face = Image.new("RGBA", (inner, inner), (255, 255, 255, 255))
        ImageDraw.Draw(face).text((inner / 2, inner / 2), name, font=jfont(inner // 4), fill=SPK_COL.get(name, GREY), anchor="mm")
    m = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(m).ellipse([0, 0, inner - 1, inner - 1], fill=255)
    out.paste(face, (ring, ring), m)
    if alpha < 1:
        out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    _AV[key] = out
    return out


def avatars(img, y, speaker, size=190):
    """Rio left, Yui right; the speaker is full strength, the other one faded. Skipped if they would hit the footer."""
    if y + size > H - 160:
        return y
    for name, cx in (("Rio", W // 2 - 250), ("Yui", W // 2 + 250)):
        on = speaker in (None, name)
        s = size if on else int(size * 0.82)
        a = avatar(name, s, 9 if on else 6, 1.0 if on else 0.45)
        img.alpha_composite(a, (cx - s // 2, int(y + (size - s) / 2)))
    return y + size


def card(img, top, height, outline=(226, 230, 238), width=3, fill=(255, 255, 255), x0=72, x1=None):
    x1 = x1 or W - 72
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0, top + 10, x1, top + height + 10], 40, fill=(60, 70, 110, 26))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
    ImageDraw.Draw(img).rounded_rectangle([x0, top, x1, top + height], 40, fill=fill, outline=outline, width=width)


def pattern_box(img, y, pattern, col, size=66):
    d = ImageDraw.Draw(img)
    f = jfont(size)
    lines = rich_lines(d, [(pattern, "p")], f, 860)
    h = len(lines) * int(size * 1.42) + 90
    card(img, y, h, outline=col, width=6, x0=80, x1=W - 80)
    rich_block(d, W / 2, y + 45, [(pattern, "p")], f, 860, col, hl=False, ncol=col)
    return y + h


def sentence_card(img, y, segs, kana, col, hl, size=62):
    d = ImageDraw.Draw(img)
    f = jfont(size)
    hj = rich_height(d, segs, f, 860)
    kf = jfont(34, False)
    hk = len(kana_lines(d, kana, kf, 840)) * int(34 * 1.45) + 12 if kana else 0
    h = hj + hk + 70
    card(img, y, h, fill=(246, 250, 255) if not hl else (255, 255, 255))
    yy = rich_block(d, W / 2, y + 42, segs, f, 860, col, ncol=(52, 110, 180) if not hl else INK, hl=hl)
    if kana:
        kana_block(d, yy + 12, kana, 34, (90, 130, 190) if not hl else GREY, 840)
    return y + h


def step_label(d, y, text, col):
    d.text((W / 2, y), text, font=jfont(40, False), fill=col, anchor="mt")
    return y + 70


# ---------------------------------------------------------------- frames
def overview_frame(s, upto, prog):
    img = base("4 STEPS STORY", prog)
    d = ImageDraw.Draw(img)
    y = mm_block(d, 260, "ဒီ pattern ၄ ခုကို တစ်ခုပြီးတစ်ခု ဆက်ပြီး ပြောကြည့်ရအောင်!", 46, INK, weight=650)
    y += 40
    for k, st in enumerate(s["steps"]):
        col = STEP_COL[k]
        f = jfont(50)
        hp = rich_height(d, [(st["pattern"], "p")], f, 760)
        hm = len(R.wrap(d, st.get("pattern_mm", ""), mfont(36), 760, jfont(32, False))) * 64
        h = hp + hm + 70
        cur = k == upto
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        card(layer, y, h, outline=col if cur else (226, 230, 238), width=6 if cur else 3)
        ld = ImageDraw.Draw(layer)
        ld.ellipse([110, y + 34, 170, y + 94], fill=col if k <= upto else (220, 224, 232))
        ld.text((140, y + 64), str(k + 1), font=jfont(34), fill=(255, 255, 255), anchor="mm")
        yy = rich_block(ld, 0, y + 32, [(st["pattern"], "p")], f, 760, col, hl=False, ncol=col, center=False, x0=200)
        R.lblock(ld, 200, yy + 4, st.get("pattern_mm", ""), mfont(36), SUB, 760)
        if k > upto:
            layer.putalpha(layer.getchannel("A").point(lambda v: int(v * 0.35)))
        img.alpha_composite(layer)
        y += h + 30
    return img.convert("RGB")


def intro_frame(s, k, prog):
    st, col = s["steps"][k], STEP_COL[k]
    img = base("JAPANESE + HIRAGANA", prog)
    d = ImageDraw.Draw(img)
    y = step_label(d, 270, "STEP %d / 4" % (k + 1), col)
    y = pattern_box(img, y, st["pattern"], col) + 26
    y = mm_block(d, y, st.get("pattern_mm", ""), 40, SUB, weight=500) + 40
    y = avatars(img, y, st["main"]["who"]) + 50
    y = sentence_card(img, y, segments(st["main"]["jp"]), st["main"].get("kana", ""), col, hl=False) + 34
    mm_block(d, y, st["main"].get("mm", ""), 46, INK, weight=600)
    return img.convert("RGB")


def highlight_frame(s, k, prog):
    st, col = s["steps"][k], STEP_COL[k]
    img = base("PATTERN HIGHLIGHT", prog)
    d = ImageDraw.Draw(img)
    y = step_label(d, 260, "STEP %d / 4" % (k + 1), col)
    y = mm_block(d, y, "ပုံသေ = pattern ၊ အပြာ = ပြောင်းလို့ရတယ်", 40, INK, weight=550) + 30
    y = pattern_box(img, y, st["pattern"], col) + 50
    y = sentence_card(img, y, segments(st["main"]["jp"]), st["main"].get("kana", ""), col, hl=True, size=64) + 40
    y = mm_block(d, y, st["main"].get("mm", ""), 46, INK, weight=600) + 40
    avatars(img, max(y, 1500), st["main"]["who"], size=150)
    return img.convert("RGB")


def example_frame(s, k, j, prog):
    st, col = s["steps"][k], STEP_COL[k]
    ex = st["ex"][j]
    tag = (s.get("ex_tags") or ["", ""])[j]
    img = base("NEW WORDS · SAME GRAMMAR", prog)
    d = ImageDraw.Draw(img)
    y = step_label(d, 270, "EXAMPLE %d  ・  %s" % (j + 1, tag) if tag else "EXAMPLE %d" % (j + 1), col)
    y = pattern_box(img, y, st["pattern"], col) + 40
    f = mfont(40, 650)
    chip = "စကားလုံးပဲ ပြောင်းတယ်၊ ပုံစံက အတူတူပဲ"
    alt = jfont(36, False)
    tw = R.tlen(d, chip, f, alt)
    d.rounded_rectangle([W / 2 - tw / 2 - 40, y, W / 2 + tw / 2 + 40, y + 84], 42, fill=(234, 242, 253))
    R.block(d, y + 8, chip, f, BLUE, maxw=900)
    y += 84 + 46
    y = sentence_card(img, y, segments(ex["jp"]), ex.get("kana", ""), col, hl=True, size=64) + 40
    y = mm_block(d, y, ex.get("mm", ""), 46, INK, weight=600) + 40
    avatars(img, max(y, 1500), ex["who"], size=150)
    return img.convert("RGB")


def rows(img, s, y, cur, bottom):
    """The 4 lines of the story as stacked cards; cur is outlined in its step colour."""
    d = ImageDraw.Draw(img)
    for js, ks, ms, show_k in ((44, 26, 32, True), (40, 24, 30, True), (36, 22, 28, True), (36, 22, 28, False), (32, 20, 26, False)):
        fj, fk, fm = jfont(js), jfont(ks, False), mfont(ms)
        alt = jfont(ms - 4, False)
        items = []
        for k, st in enumerate(s["steps"]):
            m = st["main"]
            hj = rich_height(d, segments(m["jp"]), fj, 780)
            hk = len(kana_lines(d, m.get("kana", ""), fk, 780)) * int(ks * 1.45) if show_k and m.get("kana") else 0
            hm = len(R.wrap(d, m.get("mm", ""), fm, 780, alt)) * int(ms * 1.8)
            items.append(hj + hk + hm + 50)
        if sum(items) + 3 * 14 <= bottom - y:
            break
    gap = max(8, min(40, (bottom - y - sum(items)) // 3))
    for k, st in enumerate(s["steps"]):
        m, col, h = st["main"], STEP_COL[k], items[k]
        on = k == cur
        card(img, y, h, outline=col if on else (226, 230, 238), width=6 if on else 3,
             fill=(255, 255, 255) if on or cur is None else (250, 251, 253))
        d.text((112, y + 30), str(k + 1), font=jfont(34), fill=col)
        yy = rich_block(d, 0, y + 26, segments(m["jp"]), fj, 780, col, center=False, x0=170)
        if show_k and m.get("kana"):
            yy = kana_block(d, yy - 2, m["kana"], ks, GREY, 780, x0=170)
        R.lblock(d, 170, yy + 4, m.get("mm", ""), fm, SUB, 780)
        y += h + gap
    return y


def chain_frame(s, cur, prog):
    img = base("ALL 4 · SPEAK CONTINUOUSLY", prog)
    d = ImageDraw.Draw(img)
    d.text((W / 2, 250), "つなげて話すと…", font=jfont(60), fill=INK, anchor="mt")
    y = mm_block(d, 345, "၄ ကြောင်း ဆက်ပြောလိုက်ရင် ဇာတ်လမ်းတစ်ပုဒ် ဖြစ်သွားပြီ!", 38, SUB) + 24
    rows(img, s, y, cur, H - 180)
    return img.convert("RGB")


def final_frame(s, cur, prog):
    img = base("YOUR TURN", prog)
    d = ImageDraw.Draw(img)
    y = mm_block(d, 240, "အပြာရောင် စကားလုံးတွေကို ကိုယ့်အကြောင်းနဲ့ ပြောင်းပြီး ပြောကြည့်နော်!", 44, INK, weight=650) + 24
    rows(img, s, y, cur, H - 250)
    d.text((W / 2, H - 205), "SWAP THE BLUE WORDS!", font=jfont(40), fill=BLUE, anchor="mm")
    return img.convert("RGB")


def outro_frame(prog):
    img = base("FOLLOW", prog)
    d = ImageDraw.Draw(img)
    avatars(img, 520, None, size=230)
    d.text((W / 2, 860), "Follow", font=jfont(62), fill=(222, 98, 150), anchor="mt")
    d.text((W / 2, 960), "Learn with Rio ♡", font=jfont(88), fill=INK, anchor="mt")
    y = R.block(d, 1150, "リアルな日本語を話したいなら、", jfont(46), SUB, maxw=900, gap=14)
    y = R.block(d, y, "Rioをフォローしてね！", jfont(46), SUB, maxw=900, gap=14)
    mm_block(d, y + 26, TAIL[1][3], 40, GREY)
    return img.convert("RGB")


def title_frame(s, prog):
    img = base("4 STEPS STORY", prog)
    d = ImageDraw.Draw(img)
    avatars(img, 420, "Rio", size=240)
    y = R.block(d, 760, s["hook"]["jp"], jfont(70), INK, maxw=920, gap=26)
    if s["hook"].get("kana"):
        y = kana_block(d, y + 6, s["hook"]["kana"], 34, GREY, 900)
    y = mm_block(d, y + 40, s["hook"].get("mm", ""), 46, SUB, weight=600)
    R.block(d, max(y + 80, 1400), s["title"], jfont(50), (222, 98, 150), maxw=920)
    return img.convert("RGB")


# ---------------------------------------------------------------- audio order
def main_turns(s):
    """Spoken order of main.wav."""
    t = [dict(s["hook"], who="Rio", type="hook")]
    for k, st in enumerate(s["steps"]):
        t.append(dict(st["main"], jp=plain(st["main"]["jp"]), type="main", step=k))
        for j, ex in enumerate(st["ex"]):
            t.append(dict(ex, jp=plain(ex["jp"]), type="ex", step=k, ex=j))
    for w, j, k, m in TAIL:
        t.append({"who": w, "jp": j, "kana": k, "mm": m, "type": "tail"})
    return t


def audio_groups(s):
    mt = main_turns(s)
    groups = [[mt[0]]]
    for k in range(len(s["steps"])):
        groups.append([t for t in mt if t.get("step") == k])
    groups.append([t for t in mt if t["type"] == "tail"])
    assert sum(len(g) for g in groups) == len(mt)
    return groups


# ---------------------------------------------------------------- build
def bounds(wav, turns):
    bf = wav[:-4] + ".bounds.json"
    if os.path.exists(bf):
        b = json.load(open(bf))
        if len(b) == len(turns) + 1:
            return b, b[-1]
        print("bounds file has wrong length", len(b), len(turns) + 1)
    pts, T = R.split_points(wav, turns)
    return [0.0] + pts + [T], T


def timeline(s, mb):
    """List of (frame_fn, audio_spec). audio_spec = (start, end, pad) slice of main.wav, or ('silence', secs)."""
    mt = main_turns(s)
    idx = {(t["type"], t.get("step"), t.get("ex")): i for i, t in enumerate(mt)}
    tl = []
    # hook: title card, then overview rows appear one by one
    a, b = mb[0], mb[1]
    tl.append((lambda p: title_frame(s, p), (a, b, 0.5)))
    for k in range(4):
        tl.append((lambda p, k=k: overview_frame(s, k, p), ("silence", 1.1 if k < 3 else 1.8)))
    for k in range(4):
        i = idx[("main", k, None)]
        tl.append((lambda p, k=k: intro_frame(s, k, p), (mb[i], mb[i + 1], 0.7)))
        tl.append((lambda p, k=k: highlight_frame(s, k, p), (mb[i], mb[i + 1], 0.9)))
        for j in range(2):
            e = idx[("ex", k, j)]
            tl.append((lambda p, k=k, j=j: example_frame(s, k, j, p), (mb[e], mb[e + 1], 0.8 if j == 0 else 1.0)))
    tl.append((lambda p: chain_frame(s, None, p), ("silence", 1.0)))
    for k in range(4):
        i = idx[("main", k, None)]
        tl.append((lambda p, k=k: chain_frame(s, k, p), (mb[i], mb[i + 1], 0.6)))
    tail_i = [i for i, t in enumerate(mt) if t["type"] == "tail"]
    y0 = tail_i[0]
    tl.append((lambda p: final_frame(s, None, p), (mb[y0], mb[y0 + 1], 0.6)))
    for k in range(4):
        tl.append((lambda p, k=k: final_frame(s, k, p), ("silence", FINAL_PRACTICE)))
    r0 = tail_i[1]
    tl.append((lambda p: outro_frame(p), (mb[r0], mb[-1], 1.2)))
    return tl


def render(lesson_path, wav, out_path):
    s = json.load(open(lesson_path, encoding="utf-8"))
    tmp = tempfile.mkdtemp()
    mt = main_turns(s)
    mb, mT = bounds(wav, mt)
    tl = timeline(s, mb)
    alst, vlst = os.path.join(tmp, "a.txt"), os.path.join(tmp, "v.txt")
    n = len(tl)
    with open(alst, "w") as fa, open(vlst, "w") as fv:
        for i, (fn, spec) in enumerate(tl):
            af = os.path.join(tmp, "a%03d.wav" % i)
            if spec[0] == "silence":
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                       "-t", "%.3f" % spec[1], af]
            else:
                a, b, pad = spec
                cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.3f" % a, "-to", "%.3f" % b, "-i", wav,
                       "-ar", "24000", "-ac", "1", "-af", "apad=pad_dur=%s" % pad, af]
            subprocess.run(cmd, check=True)
            p = os.path.join(tmp, "f%03d.png" % i)
            fn((i + 1) / n).save(p)
            fv.write("file '%s'\nduration %.3f\n" % (p, R.duration(af)))
            fa.write("file '%s'\n" % af)
        fv.write("file '%s'\n" % p)
    aud = os.path.join(tmp, "all.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", alst, "-c", "copy", aud], check=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = out_path[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", vlst, "-i", aud,
                    "-map", "0:v", "-map", "1:a", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out_path)
    print("rendered steps", out_path, n, "segments", round(R.duration(aud), 1), "s")
    return R.duration(aud)


if __name__ == "__main__":
    render(*sys.argv[1:4])
