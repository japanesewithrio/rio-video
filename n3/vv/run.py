"""VOICEVOX lines (free, unlimited). n3/vv/lines.json: [{"out","speaker","style","text","speed","pitch","volume"}] -> n3/gv/out/<out>"""
import json, os, requests, time
VV = "http://localhost:50021"; H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(H), "gv", "out")
for _ in range(60):
    try:
        sp = requests.get(VV + "/speakers", timeout=5).json(); break
    except Exception:
        time.sleep(3)
ids = {(s["name"], st["name"]): st["id"] for s in sp for st in s["styles"]}
print(sorted(ids)[:400])
for j in json.load(open(os.path.join(H, "lines.json"))):
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst) and not j.get("force"):
        continue
    sid = ids.get((j["speaker"], j.get("style", "ノーマル"))) or ids[(j["speaker"], "ノーマル")]
    q = requests.post(VV + "/audio_query", params={"text": j["text"], "speaker": sid}, timeout=120).json()
    q["speedScale"] = j.get("speed", 1.05); q["pitchScale"] = j.get("pitch", 0); q["volumeScale"] = j.get("volume", 1)
    q["intonationScale"] = j.get("into", 1.0); q["prePhonemeLength"] = 0.05; q["postPhonemeLength"] = 0.1
    open(dst, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q, timeout=300).content)
    print("OK", j["out"], j["speaker"], j.get("style"))
