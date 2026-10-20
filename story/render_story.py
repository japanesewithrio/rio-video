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


def tail_turns(s):
    """Spoken order of tail.wav: chain intro + tip."""
    return [{"who": "Rio", "jp": "今日のパターンのつながり、チェックしよう！", "kana": "", "type": "tail"},
            {"who": "Yui", "jp": "一個ずつじゃなくて、つなげて覚えるのがコツだよ！", "kana": "", "type": "tail"}]


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


def step_card(p, l, cur):
    """One chain step: pattern chip + meaning, then the story line with the pattern highlighted."""
    width, pad = 980, 40
    layer = Image.new("RGBA", (width, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pat = "〜" + p["p"].lstrip("〜～")
    f = R.font(R.JP_BOLD, 40 if cur else 34)
    tw = d.textlength(pat, font=f)
    d.rounded_rectangle([pad - 6, pad - 6, pad + tw + 22, pad + f.size + 14], 18, fill=(237, 231, 255))
    d.text((pad + 8, pad), pat, font=f, fill=PURPLE)
    R.lblock(d, pad + tw + 40, pad - 2, p.get("mm", ""), R.font(R.MM, 38 if cur else 32, 600), PURPLE, width - tw - 2 * pad - 40)
    y = pad + f.size + 34
    R.HIGHLIGHTS[:] = [p["p"].lstrip("〜～")]
    y = R.lblock_hl(d, pad, y, l["who"] + "： " + l["jp"], R.font(R.JP_BOLD, 50 if cur else 40), R.INK, width - 2 * pad)
    if cur and kana_of(l):
        y = R.lblock_hl(d, pad, y + 2, kana_of(l), R.font(R.JP_MED, 30), R.GREY, width - 2 * pad, hl=False)
    y = R.lblock_hl(d, pad, y + 10, l.get("mm", ""), R.font(R.MM, 40 if cur else 34, 500), R.SUBINK, width - 2 * pad, hl=False)
    if cur and p.get("use"):
        y = R.lblock_hl(d, pad, y + 6, "→ " + p["use"], R.font(R.MM, 36, 500), R.GREY, width - 2 * pad, hl=False)
    R.HIGHLIGHTS[:] = []
    h = y + pad - 14
    c = Image.new("RGBA", (width + 24, h + 24), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle([12, 8, width + 12, h + 8], 30, fill=(255, 255, 255, 255),
                                        outline=PURPLE if cur else R.LINE, width=4 if cur else 3)
    c.alpha_composite(layer.crop((0, 0, width, h)), (12, 8))
    return c


def chain_frame(s, upto, prog):
    """Steps 0..upto of the chain; the newest is big, earlier ones small and faded, connected by arrows."""
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = head(d, "パターンをつなげて話そう！", "", "ဇာတ်လမ်းထဲမှာ pattern တွေ ဒီလို ဆက်သွားတယ်", y=240)
    ls = story_lines(s)
    pats = s["patterns"]
    if upto < 0:
        chain = "  →  ".join("〜" + p["p"].lstrip("〜～") for p in pats)
        R.block(d, y + 200, chain, R.font(R.JP_BOLD, 54), R.INK, maxw=920, gap=26)
    else:
        cards = [step_card(pats[k], ls[pats[k]["line"] - 1], k == upto) for k in range(upto + 1)]
        cut = False
        while len(cards) > 1 and y + 46 + sum(c.height + 60 for c in cards) > H - 110:
            cards.pop(0)
            cut = True
        if cut:
            d.text((W / 2, y - 6), "⋮", font=R.font(R.JP_BOLD, 44), fill=R.GREY, anchor="mt")
            y += 46
        for j, c in enumerate(cards):
            if j:
                d.text((W / 2, y - 2), "↓", font=R.font(R.JP_BOLD, 46), fill=PURPLE, anchor="mt")
                y += 56
            y = R.paste_card(img, c, y, 1.0 if j == len(cards) - 1 else 0.6) - 4
    R.light_progress(d, prog)
    return img.convert("RGB")


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
    total_units = n_story + len(pats) + 5

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
    segs.append((chain_frame(s, -1, prog(u)), clip(tail_wav, tb[0], tb[1], "t0", 0.6)))
    for k, p in enumerate(pats):
        u += 1
        i = story_idx[p["line"] - 1]
        segs.append((chain_frame(s, k, prog(u)), clip(wav, mb[i], mb[i + 1], f"ch{k}", 2.4)))
    u += 1
    segs.append((tip_frame(s, prog(u)), clip(tail_wav, tb[1], tT, "tip", 2.5)))
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
