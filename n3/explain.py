"""N3 explainer video test (Ye 11/11): 'EX <no>' in n3/explain_trigger.txt -> video to the owner's Telegram DM only.
Content: n3/explain_enc/NNN.enc + .key (encrypted like n3/chat_enc)."""
import json, os, re, shutil, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import chat3 as C3  # noqa: E402  (decrypt, voices, sync check)
import render_explain as RX  # noqa: E402

D, S = C3.D, C3.S


def voice(x, wav):
    groups = [[{"key": k, "who": "Rio", "jp": t, "kana": ""} for k, t in g] for g in RX.lines(x)]
    keys = [t["key"] for g in groups for t in g]
    texts = [t["jp"] for g in groups for t in g]
    bad = []
    for attempt in (1, 2):
        bounds = S.build_audio(groups, C3.P_MULTI, C3.P_ONE, wav)
        y = S.RS.R.pcm(wav, 24000)
        bad = C3.bad_lines(keys, texts, bounds, y)
        D.log("sync check", attempt, bad or "ok")
        if not bad:
            break
    if bad:
        D.WARN.append("voice/text may not match: " + " | ".join(bad)[:300])
    return {k: y[int(bounds[i] * 24000):int(bounds[i + 1] * 24000)] for i, k in enumerate(keys)}


def main():
    no = int(re.search(r"\d+", open(os.path.join(HERE, "explain_trigger.txt"), encoding="utf-8").read()).group(0))
    x = C3.decrypt("explain_enc", no)
    if not x:
        raise RuntimeError("explainer content %03d missing" % no)
    C3.setup_voices()
    work = os.path.join(ROOT, "work", "n3"); os.makedirs(work, exist_ok=True)
    wav = os.path.join(work, "ex_%03d.wav" % no)
    clips = voice(x, wav)
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out = os.path.join(HERE, "out", "explain_test_%03d.mp4" % no)
    secs = RX.render(x, clips, out, tempfile.mkdtemp())
    shutil.copy(wav, os.path.join(HERE, "out", "explain_test_%03d.wav" % no))
    os.chdir(ROOT)
    D.push("n3 explain test %03d" % no, ["n3/out"])
    cap = "🧪 N3 ရှင်းပြပုံစံ test No.%d %s (%ds)\nမတင်ရသေးဘူး၊ မင်းကြည့်ဖို့ပဲ။" % (no, x["title"], secs)
    if D.WARN:
        cap += "\n⚠️ " + " / ".join(D.WARN)[:300]
    if not D.tg("sendVideo", {"chat_id": D.OWNER, "caption": cap, "supports_streaming": "true"}, {"video": open(out, "rb")}):
        D.WARN.append("Telegram sendVideo failed")
    D.log(cap, D.WARN)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ N3 explainer test: error\n%s: %s" % (type(e).__name__, str(e)[:500])})
        raise
