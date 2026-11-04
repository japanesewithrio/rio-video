"""Learn with Rio - format F "Chat Before -> After" (test, Ye 2026-11-03, design approved on mockups v3-v6).
 1 まだこう答えてる？  Yui asks, Rio gives the plain textbook answer, 教科書っぽい… + Burmese note
 2 …会話が終わった    Yui: …そっか。 (crickets)
 3 じゃあ、こう答えてみよう！ (Rio)
 4 the 4 pattern cards pop in one by one
 5 the cool answer as a chat: the line being spoken is big (JP with furigana + Burmese), earlier lines shrink and fade
 6 一つにつなげると… the whole chain in one go, patterns coloured, furigana above
 7 YOUR TURN blanks + 3-2-1, then 例えば… an easy example line by line
 8 follow
Markup in the lesson: 漢字《よみ》 = furigana for the kanji right before it; {1...} = pattern part of step 1 (coloured).
usage: python steps/render_chat.py lesson.json main.wav out.mp4   (main.bounds.json next to the wav)
"""
import json, math, os, re, subprocess, sys, tempfile, wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render_steps as RS  # noqa: E402
from render_steps import Scene, jfont, mfont, R, W, H  # noqa: E402
from PIL import Image, ImageDraw, ImageFilter  # noqa: E402
import numpy as np  # noqa: E402

BG = (238, 231, 222)
ME = (140, 220, 120)
YOU = (255, 255, 255)
INK = (35, 38, 48)
SUB = (110, 112, 125)
FADE = (150, 150, 160)
PINK = (222, 98, 150)
RED = (214, 69, 69)
GREEN = (40, 160, 120)
STEP = {1: (232, 112, 40), 2: (222, 74, 128), 3: (28, 150, 104), 4: (134, 92, 214)}
SPK = {"Rio": (52, 120, 200), "Yui": (222, 98, 150)}
KANJI = re.compile(r"[一-鿿々〆ヶ]")
NO_START = set("、。！？!?ー」』）)ぁぃぅぇぉっゃゅょァィゥェォッャュョ…")
SR, FPS = RS.SR, RS.FPS
SFX_GAIN = 0.5


# ---------------------------------------------------------------- markup
def plain(s):
    """Text for TTS / small faded bubbles."""
    return re.sub(r"\{\d?", "", re.sub(r"《[^》]*》", "", s)).replace("}", "")


def reading(s):
    """Kana reading: kanji run + 《よみ》 -> よみ (used by the TTS speed check and line alignment)."""
    return re.sub(r"\{\d?", "", re.sub(r"[一-鿿々〆ヶ]+《([^》]*)》", r"\1", s)).replace("}", "")


def units(s):
    """-> list of (text, ruby or None, step or 0). A kanji run followed by 《よみ》 is one unit; other characters are single units."""
    out, step, i = [], 0, 0
    while i < len(s):
        c = s[i]
        if c == "{":
            i += 1
            if i < len(s) and s[i].isdigit():
                step = int(s[i]); i += 1
            else:
                step = 1
            continue
        if c == "}":
            step = 0; i += 1
            continue
        if c == "《":
            j = s.index("》", i)
            ruby = s[i + 1:j]
            run = []
            while out and out[-1][1] is None and len(out[-1][0]) == 1 and KANJI.match(out[-1][0]):
                run.insert(0, out.pop())
            if run:
                out.append(("".join(u[0] for u in run), ruby, run[-1][2]))
            i = j + 1
            continue
        out.append((c, None, step))
        i += 1
    return out


RUBY = 0.75
RIGHT = 150   # TikTok safe zone: keep text clear of the like/comment buttons on the right   # Ye 2026-11-04: option D (kanji 40 / furigana 30)


def adv(d, u, fnt, rf):
    """Width a unit takes: furigana may overhang its neighbours a little (like printed books)."""
    tw = d.textlength(u[0], font=fnt)
    return max(tw, d.textlength(u[1], font=rf)) if u[1] else tw   # safe width for wrapping/sizing


def wrap_units(d, us, fnt, maxw):
    rf = jfont(int(fnt.size * RUBY), False)
    lines, cur, w = [], [], 0.0
    for u in us:
        uw = adv(d, u, fnt, rf)
        if cur and w + uw > maxw and u[0] not in NO_START:
            lines.append(cur); cur, w = [], 0.0
        cur.append(u); w += uw
    if cur:
        lines.append(cur)
    return lines


