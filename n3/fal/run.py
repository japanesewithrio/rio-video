"""Paid quality test on fal.ai (needs the FAL_KEY secret and credit). Outputs n3/fal/out/*.mp4
jobs: {"kind": "s2v"|"i2v", "model", "img", "say"/"voice" (s2v), "prompt", "out", "args"}"""
import json, os, sys, time, requests
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
if not os.environ.get("FAL_KEY"):
    print("NO FAL_KEY secret - nothing to do"); sys.exit(0)
import fal_client
VV = "http://localhost:50021"
def voice(text, name, path):
    for _ in range(90):
        try:
            if requests.get(VV + "/version", timeout=5).ok: break
        except Exception: pass
        time.sleep(5)
    sp = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in requests.get(VV + "/speakers").json()}
    sid = sp[name]["ノーマル"]
    q = requests.post(VV + "/audio_query", params={"text": text, "speaker": sid}).json()
    q["postPhonemeLength"] = 0.4
    open(path, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q).content)
for j in json.load(open(os.path.join(H, "jobs.json"))):
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst): continue
    t0 = time.time()
    try:
        img_url = fal_client.upload_file(os.path.join(H, "..", j["img"]))
        args = {"image_url": img_url, "prompt": j.get("prompt", "")}
        if j["kind"] == "s2v":
            wav = os.path.join(OUT, j["out"] + ".wav"); voice(j["say"], j["voice"], wav)
            args["audio_url"] = fal_client.upload_file(wav)
        args.update(j.get("args", {}))
        r = fal_client.subscribe(j["model"], arguments=args, with_logs=False)
        url = (r.get("video") or {}).get("url") or r.get("video_url")
        open(dst, "wb").write(requests.get(url, timeout=300).content)
        if j["kind"] == "s2v":   # put our clean voice on the clip
            os.system('ffmpeg -v error -y -i "%s" -i "%s" -map 0:v -map 1:a -c:v copy -c:a aac -shortest "%s.m.mp4" && mv "%s.m.mp4" "%s"' % (dst, wav, dst, dst, dst))
        print("OK", j["model"], j["out"], "%.0fs" % (time.time() - t0), flush=True)
    except Exception as e:
        print("FAIL", j["model"], j["out"], type(e).__name__, str(e)[:400], flush=True)
