"""N3 chat-style video (Ye 11/09) - test run: 'CHAT <no>' in n3/chat_trigger.txt -> video to the owner's Telegram DM only.
Content: n3/chat_enc/NNN.enc + NNN.key (same private-note encryption as n3/notes_enc; written and checked by Claude)."""
import json, os, re, sys, tempfile, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "steps"))
sys.path.insert(0, HERE)
import steps as ST  # noqa: E402  (patches: patient TTS retries, silence squeeze)
import render_chat3 as R  # noqa: E402
import render_chat3 as R3  # noqa: E402
import render_chat4 as R4  # noqa: E402  (Ye 11/11: clean mint design + motion, used when the content has a 'hook')

D, S = ST.D, ST.S
P_MULTI = ("TTS the following lines. Rio: a young Japanese man around 20. Yui: a young Japanese woman around 20. They are close friends "
           "chatting casually. Natural, relaxed, normal speed, very clear. Not like an announcer, not anime, not acting. "
           "Leave a clear pause of about one second between lines.\n")
P_ONE = ("Say the following Japanese lines as Rio, a friendly Japanese young man around 20, talking to learners watching his video: "
         "relaxed, natural, normal speed, very clear. Like a kind senpai, not an announcer. "
         "Leave a clear pause of about one second between lines.\n")


def decrypt(folder, no):
    enc = os.path.join(HERE, folder, "%03d" % no)
    if not os.path.exists(enc + ".enc"):
        return None
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    priv = os.path.join(work, "priv.pem")
    if not os.path.exists(priv):
        subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-in", os.path.join(HERE, "key", "priv.enc"),
                        "-out", priv, "-pass", "env:TG_TOKEN"], check=True)
    k = subprocess.run(["openssl", "pkeyutl", "-decrypt", "-inkey", priv, "-pkeyopt", "rsa_padding_mode:oaep", "-in", enc + ".key"],
                       capture_output=True, check=True).stdout
    data = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-in", enc + ".enc", "-pass", "env:K"],
                          capture_output=True, check=True, env=dict(os.environ, K=k.decode())).stdout
    return json.loads(data.decode("utf-8"))


def setup_voices():
    ms = D.list_models()
    D.TTS_CHAIN = [m for m in ST.VOICE_MODELS if not ms or m in ms] + [m for m in D.TTS_CHAIN if m not in ST.VOICE_MODELS]
    vf = os.path.join(ROOT, "story", "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])


def bad_lines(keys, texts, bounds, x):
    """A clip must sound like its line: Japanese is ~3-13.5 characters a second of speech."""
    import numpy as np
    bad = []
    for i, (k, t) in enumerate(zip(keys, texts)):
        seg = np.abs(x[int(bounds[i] * 24000):int(bounds[i + 1] * 24000)])
        m = len(seg) // 480
        sp = float((seg[:m * 480].reshape(m, 480).max(1) > 0.02).sum()) * 0.02 if m else 0.0
        rate = len(re.sub(r"[、。！？…〜「」ー]", "", t)) / max(sp, 0.05)
        if sp < 0.3 or not 3.0 <= rate <= 13.5:
            bad.append("%s %.1f/s %s" % (k, rate, t))
    return bad


def voice(c, wav):
    """3 TTS requests (chat+outro / Rio notes / Rio 問題). One retry when the sync check fails. Returns key -> clip."""
    groups = [[{"key": k, "who": w, "jp": t, "kana": ""} for k, w, t in g] for g in R.lines(c)]
    keys = [t["key"] for g in groups for t in g]
    texts = [t["jp"] for g in groups for t in g]
    for attempt in (1, 2):
        bounds = S.build_audio(groups, P_MULTI, P_ONE, wav)
        json.dump(bounds, open(wav[:-4] + ".bounds.json", "w"))
        x = S.RS.R.pcm(wav, 24000)
        bad = bad_lines(keys, texts, bounds, x)
        D.log("sync check", attempt, bad or "ok")
        if not bad:
            break
    if bad:
        D.WARN.append("voice/text may not match: " + " | ".join(bad)[:300])
    return {k: x[int(bounds[i] * 24000):int(bounds[i + 1] * 24000)] for i, k in enumerate(keys)}


def lines_hash(c):
    import hashlib
    return hashlib.sha1(json.dumps(R.lines(c), ensure_ascii=False).encode()).hexdigest()[:16]


def cached(c, no):
    """The voice of a test of exactly these lines (checked by Ye/Claude) -> reuse it: saves 3 TTS requests."""
    base = os.path.join(HERE, "out", "chat_test_%03d" % no)
    try:
        meta = json.load(open(base + ".meta.json"))
        if meta["hash"] != lines_hash(c):
            return None
        b = meta["bounds"]
        x = S.RS.R.pcm(base + ".wav", 24000)
        keys = [k for g in R.lines(c) for k, _, _ in g]
        D.log("using the tested voice of chat", no)
        return {k: x[int(b[i] * 24000):int(b[i + 1] * 24000)] for i, k in enumerate(keys)}
    except Exception:
        return None


def make(no, out):
    global R
    if os.path.exists(os.path.join(HERE, "explain_enc", "%03d.enc" % no)):   # Ye 11/12: explainer style when its content exists
        import explain as EX
        x = decrypt("explain_enc", no)
        if x:
            setup_voices()
            work = os.path.join(ROOT, "work", "n3")
            os.makedirs(work, exist_ok=True)
            wav = os.path.join(work, "ex_%03d.wav" % no)
            clips = EX.voice(x, wav)
            secs = EX.RX.render(x, clips, out, tempfile.mkdtemp())
            return x, secs, wav
    c = decrypt("chat_enc", no)
    if not c:
        raise RuntimeError("chat content %03d is not in n3/chat_enc yet" % no)
    R = R4 if c.get("hook") else R3
    setup_voices()
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "chat_%03d.wav" % no)
    clips = cached(c, no)
    if clips is None:
        clips = voice(c, wav)
    else:
        shutil.copy(os.path.join(HERE, "out", "chat_test_%03d.wav" % no), wav)
    secs = R.render(c, clips, out, tempfile.mkdtemp())
    return c, secs, wav


