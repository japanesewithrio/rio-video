"""Picture check for finished explainer videos (Ye 11/14: Claude checks its own edit).
1) render_explain already shrinks text that runs off the screen and lists anything it could not fix (QA["dom"]).
2) Here a Gemini vision model looks at one settled frame per scene and reports layout problems.
Problems go into D.WARN and the frames go to Ye/Claude on Telegram before posting time."""
import base64, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "daily"))
import daily as D

PROMPT = """You are checking frames of a vertical (1080x1920) Japanese-grammar video for Burmese learners before it is posted.
The design is intentional: mint background with soft blurred rings, a green wave line near the bottom, small grey progress dots at the top,
green highlight pills, red-underlined た/ば/ない characters, small furigana above kanji. Do NOT report those.
Report ONLY real defects a viewer would notice:
- text cut off at a screen edge or clipped inside its card
- text or cards overlapping each other so something is hard to read
- broken characters (empty boxes □, missing Burmese/Japanese glyphs)
- an empty card or an obviously missing element
- text far too small to read on a phone
Frames are numbered from 1 in the order given.
Answer with JSON only: {"ok": true/false, "issues": [{"frame": n, "problem": "short description"}]}"""


def review(frames, title=""):
    if not frames or not D.GKEY:
        return []
    parts = [{"text": PROMPT + "\nVideo: " + title}]
    for f in frames[:10]:
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(open(f, "rb").read()).decode()}})
    body = {"contents": [{"parts": parts}], "generationConfig": {"temperature": 0, "response_mime_type": "application/json"}}
    try:
        ms = D.list_models()
        model = D.pick(ms, "gemini-2.5-flash", r"gemini-[\d.]+-flash")
        j = D.gemini([model, "gemini-2.5-flash"], body, tries=2)
        txt = j["candidates"][0]["content"]["parts"][0]["text"]
        res = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    except Exception as e:
        D.log("qa: picture check skipped", type(e).__name__, str(e)[:200])
        return []
    issues = [i for i in res.get("issues", []) if isinstance(i, dict)]
    D.log("qa:", "ok" if not issues else issues)
    return issues


def report(no, title, dom, frames):
    """Add problems to D.WARN and send the problem frames to the owner. Returns True if all clear."""
    probs = []
    if dom:
        probs.append("text still too wide at %s" % ", ".join("%.1fs %s" % (t, b[0]) for t, b in dom[:3]))
    issues = review(frames, "No.%d %s" % (no, title))
    for i in issues[:4]:
        probs.append("frame %s: %s" % (i.get("frame"), str(i.get("problem"))[:80]))
    if not probs:
        D.log("qa: No.%d looks fine" % no)
        return True
    D.WARN.append("🔍 picture check No.%d: " % no + " | ".join(probs))
    if D.OWNER and D.TG:
        sent = set()
        for i in issues[:3]:
            k = i.get("frame")
            if isinstance(k, int) and 1 <= k <= len(frames) and k not in sent:
                sent.add(k)
                D.tg("sendPhoto", {"chat_id": D.OWNER, "caption": "🔍 No.%d frame %d: %s" % (no, k, str(i.get("problem"))[:200])},
                     {"photo": open(frames[k - 1], "rb")})
    return False
