"""Format F test run (Ye 2026-11-03): chat Before -> After. Makes Rio/Yui voices with Gemini TTS, renders with render_chat.py and
sends the video ONLY to the owner's Telegram DM. Never posts, never commits."""
import json, os, re, sys, wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import steps as SP  # noqa: E402  (daily/story helpers + TTS patches)
import render_chat as RC  # noqa: E402

D, S = SP.D, SP.S

P_CHAT = ("TTS the following short chat between two close Japanese friends around 20 years old. Rio: a young man, relaxed and friendly. "
          "Yui: a young woman, bright and friendly. Speak naturally like real young people, normal natural speed, very clear. "
          "Do NOT act and do NOT exaggerate; not like an announcer or anime. Leave a clear pause of about one second between lines.\n")
P_PLAIN = ("TTS the following short lines by two Japanese friends around 20. Line 1 Yui asks casually and brightly. "
           "Line 2 Rio answers stiffly and flatly, like reading a textbook (that is the joke). "
           "Line 3 Rio now talks to the viewer, playful and teasing. Line 4 Yui sounds a little let down and the talk dies. "
           "Natural, not exaggerated. Leave a clear pause of about one second between lines.\n")
P_ONE = ("Say the following Japanese as Rio, a friendly Japanese young man around 20, talking to learners watching his video: relaxed, "
         "natural, normal speed, very clear. Not an announcer, not acting.\n")


def build(groups, out_wav, gap=0.35):
    import numpy as np
    pieces, bounds, t0, sr = [], [0.0], 0.0, 24000
    for gi, (style, turns) in enumerate(groups):
        gw = out_wav[:-4] + "_g%02d.wav" % gi
        S.tts_lines(P_PLAIN if style == "plain" else P_CHAT, P_ONE, turns, gw)
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


def main():
    ms = D.list_models()
    D.TTS_CHAIN = [m for m in SP.VOICE_MODELS if not ms or m in ms] + [m for m in D.TTS_CHAIN if m not in SP.VOICE_MODELS]
    vf = os.path.join(ROOT, "story", "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
    trig = open(os.path.join(HERE, "trigger.txt"), encoding="utf-8").read()
    lessons = re.findall(r"steps/[A-Za-z0-9_]+\.json", trig) or ["steps/chat_sample.json"]
    for name in lessons:
        lesson = os.path.join(ROOT, name)
        s = json.load(open(lesson, encoding="utf-8"))
        D.log("chat test", lesson, "voices", D.VOICES, "tts", D.TTS_CHAIN)
        key = os.path.splitext(os.path.basename(name))[0]
        work = os.path.join(ROOT, "work", "chat", key)
        os.makedirs(work, exist_ok=True)
        wav = os.path.join(work, "main.wav")
        build(RC.audio_groups(s), wav)
        out = os.path.join(work, key + ".mp4")
        secs = RC.render(lesson, wav, out)
        cap = "🧪 Format F TEST — %s (%ds)\nမတင်ရသေးဘူး၊ မင်းကြည့်ဖို့ပဲ။" % (s["title"], secs)
        if not D.tg("sendVideo", {"chat_id": D.OWNER, "caption": cap[:1020], "supports_streaming": "true"}, {"video": open(out, "rb")}):
            raise RuntimeError("Telegram sendVideo failed")
        D.log("sent", out, secs)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ Format F test: %s: %s" % (type(e).__name__, str(e)[:500])})
        raise
