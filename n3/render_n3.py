"""Learn with Rio - N3 grammar "Rio先生" chalkboard video, made from Ye's own note (N3 文法 先生ノート).
One note = one video: hook -> ① meaning -> ② how to connect -> ④ examples -> ⑤ common mistake -> ⑦ quiz -> outro.
All teaching text comes from the note as it is (nothing rewritten by AI).

usage: python n3/render_n3.py n3/notes/001.json main.wav out.mp4   (main.bounds.json next to the wav = exact line bounds)"""
import json, math, os, re, subprocess, sys, wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "steps"))
sys.path.insert(0, ROOT)
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
import render_steps as RS  # noqa: E402

W, H, FPS, SR = RS.W, RS.H, 30, 24000
BOARD = (38, 84, 72)
CHALK = (244, 246, 240)
SOFT = (200, 226, 216)
YEL = (255, 214, 92)
PINK = (255, 170, 186)
RED = (240, 96, 96)
OK_GREEN = (110, 214, 150)
BX0, BX1, BY0, BY1 = 64, W - 64, 174, 1216
JP = re.compile("[぀-ヿ一-鿿]")


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def back(x):
    x = max(0.0, min(1.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------------------------------------------------------------- note -> script
def core_forms(title):
    """'〜ようになる/〜ようにする' -> ['ようになる', 'ようにする'] (the part to highlight in sentences)."""
    out = []
    for p in re.split(r"[/／・]", title):
        p = re.sub(r"[〜~（）()]", "", p).strip()
        if p:
            out.append(p)
    return out


def grammar_segs(sentence, title):
    """Split a sentence into [(text, is_grammar)] - the grammar part is highlighted."""
    cores = sorted(core_forms(title), key=len, reverse=True)
    spans = []
    for c in cores:
        for cut in (c, c[:-1] if len(c) > 2 else c):   # 'ようになる' also matches 'ようになった'
            for m in re.finditer(re.escape(cut), sentence):
                if not any(a < m.end() and m.start() < b for a, b in spans):
                    spans.append((m.start(), m.end()))
            if spans:
                break
    spans.sort()
    out, i = [], 0
    for a, b in spans:
        if a > i:
            out.append((sentence[i:a], False))
        out.append((sentence[a:b], True))
        i = b
    if i < len(sentence):
        out.append((sentence[i:], False))
    return out


# Ye (11/06): no English letters like A / Na on screen -> Japanese grammar words (+ Burmese under the table labels)
V_KIND = {"辞": "辞書形", "ている": "ている", "ない": "ない形", "た": "た形", "て": "て形", "ます": "ます形", "可能": "可能形",
          "": "", "る": "辞書形", "よう": "意向形", "ば": "ば形", "ず": "ない形"}
TOKEN = re.compile(r"(?<![A-Za-z0-9])(V|Aい|Na(?:な|である)?|N(?:の|である)?)(?![A-Za-z0-9])([\u3040-\u30ff\u4e00-\u9fff]*)")


def jp_terms(text):
    """'Aい + までに' -> 'い形容詞 + までに'; 'V辞' -> '動詞(辞書形)'."""
    def one(m):
        head, rest = m.group(1), m.group(2)
        if head == "V":
            k = next((V_KIND[x] for x in sorted(V_KIND, key=len, reverse=True) if rest.startswith(x)), "")
            tail = rest[len(next((x for x in sorted(V_KIND, key=len, reverse=True) if rest.startswith(x)), "")):]
            return ("動詞(%s)" % k if k else "動詞") + tail
        if head == "Aい":
            return "い形容詞" + rest
        if head.startswith("Na"):
            return "な形容詞" + ("＋" + head[2:] if head[2:] else "") + rest
        return "名詞" + ("＋" + head[1:] if head[1:] else "") + rest
    return TOKEN.sub(one, text)


def form_label(form):
    """'V辞・Vている・Vない' -> ('動詞(辞書形・ている・ない形)', 'ကြိယာ')"""
    parts = [x.strip() for x in re.split("[・/]", form) if x.strip()]
    if parts and all(p.startswith("V") for p in parts):
        ks = [jp_terms(p) for p in parts]
        inner = [re.sub(r"^動詞\((.*)\)$", r"\1", k) for k in ks]
        return "動詞(%s)" % "・".join(i for i in inner if i != "動詞"), "ကြိယာ"
    lab = "・".join(jp_terms(p) for p in parts)
    mm_ = "နာမဝိသေသန" if "形容詞" in lab else ("နာမ်" if lab.startswith("名詞") else ("ကြိယာ" if "動詞" in lab else ""))
    return lab, mm_


NUM_MM = {"A": "1", "B": "2", "C": "3", "D": "4"}


def split_meaning(line):
    """'A. 〜နေတုန်း (မပြောင်းခင်) — explanation (若いうちに・温かいうちに)' -> label, head, body, [jp examples]"""
    m = re.match(r"\s*([A-Z])[.．]\s*(.*)", line)
    label, rest = (m.group(1), m.group(2)) if m else ("", line)
    jp = []
    pm = re.search(r"[（(]([^()（）]*)[)）]\s*$", rest)
    if pm and JP.search(pm.group(1)) and not re.search("[က-႟]", pm.group(1)):
        jp = [x.strip() for x in re.split("[・、]", pm.group(1)) if x.strip()]
        rest = rest[:pm.start()].rstrip()
    head, _, body = rest.partition("—")
    return label, head.strip(), body.strip(), jp


def split_mistake(line):
    """'日本に来たうちに… ❌ → 日本にいるうちに ✅ (note)' -> wrong, right, note"""
    a, _, b = line.partition("→")
    wrong = a.replace("❌", "").strip()
    m = re.match(r"(.*?)✅\s*(.*)", b.strip())
    right, note = (m.group(1).strip(), m.group(2).strip()) if m else (b.strip(), "")
    note = re.sub(r"^[（(](.*)[)）]$", r"\1", note)
    return wrong, right, note


def quiz_sentence(q, ans):
    return re.sub(r"[（(]\s*[）)]", ans, q)


_KK = None


def auto_kana(jp):
    """Hiragana with spaces between words (pykakasi on the runner; hand-checked kana in the note file wins)."""
    global _KK
    try:
        import pykakasi
    except ImportError:
        return ""
    if _KK is None:
        _KK = pykakasi.kakasi()
    out = []
    for tok in _KK.convert(jp):
        h = tok["hira"]
        if not h.strip():
            continue
        if out and (re.match(r"^[、。！？!?」』）)…〜ー]", h) or re.match(r"^(は|が|を|に|へ|で|と|も|の|ね|よ|か|な|て|た|だ|ます|ない)$", h)):
            out[-1] += h
        else:
            out.append(h)
    return " ".join(out)


def fill_kana(n):
    """Every Japanese line shown on screen gets hiragana (Ye: 'hiragana ပါ')."""
    k = n.setdefault("kana", {})
    lines = [e["jp"] for e in n.get("examples", [])]
    for m in n.get("mistakes", [])[:1]:
        w, r, _ = split_mistake(m)
        lines += [w, r]
    for q in n.get("quiz", [])[:1]:
        lines += [q["q"], quiz_sentence(q["q"], q["choices"][q["answer"] - 1])]
    lines += [h["jp"] for h in n.get("hook", [])]
    for ln in lines:
        if ln and ln not in k and JP.search(ln) and re.search("[\u4e00-\u9fff]", ln):
            kk = auto_kana(ln)
            if kk:
                k[ln] = kk
    return n


def script(n):
    """Spoken lines (TTS) grouped into 5 short TTS requests + the plan of the video."""
    k = n.get("kana", {})
    title = n["title"]
    say = []

    def add(key, who, jp, grp):
        say.append({"key": key, "who": who, "jp": jp, "kana": k.get(jp, ""), "grp": grp})

    hook = n.get("hook") or [
        {"who": "Yui", "jp": "先生、「%s」って、どういう意味？" % "」と「".join(core_forms(title)), "mm": "ဆရာ၊ ဒါ ဘာကို ပြောတာလဲ?"},
        {"who": "Rio", "jp": "N3によく出る文法だよ。いっしょに見よう！", "mm": "N3 မှာ မကြာခဏ ထွက်တယ်၊ အတူတူ ကြည့်ရအောင်"}]
    for i, h in enumerate(hook):
        add("h%d" % i, h["who"], h["jp"], 0)
    # the meaning is Burmese text on the board; Rio only introduces it (the examples come later, so no repeats here)
    add("m0", "Rio", "意味は二つあるよ。" if len(n["meaning"]) > 1 else "意味はこれだよ。", 0)
    spoken = {x for e in n["examples"][:3] for x in [e["jp"]]}
    for i, (form, exs) in enumerate(n["form"][:4]):
        cands = [x.strip() for x in re.split("[・、]", exs) if x.strip()]
        pick = next((c for c in cands if not any(c in x for x in spoken)), cands[0] if cands else "")
        if pick:
            add("f%d" % i, "Rio", pick + "。", 1)
            spoken.add(pick)
    for i, e in enumerate(n["examples"][:3]):
        add("e%d" % i, "Rio" if i % 2 == 0 else "Yui", e["jp"], 1)
    if n.get("mistakes"):
        wrong, right, _ = split_mistake(n["mistakes"][0])
        cores = core_forms(title)
        cut = next((wrong[:wrong.find(c) + len(c)] for c in cores if c in wrong), "")
        add("x0", "Rio", ("%s…じゃなくて、%s！" % (cut, right)) if cut else ("正しいのは、%s！" % right), 2)
    if n.get("quiz"):
        q = n["quiz"][0]
        add("q0", "Yui", "問題！", 2)
        add("q1", "Rio", quiz_sentence(q["q"], q["choices"][q["answer"] - 1]), 2)
    if n.get("quiz") and n["quiz"][0].get("each"):
        # Yui asks about each choice, Rio answers: the change of speaker keeps voice and text in sync (11/06: one voice drifted)
        no = ["ちがうよ。", "これも、ちがう。", "それも、だめなんだ。"]
        w = 0
        for i, c in enumerate(n["quiz"][0]["each"][:4]):
            add("c%d" % i, "Yui", "%sは？" % c["choice"], 3)
            if c["ok"]:
                add("r%d" % i, "Rio", "正解！", 3)
            else:
                add("r%d" % i, "Rio", no[min(w, 2)], 3)
                w += 1
    add("o0", "Yui", "わかった！ありがとう、先生！", 4)
    add("o1", "Rio", "リアルな日本語を話したいなら、Rioをフォローしてね！", 4)
    add("o2", "Yui", "バイバーイ！", 4)
    return hook, say


def audio_groups(n):
    fill_kana(n)
    _, say = script(n)
    return [g for g in ([t for t in say if t["grp"] == k] for k in range(5)) if g]


# ---------------------------------------------------------------- drawing helpers
d0 = ImageDraw.Draw(Image.new("RGB", (10, 10)))


def make_bg():
    bg = Image.new("RGB", (W, H), (246, 241, 232))
    bd = ImageDraw.Draw(bg)
    bd.rectangle([0, 1300, W, H], fill=(214, 186, 150))
    bd.rounded_rectangle([40, 150, W - 40, 1240], 30, fill=(120, 86, 56))
    bd.rounded_rectangle([BX0, BY0, BX1, BY1], 18, fill=BOARD)
    for i in range(70):
        x, y = (i * 137) % (W - 160) + 80, (i * 251) % 1000 + 190
        bd.ellipse([x, y, x + 3, y + 3], fill=(70, 116, 102))
    bd.rectangle([120, 1216, W - 120, 1240], fill=(150, 110, 74))
    for i, c in enumerate([(255, 255, 255), YEL, PINK]):
        bd.rounded_rectangle([200 + i * 70, 1206, 250 + i * 70, 1220], 6, fill=c)
    bd.rectangle([0, H - 140, W, H], fill=(255, 255, 255))
    bd.text((W / 2, H - 70), "Learn with Rio ♡", font=RS.jfont(40), fill=(222, 98, 150), anchor="mm")
    return bg.convert("RGBA")


def layer():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)


def put(img, lay, alpha=1.0, dy=0):
    if alpha <= 0:
        return
    if alpha < 1:
        lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    if dy:
        img.alpha_composite(lay, (0, int(dy)))
    else:
        img.alpha_composite(lay)


def text(img, xy, s, size, col=CHALK, anchor="mt", alpha=1.0, bold=True, dy=0):
    if alpha <= 0 or not s:
        return
    lay, d = layer()
    d.text(xy, s, font=RS.jfont(max(8, int(size)), bold), fill=col, anchor=anchor)
    put(img, lay, alpha, dy)


def mm(img, s, y, alpha=1.0, size=38, col=CHALK, maxw=880, dy=0):
    """Burmese (may contain Japanese too). Returns the y under the text."""
    if not s:
        return y
    lay, d = layer()
    y2 = RS.R.block(d, y, s, RS.mfont(size, 600), col, maxw=maxw, gap=16)
    put(img, lay, alpha, dy)
    return y2


def kana(img, s, y, alpha=1.0, size=30, col=SOFT, dy=0):
    if not s:
        return y
    lay, d = layer()
    y2 = RS.kana_block(d, y, s, size, col, 900)
    put(img, lay, alpha, dy)
    return y2


def rich_lines(segs, fnt, maxw):
    """Wrap [(text, hl)] by characters -> lines of [(text, hl)]."""
    lines, cur, cw = [], [], 0.0
    for s, hl in segs:
        for ch in s:
            w = d0.textlength(ch, font=fnt)
            if cur and cw + w > maxw and ch not in RS.NO_START:
                lines.append(cur)
                cur, cw = [], 0.0
            if cur and cur[-1][1] == hl:
                cur[-1] = (cur[-1][0] + ch, hl)
            else:
                cur.append((ch, hl))
            cw += w
    if cur:
        lines.append(cur)
    return lines


def rich(img, segs, y, size=56, alpha=1.0, hl_p=1.0, col=CHALK, hcol=YEL, maxw=900, dy=0):
    """Sentence with the grammar part highlighted (yellow, underline grows in with hl_p). Returns the y under it."""
    fnt = RS.jfont(size)
    lay, d = layer()
    for ln in rich_lines(segs, fnt, maxw):
        tw = sum(d.textlength(s, font=fnt) for s, _ in ln)
        x = (W - tw) / 2
        for s, hl in ln:
            w = d.textlength(s, font=fnt)
            if hl:
                d.rounded_rectangle([x - 6, y - 6, x + w + 6, y + size + 10], 14, fill=(255, 214, 92, int(60 * hl_p)))
                d.line([(x, y + size + 8), (x + w * hl_p, y + size + 8)], fill=hcol, width=6)
            d.text((x, y), s, font=fnt, fill=hcol if hl else col)
            x += w
        y += int(size * 1.5)
    put(img, lay, alpha, dy)
    return y


def heading(img, s, t):
    """Section label at the top of the board ('① အဓိပ္ပာယ်')."""
    p = ease(t / 0.35)
    lay, d = layer()
    f = RS.mfont(40, 700)
    w = RS.R.tlen(d, s, f, RS.jfont(36)) if hasattr(RS.R, "tlen") else d.textlength(s, font=f)
    x0 = W / 2 - w / 2 - 34
    d.rounded_rectangle([x0, 300, x0 + w + 68, 376], 38, fill=(255, 255, 255, 40), outline=YEL, width=3)
    RS.R.block(d, 312, s, f, YEL, maxw=900, gap=0)
    put(img, lay, p, 30 * (1 - p))


def badge(img, cx, cy, s, col, p, size=44):
    if p <= 0:
        return
    r = 40 * min(1.15, p)
    lay, d = layer()
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    f = RS.mfont(max(8, int(size * min(1.15, p))), 700) if re.search("[က-႟]", s) else RS.jfont(max(8, int(size * min(1.15, p))))
    d.text((cx, cy + (4 if re.search("[က-႟]", s) else 0)), s, font=f, fill=(255, 255, 255), anchor="mm")
    put(img, lay, min(1, p * 1.5))


def mark(img, cx, cy, good, p):
    """Round ✅ / ❌ mark drawn with lines (the fonts have no emoji)."""
    if p <= 0:
        return
    r = 34 * min(1.15, p)
    lay, d = layer()
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=OK_GREEN if good else RED)
    if good:
        d.line([(cx - r * .45, cy), (cx - r * .1, cy + r * .38), (cx + r * .5, cy - r * .35)], fill=(255, 255, 255), width=8, joint="curve")
    else:
        for s in (1, -1):
            d.line([(cx - r * .4, cy - s * r * .4), (cx + r * .4, cy + s * r * .4)], fill=(255, 255, 255), width=8)
    put(img, lay, min(1, p * 1.5))


