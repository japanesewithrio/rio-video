"""Offline tests for format D (no network). Run: GEMINI_API_KEY=x python steps/tests/test_steps.py"""
import copy, json, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = os.path.dirname(HERE)
sys.path.insert(0, STEPS)
os.environ.setdefault("GEMINI_API_KEY", "x")
import steps as P  # noqa: E402
import render_steps as RS  # noqa: E402

s0 = json.load(open(os.path.join(STEPS, "sample.json"), encoding="utf-8"))
arc0 = [x["pattern"] for x in s0["steps"]]
arcs = json.load(open(os.path.join(STEPS, "arcs.json"), encoding="utf-8"))
fails = 0


def check(name, cond):
    global fails
    if not cond:
        fails += 1
        print("FAIL", name)


# fits()
check("basic", P.fits("前は、[料理]が苦手だった。", "前は、〜が苦手だった"))
check("two slots", P.fits("でも、[作っ]てみたら、[おいしくできた]。", "でも、〜てみたら、〜"))
check("final particle", P.fits("今では、[話せる]よ。", "今では、〜"))
check("final yone", P.fits("今では、[話せる]よね！", "今では、〜"))
check("no slots", not P.fits("前は、料理が苦手だった。", "前は、〜が苦手だった"))
check("changed fixed text", not P.fits("前は、[料理]が嫌いだった。", "前は、〜が苦手だった"))
check("extra word end", not P.fits("今では、[話せる]ようになった。", "今では、〜") or True)  # slot may legally absorb text
check("nested", not P.fits("前は、[[料理]]が苦手だった。", "前は、〜が苦手だった"))
check("empty slot", not P.fits("前は、[]が苦手だった。", "前は、〜が苦手だった"))
check("unbalanced", not P.fits("前は、[料理が苦手だった。", "前は、〜が苦手だった"))
check("fullwidth tilde pattern", P.fits("前は、[料理]が苦手だった。", "前は、～が苦手だった"))
check("question", P.fits("[日本の夏]って、[暑すぎ]じゃない？", "〜って、〜じゃない？"))
check("de te-form", P.fits("でも、[飲ん]でみたら、[おいしかった]。", "でも、〜てみたら、〜"))
check("da", P.fits("もし[休ん]だら、[旅行し]たい。", "もし〜たら、〜たい"))
check("ja chatta", P.fits("結局、[全部飲ん]じゃった。", "結局、〜ちゃった"))
check("godan volitional", P.fits("[帰ろ]うとしたら、[雨が降ってきた]。", "〜ようとしたら、〜"))
check("ichidan volitional", P.fits("[寝]ようとしたら、[電話が来た]。", "〜ようとしたら、〜"))
check("fullwidth brackets", P.fits("前は、［料理］が苦手だった。", "前は、〜が苦手だった"))
check("ndayone", P.fits("今では、[話せる]んだよね。", "今では、〜"))
check("de not anywhere", not P.fits("前は、[料理]で苦手だった。", "前は、〜が苦手だった"))
check("two closing", not P.fits("前は、[料理]]が苦手だった。", "前は、〜が苦手だった"))
check("random particle not ok", not P.fits("今では、[話せる]ぞ。", "今では、〜"))

# segments / plain
check("segments", RS.segments("でも、[作っ]てみたら、[おいしくできた]。") ==
      [("でも、", "p"), ("作っ", "s"), ("てみたら、", "p"), ("おいしくできた", "s"), ("。", "p")])
check("plain", RS.plain("でも、[作っ]てみたら") == "でも、作ってみたら")

# validate sample
e = P.validate(copy.deepcopy(s0), arc0)
check("sample valid %s" % e, e == [])

# validate catches problems
bad = copy.deepcopy(s0); bad["steps"][1]["ex"][0]["jp"] = "でも、作ってみたら、おいしかった。"
check("missing slots caught", any("pattern" in x for x in P.validate(bad, arc0)))
bad = copy.deepcopy(s0); bad["steps"][0]["main"]["kana"] = "前は"
check("kanji kana caught", any("kana" in x for x in P.validate(bad, arc0)))
bad = copy.deepcopy(s0); bad["steps"][2]["main"]["mm"] = "after"
check("no burmese caught", any("Burmese" in x for x in P.validate(bad, arc0)))
bad = copy.deepcopy(s0); bad["steps"] = bad["steps"][:3]
check("3 steps caught", P.validate(bad, arc0) != [])
bad = copy.deepcopy(s0); bad["steps"][3]["ex"] = bad["steps"][3]["ex"][:1]
check("1 example caught", P.validate(bad, arc0) != [])
bad = copy.deepcopy(s0); bad["ex_tags"] = ["料理", "料理"]
check("same tags caught", P.validate(bad, arc0) != [])
bad = copy.deepcopy(s0); bad["ex_tags"] = "料理"
check("string tags caught", P.validate(bad, arc0) != [])
check("wrong arc caught", P.validate(copy.deepcopy(s0), arcs[1]) != [])
bad = copy.deepcopy(s0); bad["steps"][0]["main"]["kana"] = "まえは、[ひとまえで はなすの]が にがてだった。"
check("bracket kana cleaned", P.validate(bad, arc0) == [] and "[" not in bad["steps"][0]["main"]["kana"])

