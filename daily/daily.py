"""Learn with Rio - daily Format B (Pattern Chain) pipeline, runs on GitHub Actions.
generate lesson (Gemini) -> review -> validate -> TTS -> timestamps -> render -> commit -> post
(Telegram channel, TikTok + YouTube via Zernio). DRY=1 sends everything to the owner's DM only."""
import base64, datetime as dt, json, os, re, subprocess, sys, time, wave
import requests

GKEY = os.environ["GEMINI_API_KEY"]
TG = os.environ.get("TG_TOKEN")
OWNER = os.environ.get("TG_CHAT")
ZKEY = os.environ.get("ZERNIO_API_KEY")
DRY = os.environ.get("DRY", "") == "1"
CHANNEL = "@japanesewithrio"
TIKTOK_ID, YOUTUBE_ID = "6ab3bf2d8d284ffb2134135b", "6ab3bf7c8d284ffb21341619"
REPO_RAW = "https://raw.githubusercontent.com/japanesewithrio/rio-video/main/"
TEXT_MODEL, FAST_MODEL, TTS_MODEL = "gemini-2.5-pro", "gemini-3.6-flash", "gemini-3.1-flash-tts-preview"
API = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
JST = dt.timezone(dt.timedelta(hours=9))
WEAK = ["てる", "とか", "なんだ"]
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


LAST_ERR = [""]


