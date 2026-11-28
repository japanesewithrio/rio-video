"""LivePortrait test (free HF Space): move a clean character still with the motion of a driving clip.
jobs.json: [{"src": repo image, "drive": repo video, "out": name.mp4}]"""
import json, os, shutil, time
from gradio_client import Client, handle_file
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(H))
tok = os.environ.get("HF_TOKEN") or None
for sp in ["KlingTeam/LivePortrait", "innoai/LivePortrait", "Han-123/LivePortrait"]:
    try:
        cl = Client(sp, token=tok); break
    except Exception as e:
        print("space fail", sp, e)
api = cl.view_api(print_info=False, return_format="dict")["named_endpoints"]
for k, v in api.items():
    print("EP", k, [(p["parameter_name"], p["component"], p.get("parameter_default")) for p in v["parameters"]][:30], flush=True)
ep = next(k for k, v in api.items() if any(p["component"] == "Image" for p in v["parameters"]) and any(p["component"] == "Video" for p in v["parameters"]))
print("using", ep, flush=True)
for j in json.load(open(os.path.join(H, "jobs.json"))):
    dst = os.path.join(H, "out", j["out"])
    if os.path.exists(dst):
        continue
    kw = {}
    for p in api[ep]["parameters"]:
        n, comp = p["parameter_name"], p["component"]
        if comp == "Image":
            kw[n] = handle_file(os.path.join(ROOT, j["src"]))
        elif comp == "Video":
            kw[n] = {"video": handle_file(os.path.join(ROOT, j["drive"]))}
        elif p.get("parameter_has_default"):
            kw[n] = p.get("parameter_default")
    for over in j.get("set", {}).items():
        kw[over[0]] = over[1]
    t0 = time.time()
    try:
        res = cl.predict(api_name=ep, **kw)
        print("RES", str(res)[:500], flush=True)
        outs = res if isinstance(res, (list, tuple)) else [res]
        vids = []
        for o in outs:
            v = o.get("video") if isinstance(o, dict) else o
            if isinstance(v, str) and v.endswith(".mp4"):
                vids.append(v)
        for i, v in enumerate(vids):
            shutil.copy(v, dst if i == 0 else dst.replace(".mp4", "_b%d.mp4" % i))
        print("OK", j["out"], len(vids), "%.0fs" % (time.time() - t0), flush=True)
    except Exception as e:
        print("FAIL", j["out"], type(e).__name__, str(e)[:400], flush=True)