def main():
    trig = open(os.path.join(HERE, "chat_trigger.txt"), encoding="utf-8").read()
    no = int(re.search(r"\d+", trig).group(0))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    keep = os.path.join(HERE, "out", "chat_test_%03d.mp4" % no)
    c, secs, wav = make(no, keep)
    shutil.copy(wav, os.path.join(HERE, "out", "chat_test_%03d.wav" % no))
    if os.path.exists(wav[:-4] + ".bounds.json"):
        json.dump({"hash": lines_hash(c), "bounds": json.load(open(wav[:-4] + ".bounds.json"))},
                  open(os.path.join(HERE, "out", "chat_test_%03d.meta.json" % no), "w"))
    os.chdir(ROOT)
    D.push("n3 chat test %03d" % no, ["n3/out"])
    cap = "🧪 N3 စကားပြောပုံစံ test No.%d %s (%ds)\nမတင်ရသေးဘူး၊ မင်းကြည့်ဖို့ပဲ။" % (no, c["title"], secs)
    if D.WARN:
        cap += "\n⚠️ " + " / ".join(D.WARN)[:300]
    if not D.tg("sendVideo", {"chat_id": D.OWNER, "caption": cap, "supports_streaming": "true"}, {"video": open(keep, "rb")}):
        D.WARN.append("Telegram sendVideo failed")
    D.log(cap, D.WARN)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ N3 chat test: error\n%s: %s" % (type(e).__name__, str(e)[:500])})
        raise


# ---------------------------------------------------------------- daily post (steps/steps.py, state "format" == "n3chat")
# Ye 11/09: 2 videos a day until JLPT (12/06): ★ grammar first. Video A = <key> (Make posts it at 19:00),
# video B = <key>b (Make posts it to Facebook at 19:00 and schedules TikTok/YouTube for 12:00 the next day).
ORDER = [2, 3, 1, 4, 5, 6, 7, 8, 9, 10, 16, 17, 18, 19, 20, 25, 26, 27, 28, 32, 33, 34, 35, 36, 37, 42, 43, 44, 45, 46,
         52, 53, 54, 55, 56, 57, 62, 63, 64, 65, 66,
         11, 12, 13, 14, 15, 21, 22, 23, 24, 29, 30, 31, 38, 39, 40, 41, 47, 48, 49, 50, 51, 58, 59, 60, 61]


def strip_html(s):
    return re.sub(r"<[^>]+>", "", s.replace("<br>", " ")).strip()


def title_caption(c):
    if c.get("title_card"):
        return ex_title_caption(c)
    title = "N3文法 No.%d｜%s" % (c["no"], c["title"])
    cap = ["📘 N3 文法 No.%d  %s" % (c["no"], c["title"]), ""]
    cap += ["・%s = %s" % (g, mm) for g, mm in c.get("points", [])]
    cap += ["", "🗣"] + ["%s: %s" % (l["who"], plain_jp(l["jp"])) for l in c["chat"]]
    cap += ["", "✍️ ဒီ grammar နဲ့ ကိုယ်ပိုင်ဝါကျ တစ်ကြောင်း comment မှာ ရေးကြည့်နော်!", "", "#ဂျပန်စာ #日本語 #JLPT #N3 #N3文法 #LearnWithRio"]
    return title, "\n".join(cap)


def plain_jp(s):
    s = re.sub(r"《.+?》", "", s)   # drop furigana
    return re.sub(r"[\[\]{}]", "", s)


