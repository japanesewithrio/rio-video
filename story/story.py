"""Learn with Rio - "Story Cards" video (format C), runs on GitHub Actions.
Gemini writes a short funny Rio & Yui story (JSON) -> review -> validate -> TTS (story + expressions)
-> timestamps -> render -> commit -> post. DRY=1 sends the result to the owner's Telegram DM only."""
import datetime as dt, json, os, random, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "daily"))
sys.path.insert(0, HERE)
import daily as D  # noqa: E402  (gemini, tts, timestamps, telegram, zernio, git helpers)
import render_story as RS  # noqa: E402

DRY = os.environ.get("DRY", "") == "1"
STATE = os.path.join(HERE, "state.json")
MYA = re.compile("[က-႟]")
KANJI = re.compile("[一-鿿々]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")

THEMES = [
    "lending something to a friend who never gives it back", "a part-time job (baito) mistake", "a cooking disaster at home",
    "oversleeping on an important day", "a misunderstanding in a LINE message", "a first date plan that goes wrong",
    "a diet that lasts one day", "getting lost in a huge train station", "a surprise birthday plan that almost gets found out",
    "buying something online that looks different in real life", "a haircut that went wrong", "a pet that does something funny",
    "losing a phone and finding it in a strange place", "a bet between friends", "a convenience store late-night snack plan",
    "a karaoke night", "trying to wake up early to study", "a roommate eating the other's pudding", "a typhoon day at home",
    "a gym membership nobody uses", "pretending to understand a difficult word", "a gift that the other person already has",
    "forgetting a friend's name", "a summer festival (natsu matsuri) plan", "a part-time job interview", "a delivery that arrives at the worst time",
]

GEN = """You write scripts for "Learn with Rio ♡", a channel that teaches REAL casual spoken Japanese to Burmese (Myanmar) people living in Japan.
Format "Story Cards": one short, FUNNY everyday story between two close friends, told in 6 scenes like a mini comic. Inside the story, the friends naturally CHAIN together casual conversation-connecting patterns; after the story the patterns and the chain are explained, so learners learn to connect patterns when they speak instead of memorising them one by one.
Characters: Rio (Japanese young man, 20, cool and confident but easily flustered, often the victim of the joke) and Yui (Japanese young woman, 20, bright, cheerful, a bit airheaded and teasing). They talk in natural casual Japanese like real young people in Tokyo.

Today's story idea (use it freely as inspiration, change details to make it funnier): @@THEME@@
Do NOT reuse any of these past story titles or their plots: @@AVOID@@

Story rules:
- 6 scenes (5 to 7 allowed). Each scene has a short Japanese heading like a comic panel title (ある日 / 次の日 / そして、一週間後 / Rio、固まる / Yui、思い出す / 最後のオチ ...), max 12 characters, plus its hiragana reading and a short Burmese translation.
- Every scene has 2 or 3 lines; 15 to 18 lines in total. Inside a scene Rio and Yui alternate (never the same speaker twice in a row).
- A clear setup, a build-up with a twist, and a really funny punchline in the last scene (the punchline must make a Burmese viewer laugh).
- Each line is short and natural (max 26 Japanese characters), the way young Japanese really speak: contractions, ちゃう, じゃん, って, でしょ, マジ, やばい, 〜の？, etc. Never textbook style.
- Never write 笑, w, emojis, the 〜 symbol, stage directions or narration inside lines; laughter is written as あはは.
- hook: one line by Rio spoken TO THE VIEWER that teases the story, e.g. 友達に傘を貸したら、大変なことになった話！
- closing: one line by Rio TO THE VIEWER after the story, a funny lesson from the story, e.g. みんなも、借りたものはすぐ返そうね！
- patterns: exactly 6 CONVERSATION-CONNECTING casual patterns used in the story, chosen from this pool (or similar): ってば, ってこと？, っていうか, じゃなくて, って感じ, じゃん, ばいいじゃん, たら？, わけない, でしょ？, っけ？, ちゃう/ちゃった, なきゃ, とく, っぽい, のに, って（quoting）, とか言って, かも, んだけど, し（reasons）, よね. Never use weak items like とか, なんだ, てる. Each pattern: p = the pattern exactly as its characters literally appear inside the story line (no 〜 symbol, 2 to 6 characters), mm = short Burmese gloss written as 「…」, use = when it is used (Burmese, max 45 characters), line = the number of the story line where it appears (counting all story lines from 1, NOT counting hook and closing). List them in story order, all different, and no pattern used more than 3 times in the story.
- chain: 6 or 7 story line numbers, in increasing order, that show the patterns flowing from one to the next (question → denial → clarification → feeling → advice …). Every chain line contains at least one of the patterns. Make at least 5 of them consecutive or nearly consecutive lines, so the chain sounds like one natural flow.
- tip: one short Burmese sentence (max 80 characters) telling learners to say this chain as one flow, so the patterns come out naturally when they speak.
- Every kana field is the full reading in hiragana (katakana words may stay katakana); it must match the Japanese exactly.
- Burmese must be natural, short, spoken-style, correctly spelled Unicode Burmese, never with double quotes. For each expression: mm = short Burmese meaning, use = when you use it (max 45 characters, Burmese, may quote the pattern like じゃん = 「…ပဲလေ」).
- title: Japanese story title in the style 友達に傘を貸した日の話 (max 16 characters); title_mm its Burmese.
- caption: Burmese, max 180 characters, 1-2 emojis, teasing the story and naming the patterns chained today.

Output ONLY JSON with exactly this structure:
{"title": "", "title_kana": "", "title_mm": "",
 "hook": {"jp": "", "kana": "", "mm": ""},
 "scenes": [{"head": "", "head_kana": "", "head_mm": "", "lines": [{"who": "Rio or Yui", "jp": "", "kana": "", "mm": ""}]}],
 "patterns": [{"p": "", "mm": "", "use": "", "line": 1}],
 "chain": [1, 2, 3, 4, 5, 6],
 "tip": "",
 "closing": {"jp": "", "kana": "", "mm": ""},
 "caption": ""}"""

