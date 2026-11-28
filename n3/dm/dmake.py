"""Make every shot of a drama episode as one continuous film (Ye 11/28):
1) one Gemini multi-speaker TTS call for all spoken lines (acted, natural), split into one wav per line;
2) shots in order; a shot can start from the LAST FRAME of the previous shot of the same chain (same scene + character),
   so poses continue across cuts; talking shots = WaveSpeed Wan 2.2 speech-to-video (lip sync), silent shots = Wan i2v (HF ZeroGPU).
Input: the decrypted episode JSON path in argv[1]. Writes n3/dm/<no>/voice/NN.wav and n3/ws/out/<clip>.mp4"""
import base64, json, os, re, subprocess, sys, time, wave, shutil
import numpy as np, requests
from PIL import Image
H = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(H, "..", ".."))
A = os.path.join(ROOT, "n3", "cartoon", "assets")
c = json.load(open(sys.argv[1])); no = c["no"]
VD = os.path.join(H, str(no), "voice"); FD = os.path.join(H, str(no), "frames"); os.makedirs(VD, exist_ok=True); os.makedirs(FD, exist_ok=True)
WS_OUT = os.path.join(ROOT, "n3", "ws", "out"); os.makedirs(WS_OUT, exist_ok=True)
REPO = os.environ.get("GITHUB_REPOSITORY", "japanesewithrio/rio-video")
def sh(cmd): return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
def push(msg):
    sh('git config user.name rio-bot; git config user.email rio-bot@users.noreply.github.com; git add n3/dm n3/ws/out n3/i2v/out')
    sh('git commit -qm "%s [skip ci]"' % msg)
    for _ in range(3):
        sh("git pull -q --rebase"); r = subprocess.run("git push -q", shell=True)
        if r.returncode == 0: break
    return sh("git rev-parse HEAD")