def ex_title_caption(x):
    tc = x["title_card"]
    title = "N3文法 No.%d｜%s" % (x["no"], x["title"])
    cap = ["📘 N3 文法 No.%d  %s" % (x["no"], x["title"]), "",
           "📖 " + strip_html(tc["meaning"].replace("<br>", " ・ ")), "💡 " + strip_html(tc["use"]), ""]
    for e in x["examples"]:
        cap += ["・" + plain_jp(e["jp"]).replace(" ", ""), "  " + strip_html(e["mm"])]
    cap += ["", "⚠️ ❌ " + plain_jp(x["trap"]["bad"]), "   ✅ " + plain_jp(x["trap"]["good"])]
    cap += ["", "✍️ ဒီ grammar နဲ့ ကိုယ်ပိုင်ဝါကျ တစ်ကြောင်း comment မှာ ရေးကြည့်နော်!", "", "#ဂျပန်စာ #日本語 #JLPT #N3 #N3文法 #LearnWithRio"]
    return title, "\n".join(cap)


def ex_transcript(x):
    q = x["quiz"]
    out = ["📘 N3 No.%d %s" % (x["no"], x["title"]), "", "📖 " + strip_html(x["title_card"]["meaning"].replace("<br>", " ・ ")),
           "💡 " + strip_html(x["title_card"]["use"]), "🧩 " + plain_jp(x["form_name"]), ""]
    for e in x["examples"]:
        out += [plain_jp(e["jp"]).replace(" ", ""), "   🇲🇲 " + strip_html(e["mm"]), "   💡 " + strip_html(e["why"])]
    out += ["", "⚠️ ❌ " + plain_jp(x["trap"]["bad"]), "✅ " + plain_jp(x["trap"]["good"]), "   " + strip_html(x["trap"]["why"])]
    out += ["", "✍️ " + plain_jp(q["q"])] + ["%d %s" % (i + 1, plain_jp(o)) for i, o in enumerate(q["opts"])]
    out += ["အဖြေ: %d %s" % (q["ans"], plain_jp(q["opts"][q["ans"] - 1])), "💭 " + strip_html(q["think"])]
    return "\n".join(out)[:4000]


def transcript(c):
    if c.get("title_card"):
        return ex_transcript(c)
    m = c["mondai"]
    out = ["📘 N3 No.%d %s" % (c["no"], c["title"]), ""]
    for l in c["chat"]:
        out += ["%s: %s" % (l["who"], plain_jp(l["jp"])), "   " + l.get("kana", ""), "   🇲🇲 " + l.get("mm", "")]
        out += ["   📝 " + strip_html(n) for n in l.get("notes", [])]
    if c.get("cautions"):
        out += ["", "⚠️ သတိ"]
        for w in c["cautions"]:
            out += ["❌ " + plain_jp(w["bad"]), "✅ " + plain_jp(w["good"]), "   " + strip_html(w["mm"])]
    out += ["", "✍️ " + m["q"]] + ["%d %s" % (i + 1, o) for i, o in enumerate(m["opts"])]
    out += ["အဖြေ: %d %s" % (m["ans"], m["opts"][m["ans"] - 1]), "💭 " + strip_html(m["think"])]
    for w in m["wrong"]:
        out += ["✕ %s – %s" % (w["g"], strip_html(w["mm"])), "   ✅ " + plain_jp(w["ex"])]
    return "\n".join(out)[:4000]


def daily(st, key, dry):
    """Make today's 2 videos. Returns a list of (vid, title, caption, secs, transcript, no). Updates st (unless dry)."""
    queue = st.get("chat_queue") or list(ORDER)
    # Ye 11/13: explainer style only. Use queue items that have explainer content; chat style only if none are ready.
    exq = [no for no in queue if os.path.exists(os.path.join(HERE, "explain_enc", "%03d.enc" % no))]
    picks = exq[:2]
    if len(picks) < 2:
        D.WARN.append("⚠️ explainer content running out (ready: %s) - Claude needs to write more" % exq)
    if not picks:
        picks = [no for no in queue if os.path.exists(os.path.join(HERE, "chat_enc", "%03d.enc" % no))][:2]
    if not picks:
        raise RuntimeError("no N3 chat content left in n3/chat_enc for the queue %s" % queue[:5])
    if len(picks) < 2:
        D.WARN.append("only one N3 chat video today (next content missing: %s)" % [q for q in queue if q not in picks][:3])
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    out = []
    for i, no in enumerate(picks):
        k = key if i == 0 else key + "b"
        vid = os.path.join(ROOT, "videos", k + ".mp4")
        c, secs, wav = make(no, vid)
        title, cap = title_caption(c)
        json.dump({"title": title, "caption": cap, "n3": no}, open(os.path.join(ROOT, "text", k + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        with open(os.path.join(ROOT, "text", k + ".txt"), "w", encoding="utf-8") as f:
            f.write("===TITLE===\n%s\n===CAPTION===\n%s\n===END===\n" % (title, cap))
        out.append((vid, title, cap, secs, transcript(c), no, k))
    if not dry:
        st["chat_queue"] = [q for q in queue if q not in picks]
        st["n3_last"] = picks[-1]
    return out
