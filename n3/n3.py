"""Learn with Rio - N3 grammar video (Rio先生) from Ye's note "N3 文法 先生ノート".
Daily: steps/steps.py calls daily() when steps/state.json has "format": "n3" (Ye 11/06: N3 replaces 4 Steps).
Test: put 'DRY 1' (note number) into n3/trigger.txt and push -> the video goes to the owner's Telegram DM only.
Ye's notes are private: n3/notes_enc/NNN.enc (AES) + NNN.key (AES key encrypted with n3/key/pub.pem). The private key is
n3/key/priv.enc, encrypted with the TG_TOKEN secret, so only the GitHub runner can read the notes."""
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


def load_note(no):
    """Decrypt note `no` into work/n3 (never committed). Returns the path, or None if there is no such note."""
    import subprocess
    enc = os.path.join(HERE, "notes_enc", "%03d" % no)
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
    out = os.path.join(work, "note_%03d.json" % no)
    open(out, "wb").write(data)
    return out


def next_note(st):
    no = st.get("n3_next", 1)
    while no <= 80 and not os.path.exists(os.path.join(HERE, "notes_enc", "%03d.enc" % no)):
        no += 1   # a few numbers are missing in the parsed PDF (13, 29, 62, 63, 65, 66) - skipped until they are added
    return no


def check_sync(n, wav):
    """Each line's piece of audio must sound like that line: Japanese is ~4-12 characters a second.
    Returns the lines that look wrong (a piece too short/long = the voice and the text drift apart)."""
    import numpy as np
    b = json.load(open(wav[:-4] + ".bounds.json"))
    x = N.RS.load_wav(wav)
    bad = []
    for i, t in enumerate(N.script(n)[1]):
        seg = np.abs(x[int(b[i] * 24000):int(b[i + 1] * 24000)])
        m = len(seg) // 480
        sp = float((seg[:m * 480].reshape(m, 480).max(1) > 0.02).sum()) * 0.02 if m else 0.0
        rate = len(re.sub(r"[、。！？…〜「」]", "", t["jp"])) / max(sp, 0.05)
        if sp < 0.3 or not 3.0 <= rate <= 13.5:
            bad.append("%s %.1f/s %s" % (t["key"], rate, t["jp"]))
    return bad


def voice(n, wav):
    """TTS with one retry when the sync check fails (a whole voice set is 5 calls; the daily quota is ~10)."""
    for attempt in (1, 2):
        S.build_audio(N.audio_groups(n), P_MULTI, P_ONE, wav)
        bad = check_sync(n, wav)
        D.log("sync check", attempt, bad or "ok")
        if not bad:
            return []
    D.WARN.append("voice/text may not match: " + " | ".join(bad)[:300])
    return bad


def main():
    ms = D.list_models()
    D.TTS_CHAIN = [m for m in ST.VOICE_MODELS if not ms or m in ms] + [m for m in D.TTS_CHAIN if m not in ST.VOICE_MODELS]
    vf = os.path.join(ROOT, "story", "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
    trig = open(os.path.join(HERE, "trigger.txt"), encoding="utf-8").read()
    note = load_note(int(re.search(r"\d+", trig).group(0)))
    n = json.load(open(note, encoding="utf-8"))
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "main.wav")
    voice(n, wav)
    out = os.path.join(work, "N3_%03d.mp4" % n["no"])
    secs = N.render(note, wav, out)
    os.makedirs(os.path.join(ROOT, "n3", "out"), exist_ok=True)
    keep = os.path.join(ROOT, "n3", "out", "test_%03d.mp4" % n["no"])
    os.replace(out, keep)
    import shutil  # keep the voice + line bounds of the test so the sync can be checked offline
    shutil.copy(wav, os.path.join(ROOT, "n3", "out", "test_main.wav"))
    shutil.copy(wav[:-4] + ".bounds.json", os.path.join(ROOT, "n3", "out", "test_main.bounds.json"))
    import datetime as dt
    json.dump({"no": n["no"], "date": dt.datetime.now(D.JST).strftime("%Y-%m-%d"), "lines": len(N.script(n)[1])},
              open(os.path.join(ROOT, "n3", "out", "test_meta.json"), "w"))
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
    no = next_note(st)
    path = load_note(no)
    if not path:
        raise RuntimeError("N3 note %03d is not in n3/notes_enc yet (all notes done?)" % no)
    n = N.fill_kana(json.load(open(path, encoding="utf-8")))
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "main.wav")
    # a test of the same note made today (checked by Claude) -> reuse its voice: no second TTS round (quota is ~10 a day)
    import datetime as dt, shutil
    mf = os.path.join(ROOT, "n3", "out", "test_meta.json")
    meta = json.load(open(mf)) if os.path.exists(mf) else {}
    today = dt.datetime.now(D.JST)
    if (meta.get("no") == no and meta.get("date") in (today.strftime("%Y-%m-%d"), (today - dt.timedelta(days=1)).strftime("%Y-%m-%d"))
            and meta.get("lines") == len(N.script(n)[1]) and os.path.exists(os.path.join(ROOT, "n3", "out", "test_main.wav"))):
        shutil.copy(os.path.join(ROOT, "n3", "out", "test_main.wav"), wav)
        shutil.copy(os.path.join(ROOT, "n3", "out", "test_main.bounds.json"), wav[:-4] + ".bounds.json")
        D.log("using today's checked test voice for note", no)
    else:
        voice(n, wav)
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    vid = os.path.join(ROOT, "videos", key + ".mp4")
    secs = N.render(path, wav, vid)
    os.makedirs(os.path.join(ROOT, "n3", "out"), exist_ok=True)   # keep the last voice to check it later
    shutil.copy(wav, os.path.join(ROOT, "n3", "out", "last_main.wav"))
    shutil.copy(wav[:-4] + ".bounds.json", os.path.join(ROOT, "n3", "out", "last_main.bounds.json"))
    title, cap = title_caption(n)
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    json.dump({"title": title, "caption": cap, "n3": no}, open(os.path.join(ROOT, "text", key + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "text", key + ".txt"), "w", encoding="utf-8") as f:
        f.write("===TITLE===\n%s\n===CAPTION===\n%s\n===END===\n" % (title, cap))
    if not dry:
        st["n3_next"] = no + 1
        st["n3_last"] = no
    return vid, title, cap, secs, transcript(n)
