"""Gemini TTS for drama lines (natural acted voices). job.json: {"speakers": {name: voice}, "style": "...", "lines": [[speaker, direction, text]], "out"}
One multi-speaker call; writes out.wav (24 kHz mono) and, if asked, splits it into lines on the pauses."""
import base64, json, os, sys, time, wave, requests
import numpy as np
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
J = json.load(open(os.path.join(H, "job.json")))
KEY = os.environ["GEMINI_API_KEY"]
text = J["style"] + "\n\n" + "\n".join("%s: (%s) %s" % (s, d, t) if d else "%s: %s" % (s, t) for s, d, t in J["lines"])
body = {"contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
            {"speaker": k, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for k, v in J["speakers"].items()]}}}}
for model in ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]:
    for i in range(4):
        r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model, params={"key": KEY}, json=body, timeout=600)
        if r.ok and "candidates" in r.json():
            pcm = base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"])
            with wave.open(os.path.join(OUT, J["out"]), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
            print("OK", model, len(pcm) / 48000, "s"); sys.exit(0)
        print("retry", model, r.status_code, r.text[:200]); time.sleep(20 * (i + 1))
        if r.status_code == 429 and "PerDay" in r.text: break
print("FAIL"); sys.exit(1)
