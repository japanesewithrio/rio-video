"""One Gemini TTS call per line (single speaker, acted). n3/gv/lines.json: [{"out", "voice", "style", "text"}].
Skips files that already exist; writes n3/gv/out/<out> (24 kHz mono)."""
import base64, json, os, sys, time, wave, requests
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
KEY = os.environ["GEMINI_API_KEY"]
MODELS = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts", "gemini-3.1-flash-tts-preview", "gemini-3.8-flash-tts"]
bad = set(); fails = 0
for j in json.load(open(os.path.join(H, "lines.json"))):
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst):
        continue
    body = {"contents": [{"parts": [{"text": j["style"] + "\n\n" + j["text"]}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": j["voice"]}}}}}
    done = False
    for model in [m for m in MODELS if m not in bad]:
        for i in range(3):
            r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model, params={"key": KEY}, json=body, timeout=300)
            if r.ok and "inlineData" in str(r.json().get("candidates", [{}])[0].get("content", {})):
                pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
                secs = len(pcm) / 48000
                if secs > 3.0 + 0.4 * len(j["text"]):      # it read the instructions aloud: try the next model
                    print("too long", model, j["out"], "%.1fs" % secs); break
                with wave.open(dst, "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
                print("OK", model, j["out"], "%.1fs" % (len(pcm) / 48000)); done = True; break
            print("retry", model, j["out"], r.status_code, r.text[:160])
            if r.status_code in (404, 400) or (r.status_code == 429 and "PerDay" in r.text):
                bad.add(model); break
            time.sleep(15 * (i + 1))
        if done:
            break
        time.sleep(3)
    if not done:
        fails += 1
    time.sleep(7)   # free tier ~10 requests/min
sys.exit(1 if fails else 0)
