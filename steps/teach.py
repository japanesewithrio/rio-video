"""Format E test run (Ye 2026-11-03): Rio alone teaches a pattern chain.
Reads a prepared lesson (steps/teach_sample.json or the file named in steps/trigger.txt), makes Rio's voice with Gemini TTS,
renders the video with render_teach.py and sends it ONLY to the owner's Telegram DM. Never posts, never commits."""
import json, os, re, sys, wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import steps as SP  # noqa: E402  (loads daily/story helpers and the TTS patches: patient retries, silence squeeze)
import render_teach as RT  # noqa: E402

D, S = SP.D, SP.S

P_NORMAL = ("Say the following Japanese lines as Rio, a friendly Japanese young man around 20, talking to learners watching his video: "
            "relaxed, natural, normal speed, very clear. Like a kind senpai, not an announcer, not acting. "
            "Leave a clear pause of about one second between lines.\n")
P_SLOW = ("Say the following Japanese lines as Rio, a friendly Japanese young man around 20, showing a learner each sentence one by one: "
          "slowly and very clearly, with a tiny pause between phrases, still warm and natural (not robotic, not a teacher reading a textbook). "
          "Leave a clear pause of about one and a half seconds between lines.\n")


def build(groups, out_wav, gap=0.35):
    import numpy as np
    pieces, bounds, t0, sr = [], [0.0], 0.0, 24000
    for gi, (style, turns) in enumerate(groups):
        gw = out_wav[:-4] + "_g%02d.wav" % gi
        S.tts_lines(SP.P_MULTI, P_SLOW if style == "slow" else P_NORMAL, turns, gw)
        pts, T = (S.RS.R.split_points(gw, turns) if len(turns) > 1 else ([], S.RS.R.duration(gw)))
        x = np.concatenate([S.RS.R.pcm(gw, sr), np.zeros(int(sr * gap), np.float32)])
        pieces.append(x)
        bounds += [t0 + p for p in pts]
        t0 += len(x) / sr
        bounds.append(t0)
    y = (np.clip(np.concatenate(pieces), -1, 1) * 32767).astype(np.int16)
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())
    json.dump(bounds, open(out_wav[:-4] + ".bounds.json", "w"))
    return bounds


def main():
    ms = D.list_models()
    D.TTS_CHAIN = [m for m in SP.VOICE_MODELS if not ms or m in ms] + [m for m in D.TTS_CHAIN if m not in SP.VOICE_MODELS]
    vf = os.path.join(ROOT, "story", "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
    trig = open(os.path.join(HERE, "trigger.txt"), encoding="utf-8").read()
    m = re.search(r"steps/[A-Za-z0-9_]+\.json", trig)
    lesson = os.path.join(ROOT, m.group(0) if m else "steps/teach_sample.json")
    s = json.load(open(lesson, encoding="utf-8"))
    D.log("teach test", lesson, "voices", D.VOICES, "tts", D.TTS_CHAIN)
    work = os.path.join(ROOT, "work", "teach")
    os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "main.wav")
    build(RT.audio_groups(s), wav)
    out = os.path.join(work, "teach_test.mp4")
    secs = RT.render(lesson, wav, out)
    cap = "🧪 Format E TEST (Rio တစ်ယောက်တည်း) — %s (%ds)\nမတင်ရသေးဘူး၊ မင်းကြည့်ဖို့ပဲ။" % (s["title"], secs)
    if not D.tg("sendVideo", {"chat_id": D.OWNER, "caption": cap[:1020], "supports_streaming": "true"}, {"video": open(out, "rb")}):
        raise RuntimeError("Telegram sendVideo failed")
    D.log("sent", out, secs)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ Format E test: %s: %s" % (type(e).__name__, str(e)[:500])})
        raise
