import os, shutil, json
from gradio_client import Client
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
J = json.load(open(os.path.join(H, "ace.json")))
cl = Client("timefractal/ACE-Step-Turbo-Music-Gen", token=os.environ.get("HF_TOKEN"))
for j in J:
    dst = os.path.join(OUT, j["out"])
    if os.path.exists(dst): continue
    try:
        r = cl.predict(prompt=j["prompt"], lyrics=j["lyrics"], duration=j["dur"], seed=j.get("seed", 7), num_steps=j.get("steps", 8), api_name="/generate_music")
        f = r[0] if isinstance(r, (list, tuple)) else r
        f = f.get("path", f) if isinstance(f, dict) else f
        shutil.copy(f, dst); print("OK", j["out"], f, flush=True)
    except Exception as e:
        print("FAIL", j["out"], type(e).__name__, str(e)[:300], flush=True)
