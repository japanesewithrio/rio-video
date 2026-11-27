"""Lip-sync test without the ZeroGPU quota (runs on the GitHub runner's CPU):
1) upscale the character's bust with an anime upscaler, 2) paint 5 mouth shapes (a i u e o) with an SD inpainting model,
3) take each mora's vowel + timing from VOICEVOX and switch mouths, with blinks and a little head motion."""
import json, os, subprocess, sys, time, wave
import numpy as np, requests, torch
from PIL import Image, ImageDraw, ImageFilter
H = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(H, "out"); os.makedirs(OUT, exist_ok=True)
torch.set_num_threads(os.cpu_count())
cfg = json.load(open(os.path.join(H, "job.json")))
src = Image.open(os.path.join(H, "..", "cartoon", "assets", cfg["img"] + ".png")).convert("RGB")
x0, y0, x1, y1 = cfg["crop"]
bust = src.crop((x0, y0, x1, y1))
# 1) upscale x4 (Real-ESRGAN anime 6B) ------------------------------------------------------------
t0 = time.time()
try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer
    m = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=6, num_grow_ch=32, scale=4)
    up = RealESRGANer(scale=4, model_path="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
                      model=m, tile=256, half=False, device="cpu")
    arr, _ = up.enhance(np.array(bust)[:, :, ::-1], outscale=4)
    big = Image.fromarray(arr[:, :, ::-1])
    print("upscaled", big.size, "%.0fs" % (time.time() - t0))
except Exception as e:
    print("upscale failed", type(e).__name__, str(e)[:300])
    big = bust.resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.LANCZOS)
big.save(os.path.join(OUT, "big.png"))
S = big.width / (x1 - x0)
mx, my = (cfg["mouth"][0] - x0) * S, (cfg["mouth"][1] - y0) * S
# 2) mouth shapes --------------------------------------------------------------------------------
from diffusers import StableDiffusionInpaintPipeline
pipe = StableDiffusionInpaintPipeline.from_pretrained(cfg.get("model", "Lykon/dreamshaper-8-inpainting"), torch_dtype=torch.float32, safety_checker=None)
pipe.set_progress_bar_config(disable=True)
R = int(cfg.get("box", 300))
box = (int(mx - R / 2), int(my - R * 0.45), int(mx + R / 2), int(my + R * 0.55))
crop = big.crop(box).resize((512, 512), Image.LANCZOS)
mw, mh = cfg.get("mask", [0.42, 0.34])
mask = Image.new("L", (512, 512), 0)
ImageDraw.Draw(mask).ellipse((256 - 256 * mw, 230 - 256 * mh * 0.8, 256 + 256 * mw, 230 + 256 * mh * 1.2), fill=255)
mask_s = mask.filter(ImageFilter.GaussianBlur(10))
SH = {"a": "mouth wide open saying 'ah', open jaw, visible tongue and upper teeth",
      "i": "mouth open in a wide flat shape saying 'ee', teeth showing, lips stretched sideways",
      "u": "small round puckered mouth saying 'oo', lips pushed forward, small dark opening",
      "e": "mouth half open in a wide shape saying 'eh', upper teeth visible",
      "o": "round open mouth saying 'oh', oval opening"}
mouths = {}
for v, desc in SH.items():
    t0 = time.time()
    g = torch.Generator().manual_seed(7)
    r = pipe(prompt="korean webtoon anime style, clean black line art, flat cel shading, close-up of a young man's face, " + desc,
             negative_prompt="realistic, photo, blurry, deformed, extra teeth, lipstick, beard, text",
             image=crop, mask_image=mask, num_inference_steps=cfg.get("steps", 22), guidance_scale=7.5, strength=cfg.get("strength", 0.95),
             generator=g).images[0]
    piece = Image.composite(r, crop, mask_s).resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
    piece.save(os.path.join(OUT, "mouth_%s.png" % v))
    mouths[v] = piece
    print("mouth", v, "%.0fs" % (time.time() - t0))
# 3) voice + timing ------------------------------------------------------------------------------
VV = "http://localhost:50021"
for _ in range(90):
    try:
        if requests.get(VV + "/version", timeout=5).ok:
            break
    except Exception:
        pass
    time.sleep(5)
sp = {s["name"]: {st["name"]: st["id"] for st in s["styles"]} for s in requests.get(VV + "/speakers").json()}
sid = sp[cfg["voice"]]["ノーマル"]
q = requests.post(VV + "/audio_query", params={"text": cfg["text"], "speaker": sid}).json()
wav = os.path.join(OUT, "v.wav")
open(wav, "wb").write(requests.post(VV + "/synthesis", params={"speaker": sid}, json=q).content)
seq, t = [], q["prePhonemeLength"]
for ap in q["accent_phrases"]:
    for mo in ap["moras"]:
        c = mo.get("consonant_length") or 0
        if c:
            seq.append((t, t + c, "x")); t += c          # consonant: mouth nearly closed
        seq.append((t, t + mo["vowel_length"], mo["vowel"].lower())); t += mo["vowel_length"]
    if ap.get("pause_mora"):
        seq.append((t, t + ap["pause_mora"]["vowel_length"], "x")); t += ap["pause_mora"]["vowel_length"]
dur = t + q["postPhonemeLength"] + 0.6
FPS = 30
W = 1080; sc = W / big.width
frame0 = big.resize((W, int(big.height * sc)), Image.LANCZOS)
FH = min(frame0.height, 1920)
eyes = [((e[0] - x0) * S * sc, (e[1] - y0) * S * sc) for e in cfg["eyes"]]
skin = frame0.getpixel((int(mx * sc - 70), int(my * sc - 60)))
os.makedirs(os.path.join(OUT, "f"), exist_ok=True)
blinks = [0.9, 3.3, 5.6, 8.0]
for i in range(int(dur * FPS)):
    t = i / FPS
    shape = next((s for a, b, s in seq if a <= t < b), "x")
    im = big.copy()
    if shape in mouths:
        im.paste(mouths[shape], box[:2])
    elif shape == "N":
        pass
    im = im.resize((W, int(big.height * sc)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    if any(0 <= t - b < 0.12 for b in blinks):
        for ex, ey in eyes:
            r = cfg.get("eye_r", 26)
            d.ellipse((ex - r, ey - r * 0.65, ex + r, ey + r * 0.6), fill=skin)
            d.arc((ex - r * 0.95, ey - r * 0.55, ex + r * 0.95, ey + r * 0.4), 20, 160, fill=(35, 25, 25), width=5)
    talk = 1.0 if shape in mouths else 0.0
    im = im.rotate(0.9 * np.sin(t * 1.6), center=(W / 2, FH * 0.8), resample=Image.BICUBIC,
                   translate=(0, 3 * np.sin(t * 2.3) - 3 * talk), fillcolor=frame0.getpixel((5, 5)))
    canvas = Image.new("RGB", (W, 1920), frame0.getpixel((5, 5)))
    canvas.paste(im.crop((0, 0, W, FH)), (0, 1920 - FH if FH < 1920 else 0))
    canvas.save(os.path.join(OUT, "f", "%05d.jpg" % i), quality=90)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.join(OUT, "f", "%05d.jpg"), "-i", wav,
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                os.path.join(OUT, cfg["out"])], check=True)
subprocess.run(["rm", "-rf", os.path.join(OUT, "f")])
print("video ok", cfg["out"])