def line_layout(d, line, fnt, rf):
    """-> list of (x_offset, box_width). Furigana may overhang neighbouring kana (printed-book style),
    but it never starts left of the line or overlaps the previous furigana."""
    out, x, last_r = [], 0.0, 0.0
    for t, r, st in line:
        tw = d.textlength(t, font=fnt)
        if not r:
            out.append((x, tw)); x += tw
            continue
        rw = d.textlength(r, font=rf)
        bw = max(tw, rw * 0.62)
        left = x + bw / 2 - rw / 2
        push = max(0.0, last_r + 6 - left)
        x += push
        out.append((x, bw))
        last_r = x + bw / 2 + rw / 2
        x += bw
    return out


def draw_units(d, x, y, line, fnt, rf, base_col, ruby=True, step_cols=True):
    rf = jfont(int(fnt.size * RUBY), False)
    for (t, r, st), (ox, bw) in zip(line, line_layout(d, line, fnt, rf)):
        col = STEP[st] if (st and step_cols) else base_col
        tw = d.textlength(t, font=fnt)
        if r and ruby:
            d.text((x + ox + bw / 2, y - 2), r, font=rf, fill=(90, 96, 112), anchor="md")
        d.text((x + ox + (bw - tw) / 2, y), t, font=fnt, fill=col)
    return x


def text_block_h(d, s, size, maxw, ruby=True):
    f = jfont(size)
    n = len(wrap_units(d, units(s), f, maxw))
    return n * (size + (int(size * RUBY + 6) if ruby else 0) + 16)


def draw_text_block(d, x, y, s, size, maxw, col=INK, ruby=True, center=False):
    f, rf = jfont(size), jfont(int(size * 0.46), False)
    lh = size + (int(size * RUBY + 6) if ruby else 0) + 16
    for line in wrap_units(d, units(s), f, maxw):
        xx = x
        if center:
            xx = (W - sum(adv(d, u, f, rf) for u in line)) / 2
        draw_units(d, xx, y + (int(size * RUBY + 6) if ruby else 0), line, f, rf, col, ruby)
        y += lh
    return y


def mm_lines(d, text, size, maxw, weight=600):
    return R.wrap(d, text, mfont(size, weight), maxw, jfont(size - 4, False))


# ---------------------------------------------------------------- scene base
class ChatScene(Scene):
    def __init__(self, title, sub, tag, prog):
        self.base = chat_base(title, sub, tag, prog)
        self.layers, self.sfx = [], []


_BASE = {}


def chat_base(title, sub, tag, prog):
    im = Image.new("RGBA", (W, H), BG + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 150], fill=(255, 255, 255))
    d.text((60, 75), "‹  Yui", font=jfont(48), fill=INK, anchor="lm")
    if tag:
        f = jfont(26, False)
        tw = d.textlength(tag, font=f)
        d.rounded_rectangle([W - 90 - tw, 45, W - 50, 105], 30, fill=(252, 228, 237))
        d.text((W - 70 - tw / 2, 75), tag, font=f, fill=PINK, anchor="mm")
    if title:
        d.rounded_rectangle([40, 185, W - 40, 405], 40, fill=(255, 255, 255))
        d.text((W / 2, 250), title, font=jfont(66), fill=INK, anchor="mm")
        R.block(d, 312, sub, mfont(40, 650), SUB, maxw=960)
    d.rounded_rectangle([84, H - 128, W - 84, H - 116], 6, fill=(225, 216, 205))
    d.rounded_rectangle([84, H - 128, 84 + max(12, int((W - 168) * min(1.0, prog))), H - 116], 6, fill=PINK)
    d.text((W / 2, H - 62), "Learn with Rio ♡", font=jfont(36), fill=PINK, anchor="mm")
    return im


def avatar_img(name, size):
    key = (name, size)
    if key not in _BASE:
        _BASE[key] = RS.avatar(name, size, 6, 1.0)
    return _BASE[key]