def list_models():
    try:
        r = requests.get("https://generativelanguage.googleapis.com/v1beta/models", params={"key": GKEY, "pageSize": 200}, timeout=60)
        ms = [m["name"].split("/")[-1] for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
        log("models available:", ", ".join(ms))
        return ms
    except Exception as e:
        log("list models failed", e)
        return []


def pick(models, want, pattern, avoid=("tts", "image", "live", "embedding", "audio", "lite")):
    if want in models:
        return want
    cand = [m for m in models if re.search(pattern, m) and not any(a in m for a in avoid)]

    def ver(m):
        n = re.findall(r"gemini-(\d+(?:\.\d+)?)", m)
        return (float(n[0]) if n else 0, "preview" not in m and "exp" not in m)
    cand.sort(key=ver, reverse=True)
    return cand[0] if cand else want


def gemini(model, body, tries=5):
    for i in range(tries):
        try:
            r = requests.post(API % model, params={"key": GKEY}, json=body, timeout=600)
            if r.status_code == 200:
                return r.json()
            LAST_ERR[0] = "%s %s %s" % (model, r.status_code, r.text[:300])
            log("gemini", LAST_ERR[0])
            if r.status_code in (400, 403, 404):
                break
        except Exception as e:
            LAST_ERR[0] = "%s %s" % (model, type(e).__name__)
            log("gemini", LAST_ERR[0])
        time.sleep(20 * (i + 1))
    raise RuntimeError("gemini failed: " + LAST_ERR[0])


def text_of(resp):
    return "".join(p.get("text", "") for p in resp["candidates"][0]["content"]["parts"])


def ask(prompt, model=None):
    return text_of(gemini(model or TEXT_MODEL, {"contents": [{"parts": [{"text": prompt}]}]})).strip()


def sec(raw, a):
    m = re.search(r"===%s===\s*\n(.*?)(?=\n===[A-Z]+===|\Z)" % a, raw, re.S)
    return m.group(1).strip() if m else ""


def clean_file(t):
    t = t.strip()
    t = re.sub(r"^```\w*\n|\n```$", "", t)
    i = t.find("===TITLE===")
    j = t.rfind("===END===")
    if i < 0 or j < 0:
        return t
    t = t[i:j + 9]
    return t.replace("| Rio: ", "| ").replace("| Yui: ", "| ")


def validate(raw):
    err = []
    for s in ["TITLE", "CAPTION", "SCRIPT", "LINES", "HIGHLIGHT", "FLOW", "CHAIN", "TAIL", "TIP", "QUOTE", "LOVENOTE", "TRANSCRIPT"]:
        if not sec(raw, s):
            err.append("section %s is missing or empty" % s)
    if err:
        return err
    script = [l.strip() for l in sec(raw, "SCRIPT").splitlines() if l.strip()]
    lines = [l for l in sec(raw, "LINES").splitlines() if l.strip()]
    if len(script) != len(lines):
        err.append("SCRIPT has %d lines but LINES has %d" % (len(script), len(lines)))
    spk = [l.split(":", 1)[0].strip() for l in script]
    if any(s not in ("Rio", "Yui") for s in spk):
        err.append("every SCRIPT line must start with Rio: or Yui:")
    chat = script[1:-2]
    if not 14 <= len(chat) <= 20:
        err.append("chat must have 16-18 lines, it has %d" % len(chat))
    for a, b in zip(chat, chat[1:]):
        if a.split(":")[0] == b.split(":")[0]:
            err.append("two chat lines in a row by the same speaker: '%s' / '%s'" % (a, b))
    if not script[-2].startswith("Rio: 日本語もっと上手になりたいなら") or not script[-1].startswith("Yui: バイバーイ"):
        err.append("the last two SCRIPT lines must be the fixed outro")
    flow = [l for l in sec(raw, "FLOW").splitlines() if "|" in l]
    if len(flow) != 6:
        err.append("FLOW must have exactly 6 lines, it has %d" % len(flow))
    chat_jp = [c.split(":", 1)[1].strip() for c in chat]
    for l in flow:
        p = l.split("|")[0].strip().lstrip("〜").rstrip("？?")
        if p in WEAK:
            err.append("FLOW pattern 〜%s is too weak, replace it with a conversation-connecting pattern" % p)
        if p and not any(p in c for c in chat_jp):
            err.append("FLOW pattern 〜%s does not appear in the chat" % p)
    chain = [l for l in sec(raw, "CHAIN").splitlines() if "|" in l]
    if len(chain) != 7:
        err.append("CHAIN must have exactly 7 lines, it has %d" % len(chain))
    for l in chain:
        p = [x.strip() for x in l.split("|")]
        n = int(re.sub(r"\D", "", p[0]) or 0)
        if not (1 <= n <= len(chat_jp)) or chat_jp[n - 1] != p[1]:
            want = [i + 1 for i, c in enumerate(chat_jp) if c == p[1]]
            err.append("CHAIN line '%s': N must be %s (number of that chat line, first chat line = 1) and the text must equal the chat line exactly" % (l, want or "?"))
    if len([l for l in sec(raw, "TAIL").splitlines() if l.strip()]) != 9:
        err.append("TAIL must have exactly 9 lines")
    if not re.search("[က-႟]", sec(raw, "CAPTION")):
        err.append("CAPTION must be written in Burmese")
    t = sec(raw, "TITLE")
    if not re.match(r"^〜[^・]+・〜", t):
        err.append("TITLE must be 〜A・〜B with 〜 before both patterns")
    for h in [x.strip() for x in re.split(r"[,、]", sec(raw, "HIGHLIGHT")) if x.strip()]:
        if not any(h in c for c in chat_jp):
            err.append("HIGHLIGHT item %s does not appear in the chat" % h)
    return err


def make_lesson(topic, level):
    gen = open("daily/gen.txt", encoding="utf-8").read().replace("@@TOPIC@@", topic).replace("@@LEVEL@@", level)
    rev = open("daily/rev.txt", encoding="utf-8").read()
    for attempt in range(2):
        raw = clean_file(ask(gen))
        raw2 = clean_file(ask(rev.replace("@@FILE@@", raw)))
        if "===END===" in raw2:
            raw = raw2
        for fix in range(3):
            err = validate(raw)
            log("attempt", attempt, "fix", fix, "errors", err)
            if not err:
                return raw
            prompt = rev.replace("@@FILE@@", raw) + "\n\nIMPORTANT - these problems were found by an automatic check, fix ALL of them:\n- " + "\n- ".join(err)
            out = clean_file(ask(prompt))
            if "===END===" in out:
                raw = out
    raise RuntimeError("lesson failed validation: %s" % err)


VOICES = {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
    {"speaker": "Rio", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Enceladus"}}},
    {"speaker": "Yui", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Leda"}}}]}}
P_MAIN = ("TTS the following conversation between two close Japanese friends around 20 years old, really chatting in a cafe in Tokyo. "
          "Rio: a young man with a smooth, cool and confident voice, relaxed and a little playful. Yui: a young woman with a bright, cute and "
          "youthful voice, expressive, cheerful and teasing. Make it sound like a real recorded conversation between friends, not voice actors "
          "reading a script: natural rhythm, small pauses, soft natural laughs, intonation that goes up and down like real talk. Do not over-act "
          "and do not sound like an announcer. Normal natural speed like real native young people. Leave a short clear pause between turns. "
          "The first line is Rio speaking to the viewer, and the last two lines are a friendly goodbye to the viewer.\n")
P_TAIL = ("TTS the following short lines between two close Japanese friends around 20 years old. Rio: a young man with a smooth, cool and "
          "confident voice. Yui: a young woman with a bright, cute and youthful voice. They are happily pointing out casual expressions to the "
          "viewer, lively and friendly like real friends, not like a teacher or an announcer. Normal natural speed, with a short clear pause between lines.\n")


def tts(text, path):
    r = gemini(TTS_MODEL, {"contents": [{"parts": [{"text": text}]}],
                           "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": VOICES}})
    part = [p for p in r["candidates"][0]["content"]["parts"] if "inlineData" in p][0]["inlineData"]
    pcm = base64.b64decode(part["data"])
    rate = int((re.search(r"rate=(\d+)", part.get("mimeType", "")) or [0, 24000])[1])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    log("tts", path, round(len(pcm) / 2 / rate, 1), "s")


def timestamps(wav, script, out):
    b64 = base64.b64encode(open(wav, "rb").read()).decode()
    prompt = ("This audio is a Japanese conversation between Rio (young man) and Yui (young woman). The script lines, in order and separated by "
              "a slash, are: " + " / ".join(script) + " . Listen carefully and return, for every script line in order, the exact start and end "
              "time in seconds (2 decimals) where it is spoken. Output only JSON: a list of objects {\"line\": number starting at 1, \"start\": seconds, \"end\": seconds}.")
    for model in (FAST_MODEL, TEXT_MODEL):
        try:
            r = gemini(model, {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/wav", "data": b64}}, {"text": prompt}]}],
                               "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}, tries=3)
            arr = json.loads(text_of(r))
            if len(arr) == len(script):
                json.dump(arr, open(out, "w"))
                log("timestamps ok", model)
                return True
            log("timestamps wrong count", len(arr), len(script))
        except Exception as e:
            log("timestamps failed", model, e)
    return False


def tg(method, data, files=None):
    if not TG:
        return None
    r = requests.post("https://api.telegram.org/bot%s/%s" % (TG, method), data=data, files=files, timeout=300)
    ok = r.ok and r.json().get("ok")
    log("telegram", method, "ok" if ok else r.text[:200])
    return ok


def zernio(body):
    if not ZKEY:
        log("zernio: no ZERNIO_API_KEY secret")
        return False
    r = requests.post("https://zernio.com/api/v1/posts", headers={"Authorization": "Bearer " + ZKEY}, json=body, timeout=120)
    log("zernio", body["platforms"][0]["platform"], r.status_code, r.text[:300])
    return r.status_code < 300


def git(*a):
    subprocess.run(["git"] + list(a), check=True)


def push(msg, paths):
    git("config", "user.name", "rio-bot")
    git("config", "user.email", "rio-bot@users.noreply.github.com")
    git("add", "-A", *paths)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode:
        git("commit", "-q", "-m", msg)
    for _ in range(4):
        if subprocess.run(["git", "pull", "-q", "--rebase"]).returncode == 0 and subprocess.run(["git", "push", "-q"]).returncode == 0:
            return
        time.sleep(5)
    raise RuntimeError("git push failed")


def main():
    global TEXT_MODEL, FAST_MODEL, TTS_MODEL
    ms = list_models()
    if ms:
        TEXT_MODEL = pick(ms, TEXT_MODEL, r"^gemini-[\d.]+-pro")
        if TEXT_MODEL not in ms:
            TEXT_MODEL = pick(ms, "none", r"^gemini-[\d.]+-flash")
        FAST_MODEL = pick(ms, FAST_MODEL, r"^gemini-[\d.]+-flash")
        TTS_MODEL = pick(ms, TTS_MODEL, r"tts", avoid=())
    log("using", TEXT_MODEL, FAST_MODEL, TTS_MODEL)
    st = json.load(open("daily/topics.json", encoding="utf-8"))
    todo = [t for t in st["topics"] if t["status"] == "todo"]
    if DRY:
        key = "T" + dt.datetime.now(JST).strftime("%m%d%H%M")
        topic = todo[0] if todo else {"topic": "free choice", "level": "N4"}
    else:
        topic = todo[0] if todo else {"key": "D" + dt.datetime.now(JST).strftime("%y%m%d"), "topic": "free choice: pick 6 useful patterns", "level": "N4"}
        key = topic["key"]
    log("key", key, "topic", topic["topic"])
    raw = make_lesson(topic["topic"], topic.get("level", "N4"))
    os.makedirs("text", exist_ok=True)
    open("text/%s.txt" % key, "w", encoding="utf-8").write(raw)
    script = [l.strip() for l in sec(raw, "SCRIPT").splitlines() if l.strip()]
    work = "work"
    tts(P_MAIN + "\n".join(script), "%s/audio/%s.wav" % (work, key))
    tts(P_TAIL + sec(raw, "TAIL"), "%s/tail/%s.wav" % (work, key))
    timestamps("%s/audio/%s.wav" % (work, key), script, "%s/audio/%s.times.json" % (work, key))
    os.makedirs("videos", exist_ok=True)
    subprocess.run([sys.executable, "render.py", "text/%s.txt" % key, "%s/audio/%s.wav" % (work, key), "videos/%s.mp4" % key], check=True)
    for old in sorted([f for f in os.listdir("videos") if f.endswith(".mp4")], key=lambda f: os.path.getmtime("videos/" + f))[:-10]:
        for f in (old, old[:-4] + "_quote.jpg"):
            if os.path.exists("videos/" + f):
                os.remove("videos/" + f)
    if not DRY:
        for t in st["topics"]:
            if t.get("key") == key:
                t["status"] = "posted"
                t["date"] = dt.datetime.now(JST).strftime("%Y-%m-%d")
        json.dump(st, open("daily/topics.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    push("daily %s" % key, ["text", "videos", "daily/topics.json"])

    title, cap = sec(raw, "TITLE"), sec(raw, "CAPTION")
    chat = OWNER if DRY else CHANNEL
    vid = "videos/%s.mp4" % key
    tg("sendVideo", {"chat_id": chat, "caption": "🎬 %s\n%s" % (title, cap), "supports_streaming": "true"}, {"video": open(vid, "rb")})
    tg("sendAudio", {"chat_id": chat, "caption": "🎧 %s\n%s" % (title, cap)}, {"audio": ("Rio_Yui_%s.wav" % key, open("%s/audio/%s.wav" % (work, key), "rb"))})
    if not tg("sendMessage", {"chat_id": chat, "text": sec(raw, "TRANSCRIPT")[:4000], "parse_mode": "HTML", "disable_web_page_preview": "true"}):
        tg("sendMessage", {"chat_id": chat, "text": re.sub(r"<[^>]+>", "", sec(raw, "TRANSCRIPT"))[:4000]})
    q = "videos/%s_quote.jpg" % key
    if os.path.exists(q):
        tg("sendPhoto", {"chat_id": chat, "caption": ("💌 恋のひとこと\n\n" + sec(raw, "LOVENOTE"))[:1020]}, {"photo": open(q, "rb")})
    ok = {}
    if not DRY:
        url = REPO_RAW + vid
        time.sleep(20)
        ok["tiktok"] = zernio({"content": "🔗 %s\n%s\n\n#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui #リアル日本語 #JLPT #fyp" % (title, cap),
                               "mediaItems": [{"type": "video", "url": url}],
                               "platforms": [{"platform": "tiktok", "accountId": TIKTOK_ID}],
                               "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": True,
                                                  "allow_stitch": True, "content_preview_confirmed": True, "express_consent_given": True},
                               "publishNow": True})
        ok["youtube"] = zernio({"content": "%s\n\n%s\n\n#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui #shorts" % (cap, "\n".join(script)),
                                "mediaItems": [{"type": "video", "url": url}],
                                "platforms": [{"platform": "youtube", "accountId": YOUTUBE_ID,
                                               "platformSpecificData": {"title": ("%s｜パターンをつなげて話そう #shorts" % title)[:100],
                                                                        "visibility": "public", "madeForKids": False,
                                                                        "containsSyntheticMedia": True}}],
                                "publishNow": True})
    summary = "✅ Learn with Rio %s %s\n%s\nTikTok: %s / YouTube: %s" % (
        "TEST" if DRY else "posted", key, title, ok.get("tiktok", "-"), ok.get("youtube", "-"))
    if OWNER and not DRY:
        tg("sendMessage", {"chat_id": OWNER, "text": summary})
    log(summary)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("FAILED", type(e).__name__, e)
        if OWNER and TG:
            tg("sendMessage", {"chat_id": OWNER, "text": "⚠️ Learn with Rio daily video: error\n%s: %s" % (type(e).__name__, str(e)[:500])})
        raise
