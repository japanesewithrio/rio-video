"""Pictures through Hugging Face Inference Providers (paid per picture from the account's monthly free credit,
not the ZeroGPU quota). Jobs in n3/prov_jobs.json: [{"out", "prompt", "w", "h", "model"?, "ref"?}]"""
import io, json, os, sys, time
from huggingface_hub import InferenceClient
H = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(H, "cartoon", "assets")
cl = InferenceClient(provider="auto", api_key=os.environ["HF_TOKEN"])
for j in json.load(open(os.path.join(H, "prov_jobs.json"))):
    dst = os.path.join(A, j["out"] + ".png")
    if os.path.exists(dst):
        continue
    t0 = time.time()
    try:
        if j.get("ref"):
            img = cl.image_to_image(open(os.path.join(A, j["ref"] + ".png"), "rb").read(), prompt=j["prompt"],
                                    model=j.get("model", "black-forest-labs/FLUX.1-Kontext-dev"))
        else:
            img = cl.text_to_image(j["prompt"], model=j.get("model", "black-forest-labs/FLUX.1-schnell"),
                                   width=j.get("w", 1024), height=j.get("h", 1024))
        img.save(dst)
        print("OK", j["out"], j.get("model", ""), "%.0fs" % (time.time() - t0))
    except Exception as e:
        print("FAIL", j["out"], type(e).__name__, str(e)[:400])