# ---------------------------------------------------------------- bubbles
def full_bubble(img, y, line, me, outline=None, size=50):
    """Spoken line: JP with furigana (pattern parts coloured) + Burmese."""
    d = ImageDraw.Draw(img)
    maxw = W - 150 - RIGHT - 70
    f = jfont(size)
    jl = wrap_units(d, units(line["jp"]), f, maxw)
    mml = mm_lines(d, line.get("mm", ""), 37, maxw)
    jw = max(sum(adv(d, u, f, jfont(int(size * RUBY), False)) for u in ln) for ln in jl)
    mw = max([d.textlength(m, font=mfont(37, 600)) for m in mml] or [0])
    bw = min(max(jw, mw) + 70, W - 150 - RIGHT)
    lh = size + int(size * RUBY + 6) + 26
    bh = len(jl) * lh + len(mml) * 58 + 56
    x = W - RIGHT - bw if me else 150
    if not me:
        img.alpha_composite(avatar_img(line["who"], 84), (46, int(y)))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x, y + 8, x + bw, y + bh + 8], 36, fill=(0, 0, 0, 38))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    d.rounded_rectangle([x, y, x + bw, y + bh], 36, fill=ME if me else YOU, outline=outline, width=5 if outline else 0)
    yy = y + 22
    rf = jfont(int(size * 0.46), False)
    for ln in jl:
        draw_units(d, x + 35, yy + int(size * RUBY + 6), ln, f, rf, INK)
        yy += lh
    yy += 4
    for m in mml:
        R.lblock(d, x + 35, yy - 4, m, mfont(37, 600), INK, maxw + 60)
        yy += 58
    return y + bh + 26, (x, y, x + bw, y + bh)


def small_bubble(img, y, text, me):
    d = ImageDraw.Draw(img)
    f = jfont(32)
    t = plain(text)
    while d.textlength(t, font=f) > W - 150 - RIGHT - 50 and len(t) > 4:
        t = t[:-2] + "…" if not t.endswith("…") else t[:-3] + "…"
    w = d.textlength(t, font=f) + 50
    x = W - RIGHT - w if me else 150
    if not me:
        d.ellipse([96, y + 6, 136, y + 46], fill=(235, 190, 205))
    d.rounded_rectangle([x, y, x + w, y + 56], 26, fill=(205, 232, 198) if me else (250, 250, 250))
    d.text((x + 25, y + 28), t, font=f, fill=FADE, anchor="lm")
    return y + 72