def speaker_bubble(img, who, jp, kana_s, mm_s, y, p):
    """Chat-like bubble on the board: Yui left, Rio right."""
    if p <= 0:
        return y
    left = who == "Yui"
    fnt = RS.jfont(46)
    lines = rich_lines([(jp, False)], fnt, 700)
    bw = max(d0.textlength("".join(s for s, _ in ln), font=fnt) for ln in lines) + 70
    bw = max(bw, 360)
    bh = len(lines) * 66 + 40
    x0 = 110 if left else BX1 - 46 - bw
    lay, d = layer()
    col = (255, 255, 255) if left else (214, 246, 196)
    d.rounded_rectangle([x0, y, x0 + bw, y + bh], 34, fill=col)
    yy = y + 22
    for ln in lines:
        d.text((x0 + 35, yy), "".join(s for s, _ in ln), font=fnt, fill=RS.INK)
        yy += 66
    d.text((x0 + (0 if left else bw), y - 12), who, font=RS.jfont(28), fill=RS.SPK_COL[who] if left else (150, 230, 170),
           anchor="lb" if left else "rb")
    put(img, lay, min(1, p * 1.4), 40 * (1 - p))
    y2 = y + bh + 12
    if kana_s:
        y2 = kana(img, kana_s, y2, p, 28)
    y2 = mm(img, mm_s, y2 + 4, p, 34, SOFT)
    return y2 + 30


