"""Send short voice samples (one per Gemini TTS voice) to the owner's Telegram DM so he can pick Rio's and Yui's voices."""
import os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily"))
import daily as D  # noqa: E402

MALE = ["Puck", "Umbriel", "Algieba", "Achird", "Iapetus", "Sadachbia", "Enceladus"]
FEMALE = ["Aoede", "Zephyr", "Callirrhoe", "Despina", "Laomedeia", "Achernar", "Leda"]
LINE_M = "え、マジで？それ、俺の傘じゃん。まあ、いいけどさ…明日はちゃんと返してね。"
LINE_F = "あ、ごめん！完全に忘れてた。でもさ、ピンクの傘もかわいくない？あはは。"
STYLE = ("Say this in Japanese like a real young person around 20 casually chatting with a close friend: relaxed, natural, "
         "low-key everyday tone, normal natural speed. Do not act, do not exaggerate emotions, not like a voice actor or announcer:\n")


def one(voice, text, path):
    body = {"contents": [{"parts": [{"text": STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    import base64, re, wave
    r = D.gemini(D.TTS_CHAIN, body)
    part = [p for p in r["candidates"][0]["content"]["parts"] if "inlineData" in p][0]["inlineData"]
    pcm = base64.b64decode(part["data"])
    rate = int((re.search(r"rate=(\d+)", part.get("mimeType", "")) or [0, 24000])[1])
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm)


def main():
    ms = D.list_models()
    if ms:
        D.TTS_CHAIN = [m for m in D.TTS_CHAIN if m in ms] or [D.pick(ms, "none", r"tts", avoid=())]
    os.makedirs("work/voices", exist_ok=True)
    D.tg("sendMessage", {"chat_id": D.OWNER, "text": "🎙 Voice samples\n♂ Rio အတွက် ယောကျာ်းအသံ %d ခု၊ ♀ Yui အတွက် မိန်းကလေးအသံ %d ခု\nကြိုက်တဲ့ နာမည်ကို Claude ကို ပြောပါ (ဥပမာ Rio = Puck, Yui = Aoede)" % (len(MALE), len(FEMALE))})
    for sex, voices, text in (("♂ Rio", MALE, LINE_M), ("♀ Yui", FEMALE, LINE_F)):
        for v in voices:
            p = "work/voices/%s.wav" % v
            try:
                one(v, text, p)
                cap = "%s : %s%s" % (sex, v, "  (အခုသုံးနေတဲ့အသံ)" if v in ("Enceladus", "Leda") else "")
                D.tg("sendAudio", {"chat_id": D.OWNER, "caption": cap, "title": v, "performer": sex}, {"audio": (v + ".wav", open(p, "rb"))})
            except Exception as e:
                D.log("voice failed", v, e)
            time.sleep(8)


if __name__ == "__main__":
    main()
