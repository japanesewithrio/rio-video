"""image -> short video clips with a free Wan 2.2 Space (ZeroGPU, HF_TOKEN). Writes n3/i2v/out/*.mp4"""
import json, os, shutil, time
from gradio_client import Client, handle_file
H = os.path.dirname(os.path.abspath(__file__))
SPACES = ["zerogpu-aoti/wan2-2-fp8da-aoti-faster", "r3gm/wan2-2-fp8da-aoti-preview"]
tok = os.environ.get("HF_TOKEN") or None
os.makedirs(os.path.join(H, "out"), exist_ok=True)
for j in json.load(open(os.path.join(H, "jobs.json"))):
    dst = os.path.join(H, "out", j["out"])
    if os.path.exists(dst):
        continue
    for sp in SPACES:
        try:
            cl = Client(sp, token=tok)
            api = cl.view_api(print_info=False, return_format="dict")["named_endpoints"]
            name = [k for k in api if "video" in k] or list(api)
            t0 = time.time()
            res = cl.predict(input_image=handle_file(os.path.join(H, "in", j["in"])), prompt=j["prompt"],
                             duration_seconds=j.get("dur", 3.5), steps=j.get("steps", 6), api_name=name[0])
            v = res[0] if isinstance(res, (list, tuple)) else res
            v = v.get("video", v) if isinstance(v, dict) else v
            shutil.copy(v, dst)
            print("OK", sp, j["out"], "%.0fs" % (time.time() - t0))
            break
        except Exception as e:
            print("FAIL", sp, j["out"], type(e).__name__, str(e)[:300])
