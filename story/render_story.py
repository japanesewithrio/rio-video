"""Learn with Rio - "Story Cards" video (format C).
A short funny story between Rio and Yui told as scenes of chat cards, then 今日のリアル表現 cards.

usage: python story/render_story.py story.json main.wav tail.wav out.mp4
  story.json : see story/sample.json
  main.wav   : hook + all story lines + closing + 2 outro lines (one TTS call)
  tail.wav   : 今日のリアル表現、チェックしよう！ + one line per expression
  optional main.times.json / tail.times.json next to the wavs (Gemini timestamps, soft guide)
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import render as R  # noqa: E402  (render.py in the repo root, gunzipped by the workflow)
from PIL import Image, ImageDraw  # noqa: E402

W, H = R.W, R.H
PURPLE = (150, 120, 230)
OUTRO = [("Rio", "日本語もっと上手になりたいなら、Rioをフォローしてね！", "にほんごもっとじょうずになりたいなら、Rioをフォローしてね！",
          "ဂျပန်စကား ပိုတော်ချင်ရင် Rio ကို Follow လုပ်ထားနော်!"),
         ("Yui", "バイバーイ！", "", "Bye bye!")]
CIRCLED = "①②③④⑤⑥"


def outro_turns():
    return [{"who": w, "jp": j, "kana": k, "mm": m, "type": "outro"} for w, j, k, m in OUTRO]


def main_turns(s):
    """Spoken order of main.wav: hook, story lines, closing, outro."""
    t = [dict(s["hook"], who="Rio", type="hook")]
    for si, sc in enumerate(s["scenes"]):
        for li, l in enumerate(sc["lines"]):
            t.append(dict(l, type="chat", scene=si, idx=li))
    t.append(dict(s["closing"], who="Rio", type="closing"))
    return t + outro_turns()


STEP = ["まず", "次は", "それから", "あと", "そして", "最後に"]


def tail_turns(s):
    """Spoken order of tail.wav: intro, one line per pattern, chain call, tip."""
    pats = s["patterns"]
    steps = STEP[:len(pats) - 1] + ["最後に"]
    t = [{"who": "Rio", "jp": "今日のパターン、チェックしよう！", "kana": "", "type": "tail"}]
    for k, p in enumerate(pats):
        t.append({"who": "Rio" if k % 2 == 0 else "Yui", "jp": "%s、%s！" % (steps[k], p["p"].rstrip("！!")), "kana": "", "type": "tail"})
    t.append({"who": "Rio", "jp": "じゃあ、つなげて言ってみよう！", "kana": "", "type": "tail"})
    t.append({"who": "Yui", "jp": "一個ずつじゃなくて、つなげて覚えるのがコツだよ！", "kana": "", "type": "tail"})
    return t


def tail_script(s):
    return [t["who"] + ": " + t["jp"] for t in tail_turns(s)]


def story_lines(s):
    return [l for sc in s["scenes"] for l in sc["lines"]]


def main_script(s):
    return [t["who"] + ": " + t["jp"] for t in main_turns(s)]


# ---------------------------------------------------------------- frames
def kana_of(t):
    k = (t.get("kana") or "").strip()
    return "" if not k or k == t.get("jp") or k == "-" else k


def line_card(t):
    return R.box_card([("jp", t["jp"]), ("kana", kana_of(t)), ("mm", t.get("mm", ""))],
                      label=t["who"], label_col=R.SPK.get(t["who"], (110, 90, 160)))


def head(d, jp, kana, mm, y=250):
    y = R.lblock(d, 60, y, jp, R.font(R.JP_BOLD, 64), R.INK, 960)
    if kana and kana != jp:
        y = R.lblock(d, 62, y - 4, kana, R.font(R.JP_MED, 30), R.GREY, 960)
    if mm:
        y = R.lblock(d, 62, y + 8, mm, R.font(R.MM, 40, 600), PURPLE, 960)
    return y + 24


def scene_frame(sc, upto, prog):
    """Scene heading + its cards up to line `upto` (cards stay, newest one at full strength)."""
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = head(d, sc["head"], sc.get("head_kana", ""), sc.get("head_mm", ""))
    cards = [line_card(l) for l in sc["lines"][:upto + 1]]
    while len(cards) > 1 and y + sum(c.height + 18 for c in cards) > H - 110:
        cards.pop(0)
    for c in cards:
        y = R.paste_card(img, c, y)
    R.light_progress(d, prog)
    return img.convert("RGB")


def title_frame(s, prog):
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = R.block(d, 600, s["title"], R.font(R.JP_BOLD, 88), R.INK, maxw=940, gap=24)
    if s.get("title_kana"):
        y = R.block(d, y + 6, s["title_kana"], R.font(R.JP_MED, 36), R.GREY, maxw=940)
    if s.get("title_mm"):
        y = R.block(d, y + 40, s["title_mm"], R.font(R.MM, 48, 600), PURPLE, maxw=940, gap=26)
    R.block(d, 1500, "Rio  ×  Yui", R.font(R.JP_BOLD, 44), R.SUBINK, maxw=900)
    R.light_progress(d, prog)
    return img.convert("RGB")


def chain_intro(s, prog):
    img = R.light_base()
    d = ImageDraw.Draw(img)
    d.text((W / 2, 600), "パターンを", font=R.font(R.JP_BOLD, 92), fill=R.INK, anchor="mt")
    d.text((W / 2, 725), "つなげて話そう！", font=R.font(R.JP_BOLD, 92), fill=R.INK, anchor="mt")
    R.block(d, 880, "ဇာတ်လမ်းထဲမှာ Rio နဲ့ Yui ဆက်တိုက်သုံးသွားတဲ့ pattern %d ခု ↓" % len(s["patterns"]),
            R.font(R.MM, 46, 600), PURPLE, maxw=900, gap=26)
    R.light_progress(d, prog)
    return img.convert("RGB")


def pattern_frame(s, k, prog):
    """Pattern k: big pattern card + the story line where it was used (highlighted)."""
    p = s["patterns"][k]
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = head(d, "今日のパターン " + CIRCLED[k], "きょうのパターン", "ဒီနေ့ ချိတ်ဆက်သုံးတဲ့ pattern")
    R.HIGHLIGHTS[:] = []
    c = R.box_card([("jp_huge", "〜" + p["p"].lstrip("〜～")), ("mm", p.get("mm", "")),
                    ("mm", "→ " + p["use"] if p.get("use") else "")])
    y = R.paste_card(img, c, y)
    y = R.lblock(d, 80, y + 6, "ဇာတ်လမ်းထဲမှာ ဒီလိုသုံးခဲ့တယ် ↓", R.font(R.MM, 36, 600), R.GREY, 900) + 4
    R.HIGHLIGHTS[:] = [p["p"].lstrip("〜～")]
    l = story_lines(s)[p["line"] - 1]
    R.paste_card(img, line_card(l), y)
    R.HIGHLIGHTS[:] = []
    R.light_progress(d, prog)
    return img.convert("RGB")


def chain_frame(s, upto, prog):
    R.HIGHLIGHTS[:] = [p["p"].lstrip("〜～") for p in s["patterns"]]
    ls = story_lines(s)
    lines = [(ls[n - 1]["jp"], ls[n - 1].get("mm", "")) for n in s["chain"]]
    img = R.chain_frame(lines, upto, prog) if upto >= 0 else None
    if img is None:
        im = R.light_base()
        d = ImageDraw.Draw(im)
        y = R.light_header(d, "つなげて言ってみよう", y=260)
        R.block(d, y + 120, "ဇာတ်လမ်းထဲက pattern တွေ တစ်ခုနဲ့တစ်ခု ဘယ်လို ဆက်သွားလဲ ကြည့်ရအောင် ↓",
                R.font(R.MM, 46, 600), R.SUBINK, maxw=900, gap=26)
        R.light_progress(d, prog)
        img = im.convert("RGB")
    R.HIGHLIGHTS[:] = []
    return img


def tip_frame(s, prog):
    img = R.light_base()
    d = ImageDraw.Draw(img)
    d.text((W / 2, 560), "このチェーンで", font=R.font(R.JP_BOLD, 84), fill=PURPLE, anchor="mt")
    d.text((W / 2, 675), "話してみよう！", font=R.font(R.JP_BOLD, 84), fill=PURPLE, anchor="mt")
    chain = "  →  ".join("〜" + p["p"].lstrip("〜～") for p in s["patterns"])
    y = R.block(d, 830, chain, R.font(R.JP_BOLD, 50), R.INK, maxw=920, gap=22)
    R.block(d, y + 50, s.get("tip") or "ဒီ pattern တွေကို တစ်ခုချင်း မကျက်ဘဲ chain လိုက် ဆက်ပြောကြည့်ပါ။ Comment မှာ ရေးပြကြနော်!",
            R.font(R.MM, 46, 600), R.SUBINK, maxw=900, gap=28)
    R.light_progress(d, prog)
    return img.convert("RGB")


def closing_frame(t, prog):
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = head(d, "最後に", "さいごに", "နောက်ဆုံးအနေနဲ့")
    R.paste_card(img, line_card(t), y)
    R.light_progress(d, prog)
    return img.convert("RGB")


def outro_frame(t, prog):
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = 700
    d.text((W / 2, y), "Follow", font=R.font(R.JP_BOLD, 60), fill=PURPLE, anchor="mt")
    d.text((W / 2, y + 100), "Learn with Rio ♡", font=R.font(R.JP_BOLD, 84), fill=R.INK, anchor="mt")
    yy = R.block(d, y + 260, OUTRO[0][1], R.font(R.JP_BOLD, 46), R.SUBINK, maxw=900)
    R.block(d, yy + 30, OUTRO[0][3], R.font(R.MM, 40, 500), R.GREY, maxw=900, gap=24)
    R.light_progress(d, prog)
    return img.convert("RGB")


# ---------------------------------------------------------------- build
def bounds(wav, turns):
    """Line boundaries [0, b1, ..., T]. Uses {wav}.bounds.json (exact, written by story.py) when present."""
    bf = wav[:-4] + ".bounds.json"
    if os.path.exists(bf):
        b = json.load(open(bf))
        if len(b) == len(turns) + 1:
            return b, b[-1]
        print("bounds file has wrong length", len(b), len(turns) + 1)
    pts, T = R.split_points(wav, turns)
    return [0.0] + pts + [T], T


def render(story_path, wav, tail_wav, out_path):
    s = json.load(open(story_path, encoding="utf-8"))
    tmp = tempfile.mkdtemp()
    mt, tt = main_turns(s), tail_turns(s)
    mb, mT = bounds(wav, mt)
    tb, tT = bounds(tail_wav, tt)
    pats = s["patterns"]
    # yellow highlight of the patterns inside the story cards
    hl = [p["p"].lstrip("〜～") for p in pats]
    story_idx = [i for i, t in enumerate(mt) if t["type"] == "chat"]  # story line n (1-based) -> index in mt

    def clip(src, a, b, name, pad=0.0):
        o = os.path.join(tmp, name + ".wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src,
                        "-ar", "24000", "-ac", "1", "-af", f"apad=pad_dur={pad}", o], check=True)
        return o

    segs = []
    n_story = sum(len(sc["lines"]) for sc in s["scenes"])
    total_units = n_story + 2 + len(pats) + len(s["chain"]) + 4

    def prog(u):
        return min(1.0, u / total_units)

    u = 0
    R.HIGHLIGHTS[:] = []
    segs.append((title_frame(s, prog(u)), clip(wav, mb[0], mb[1], "hook", 0.6)))
    for i, t in enumerate(mt):
        if t["type"] != "chat":
            continue
        u += 1
        sc = s["scenes"][t["scene"]]
        R.HIGHLIGHTS[:] = hl
        last_in_scene = t["idx"] == len(sc["lines"]) - 1
        segs.append((scene_frame(sc, t["idx"], prog(u)), clip(wav, mb[i], mb[i + 1], f"m{i}", 0.8 if last_in_scene else 0.35)))
    R.HIGHLIGHTS[:] = []
    u += 1
    segs.append((chain_intro(s, prog(u)), clip(tail_wav, tb[0], tb[1], "t0", 0.4)))
    for k, p in enumerate(pats):
        u += 1
        fr = pattern_frame(s, k, prog(u))
        i = story_idx[p["line"] - 1]
        segs.append((fr, clip(tail_wav, tb[k + 1], tb[k + 2], f"t{k + 1}", 0.5)))
        segs.append((fr, clip(wav, mb[i], mb[i + 1], f"pe{k}", 2.2)))
    nt = len(pats) + 1
    u += 1
    segs.append((chain_frame(s, -1, prog(u)), clip(tail_wav, tb[nt], tb[nt + 1], "tc", 0.3)))
    for k, n in enumerate(s["chain"]):
        u += 1
        i = story_idx[n - 1]
        segs.append((chain_frame(s, k, prog(u)), clip(wav, mb[i], mb[i + 1], f"ch{k}", 1.0)))
    u += 1
    segs.append((tip_frame(s, prog(u)), clip(tail_wav, tb[nt + 1], tT, "tip", 3.0)))
    ci = [i for i, t in enumerate(mt) if t["type"] == "closing"][0]
    u += 1
    segs.append((closing_frame(mt[ci], prog(u)), clip(wav, mb[ci], mb[ci + 1], "close", 0.4)))
    segs.append((outro_frame(mt[ci + 1], 1.0), clip(wav, mb[ci + 1], mT, "outro", 1.5)))

    alst, vlst = os.path.join(tmp, "a.txt"), os.path.join(tmp, "v.txt")
    with open(alst, "w") as fa, open(vlst, "w") as fv:
        for i, (im, af) in enumerate(segs):
            p = os.path.join(tmp, f"f{i:03d}.png")
            im.save(p)
            fv.write(f"file '{p}'\nduration {R.duration(af):.3f}\n")
            fa.write(f"file '{af}'\n")
        fv.write(f"file '{p}'\n")
    aud = os.path.join(tmp, "all.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", alst, "-c", "copy", aud], check=True)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", vlst, "-i", aud,
                    "-map", "0:v", "-map", "1:a", "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path], check=True)
    print("rendered story", out_path, len(segs), "segments", round(R.duration(aud), 1), "s")
    return R.duration(aud)


if __name__ == "__main__":
    render(*sys.argv[1:5])
