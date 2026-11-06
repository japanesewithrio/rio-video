"""Learn with Rio - N3 grammar video (Rio先生) from Ye's note. TEST mode only for now: the video goes to the owner's Telegram DM.
trigger: put 'DRY n3/notes/001.json' into n3/trigger.txt and push."""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "steps"))
import steps as ST  # noqa: E402  (patches: patient TTS retries, silence squeeze)
import render_n3 as N  # noqa: E402

D, S = ST.D, ST.S
P_MULTI = ("TTS the following lines. Rio: a young Japanese man around 25, a kind, cheerful teacher explaining Japanese grammar to his "
           "friend. Yui: a young woman around 20, his bright, friendly student. Speak naturally, a little slower than normal and very clear "
           "for learners. Do NOT exaggerate; not like an announcer or anime. Leave a clear pause of about one second between lines.\n")
P_ONE = ("Say the following short Japanese phrases like a kind young teacher reading examples to a student: natural, a little slower "
         "than normal, very clear. Leave a clear pause of about one second between phrases.\n")


def main():
    ms = D.list_models()
    D.TTS_CHAIN = [m for m in ST.VOICE_MODELS if not ms or m in ms] + [m for m in D.TTS_CHAIN if m not in ST.VOICE_MODELS]
    vf = os.path.join(ROOT, "story", "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
    trig = open(os.path.join(HERE, "trigger.txt"), encoding="utf-8").read()
    note = re.search(r"n3/notes/\d+\.json", trig).group(0)
    n = json.load(open(os.path.join(ROOT, note), encoding="utf-8"))
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "main.wav")
    S.build_audio(N.audio_groups(n), P_MULTI, P_ONE, wav)
    out = os.path.join(work, "N3_%03d.mp4" % n["no"])
    secs = N.render(os.path.join(ROOT, note), wav, out)
    os.makedirs(os.path.join(ROOT, "n3", "out"), exist_ok=True)
    keep = os.path.join(ROOT, "n3", "out", "test_%03d.mp4" % n["no"])
    os.replace(out, keep)
    import shutil  # keep the voice + line bounds of the test so the sync can be checked offline
    shutil.copy(wav, os.path.join(ROOT, "n3", "out", "test_main.wav"))
    shutil.copy(wav[:-4] + ".bounds.json", os.path.join(ROOT, "n3", "out", "test_main.bounds.json"))
    os.chdir(ROOT)
    D.push("n3 test %03d" % n["no"], ["n3/out"])
    cap = "🧪 N3 test No.%d %s (%ds) - Rio先生 grammar video" % (n["no"], n["title"], secs)
    if not D.tg("sendVideo", {"chat_id": D.OWNER, "caption": cap, "supports_streaming": "true"}, {"video": open(keep, "rb")}):
        D.WARN.append("Telegram sendVideo failed")
    D.log(cap, D.WARN)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ N3 test video: error\n%s: %s" % (type(e).__name__, str(e)[:500])})
        raise


# ---------------------------------------------------------------- daily post (used by steps/steps.py when state "format" == "n3")
def title_caption(n):
    title = "N3文法 No.%d｜%s" % (n["no"], n["title"])
    heads = []
    for ln in n["meaning"][:2]:
        label, head, body, _ = N.split_meaning(ln)
        heads.append(("%s. %s" % (N.NUM_MM.get(label, label), head)) if label else head)
    cap = ["📘 Rio先生の N3 文法 No.%d  %s" % (n["no"], n["title"]), ""] + heads
    if len(n.get("quiz", [])) > 1:
        q = n["quiz"][1]
        cap += ["", "✍️ အိမ်စာ – comment မှာ ဖြေကြည့်နော်", q["q"],
                "  ".join("%d %s" % (i + 1, c) for i, c in enumerate(q["choices"]))]
    cap += ["", "#ဂျပန်စာ #日本語 #JLPT #N3 #N3文法 #LearnWithRio"]
    return title, "\n".join(cap)


def transcript(n):
    out = ["📘 N3 No.%d %s" % (n["no"], n["title"]), ""]
    out += [re.sub(r"^([A-D])[.．]", lambda m: N.NUM_MM[m.group(1)] + ".", N.jp_terms(x)) for x in n["meaning"]]
    out += ["", "② ချိတ်ပုံ"] + ["・%s → %s" % (N.form_label(f)[0], e) for f, e in n["form"]]
    out += ["", "④ ဥပမာ"]
    for e in n["examples"]:
        out += [e["jp"], "   " + n.get("kana", {}).get(e["jp"], ""), "   🇲🇲 " + e.get("mm", "")]
    if n.get("mistakes"):
        out += ["", "⑤ မှားလွယ်တာ"] + [N.jp_terms(m) for m in n["mistakes"]]
    if n.get("quiz"):
        q = n["quiz"][0]
        out += ["", "⑦ " + q["q"], "အဖြေ: %d %s" % (q["answer"], q["choices"][q["answer"] - 1]), N.jp_terms(q.get("why", ""))]
        out += ["%s %d %s – %s" % ("✅" if c["ok"] else "❌", c["n"], c["choice"], N.jp_terms(c["text"])) for c in q.get("each", [])]
    return "\n".join(x for x in out if x is not None)[:4000]


def daily(st, key, dry):
    """Make today's N3 video -> videos/<key>.mp4 + text/<key>.json (Make 'Rio ④' posts it at 19:00). Returns (path, title, caption, secs)."""
    no = st.get("n3_next", 1)
    path = os.path.join(ROOT, "n3", "notes", "%03d.json" % no)
    if not os.path.exists(path):
        raise RuntimeError("N3 note %03d is not in n3/notes yet" % no)
    n = N.fill_kana(json.load(open(path, encoding="utf-8")))
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "main.wav")
    S.build_audio(N.audio_groups(n), P_MULTI, P_ONE, wav)
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    vid = os.path.join(ROOT, "videos", key + ".mp4")
    secs = N.render(path, wav, vid)
    title, cap = title_caption(n)
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    json.dump({"title": title, "caption": cap, "n3": no}, open(os.path.join(ROOT, "text", key + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "text", key + ".txt"), "w", encoding="utf-8") as f:
        f.write("===TITLE===\n%s\n===CAPTION===\n%s\n===END===\n" % (title, cap))
    if not dry:
        st["n3_next"] = no + 1
    return vid, title, cap, secs, transcript(n)
