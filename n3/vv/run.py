"""VOICEVOX lines (free, unlimited). n3/vv/lines.json -> n3/gv/out/<out>
A line: {"out","speaker","style","text","speed","pitch","volume","into","pause","force"}
or with "parts": [{"text","style","speed","pitch","into","laugh"}...] joined into one natural take.
laugh=1 shapes the morae like a real laugh (short, breathy, high and falling)."""
import io, json, os, requests, time, wave
VV = "http://localhost:50021"; H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(H), "gv", "out")
for _ in range(60):
    try:
        sp = requests.get(VV + "/speakers", timeout=5).json(); break
    except Exception:
        time.sleep(3)
ids = {(s["name"], st["name"]): st["id"] for s in sp for st in s["styles"]}


def laughify(q):
    ms = [m for a in q["accent_phrases"] for m in a["moras"]]
    top = max([m["pitch"] for m in ms if m["pitch"] > 0] or [5.8]) + .22
    for k, m in enumerate(ms):
        if m["pitch"] > 0:
            m["pitch"] = top - .07 * k
        m["vowel_length"] = max(.05, m["vowel_length"] * .65)
        if m.get("consonant_length"):
            m["consonant_length"] = min(.07, m["consonant_length"] * 1.2)
    return q


def synth(j, p):
    st = p.get("style", j.get("style", "ノーマル"))
    sid = ids.get((j["speaker"], st)) or ids[(j["speaker"], "ノーマル")]
    q = requests.post(VV + "/audio_query", params={"text": p["text"], "speaker": sid}, timeout=120).json()
    g = lambda k, d: p.get(k, j.get(k, d))
    q["speedScale"] = g("speed", 1.05); q["pitchScale"] = g("pitch", 0); q["volumeScale"] = g("volume", 1)
    q["intonationScale"] = g("into", 1.15); q["prePhonemeLength"] = .05; q["postPhonemeLength"] = .1
    for a in q["accent_phrases"]:            # shorter breaths at 、 so the line flows in one go
        if a.get("pause_mora"):
            a["pause_mora"]["vowel_length"] *= g("pause", 1.0)
    if p.get("laugh"):
        q = laughify(q); q["speedScale"] = g("speed", 1.12)
    b = requests.post(VV + "/synthesis", params={"speaker": sid}, json=q, timeout=300).content
    w = wave.open(io.BytesIO(b)); return w.getparams(), w.readframes(w.getnframes())


for j in json.load(open(os.path.join(H, "lines.json"))):
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst) and not j.get("force"):
        continue
    parts = j.get("parts") or [{"text": j["text"]}]
    pcm, prm = b"", None
    for i, p in enumerate(parts):
        prm, f = synth(j, p)
        if i:   # trim the join: drop most of the trailing/leading silence between parts
            gap = int(prm.framerate * p.get("gap", .06)) * prm.sampwidth
            pcm = pcm[:max(0, len(pcm) - int(prm.framerate * .08) * prm.sampwidth)] + b"\0" * gap
            f = f[int(prm.framerate * .04) * prm.sampwidth:]
        pcm += f
    with wave.open(dst, "wb") as o:
        o.setparams(prm); o.writeframes(pcm)
    print("OK", j["out"], j["speaker"], [p["text"] for p in parts])
