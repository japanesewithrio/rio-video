"""AivisSpeech lines (VOICEVOX-compatible API). n3/av/lines.json: [{"out","model","style","text","speed","into","tempo"}] -> n3/gv/out/<out>"""
import json, os, requests, time
VV = os.environ.get("VV", "http://localhost:10101"); H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(os.path.dirname(H), "gv", "out")
sp = requests.get(VV + "/speakers", timeout=60).json()
ids = {(s["name"], st["name"]): st["id"] for s in sp for st in s["styles"]}
json.dump([[s["name"], [st["name"] for st in s["styles"]]] for s in sp], open(os.path.join(H, "speakers.json"), "w"), ensure_ascii=False)
for j in json.load(open(os.path.join(H, "lines.json"))):
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst) and not j.get("force"):
        continue
    sid = ids.get((j["model"], j.get("style", "ノーマル")))
    if sid is None:
        sid = next(v for (n, s), v in ids.items() if n == j["model"])
    t0 = time.time()
    q = requests.post(VV + "/audio_query", params={"text": j["text"], "speaker": sid}, timeout=300).json()
    q["speedScale"] = j.get("speed", 1.0); q["intonationScale"] = j.get("into", 1.0); q["tempoDynamicsScale"] = j.get("tempo", 1.0)
    q["prePhonemeLength"] = .05; q["postPhonemeLength"] = .1
    open(dst, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q, timeout=600).content)
    print("OK", j["out"], j["model"], "%.1fs" % (time.time() - t0), flush=True)