def label(img, x, y, text, col, size=36):
    d = ImageDraw.Draw(img)
    f = mfont(size, 700)
    w = d.textlength(text, font=f) + 44
    d.rounded_rectangle([x, y, x + w, y + size + 30], (size + 30) // 2, fill=col)
    d.text((x + w / 2, y + (size + 30) / 2), text, font=f, fill=(255, 255, 255), anchor="mm")
    return w


# ---------------------------------------------------------------- frames
def f_hook(s, stage, prog):
    """stage 0: Yui asks, 1: + plain answer, 2: + 教科書っぽい… + note"""
    sc = ChatScene(plain(s["hook"]["jp"]), s["hook"]["mm"], "HOOK", prog)
    y = 470
    lay = sc.layer("pop", 0.0) if stage == 0 else sc.layer()
    y, _ = full_bubble(lay, y, s["q"], False)
    if stage >= 1:
        lay = sc.layer("pop", 0.0) if stage == 1 else sc.layer()
        y, _ = full_bubble(lay, y, s["plain"], True, size=50)
    if stage == 0:
        sc.sfx.append((0.0, "pon"))
    elif stage == 1:
        sc.sfx.append((0.0, "pon"))
    else:
        lay = sc.layer("pop", 0.0)
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([250, y + 20, W - 250, y + 140], 60, fill=(255, 255, 255), outline=RED, width=6)
        d.text((W / 2, y + 80), "教科書っぽい…", font=jfont(54), fill=RED, anchor="mm")
        lay2 = sc.layer("in", 0.5)
        d2 = ImageDraw.Draw(lay2)
        n = len(mm_lines(d2, s["plain_note"], 40, 840))
        d2.rounded_rectangle([80, y + 180, W - 80, y + 230 + n * 66], 36, fill=(255, 255, 255))
        R.lblock(d2, 120, y + 204, s["plain_note"], mfont(40, 600), INK, 840)
        sc.sfx += [(0.0, "bonk"), (0.5, "pon_soft")]
    return sc


def f_end(s, prog):
    sc = ChatScene("…会話が終わった", s["end_note"], "", prog)
    y = 470
    st = sc.layer()
    y, _ = full_bubble(st, y, s["q"], False)
    y, _ = full_bubble(st, y, s["plain"], True, size=50)
    lay = sc.layer("pop", 0.0)
    y, _ = full_bubble(lay, y, s["end"], False, size=50)
    lay2 = sc.layer("fade", 0.6)
    d = ImageDraw.Draw(lay2)
    d.text((W / 2, y + 30), "・ ・ ・", font=jfont(70), fill=(175, 168, 160), anchor="mt")
    d.rounded_rectangle([80, y + 150, W - 80, y + 280], 36, fill=(255, 255, 255))
    d.text((W / 2, y + 215), s["end_note"], font=mfont(44, 700), fill=RED, anchor="mm")
    sc.sfx += [(0.0, "pon"), (0.6, "crickets")]
    return sc


def f_turn(s, prog):
    sc = ChatScene(plain(s["turn"]["jp"]), "ကဲ၊ ဒီ pattern လေးတွေ ချိတ်ပြီး…", "", prog)
    lay = sc.layer("bounce", 0.0)
    a = avatar_img("Rio", 320)
    lay.alpha_composite(a, (W // 2 - 160, 520))
    lay2 = sc.layer("pop", 0.2)
    d = ImageDraw.Draw(lay2)
    d.rounded_rectangle([110, 930, W - 110, 1150], 50, fill=(255, 255, 255), outline=PINK, width=6)
    d.text((W / 2, 1005), "パターンを4つ つなげるだけ！", font=jfont(52), fill=PINK, anchor="mm")
    d.text((W / 2, 1095), "ကဲ၊ ဒီ pattern လေးတွေ ချိတ်ပြီး", font=mfont(42, 700), fill=SUB, anchor="mm")
    ImageDraw.Draw(sc.layer("in", 0.5)).text((W / 2, 1230), "အထာကျကျ ပြောကြည့်ရအောင်!", font=mfont(52, 700), fill=PINK, anchor="mm")
    sc.sfx += [(0.0, "whoosh"), (0.2, "pon")]
    return sc


def f_patterns(s, upto, prog):
    sc = ChatScene("この4つをつなげる", "ဒီ pattern ၄ ခုကို ဆက်ပြောရုံပဲ", "PATTERNS", prog)
    y = 460
    for k, p in enumerate(s["patterns"]):
        if k > upto:
            break
        c = STEP[k + 1]
        lay = sc.layer("pop", 0.0) if k == upto else sc.layer()
        d = ImageDraw.Draw(lay)
        d.rounded_rectangle([70, y, W - RIGHT + 40, y + 215], 36, fill=(255, 255, 255), outline=c, width=6)
        d.ellipse([102, y + 44, 166, y + 108], fill=c)
        d.text((134, y + 76), str(k + 1), font=jfont(36), fill=(255, 255, 255), anchor="mm")
        draw_text_block(d, 190, y + 10, p["jp"], 46, 800, col=c)
        d.text((190, y + 160), p["mm"], font=mfont(36, 600), fill=SUB, anchor="lm")
        y += 240
    if upto == 3:
        ImageDraw.Draw(sc.layer("fade", 0.4)).text((W / 2, y + 40), "~ နေရာမှာ ကိုယ့်အကြောင်း ထည့်ပြီး ပြောကြည့်",
                                                   font=mfont(40, 700), fill=(37, 110, 214), anchor="mm")
    sc.sfx.append((0.0, "pon"))
    return sc


def f_talk(s, n, prog):
    """Conversation up to line n; line n is big, earlier ones small and faded."""
    sc = ChatScene("カッコよく答えると…", "Pattern ၄ ခု ဆက်ပြောလိုက်ရင်…", "", prog)
    talk = s["talk"]
    st = sc.layer()
    y = 440
    first = max(0, n - 7)
    for i in range(first, n):
        y = small_bubble(st, y, talk[i]["jp"], talk[i]["who"] == "Rio")
    y += 8
    line = talk[n]
    me = line["who"] == "Rio"
    lay = sc.layer("pop", 0.0)
    step = line.get("step")
    y2, box = full_bubble(lay, y, line, me, outline=STEP.get(step))
    if step:
        p = s["patterns"][step - 1]
        tag = "%d  %s" % (step, plain(p["jp"]))
        d = ImageDraw.Draw(sc.layer("fade", 0.35))
        f = jfont(30)
        tw = d.textlength(tag, font=f) + 40
        d.rounded_rectangle([box[2] - tw, y2 - 10, box[2], y2 + 50], 30, fill=STEP[step])
        d.text((box[2] - tw / 2, y2 + 20), tag, font=f, fill=(255, 255, 255), anchor="mm")
    if line.get("win"):
        lay3 = sc.layer("pop", 0.45)
        label(lay3, W // 2 - 190, y2 + 20, "စကားဆက်သွားပြီ", GREEN, 42)
        sc.sfx += [(0.45, "success")]
    sc.sfx.append((0.0, "pon"))
    return sc


def f_chain(s, prog):
    sc = ChatScene("一つにつなげると…", "တစ်ဆက်တည်း ပြောကြည့်ရင်", "ALL IN ONE", prog)
    lay = sc.layer("pop", 0.0)
    d = ImageDraw.Draw(lay)
    top = 450
    hj = text_block_h(d, s["chain"]["jp"], 48, 800)
    mml = mm_lines(d, s["chain"]["mm"], 36, 800, 500)
    d.rounded_rectangle([50, top, W - RIGHT + 60, top + hj + len(mml) * 56 + 120], 40, fill=(255, 255, 255))
    y = draw_text_block(d, 95, top + 40, s["chain"]["jp"], 48, 800)
    for m in mml:
        R.lblock(d, 95, y + 6, m, mfont(36, 500), SUB, 860)
        y += 58
    sc.sfx += [(0.0, "whoosh"), (0.1, "pon")]
    return sc


def f_your_turn(s, count, prog):
    """count None: blanks appear (Yui asks); 3,2,1: countdown."""
    sc = ChatScene("YOUR TURN", "ကိုယ့်အကြောင်း ထည့်ပြီး ပြောကြည့်", "YOUR TURN", prog)
    st = sc.layer("pop", 0.0) if count is None else sc.layer()
    y, _ = full_bubble(st, 470, s["q2"], False)
    y += 20
    d = ImageDraw.Draw(st)
    for k, b in enumerate(s["blanks"]):
        c = STEP[k + 1]
        f = jfont(44)
        us = units(b)
        w = sum(adv(d, u, f, jfont(int(44 * RUBY), False)) for u in us) + 70
        x = W - RIGHT - w
        d.rounded_rectangle([x, y, x + w, y + 112], 36, fill=(255, 255, 255), outline=c, width=6)
        draw_units(d, x + 35, y + 44, us, f, jfont(20, False), INK)
        y += 132
    if count is not None:
        lay = sc.layer("pop", 0.0)
        dd = ImageDraw.Draw(lay)
        dd.text((W / 2, y + 120), str(count), font=jfont(180), fill=(200, 188, 176), anchor="mm")
        dd.text((W / 2, y + 260), "စဉ်းစားကြည့်…", font=mfont(44, 650), fill=SUB, anchor="mm")
        sc.sfx.append((0.0, "tick"))
    else:
        sc.sfx.append((0.0, "pon"))
    return sc


def f_example(s, upto, prog):
    sc = ChatScene("例えば…", "ဥပမာ ဒီလို", "EXAMPLE", prog)
    st = sc.layer()
    d = ImageDraw.Draw(st)
    y = 430
    qh = text_block_h(d, s["q2"]["jp"], 44, 760)
    d.rounded_rectangle([60, y, W - RIGHT + 40, y + qh + 80], 34, fill=(250, 250, 250))
    st.alpha_composite(avatar_img("Yui", 80), (85, y + 32))
    yq = draw_text_block(d, 195, y + 18, s["q2"]["jp"], 44, 760)
    R.lblock(d, 195, yq - 6, s["q2"]["mm"], mfont(32, 500), SUB, 760)
    y += qh + 104
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for js, ms_ in ((42, 34), (40, 32), (38, 31), (36, 30), (34, 28)):  # shrink until all 4 cards fit above the footer
        tot = sum(text_block_h(probe, ex["jp"], js, 720) + len(mm_lines(probe, ex["mm"], ms_, 720)) * int(ms_ * 1.6) + 66 + 14
                  for ex in s["examples"])
        if y + tot <= H - 170:
            break
    for k, ex in enumerate(s["examples"]):
        if k > upto:
            break
        c = STEP[k + 1]
        lay = sc.layer("pop", 0.0) if k == upto else st
        dd = ImageDraw.Draw(lay)
        hj = text_block_h(dd, ex["jp"], js, 720)
        mml = mm_lines(dd, ex["mm"], ms_, 720)
        h = hj + len(mml) * int(ms_ * 1.6) + 66
        dd.rounded_rectangle([60, y, W - RIGHT + 40, y + h], 34, fill=(255, 255, 255), outline=c, width=5)
        dd.ellipse([85, y + 25, 135, y + 75], fill=c)
        dd.text((110, y + 50), str(k + 1), font=jfont(28), fill=(255, 255, 255), anchor="mm")
        yy = draw_text_block(dd, 155, y + 18, ex["jp"], js, 720)
        for m in mml:
            R.lblock(dd, 155, yy - 4, m, mfont(ms_, 600), INK, 780)
            yy += int(ms_ * 1.6)
        y += h + 14
    sc.sfx.append((0.0, "pon"))
    return sc


def f_follow(s, prog):
    sc = ChatScene("", "", "FOLLOW", prog)
    for name, cx in (("Rio", W // 2 - 200), ("Yui", W // 2 + 200)):
        sc.layer("pop", 0.0).alpha_composite(avatar_img(name, 230), (cx - 115, 420))
    d = ImageDraw.Draw(sc.layer("in", 0.2))
    d.text((W / 2, 760), "Follow", font=jfont(62), fill=PINK, anchor="mt")
    d.text((W / 2, 860), "Learn with Rio ♡", font=jfont(88), fill=INK, anchor="mt")
    d = ImageDraw.Draw(sc.layer("fade", 0.45))
    y = draw_text_block(d, 0, 1040, s["follow"][0]["jp"], 44, 900, col=SUB, center=True)
    R.block(d, y + 20, s["follow"][0]["mm"], mfont(40, 600), FADE, maxw=900)
    sc.sfx += [(0.0, "pon"), (0.2, "success")]
    return sc


# ---------------------------------------------------------------- spoken order + timeline
def main_turns(s):
    t = []
    add = lambda line, kind, **kw: t.append(dict(line, jp=plain(line["jp"]), kana=reading(line["jp"]), type=kind, **kw))  # noqa: E731
    add(s["q"], "q")
    add(s["plain"], "plain")
    add(dict(s["hook"], who="Rio"), "hook")
    add(s["end"], "end")
    add(s["turn"], "turn")
    for i, line in enumerate(s["talk"]):
        add(line, "talk", n=i)
    add(s["chain"], "chain")
    add(s["q2"], "q2")
    for i, ex in enumerate(s["examples"]):
        add(ex, "ex", n=i)
    for i, line in enumerate(s["follow"]):
        add(line, "follow", n=i)
    return t


def audio_groups(s):
    mt = main_turns(s)
    by = lambda *kinds: [x for x in mt if x["type"] in kinds]  # noqa: E731
    g = [("plain", by("q", "plain", "hook", "end")), ("normal", by("turn")), ("normal", by("talk")),
         ("normal", by("chain")), ("normal", by("q2", "ex")), ("normal", by("follow"))]
    assert sum(len(x) for _, x in g) == len(mt)
    return g


def timeline(s, mb):
    mt = main_turns(s)
    at = {(x["type"], x.get("n")): i for i, x in enumerate(mt)}
    seg = lambda key, pad: (mb[at[key]], mb[at[key] + 1], pad)  # noqa: E731
    tl = [(lambda p: f_hook(s, 0, p), seg(("q", None), 0.2)),
          (lambda p: f_hook(s, 1, p), seg(("plain", None), 0.3)),
          (lambda p: f_hook(s, 2, p), seg(("hook", None), 2.6)),
          (lambda p: f_end(s, p), seg(("end", None), 2.0)),
          (lambda p: f_turn(s, p), seg(("turn", None), 0.8))]
    for k in range(4):
        tl.append((lambda p, k=k: f_patterns(s, k, p), ("silence", 1.1 if k < 3 else 2.2)))
    for i in range(len(s["talk"])):
        last = i == len(s["talk"]) - 1
        tl.append((lambda p, i=i: f_talk(s, i, p), seg(("talk", i), 1.6 if last else 0.6)))
    tl.append((lambda p: f_chain(s, p), seg(("chain", None), 1.2)))
    tl.append((lambda p: f_your_turn(s, None, p), seg(("q2", None), 0.8)))
    for c in (3, 2, 1):
        tl.append((lambda p, c=c: f_your_turn(s, c, p), ("silence", 1.0)))
    for i in range(len(s["examples"])):
        tl.append((lambda p, i=i: f_example(s, i, p), seg(("ex", i), 0.5 if i < 3 else 1.4)))
    tl.append((lambda p: f_follow(s, p), (mb[at[("follow", 0)]], mb[-1], 1.0)))
    return tl


# ---------------------------------------------------------------- sound effects (made here, no copyright)
def _env(n, a, dcy):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / dcy)


def _tone(f, dur, a=0.003, dcy=0.1, amp=0.3, sweep=0.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * np.exp(sweep * t)) / SR
    return np.sin(ph) * _env(n, a, dcy) * amp


def _noise(dur, smooth, seed=1):
    n = int(SR * dur)
    return np.convolve(np.random.default_rng(seed).standard_normal(n), np.ones(smooth) / smooth, "same")


def _mix(*parts):
    n = max(int(o * SR) + len(p) for o, p in parts)
    y = np.zeros(n)
    for o, p in parts:
        y[int(o * SR):int(o * SR) + len(p)] += p
    return y


_SFX = {}


def sfx(name):
    if name in _SFX:
        return _SFX[name]
    if name in ("pon", "pon_soft"):  # Ye's pick "B ポン！"
        y = _mix((0, _tone(500, 0.1, 0.001, 0.03, 0.4, 14)), (0.07, _tone(2093, 0.6, 0.002, 0.16, 0.18)),
                 (0.12, _tone(3136, 0.5, 0.002, 0.12, 0.10)))
        if name == "pon_soft":
            y = y * 0.5
    elif name == "bonk":
        y = _mix((0, _tone(420, 0.45, 0.002, 0.18, 0.4, -3.2)), (0, _tone(210, 0.3, 0.002, 0.12, 0.25, -2)))
    elif name == "crickets":
        def chirp():
            n = int(SR * 0.05); t = np.arange(n) / SR
            return np.sin(2 * np.pi * 4300 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 60 * t)) * _env(n, 0.003, 0.02) * 0.12
        y = _mix(*[(i * 0.09 + (0.5 if i >= 3 else 0), chirp()) for i in range(6)])
    elif name == "whoosh":
        n = int(SR * 0.45); t = np.arange(n) / SR
        y = _noise(0.45, 12) * np.sin(np.pi * t / 0.45) ** 2 * 0.35
    elif name == "success":
        y = _mix(*[(0.08 * i, _tone(f, 0.7, 0.002, 0.18, 0.16)) for i, f in enumerate((1046.5, 1318.5, 1568, 2093))])
    elif name == "tick":
        y = _tone(880, 0.12, 0.001, 0.04, 0.3)
    else:
        y = np.zeros(1)
    _SFX[name] = y.astype(np.float32)
    return _SFX[name]


# ---------------------------------------------------------------- render
def render(lesson_path, wav, out_path):
    s = json.load(open(lesson_path, encoding="utf-8"))
    mt = main_turns(s)
    mb, _ = RS.bounds(wav, mt)
    tl = timeline(s, mb)
    voice = RS.load_wav(wav)
    tmp = tempfile.mkdtemp()
    pieces, audio, sfx_at, t0, n = [], [], [], 0, len(tl)
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
        e = sfx(name)
        m = min(len(e), len(y) - a)
        if m > 0:
            y[a:a + m] += e[:m] * SFX_GAIN
    y = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    aud = os.path.join(tmp, "all.wav")
    with wave.open(aud, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
    lst = os.path.join(tmp, "v.txt")
    with open(lst, "w") as fv:
        fv.writelines("file '%s'\n" % f for f in pieces)
    vcat = os.path.join(tmp, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vcat], check=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    part = out_path[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vcat, "-i", aud, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", part], check=True)
    os.replace(part, out_path)
    secs = len(y) / SR
    print("rendered chat", out_path, len(pieces), "pieces", round(secs, 1), "s")
    return secs


if __name__ == "__main__":
    render(*sys.argv[1:4])
