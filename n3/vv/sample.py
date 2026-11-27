"""VOICEVOX voice samples (engine runs as a service container in the workflow). Writes n3/vv/samples/*.wav"""
import json, os, time, requests
E = "http://localhost:50021"
for _ in range(90):
    try:
        if requests.get(E + "/version", timeout=5).ok:
            break
    except Exception:
        pass
    time.sleep(5)
sp = requests.get(E + "/speakers").json()
names = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in sp}
os.makedirs("n3/vv/samples", exist_ok=True)
json.dump(names, open("n3/vv/speakers.json", "w"), ensure_ascii=False, indent=1)
TEXT = {"m": "すみません！遅くなりました！アラームが鳴らなかったんです。",
        "f": "でも、アウンくんが遅刻するはずがない。毎日、十分前に来るから。"}
PICK = [("青山龍星", "m"), ("玄野武宏", "m"), ("白上虎太郎", "m"), ("剣崎雌雄", "m"),
        ("冥鳴ひまり", "f"), ("四国めたん", "f"), ("春日部つむぎ", "f"), ("雨晴はう", "f"), ("WhiteCUL", "f")]
for n, g in PICK:
    if n not in names:
        print("missing", n); continue
    sid = names[n].get("ノーマル") or list(names[n].values())[0]
    q = requests.post(E + "/audio_query", params={"text": TEXT[g], "speaker": sid}).json()
    w = requests.post(E + "/synthesis", params={"speaker": sid}, json=q).content
    open("n3/vv/samples/%s.wav" % n, "wb").write(w)
    print("ok", n, sid)
