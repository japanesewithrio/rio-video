"""Talking shots with WaveSpeed (Wan 2.2 speech-to-video). Needs the WAVESPEED_API_KEY secret.
jobs.json: [{"img": repo path of a 16:9 still, "wav": repo path of the voice, "prompt", "out", "res"?}]
Files are read through raw.githubusercontent.com (public repo), so commit them before running."""
import json, os, sys, time, requests
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
KEY = os.environ.get("WAVESPEED_API_KEY")
if not KEY:
    print("NO WAVESPEED_API_KEY secret"); sys.exit(0)
RAW = "https://raw.githubusercontent.com/%s/%s/" % (os.environ.get("GITHUB_REPOSITORY", "japanesewithrio/rio-video"), os.environ.get("GITHUB_SHA", "main"))
HD = {"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}
EP = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/speech-to-video"
todo = []
for j in json.load(open(os.path.join(H, "jobs.json"))):
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
