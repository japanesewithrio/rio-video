"""Talking shots with WaveSpeed (Wan 2.2 speech-to-video). Needs the WAVESPEED_API_KEY secret.
jobs.json: [{"img": repo path of a 16:9 still, "wav": repo path of the voice, "prompt", "out", "res"?}]
Files are read through raw.githubusercontent.com (public repo), so commit them before running."""
import json, os, sys, time, requests
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get("WAVESPEED_API_KEY")
if not KEY:
    print("NO WAVESPEED_API_KEY secret"); sys.exit(0)
RAW = "https://raw.githubusercontent.com/%s/%s/" % (os.environ.get("GITHUB_REPOSITORY", "japanesewithrio/rio-video"), os.environ.get("GITHUB_SHA", "main"))
ROOT = os.path.abspath(os.path.join(H, "..", ".."))
HD = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
EP = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/speech-to-video"
VV = "http://localhost:50021"
def make_voices(jobs):
    need = [j for j in jobs if j.get("say") and not os.path.exists(os.path.join(ROOT, j["wav"]))]
    if not need:
        return False
    for _ in range(90):
        try:
            if requests.get(VV + "/version", timeout=5).ok: break
        except Exception: pass
        time.sleep(5)
    sp = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in requests.get(VV + "/speakers").json()}
    for j in need:
        sid = sp[j["voice"]].get("ノーマル") or list(sp[j["voice"]].values())[0]
        q = requests.post(VV + "/audio_query", params={"text": j["say"], "speaker": sid}).json()
        q["speedScale"] = j.get("speed", 1.0); q["prePhonemeLength"] = 0.05; q["postPhonemeLength"] = 0.1
        f = os.path.join(ROOT, j["wav"]); os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q).content)
    return True
try:
    print("balance", requests.get("https://api.wavespeed.ai/api/v3/balance", headers=HD, timeout=30).text[:200], flush=True)
except Exception as e:
    print("balance?", e)
JOBS = json.load(open(os.path.join(H, "jobs.json")))
if make_voices(JOBS):
    os.system('git config user.name rio-bot; git config user.email rio-bot@users.noreply.github.com; git add n3/ws n3/i2v/in; '
              'git commit -qm "talk voices [skip ci]"; git pull -q --rebase; git push -q')
    RAW = RAW.rsplit("/", 2)[0] + "/" + os.popen("git rev-parse HEAD").read().strip() + "/"
todo = []
for j in JOBS:
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst):
        continue
    body = {"image": RAW + j["img"], "audio": RAW + j["wav"], "prompt": j.get("prompt", ""), "resolution": j.get("res", "480p")}
    r = requests.post(EP, headers=HD, json=body, timeout=60)
    d = r.json().get("data") or {}
    if not r.ok or not d.get("id"):
        print("FAIL submit", j["out"], r.status_code, r.text[:300], flush=True); continue
    todo.append((j, d["id"], time.time()))
    print("submitted", j["out"], d["id"], flush=True)
for j, pid, t0 in todo:
    while time.time() - t0 < 1500:
        time.sleep(8)
        d = requests.get("https://api.wavespeed.ai/api/v3/predictions/%s/result" % pid, headers=HD, timeout=60).json().get("data") or {}
        st = d.get("status")
        if st == "completed":
            open(os.path.join(OUT, j["out"]), "wb").write(requests.get(d["outputs"][0], timeout=300).content)
            print("OK", j["out"], "%.0fs" % (time.time() - t0), flush=True); break
        if st == "failed":
            print("FAIL", j["out"], d.get("error"), flush=True); break
    else:
        print("TIMEOUT", j["out"], flush=True)
