"""N3 chat-style video (Ye 11/09) - test run: 'CHAT <no>' in n3/chat_trigger.txt -> video to the owner's Telegram DM only.
Content: n3/chat_enc/NNN.enc + NNN.key (same private-note encryption as n3/notes_enc; written and checked by Claude)."""
import json, os, re, sys, tempfile, shutil, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "steps"))
sys.path.insert(0, HERE)
import steps as ST  # noqa: E402  (patches: patient TTS retries, silence squeeze)
import render_chat3 as R  # noqa: E402

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
        x = S.RS.R.pcm(wav, 24000)
        bad = bad_lines(keys, texts, bounds, x)
        D.log("sync check", attempt, bad or "ok")
        if not bad:
            break
    if bad:
        D.WARN.append("voice/text may not match: " + " | ".join(bad)[:300])
    return {k: x[int(bounds[i] * 24000):int(bounds[i + 1] * 24000)] for i, k in enumerate(keys)}


def make(no, out):
    c = decrypt("chat_enc", no)
    if not c:
        raise RuntimeError("chat content %03d is not in n3/chat_enc yet" % no)
    setup_voices()
    work = os.path.join(ROOT, "work", "n3")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "chat_%03d.wav" % no)
    clips = voice(c, wav)
    secs = R.render(c, clips, out, tempfile.mkdtemp())
    return c, secs, wav


def main():
    trig = open(os.path.join(HERE, "chat_trigger.txt"), encoding="utf-8").read()
    no = int(re.search(r"\d+", trig).group(0))
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    keep = os.path.join(HERE, "out", "chat_test_%03d.mp4" % no)
    c, secs, wav = make(no, keep)
    shutil.copy(wav, os.path.join(HERE, "out", "chat_test_%03d.wav" % no))
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