# ---------------------------------------------------------------- scenes
class Video:
    def __init__(self, n, wav, bounds):
        self.n = n
        self.hook, self.say = script(n)
        self.k = n.get("kana", {})
        self.voice = RS.load_wav(wav)
        assert len(bounds) == len(self.say) + 1, (len(bounds), len(self.say))
        self.piece = {t["key"]: (bounds[i], bounds[i + 1]) for i, t in enumerate(self.say)}
        self.who = {t["key"]: t["who"] for t in self.say}
        self.bg = make_bg()
        self.plan()

    # ---- timeline: scenes made of 'say' (a voice line) and 'hold' (silence) steps
    def plan(self):
        n = self.n
        has = set(self.piece)
        S = []
        S.append(("hook", [("hold", 0.9)] + [("say", "h%d" % i) for i in range(len(self.hook))] + [("hold", 0.4)]))
        mean = [("mark", "m0"), ("say", "m0"), ("hold", 2.4)]
        for i in range(1, min(2, len(n["meaning"]))):
            mean += [("mark", "m%d" % i), ("hold", 3.6)]
        S.append(("meaning", [("hold", 0.5)] + mean + [("hold", 0.6)]))
        S.append(("form", [("hold", 0.5)] + [("say", "f%d" % i) for i in range(4) if "f%d" % i in has] + [("hold", 1.2)]))
        ex = []
        for i in range(min(3, len(n["examples"]))):
            ex += [("say", "e%d" % i), ("hold", 1.7)]
        S.append(("examples", [("hold", 0.4)] + ex))
        if "x0" in has:
            S.append(("mistake", [("hold", 1.4), ("say", "x0"), ("hold", 2.6)]))
        if "q0" in has:
            S.append(("quiz", [("hold", 0.4), ("say", "q0"), ("hold", 0.6), ("count", 3.0), ("say", "q1"), ("hold", 3.4)]))
        each = n["quiz"][0].get("each", []) if n.get("quiz") else []
        if each and "c0" in has:
            st = [("hold", 0.5)]
            for i, c in enumerate(each[:4]):
                st += [("say", "c%d" % i), ("say", "r%d" % i), ("hold", max(1.8, len(c["text"]) / 16.0))]
            S.append(("answers", st))
        S.append(("outro", [("hold", 0.3), ("say", "o0"), ("say", "o1"), ("say", "o2"), ("hold", 1.0)]))
        self.scenes, self.audio, self.sfx = [], [], []
        t = 0.0
        for name, steps in S:
            sc = {"name": name, "t0": t, "ev": {}, "count": None}
            self.sfx.append((t + 0.02, "whoosh" if name != "hook" else "ding"))
            for kind, v in steps:
                if kind == "say":
                    a, b = self.piece[v]
                    dur = b - a
                    sc["ev"][v] = (t - sc["t0"], t - sc["t0"] + dur)
                    self.audio.append((t, a, b))
                    t += dur + 0.15
                elif kind == "mark":
                    sc["ev"].setdefault("@" + v, (t - sc["t0"], t - sc["t0"]))
                    self.sfx.append((t, "pop"))
                elif kind == "count":
                    sc["count"] = t - sc["t0"]
                    for i in range(3):
                        self.sfx.append((t + i, "tick"))
                    self.sfx.append((t + v, "ding"))
                    t += v
                else:
                    t += v
            sc["t1"] = t
            self.scenes.append(sc)
        self.T = t
        # small sounds for things that pop in
        for sc in self.scenes:
            for key, (a, _) in sc["ev"].items():
                if sc["name"] in ("form", "examples") and key in self.who:
                    self.sfx.append((sc["t0"] + a - 0.05, "pop"))
            if sc["name"] == "mistake":
                self.sfx += [(sc["t0"] + 0.9, "swish"), (sc["t0"] + sc["ev"]["x0"][0] + 0.3, "pop")]
            if sc["name"] == "outro":
                self.sfx.append((sc["t0"] + 0.4, "sparkle"))

    def speaking(self, sc, lt):
        for key, (a, b) in sc["ev"].items():
            if key in self.who and a <= lt <= b:
                return self.who[key]
        return None

    def ev(self, sc, key, default=0.0):
        return sc["ev"].get(key, (default, default))[0]

    # ---- frames
    def frame(self, t):
        sc = next((s for s in self.scenes if s["t0"] <= t < s["t1"]), self.scenes[-1])
        lt = t - sc["t0"]
        img = self.bg.copy()
        n = self.n
        # header on the board (every scene)
        text(img, (W / 2, 196), "Rio先生の N3 文法  No.%d" % n["no"], 36, SOFT, "mt", 1.0)
        if sc["name"] != "hook":
            text(img, (W / 2, 244), n["title"], 44, CHALK, "mt", 1.0)
        # scene enter: board wipe
        p_in = ease(lt / 0.45)
        getattr(self, "s_" + sc["name"])(img, sc, lt, p_in)
        # progress bar
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([BX0 + 40, BY1 - 26, BX1 - 40, BY1 - 18], 4, fill=(60, 110, 96))
        d.rounded_rectangle([BX0 + 40, BY1 - 26, BX0 + 40 + (BX1 - BX0 - 80) * min(1, t / self.T), BY1 - 18], 4, fill=YEL)
        # teacher + student
        who = self.speaking(sc, lt)
        self.person(img, "Rio", 240, 1440, 270, who == "Rio", t, "Rio 先生")
        self.person(img, "Yui", W - 240, 1460, 230, who == "Yui", t, "Yui")
        return img.convert("RGB")

    def person(self, img, name, cx, cy, size, on, t, label):
        bob = 6 * math.sin(t * 9) if on else 0
        img.alpha_composite(RS.avatar(name, size, 8 if on else 6, 1.0 if on else 0.6), (int(cx - size / 2), int(cy - size / 2 + bob)))
        if on:
            col = RS.SPK_COL[name]
            for i in range(3):
                ph = (t * 1.6 + i / 3) % 1.0
                r = size / 2 + 10 + ph * 60
                lay, d = layer()
                side = (-45, 45) if name == "Rio" else (135, 225)
                d.arc([cx - r, cy - r, cx + r, cy + r], side[0], side[1], fill=col + (int(255 * (1 - ph)),), width=6)
                img.alpha_composite(lay)
        text(img, (cx, cy + size / 2 + 14), label, 34, (90, 60, 40), "mt", 1.0)

    def s_hook(self, img, sc, lt, p):
        n = self.n
        if n.get("star"):
            text(img, (W / 2, 262), "★ N3によく出る！", 40, PINK, "mt", ease((lt - 0.2) / 0.3))
        text(img, (W / 2, 326), n.get("category", ""), 32, SOFT, "mt", ease((lt - 0.3) / 0.3))
        sp = back(lt / 0.5)
        text(img, (W / 2, 470), n["title"], 120 * min(1.1, sp), YEL, "mm", min(1, sp * 1.5))
        y = 590
        for i, h in enumerate(self.hook):
            a = self.ev(sc, "h%d" % i, 99)
            y = speaker_bubble(img, h["who"], h["jp"], self.k.get(h["jp"], ""), h.get("mm", ""), y, ease((lt - a + 0.1) / 0.35))

    def s_meaning(self, img, sc, lt, p):
        heading(img, "① အဓိပ္ပာယ်", lt)
        y = 450
        for i, ln in enumerate(self.n["meaning"][:2]):
            label, head, body, jp = split_meaning(ln)
            a = self.ev(sc, "@m%d" % i, 99)
            q = ease((lt - a + 0.25) / 0.4)
            if q <= 0:
                break
            badge(img, 140, y + 34, NUM_MM.get(label, str(i + 1)), (222, 98, 150) if i else (52, 120, 200), back((lt - a + 0.25) / 0.4))
            yy = mm(img, head, y, q, 56, CHALK, 760, 20 * (1 - q))
            yy = mm(img, body, yy + 6, q, 40, SOFT, 820, 20 * (1 - q))
            if jp:
                yy = rich(img, grammar_segs("・".join(jp), self.n["title"]), yy + 14, 52, q, ease((lt - a) / 0.5), SOFT, YEL, 860)
            y = yy + 70

    def s_form(self, img, sc, lt, p):
        heading(img, "② ချိတ်ပုံ", lt)
        y = 450
        rows = self.n["form"][:4]
        for i, (form, exs) in enumerate(rows):
            a = self.ev(sc, "f%d" % i, 0.5 + i * 0.4)
            q = back((lt - a + 0.2) / 0.4)
            if q <= 0:
                continue
            lay, d = layer()
            d.rounded_rectangle([100, y, 460, y + 112], 24, fill=(255, 255, 255, 235))
            lab, lab_mm = form_label(form)
            main_, _, sub = lab.partition("(")
            sub = sub.rstrip(")")
            fs = 40 if len(main_) <= 6 else 32
            d.text((280, y + 34), main_, font=RS.jfont(fs), fill=RS.INK, anchor="mm")
            if sub:
                d.text((280, y + 82), sub, font=RS.jfont(26 if len(sub) <= 11 else 21), fill=(90, 92, 110), anchor="mm")
            elif lab_mm:
                d.text((280, y + 84), lab_mm, font=RS.mfont(26, 600), fill=(110, 112, 130), anchor="mm")
            d.polygon([(478, y + 40), (510, y + 56), (478, y + 72)], fill=YEL)
            put(img, lay, min(1, q * 1.5), 0)
            first = re.split("[・、]", exs)[0]
            ex_line = [x for x in re.split("[・、]", exs) if x]
            said = next((t["jp"].rstrip("。") for t in self.say if t["key"] == "f%d" % i), first)
            fnt = RS.jfont(50)
            lay, d = layer()
            x = 535
            for e in sorted(ex_line[:2], key=lambda e: e != said)[:1]:
                hp = ease((lt - a) / 0.5)
                for part, hl in grammar_segs(e, self.n["title"]):
                    w = d.textlength(part, font=fnt)
                    if hl:
                        d.rounded_rectangle([x - 4, y + 22, x + w + 4, y + 92], 12, fill=(255, 214, 92, int(70 * hp)))
                        d.line([(x, y + 92), (x + w * hp, y + 92)], fill=YEL, width=6)
                    d.text((x, y + 56), part, font=fnt, fill=YEL if hl else CHALK, anchor="lm")
                    x += w
            put(img, lay, min(1, q * 1.5), 0)
            y += 150
        # usage (③) under the table
        ua = self.ev(sc, "f%d" % (len(rows) - 1), 2.0) + 0.8
        u = [x for x in self.n.get("usage", []) if x.startswith(("「", "A", "B")) and len(x) < 60][:1]
        if u and False:  # usage lines of the PDF are sometimes wrapped out of order - not shown yet
            mm(img, u[0], 1070, ease((lt - ua) / 0.5), 34, SOFT, 900)

    def s_examples(self, img, sc, lt, p):
        heading(img, "④ ဥပမာ", lt)
        exs = self.n["examples"][:3]
        cur = 0
        for i in range(len(exs)):
            if lt >= self.ev(sc, "e%d" % i) - 0.3:
                cur = i
        e = exs[cur]
        a = self.ev(sc, "e%d" % cur)
        q = ease((lt - a + 0.3) / 0.4)
        out = ease((lt - (self.ev(sc, "e%d" % (cur + 1), 999) - 0.3)) / 0.3)
        al = q * (1 - out)
        if e.get("tag"):
            badge(img, W / 2, 500, NUM_MM.get(e["tag"], e["tag"]), (52, 120, 200) if e["tag"] == "A" else (222, 98, 150), back((lt - a + 0.3) / 0.4))
        who = "Rio" if cur % 2 == 0 else "Yui"
        text(img, (W / 2, 560), "%d / %d  ·  %s" % (cur + 1, len(exs), who), 28, SOFT, "mt", al)
        y = rich(img, grammar_segs(e["jp"], self.n["title"]), 660, 72, al, ease((lt - a - 0.2) / 0.6), CHALK, YEL, 900, 30 * (1 - q))
        y = kana(img, self.k.get(e["jp"], ""), y, al, 34)
        mm(img, e.get("mm", ""), y + 40, al, 46, CHALK)

    def s_mistake(self, img, sc, lt, p):
        heading(img, "⑤ မှားလွယ်တာ", lt)
        wrong, right, note = split_mistake(self.n["mistakes"][0])
        q = ease((lt - 0.3) / 0.4)
        mark(img, W / 2, 490, False, back((lt - 0.3) / 0.4))
        segs = grammar_segs(wrong, self.n["title"])
        y = rich(img, segs, 560, 56, q, 1.0, SOFT, (255, 150, 150), 900)
        # strike-through grows over the wrong sentence
        s = ease((lt - 0.9) / 0.5)
        if s > 0:
            fnt = RS.jfont(56)
            lay, d = layer()
            yy = 560
            for ln in rich_lines(segs, fnt, 900):
                tw = sum(d.textlength(x, font=fnt) for x, _ in ln)
                x0 = (W - tw) / 2
                d.line([(x0 - 10, yy + 34), (x0 - 10 + (tw + 20) * s, yy + 34)], fill=RED, width=7)
                yy += 84
            put(img, lay)
        y = kana(img, self.k.get(wrong, ""), y, q, 28)
        a = self.ev(sc, "x0", 1.4)
        r = back((lt - a + 0.1) / 0.45)
        text(img, (W / 2, y + 30), "▼", 44, YEL, "mt", min(1, max(0, r)))
        mark(img, W / 2, y + 140, True, r)
        y2 = rich(img, grammar_segs(right, self.n["title"]), y + 200, 72, min(1, max(0, r)), ease((lt - a) / 0.5), CHALK, OK_GREEN, 900)
        y2 = kana(img, self.k.get(right, ""), y2, min(1, max(0, r)), 30)
        mm(img, jp_terms(note), y2 + 30, ease((lt - a - 0.6) / 0.5), 42, CHALK)

    def s_quiz(self, img, sc, lt, p):
        heading(img, "⑦ စမ်းဖြေကြည့်", lt)
        qz = self.n["quiz"][0]
        c0 = sc["count"] or 99
        rev = ease((lt - c0 - 3.0) / 0.4)
        ans = qz["choices"][qz["answer"] - 1]
        if rev <= 0:
            segs = [(x, False) for x in re.split(r"([（(]\s*[）)])", qz["q"])]
            segs = [(("（　？　）" if re.match(r"[（(]\s*[）)]", s) else s), s.startswith(("（", "("))) for s, _ in segs if s]
        else:
            segs = grammar_segs(quiz_sentence(qz["q"], ans), self.n["title"])
        y = rich(img, segs, 440, 54, ease(lt / 0.4), rev if rev > 0 else 1.0, CHALK, YEL if rev <= 0 else OK_GREEN, 900)
        y = kana(img, self.k.get(quiz_sentence(qz["q"], ans) if rev > 0 else qz["q"], ""), y, 1.0, 28)
        # 4 choices (2 x 2)
        cw, ch = 400, 104
        for i, c in enumerate(qz["choices"][:4]):
            cx = W / 2 - cw - 15 + (i % 2) * (cw + 30)
            cy = y + 50 + (i // 2) * (ch + 26)
            qq = back((lt - self.ev(sc, "q0") - 0.1 * i) / 0.4)
            if qq <= 0:
                continue
            good = i == qz["answer"] - 1
            fade = 1 - 0.65 * rev if not good else 1
            lay, d = layer()
            fill = (255, 255, 255, 235) if not (good and rev > 0) else OK_GREEN + (255,)
            d.rounded_rectangle([cx, cy, cx + cw, cy + ch], 26, fill=fill)
            d.text((cx + 46, cy + ch / 2), "%d" % (i + 1), font=RS.jfont(34), fill=(160, 160, 170), anchor="mm")
            d.text((cx + cw / 2 + 20, cy + ch / 2), c, font=RS.jfont(46), fill=RS.INK, anchor="mm")
            put(img, lay, min(1, qq * 1.5) * fade)
            if good and rev > 0:
                mark(img, cx + cw - 10, cy + 10, True, back((lt - c0 - 3.0) / 0.4))
        yb = y + 50 + 2 * (ch + 26) + 20
        # countdown 3-2-1 + 'comment' prompt
        if c0 <= lt < c0 + 3.0:
            k = int(lt - c0)
            f = (lt - c0) - k
            sz = 150 * (1.25 - 0.25 * ease(f / 0.3))
            text(img, (W / 2, yb + 70), str(3 - k), sz, PINK, "mm", 1 - ease((f - 0.7) / 0.3))
            mm(img, "comment မှာ အဖြေ ရေးကြည့်ပါနော်", yb + 150, ease((lt - c0) / 0.3), 34, SOFT)
        elif lt < c0:
            mm(img, "ဘယ်ဟာ ဝင်မလဲ?", yb + 40, ease((lt - self.ev(sc, "q0")) / 0.4), 40, CHALK)
        if rev > 0:
            mm(img, jp_terms(qz.get("why", "")), yb + 30, ease((lt - c0 - 3.4) / 0.5), 34, CHALK, 900)

    def s_answers(self, img, sc, lt, p):
        """Why each choice is right / wrong (from the note's ▼ answers), one row at a time."""
        heading(img, "▼ ဘာလို့ မှန်/မှားလဲ", lt)
        qz = self.n["quiz"][0]
        y = 405
        fnt = RS.jfont(44)
        for i, c in enumerate(qz["each"][:4]):
            a = self.ev(sc, "c%d" % i, 99)
            q = ease((lt - a + 0.15) / 0.35)
            if q <= 0:
                break
            now = i == max(j for j in range(len(qz["each"][:4])) if self.ev(sc, "c%d" % j, 99) - 0.15 <= lt)
            mark(img, 130, y + 35, c["ok"], back((lt - a + 0.15) / 0.35))
            lay, d = layer()
            label = "%d  %s" % (c["n"], c["choice"])
            tw = d.textlength(label, font=fnt)
            fill = (OK_GREEN if c["ok"] else (255, 255, 255)) + ((255,) if now else (150,))
            d.rounded_rectangle([190, y, 190 + tw + 50, y + 70], 22, fill=fill)
            d.text((215, y + 35), label, font=fnt, fill=RS.INK, anchor="lm")
            put(img, lay, q, 20 * (1 - q))
            y = mm(img, jp_terms(c["text"]), y + 82, q * (1.0 if now else 0.6), 36 if now else 28, CHALK if now else SOFT, 880, 20 * (1 - q))
            y += 14

    def s_outro(self, img, sc, lt, p):
        n = self.n
        sp = back(lt / 0.5)
        text(img, (W / 2, 330), "今日の文法", 40, SOFT, "mt", min(1, sp))
        text(img, (W / 2, 470), n["title"], 110 * min(1.1, sp), YEL, "mm", min(1, sp * 1.5))
        y = 580
        for ln in n["meaning"][:2]:
            label, head, _, _ = split_meaning(ln)
            y = mm(img, ("%s. %s" % (NUM_MM.get(label, label), head)) if label else head, y, ease((lt - 0.3) / 0.4), 40, CHALK, 880)
        q = back((lt - self.ev(sc, "o1")) / 0.5)
        if q > 0:
            lay, d = layer()
            d.rounded_rectangle([W / 2 - 300, 860, W / 2 + 300, 980], 60, fill=(222, 98, 150))
            d.text((W / 2, 920), "Follow ♡ Rio", font=RS.jfont(56), fill=(255, 255, 255), anchor="mm")
            put(img, lay, min(1, q * 1.5), 30 * (1 - min(1, q)))
        mm(img, "မနက်ဖြန် နောက်ထပ် grammar တစ်ခု ✨" if False else "မနက်ဖြန် နောက်ထပ် grammar တစ်ခု လာမယ်နော်", 1030,
           ease((lt - self.ev(sc, "o2")) / 0.4), 34, SOFT)

    # ---- output
    def render(self, out):
        n = int(self.T * FPS) + 1
        part = out[:-4] + ".part.mp4"
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", part],
                             stdin=subprocess.PIPE)
        for i in range(n):
            p.stdin.write(self.frame(i / FPS).tobytes())
        p.stdin.close()
        p.wait()
        y = np.zeros(int(self.T * SR) + SR, np.float32)
        for at, a, b in self.audio:
            x = self.voice[int(a * SR):int(b * SR)]
            s0 = int(at * SR)
            y[s0:s0 + len(x)] += x[:len(y) - s0]
        for at, name in self.sfx:
            e = RS.sfx(name) * RS.SFX_GAIN
            s0 = int(max(0, at) * SR)
            y[s0:s0 + len(e)] += e[:len(y) - s0]
        y = (np.clip(y[:int(self.T * SR)], -1, 1) * 32767).astype(np.int16)
        aw = out[:-4] + ".mix.wav"
        with wave.open(aw, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", part, "-i", aw, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-shortest", "-movflags", "+faststart", out], check=True)
        os.remove(part)
        os.remove(aw)
        return self.T


def render(note_path, wav, out):
    n = fill_kana(json.load(open(note_path, encoding="utf-8")))
    bf = wav[:-4] + ".bounds.json"
    b = json.load(open(bf))
    return Video(n, wav, b).render(out)


if __name__ == "__main__":
    print("seconds", round(render(*sys.argv[1:4]), 1))
