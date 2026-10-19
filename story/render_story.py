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
    t = [{"who": "Rio", "jp": "今日のリアル表現、チェックしよう！", "kana": "", "type": "tail"}]
    for k, e in enumerate(s["expressions"]):
        t.append({"who": "Rio" if k % 2 == 0 else "Yui", "jp": e["jp"], "kana": e.get("kana", ""), "type": "tail"})
    return t


def tail_script(s):
    out = []
    for t in tail_turns(s):
        j = t["jp"]
        if not j.endswith(("！", "？", "。", "!", "?")):
            j += "？" if j.endswith(("か", "の", "っけ")) else "！"
        out.append(t["who"] + ": " + j)
    return out


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


def expr_card(e, num):
    return R.box_card([("jp_huge", e["jp"]), ("kana", e.get("kana") if e.get("kana") != e["jp"] else ""),
                       ("mm", e.get("mm", "")), ("mm", "→ " + e["use"] if e.get("use") else "")], label=None)


def expr_frame(exprs, page, show, prog):
    """Page `page` (0-based) of 今日のリアル表現, 2 expressions per page, `show` = how many are visible."""
    img = R.light_base()
    d = ImageDraw.Draw(img)
    y = head(d, "今日のリアル表現 " + CIRCLED[page], "きょうのリアルひょうげん", "ဒီနေ့ရဲ့ တကယ်သုံးတဲ့ စကားများ")
    R.HIGHLIGHTS[:] = []
    for e in exprs[page * 2: page * 2 + show]:
        y = R.paste_card(img, expr_card(e, 0), y)
    R.light_progress(d, prog)
    return img.convert("RGB")


def expr_intro(prog):
    img = R.light_base()
    d = ImageDraw.Draw(img)
    d.text((W / 2, 700), "今日のリアル表現", font=R.font(R.JP_BOLD, 92), fill=PURPLE, anchor="mt")
    d.text((W / 2, 830), "きょうのリアルひょうげん", font=R.font(R.JP_MED, 38), fill=R.GREY, anchor="mt")
    R.block(d, 930, "ဇာတ်လမ်းထဲက ဂျပန်လူငယ်တွေ တကယ်ပြောတဲ့ စကားတွေ ↓", R.font(R.MM, 46, 600), R.SUBINK, maxw=900, gap=26)
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
def render(story_path, wav, tail_wav, out_path):
    s = json.load(open(story_path, encoding="utf-8"))
    tmp = tempfile.mkdtemp()
    mt, tt = main_turns(s), tail_turns(s)
    mb, mT = R.split_points(wav, mt)
    mb = [0.0] + mb + [mT]
    tb, tT = R.split_points(tail_wav, tt)
    tb = [0.0] + tb + [tT]
    exprs = s["expressions"]
    # yellow highlight of the expressions inside the story cards
    hl = [e["jp"].strip("〜～") for e in exprs]

    def clip(src, a, b, name, pad=0.0):
        o = os.path.join(tmp, name + ".wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src,
                        "-ar", "24000", "-ac", "1", "-af", f"apad=pad_dur={pad}", o], check=True)
        return o

    segs = []
    n_story = sum(len(sc["lines"]) for sc in s["scenes"])
    total_units = n_story + 2 + len(exprs) + 3

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
    segs.append((expr_intro(prog(u)), clip(tail_wav, tb[0], tb[1], "t0", 0.3)))
    for k in range(len(exprs)):
        u += 1
        page, show = k // 2, k % 2 + 1
        segs.append((expr_frame(exprs, page, show, prog(u)), clip(tail_wav, tb[k + 1], tb[k + 2], f"t{k + 1}", 2.6)))
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