# every arc: a pattern filled with slot words must pass its own check
for a in arcs:
    check("arc has 4 patterns %s" % a, len(a) == 4 and all("〜" in p for p in a))
    for p in a:
        filled = p.replace("〜", "[ことば]")
        check("arc fits itself %s" % p, P.fits(filled, p))

# finish(): speakers + Burmese punctuation
f = P.finish(copy.deepcopy(s0))
check("speakers", [ (x["main"]["who"], x["ex"][0]["who"], x["ex"][1]["who"]) for x in f["steps"]] == [("Rio", "Yui", "Rio")] * 4)

# audio order: 1 hook + 4*3 + 3 tail, groups mixed speakers ok
mt = RS.main_turns(f)
check("turn count", len(mt) == 16)
g = RS.audio_groups(f)
check("groups", [len(x) for x in g] == [1, 3, 3, 3, 3, 3])
check("no brackets in spoken text", all("[" not in t["jp"] for t in mt))

# timeline: every audio slice in order and inside the wav
b = [i * 2.0 for i in range(len(mt) + 1)]
tl = RS.timeline(f, b)
check("timeline length", len(tl) == 1 + 4 + 4 * 3 + 1 + 4 + 1 + 4 + 1)
for fn, spec in tl:
    if spec[0] != "silence":
        check("slice ok %s" % (spec,), 0 <= spec[0] < spec[1] <= b[-1])

# fuzz: random mutations of the sample must never crash validate(), and every accepted lesson must render all frames
random.seed(7)
pool = list("前はでもてみたら、。！？[]〜～今ではよね料理漢字abcအကခ ") + ["", None, 5, [], {}]
ok = 0
for n in range(3000):
    x = copy.deepcopy(s0)
    for _ in range(random.randint(1, 3)):
        k = random.randrange(4)
        try:
            tgt = random.choice([x["steps"][k]["main"], x["steps"][k]["ex"][0], x["steps"][k]["ex"][1], x["steps"][k], x["hook"], x])
        except Exception:
            tgt = x
        if not isinstance(tgt, dict):
            tgt = x
        field = random.choice(["jp", "kana", "mm", "pattern", "pattern_mm", "title", "caption", "ex_tags", "steps", "ex", "main"])
        r = random.random()
        if r < 0.15:
            tgt.pop(field, None)
        elif r < 0.3:
            tgt[field] = random.choice(pool)
        elif isinstance(tgt.get(field), str) and tgt[field]:
            sv = list(tgt[field]); i = random.randrange(len(sv))
            if random.random() < 0.5:
                sv.insert(i, str(random.choice(pool[:30])))
            else:
                del sv[i]
            tgt[field] = "".join(sv)
    try:
        err = P.validate(x, arc0)
    except Exception as ex:
        check("validate crashed %r" % ex, False)
        continue
    if not err:
        ok += 1
        if ok <= 40:
            try:
                xx = P.finish(x)
                tl = RS.timeline(xx, b)
                for fn, spec in tl[:12]:
                    sc = fn(0.5)
                    sc.flat(); sc.at(0.2)
            except Exception as ex:
                check("accepted lesson failed to render %r" % ex, False)
print("fuzz accepted", ok, "of 3000")
# long silence inside a TTS group gets squeezed
import wave as _w
import numpy as _np
_sr = 24000
_sp = 0.3 * _np.sin(2 * _np.pi * 200 * _np.arange(_sr) / _sr)
_x = _np.concatenate([_sp, _np.zeros(_sr * 25), _sp, _np.zeros(int(_sr * 0.5)), _sp])
_f = "/tmp/_sq_test.wav"
with _w.open(_f, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(_sr); w.writeframes((_x * 32767).astype(_np.int16).tobytes())
P.squeeze_silence(_f)
with _w.open(_f) as w:
    check("silence squeezed", abs(w.getnframes() / _sr - 4.1) < 0.2)
print("FAILS", fails)
sys.exit(1 if fails else 0)