REV = """You are a strict editor, a native speaker of both Japanese and Burmese (Myanmar). Below is a "Story Cards" script (JSON) for a channel teaching real casual spoken Japanese to Burmese learners. Check EVERYTHING and fix every problem:
1. Every Japanese line is 100% natural casual Japanese that young Japanese people really say; the story is logical from start to end and the last scene is really funny.
2. Inside each scene Rio and Yui alternate. 15 to 18 lines in total, 2 or 3 per scene, each line max 26 characters.
3. No 笑, w, emojis, 〜 symbol or stage directions in Japanese lines.
4. Every kana reading matches its Japanese exactly.
5. All Burmese is correct, natural, spoken-style Unicode Burmese with no double quotes, and matches the Japanese meaning.
6. patterns: exactly 6 conversation-connecting casual patterns, each p literally appears (exact characters) inside story line number `line` (story lines counted from 1, hook and closing not counted), all different, no pattern used more than 3 times. chain: 6 or 7 increasing story line numbers, each containing a pattern, flowing naturally.
@@ERRORS@@
Output ONLY the full corrected JSON with exactly the same structure.

JSON:
@@JSON@@"""


def ask_json(prompt):
    r = D.gemini(D.TEXT_CHAIN, {"contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}})
    t = D.text_of(r).strip()
    t = re.sub(r"^```\w*\n|\n```$", "", t)
    return json.loads(t)


def validate(s):
    err = []
    try:
        for k in ("title", "title_mm", "hook", "scenes", "patterns", "chain", "closing", "caption"):
            if not s.get(k):
                err.append("field %s is missing or empty" % k)
        if err:
            return err
        sc = s["scenes"]
        if not 5 <= len(sc) <= 7:
            err.append("there must be 5 to 7 scenes, there are %d" % len(sc))
        lines = [l for x in sc for l in x.get("lines", [])]
        if not 14 <= len(lines) <= 19:
            err.append("there must be 15 to 18 lines in total, there are %d" % len(lines))
        for i, x in enumerate(sc):
            ls = x.get("lines", [])
            if not 2 <= len(ls) <= 3:
                err.append("scene %d must have 2 or 3 lines, it has %d" % (i + 1, len(ls)))
            for a, b in zip(ls, ls[1:]):
                if a.get("who") == b.get("who"):
                    err.append("scene %d: two lines in a row by %s" % (i + 1, a.get("who")))
            if not x.get("head") or not MYA.search(x.get("head_mm", "")):
                err.append("scene %d needs head and a Burmese head_mm" % (i + 1))
        for l in lines + [s["hook"], s["closing"]]:
            jp = l.get("jp", "")
            if l in lines and l.get("who") not in ("Rio", "Yui"):
                err.append("who must be Rio or Yui: %s" % jp)
            if EMOJI.search(jp) or "笑" in jp or "〜" in jp:
                err.append("no emoji, 笑 or 〜 inside: %s" % jp)
            if len(jp) > 28:
                err.append("line too long (max 26 characters): %s" % jp)
            if KANJI.search(jp) and (not l.get("kana") or KANJI.search(l.get("kana", ""))):
                err.append("kana must be the full kana reading (no kanji) of: %s" % jp)
            if not MYA.search(l.get("mm", "")):
                err.append("Burmese translation missing for: %s" % jp)
        pats = s.get("patterns") or []
        if not 5 <= len(pats) <= 6:
            err.append("there must be exactly 6 patterns, there are %d" % len(pats))
        story = [l.get("jp", "") for l in lines]
        seen = set()
        for p in pats:
            j = str(p.get("p", "")).strip().lstrip("〜～")
            p["p"] = j
            if j in ("とか", "なんだ", "てる"):
                err.append("pattern %s is too weak, use a conversation-connecting pattern" % j)
            n = int(p.get("line") or 0)
            if not (1 <= n <= len(story) and j and j in story[n - 1]):
                hit = [i + 1 for i, t in enumerate(story) if j and j in t]
                if hit:
                    p["line"] = hit[0]  # wrong number but the pattern is in the story: fix it ourselves
                else:
                    err.append("pattern %s does not literally appear in any story line" % j)
            if j in seen:
                err.append("pattern %s is repeated" % j)
            seen.add(j)
            if not MYA.search(p.get("mm", "")) or not MYA.search(p.get("use", "")):
                err.append("pattern %s needs Burmese mm and use" % j)
        ch = [int(x) for x in s.get("chain") or []]
        s["chain"] = ch
        if not 5 <= len(ch) <= 7 or ch != sorted(set(ch)) or not all(1 <= n <= len(story) for n in ch):
            err.append("chain must be 6 or 7 increasing story line numbers between 1 and %d" % len(story))
        else:
            for n in ch:
                if not any(p["p"] and p["p"] in story[n - 1] for p in pats):
                    err.append("chain line %d (%s) contains none of the patterns" % (n, story[n - 1]))
        if not MYA.search(s.get("tip", "")):
            err.append("tip must be written in Burmese")
        if not MYA.search(s["caption"]):
            err.append("caption must be written in Burmese")
    except Exception as e:  # malformed structure
        err.append("JSON structure is wrong: %s" % e)
    return err


def tidy(s):
    """Burmese text uses ASCII ! and ? (full-width marks look odd next to Burmese script)."""
    def fix(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("mm", "use", "head_mm", "title_mm", "caption", "tip") and isinstance(v, str):
                    o[k] = v.replace("！", "!").replace("？", "?").replace("‘", "「").replace("’", "」")
                else:
                    fix(v)
        elif isinstance(o, list):
            for v in o:
                fix(v)
    fix(s)
    return s


def make_story(theme, avoid):
    prompt = GEN.replace("@@THEME@@", theme).replace("@@AVOID@@", "、".join(avoid[-40:]) or "(none)")
    best, best_err = None, None
    for attempt in range(2):
        s = ask_json(prompt)
        try:
            s = ask_json(REV.replace("@@ERRORS@@", "").replace("@@JSON@@", json.dumps(s, ensure_ascii=False)))
        except Exception as e:
            D.log("review failed", e)
        for fix in range(3):
            err = validate(s)
            D.log("attempt", attempt, "fix", fix, "errors", err)
            if not err:
                return s
            if best_err is None or len(err) < len(best_err):
                best, best_err = s, err
            extra = "7. IMPORTANT - an automatic check found these problems, fix ALL of them:\n- " + "\n- ".join(err)
            try:
                s = ask_json(REV.replace("@@ERRORS@@", extra).replace("@@JSON@@", json.dumps(s, ensure_ascii=False)))
            except Exception as e:
                D.log("fix failed", e)
    hard = [e for e in best_err if not e.startswith(("line too long", "pattern", "chain line", "tip"))]
    if hard:
        raise RuntimeError("story failed validation: %s" % best_err)
    # keep only patterns / chain lines that really are in the story rather than failing
    story = [l["jp"] for x in best["scenes"] for l in x["lines"]]
    best["patterns"] = [p for p in best["patterns"] if p["p"] and p["p"] in story[p["line"] - 1]][:6]
    best["chain"] = [n for n in best["chain"] if any(p["p"] in story[n - 1] for p in best["patterns"])]
    if len(best["patterns"]) < 4 or len(best["chain"]) < 4:
        raise RuntimeError("story failed validation: %s" % best_err)
    D.WARN.extend(best_err)
    return best


P_STORY = ("TTS the following short everyday story as a real, unscripted-sounding conversation between two close Japanese friends around 20. "
           "Rio: a young man, relaxed and cool. Yui: a young woman, bright and friendly. "
           "Speak exactly like real young people casually chatting: natural, low-key everyday tone, normal natural speed. "
           "Do NOT act and do NOT exaggerate emotions; surprise or annoyance stays small and natural, like real life. "
           "Not like voice actors, anime or an announcer. Leave a short clear pause between turns. "
           "The first line is Rio speaking to the viewer; the last three lines are Rio and Yui talking to the viewer.\n")
P_EXPR = ("TTS the following short lines by two close Japanese friends around 20 years old. Rio: a young man, relaxed. Yui: a young woman, "
          "bright and friendly. Rio first invites the viewer to check today's expressions, then they say each casual expression one by one "
          "with the natural intonation it has in real conversation. Relaxed and natural, not acted, not like a teacher. "
          "Normal natural speed, a clear pause between lines.\n")


def transcript(s):
    out = ["🎬 %s" % s["title"], s.get("title_mm", ""), ""]
    for sc in s["scenes"]:
        out.append("【%s】 %s" % (sc["head"], sc.get("head_mm", "")))
        for l in sc["lines"]:
            out.append("%s: %s" % (l["who"], l["jp"]))
            if RS.kana_of(l):
                out.append("   " + l["kana"])
            out.append("   🇲🇲 " + l["mm"])
        out.append("")
    out.append("🔗 今日のパターン")
    for k, p in enumerate(s["patterns"]):
        out.append("%d. 〜%s %s — %s" % (k + 1, p["p"], p["mm"], p["use"]))
    ls = RS.story_lines(s)
    out += ["", "🗣 つなげて言ってみよう"]
    out.append("\n↓\n".join(ls[n - 1]["jp"] for n in s["chain"]))
    out += ["", "💡 " + s.get("tip", "")]
    out += ["", "#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui"]
    return "\n".join(out)[:4000]


def main():
    ms = D.list_models()
    if ms:
        D.TEXT_CHAIN = [m for m in D.TEXT_CHAIN if m in ms] or [D.pick(ms, "none", r"^gemini-[\d.]+-(pro|flash)")]
        D.FAST_CHAIN = [m for m in D.FAST_CHAIN if m in ms] or [D.pick(ms, "none", r"^gemini-[\d.]+-flash")]
        D.TTS_CHAIN = [m for m in D.TTS_CHAIN if m in ms] or [D.pick(ms, "none", r"tts", avoid=())]
    vf = os.path.join(HERE, "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
    D.log("using", D.TEXT_CHAIN, D.FAST_CHAIN, D.TTS_CHAIN, D.VOICES)
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"done": []}
    now = dt.datetime.now(D.JST)
    key = ("ST" if DRY else "S") + now.strftime("%y%m%d%H%M")
    theme = random.choice(THEMES)
    D.log("key", key, "theme", theme)
    s = tidy(make_story(theme, [d["title"] for d in st["done"]]))
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    jpath = os.path.join(ROOT, "text", key + ".json")
    json.dump(s, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    work = os.path.join(ROOT, "work", "story")
    os.makedirs(work, exist_ok=True)
    main_wav, tail_wav = os.path.join(work, "main.wav"), os.path.join(work, "tail.wav")
    ms_, ts_ = RS.main_script(s), RS.tail_script(s)
    D.tts(P_STORY + "\n".join(ms_), main_wav)
    D.tts(P_EXPR + "\n".join(ts_), tail_wav)
    D.timestamps(main_wav, ms_, os.path.join(work, "main.times.json"))
    D.timestamps(tail_wav, ts_, os.path.join(work, "tail.times.json"))
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    vid = os.path.join("videos", key + ".mp4")
    secs = RS.render(jpath, main_wav, tail_wav, os.path.join(ROOT, vid))
    if not DRY:
        st["done"].append({"key": key, "title": s["title"], "date": now.strftime("%Y-%m-%d")})
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.chdir(ROOT)
    D.push("story %s" % key, ["text", "videos", "story/state.json"])

    title, cap = s["title"], s["caption"]
    chat = D.OWNER if DRY else D.CHANNEL
    D.tg("sendVideo", {"chat_id": chat, "caption": ("🎬 %s\n%s" % (title, cap))[:1020], "supports_streaming": "true"}, {"video": open(vid, "rb")})
    D.tg("sendMessage", {"chat_id": chat, "text": transcript(s)})
    ok = {}
    if not DRY:
        import time
        url = D.REPO_RAW + vid
        time.sleep(20)
        tags = "#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui #リアル日本語 #JLPT #fyp"
        ok["tiktok"] = D.zernio({"content": "🎬 %s\n%s\n\n%s" % (title, cap, tags), "mediaItems": [{"type": "video", "url": url}],
                                 "platforms": [{"platform": "tiktok", "accountId": D.TIKTOK_ID}],
                                 "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": True,
                                                    "allow_stitch": True, "content_preview_confirmed": True, "express_consent_given": True},
                                 "publishNow": True})
        ok["youtube"] = D.zernio({"content": "%s\n\n%s\n\n#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui #shorts" % (cap, transcript(s)[:3000]),
                                  "mediaItems": [{"type": "video", "url": url}],
                                  "platforms": [{"platform": "youtube", "accountId": D.YOUTUBE_ID,
                                                 "platformSpecificData": {"title": ("%s｜リアルな日本語 #shorts" % title)[:100],
                                                                          "visibility": "public", "madeForKids": False,
                                                                          "containsSyntheticMedia": True}}],
                                  "publishNow": True})
    summary = "✅ Story video %s %s\n%s (%ds)\nTikTok: %s / YouTube: %s" % (
        "TEST" if DRY else "posted", key, title, secs, ok.get("tiktok", "-"), ok.get("youtube", "-"))
    if D.WARN:
        summary += "\n(small problems: %s)" % "; ".join(D.WARN)[:600]
    if D.OWNER:
        D.tg("sendMessage", {"chat_id": D.OWNER, "text": summary})
    D.log(summary)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ Story video: error\n%s: %s" % (type(e).__name__, str(e)[:500])})
        raise
