"""Music / ambience with Stable Audio Open (HF ZeroGPU, Stability Community License - commercial OK under $1M/yr).
jobs.json: [{"out", "prompt", "dur"}] -> n3/snd/out/<out>.wav"""
import json, os, shutil, time
from gradio_client import Client
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
SPACES = ["innoai/Stable-Audio-Open-Zero", "ameerazam08/stableaudio-open-1.0", "MakiAi/Stable-Audio-Open-Zero", "artificialguybr/Stable-Audio-Open-Zero"]
def endpoint(sp):
    cl = Client(sp, token=os.environ.get("HF_TOKEN"))
    api = cl.view_api(print_info=False, return_format="dict")["named_endpoints"]
    print("API", sp, json.dumps({k: [p["parameter_name"] for p in v["parameters"]] for k, v in api.items()})[:600], flush=True)
    name, ep = next((k, v) for k, v in api.items() if any("prompt" in p["parameter_name"].lower() for p in v["parameters"]))
    return cl, name, ep
for j in json.load(open(os.path.join(H, "jobs.json"))):
    dst = os.path.join(OUT, j["out"] + ".wav")
    if os.path.exists(dst): continue
    for sp in SPACES:
        try:
            cl, name, ep = endpoint(sp)
            kw = {}
            for p in ep["parameters"]:
                n = p["parameter_name"].lower()
                if "neg" in n: kw[p["parameter_name"]] = "low quality, noise, distortion, vocals, speech"
                elif "prompt" in n: kw[p["parameter_name"]] = j["prompt"]
                elif "second" in n or "duration" in n or "length" in n: kw[p["parameter_name"]] = j["dur"]
            t0 = time.time()
            r = cl.predict(api_name=name, **kw)
            f = r[0] if isinstance(r, (list, tuple)) else r
            f = f.get("path", f) if isinstance(f, dict) else f
            if f.endswith(".wav"): shutil.copy(f, dst)
            else: os.system('ffmpeg -v error -y -i "%s" -ar 48000 "%s"' % (f, dst))
            print("OK", j["out"], sp, "%.0fs" % (time.time() - t0), flush=True)
            break
        except Exception as e:
            print("FAIL", j["out"], sp, type(e).__name__, str(e)[:200], flush=True)