def raw(path, sha): return "https://raw.githubusercontent.com/%s/%s/%s" % (REPO, sha, os.path.relpath(path, ROOT))
def plain(t): return re.sub(r"《.*?》", "", t).replace("[", "").replace("]", "").replace(" ", "")
# ---------- 1) voices ----------
spoken = [(i, l) for i, l in enumerate(c["lines"]) if l.get("who")]
if not all(os.path.exists(os.path.join(VD, "%02d.wav" % i)) for i, _ in spoken):
    sp = c["gemini"]["speakers"]
    text = c["gemini"]["style"] + "\n\n" + "\n".join("%s: (%s) %s" % (c["gemini"]["names"][l["who"]], l.get("act_voice", "natural"), plain(l["jp"])) for i, l in spoken)
    body = {"contents": [{"parts": [{"text": text}]}], "generationConfig": {"responseModalities": ["AUDIO"], "speechConfig": {"multiSpeakerVoiceConfig": {
        "speakerVoiceConfigs": [{"speaker": k, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for k, v in sp.items()]}}}}
    pcm = None
    for model in ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]:
        for k in range(4):
            r = requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model, params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=900)
            if r.ok and "candidates" in r.json():
                pcm = np.frombuffer(base64.b64decode(r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]), np.int16); break
            print("tts retry", model, r.status_code, r.text[:150], flush=True); time.sleep(20 * (k + 1))
            if r.status_code == 429 and "PerDay" in r.text: break
        if pcm is not None: break
    if pcm is None: sys.exit("no voice")
    # split on the N-1 longest silences
    x = pcm.astype(np.float32) / 32768; hop = 240  # 10 ms
    e = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) for i in range(0, len(x), hop)])
    quiet = e < max(0.01, np.percentile(e, 30) * 1.5)
    gaps, i = [], 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            if i > 0 and j < len(quiet): gaps.append((j - i, i, j))
            i = j
        else: i += 1
    n = len(spoken)
    cuts = sorted(sorted(gaps, reverse=True)[:n - 1], key=lambda g: g[1])
    if len(cuts) != n - 1: sys.exit("split failed: %d gaps for %d lines" % (len(cuts), n))
    bounds = [0] + [((a + b) // 2) * hop for _, a, b in cuts] + [len(pcm)]
    for k, (i, l) in enumerate(spoken):
        seg = pcm[bounds[k]:bounds[k + 1]]
        # trim edges, keep 0.08 s
        s = np.abs(seg.astype(np.int32)) > 300
        if s.any():
            a, b = np.argmax(s), len(s) - np.argmax(s[::-1])
            seg = seg[max(0, a - 2000):min(len(seg), b + 2000)]
        with wave.open(os.path.join(VD, "%02d.wav" % i), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(seg.tobytes())
        print("voice", i, "%.2fs" % (len(seg) / 24000), plain(l["jp"]), flush=True)
    push("drama %d voices" % no)
# ---------- 2) shots ----------
W, BH = 1280, 720
def still(l):
    bg = Image.open(os.path.join(A, l["bg"] + ".png")).convert("RGBA")
    s = max(W / bg.width, BH / bg.height); bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - BH) // 2, (bg.width - W) // 2 + W, (bg.height - BH) // 2 + BH))
    for ch in l.get("chars", []):
        im = Image.open(os.path.join(A, ch[0] + ".png")).convert("RGBA"); hp = int(ch[2] * BH); w = int(im.width * hp / im.height)
        im = im.resize((w, hp), Image.LANCZOS); bg.alpha_composite(im, (int(ch[1] * W - w / 2), int((ch[3] if len(ch) > 3 else 0.06) * BH)))
    return bg.convert("RGB")
def last_frame(mp4, png):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.15", "-i", mp4, "-frames:v", "1", "-vf", "scale=%d:%d" % (W, BH), png], check=True)
WSK = os.environ["WAVESPEED_API_KEY"]; WH = {"Authorization": "Bearer " + WSK, "Content-Type": "application/json"}
def s2v(img_url, wav_url, prompt, dst):
    r = requests.post("https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/speech-to-video", headers=WH,
                      json={"image": img_url, "audio": wav_url, "prompt": prompt, "resolution": "480p"}, timeout=60)
    pid = r.json()["data"]["id"]; t0 = time.time()
    while time.time() - t0 < 1200:
        time.sleep(6)
        d = requests.get("https://api.wavespeed.ai/api/v3/predictions/%s/result" % pid, headers=WH, timeout=60).json()["data"]
        if d["status"] == "completed":
            open(dst, "wb").write(requests.get(d["outputs"][0], timeout=300).content); return True
        if d["status"] == "failed": print("s2v failed", d.get("error")); return False
    return False
def i2v(png, prompt, dur, dst):
    from gradio_client import Client, handle_file
    cl = Client("zerogpu-aoti/wan2-2-fp8da-aoti-faster", token=os.environ.get("HF_TOKEN"))
    name = [k for k in cl.view_api(print_info=False, return_format="dict")["named_endpoints"] if "video" in k][0]
    r = cl.predict(input_image=handle_file(png), prompt=prompt, duration_seconds=dur, steps=6, api_name=name,
                   negative_prompt="extra person, new character, another person appears, text, watermark, deformed face, changing face, realistic photo, 3d render, blurry, camera shake")
    v = r[0] if isinstance(r, (list, tuple)) else r; v = v.get("video", v) if isinstance(v, dict) else v
    shutil.copy(v, dst); return True
STYLE = " Korean web animation style, keep exactly the same flat 2D art style, same face, same hair and clothes, only this person, natural subtle acting, no exaggerated effects."
last = {}
for i, l in enumerate(c["lines"]):
    clip = "d%d_%02d.mp4" % (no, i); dst = os.path.join(WS_OUT, clip); l["clip"] = clip
    key = "%s|%s" % (l.get("scene", l["bg"]), l.get("chain", ""))
    png = os.path.join(FD, "%02d_start.png" % i)
    if not os.path.exists(dst):
        if l.get("chain") and key in last and not l.get("fresh"):
            last_frame(last[key], png)
        else:
            still(l).save(png)
        t0 = time.time()
        if l.get("who"):
            sha = push("drama %d shot %d start" % (no, i))
            ok = s2v(raw(png, sha), raw(os.path.join(VD, "%02d.wav" % i), sha), l["motion"] + STYLE, dst)
        else:
            ok = i2v(png, "Korean web animation. " + l["motion"] + STYLE, l.get("dur", 4), dst)
        print("shot", i, "OK" if ok else "FAIL", "%.0fs" % (time.time() - t0), flush=True)
        if not ok: sys.exit(1)
        push("drama %d shot %d" % (no, i))
    if l.get("chain"): last[key] = dst
print("all shots done")
