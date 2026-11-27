"""Talking-character test: one picture + a VOICEVOX line -> audio-driven video (speech-to-video Spaces).
Tries with HF_TOKEN first, then anonymously (separate quota). Writes n3/talk/out/*"""
import json, os, shutil, time, traceback
import requests
from gradio_client import Client, handle_file
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
J = json.load(open(os.path.join(H, "job.json")))
TOK = os.environ.get("HF_TOKEN") or None
AUTH = [TOK, None] if TOK else [None]


def client(space):
    last = None
    for t in AUTH:
        try:
            return Client(space, token=t) if t else Client(space), t
        except Exception as e:
            last = e
    raise last


# 1) picture ------------------------------------------------------------------------------------
img = os.path.join(OUT, "face.png")
if not os.path.exists(img):
    for t in AUTH:
        try:
            cl = Client("mcp-tools/Qwen-Image-Fast", token=t) if t else Client("mcp-tools/Qwen-Image-Fast")
            r = cl.predict(prompt=J["image_prompt"], aspect_ratio="9:16", api_name="/generate_image")
            p = r[0] if isinstance(r, (list, tuple)) else r
            p = p.get("path", p) if isinstance(p, dict) else p
            shutil.copy(p, img); print("picture ok", "token" if t else "anon"); break
        except Exception as e:
            print("picture fail", "token" if t else "anon", type(e).__name__, str(e)[:200])
    if not os.path.exists(img):
        shutil.copy(os.path.join(H, "..", "cartoon", "assets", J["fallback_img"] + ".png"), img); print("picture: fallback")
# 2) voice ---------------------------------------------------------------------------------------
VV = "http://localhost:50021"
for _ in range(90):
    try:
        if requests.get(VV + "/version", timeout=5).ok: break
    except Exception: pass
    time.sleep(5)
sp = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in requests.get(VV + "/speakers").json()}
sid = sp[J["voice"]]["ノーマル"]
q = requests.post(VV + "/audio_query", params={"text": J["text"], "speaker": sid}).json()
wav = os.path.join(OUT, "voice.wav")
open(wav, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q).content)
# 3) speech-to-video -----------------------------------------------------------------------------
for space in J["spaces"]:
    for t in AUTH:
        tag = "%s (%s)" % (space, "token" if t else "anon")
        try:
            cl = Client(space, token=t) if t else Client(space)
            api = cl.view_api(print_info=False, return_format="dict")["named_endpoints"]
            print("API", space, json.dumps({k: [(p["parameter_name"], p["component"]) for p in v["parameters"]] for k, v in api.items()}, ensure_ascii=False)[:1500])
            best = None
            for name, v in api.items():
                comps = [p["component"].lower() for p in v["parameters"]]
                if "image" in comps and "audio" in comps:
                    best = (name, v); break
            if not best:
                print("no image+audio endpoint", tag); break
            name, v = best
            kw = {}
            for p in v["parameters"]:
                c, n = p["component"].lower(), p["parameter_name"]
                if c == "image": kw[n] = handle_file(img)
                elif c == "audio": kw[n] = handle_file(wav)
                elif c in ("textbox", "text") and ("prompt" in n.lower()) and "neg" not in n.lower(): kw[n] = J["motion_prompt"]
            t0 = time.time()
            r = cl.predict(api_name=name, **kw)
            vids = []
            def walk(x):
                if isinstance(x, str) and x.endswith((".mp4", ".webm", ".mov")): vids.append(x)
                elif isinstance(x, dict): [walk(y) for y in x.values()]
                elif isinstance(x, (list, tuple)): [walk(y) for y in x]
            walk(r)
            if vids:
                dst = os.path.join(OUT, space.replace("/", "__") + ".mp4"); shutil.copy(vids[0], dst)
                print("VIDEO OK", tag, "%.0fs" % (time.time() - t0)); break
            print("no video in result", tag, str(r)[:300])
        except Exception as e:
            print("FAIL", tag, type(e).__name__, str(e)[:300])
