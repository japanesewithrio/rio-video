"""Royalty-free music (Kevin MacLeod / incompetech, CC BY 4.0 - credit in the description) + ACE-Step karaoke try."""
import os, json, requests, shutil, time
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
T = {"bgm_monkeys": "Monkeys Spinning Monkeys", "bgm_snitch": "Sneaky Snitch", "bgm_duck": "Fluffing a Duck", "bgm_pixel": "Pixel Peeker Polka - faster", "bgm_karaoke_enka": "Hep Cats"}
for k, name in T.items():
    dst = os.path.join(OUT, k + ".mp3")
    if os.path.exists(dst): continue
    u = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/" + requests.utils.quote(name) + ".mp3"
    r = requests.get(u, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    print(k, r.status_code, len(r.content), r.headers.get("content-type"), flush=True)
    if r.ok and len(r.content) > 100000: open(dst, "wb").write(r.content)
# ACE-Step (Apache-2.0) karaoke backing, best effort
try:
    from gradio_client import Client
    for sp in ["ACE-Step/ACE-Step", "timefractal/ACE-Step-Turbo-Music-Gen", "Kansasfan/ace-step-music-studio"]:
        try:
            cl = Client(sp, token=os.environ.get("HF_TOKEN"))
            api = cl.view_api(print_info=False, return_format="dict")["named_endpoints"]
            print("API", sp, json.dumps({k: [(p["parameter_name"], p["component"]) for p in v["parameters"]] for k, v in api.items()})[:1500], flush=True)
        except Exception as e:
            print("ace", sp, type(e).__name__, str(e)[:200], flush=True)
except Exception as e:
    print("ace", e)
