"""Parse Ye's 'N3 文法 先生ノート' PDF (pdftotext -layout) into n3/grammar.json (one entry per grammar note).
usage: pdftotext -layout note.pdf note.txt && python n3/parse_note.py note.txt n3/grammar.json"""
import json, re, sys

KANA_ONLY = re.compile(r"^[\sぁ-ゖァ-ヺー]+$")
FOOT = re.compile(r"N3 文法\s+先生ノート .*\d+/\d+")
HEAD = re.compile(r"^\s{0,3}(\d{1,2})\s{2,}(〜.+?)(?:\s{2,}(★.*))?\s*$")
SEC = {"①": "meaning", "②": "form", "③": "usage", "④": "examples", "⑤": "mistakes", "⑥": "compare", "⑦": "quiz", "▼": "answers"}


def clean(t):
    return re.sub(r"\s+", " ", t).strip()


def parse(lines):
    notes, cur, sec, cat = [], None, None, ""
    for raw in lines:
        if FOOT.search(raw):
            continue
        line = raw.rstrip()
        m = re.match(r"^\s*([⏰🔗💭🎯📏🗣🔀📌🧩⚖️💬🔁🎌🗂️][^\s]*)?\s*(\S.*\S)\s*$", line)
        h = HEAD.match(line)
        if h and "〜" in h.group(2):
            cur = {"no": int(h.group(1)), "title": clean(h.group(2)), "star": bool(h.group(3)), "category": cat,
                   "meaning": [], "form": [], "usage": [], "examples": [], "mistakes": [], "compare": [], "quiz": [], "answers": []}
            notes.append(cur)
            sec = None
            continue
        if re.search(r"grammar \d+ ခု", line) and notes is not None:
            continue
        if cur is None:
            if line.strip() and not line.strip().startswith(("N3", "Learn", "grammar", "🟢", "💡")):
                cat = clean(line)
            continue
        mk = re.search(r"[①②③④⑤⑥⑦▼]", line[:12])
        if mk:
            sec = SEC[mk.group(0)]
            continue
        s = line.strip()
        if not s or sec is None:
            continue
        if KANA_ONLY.match(s):   # furigana line
            continue
        cur[sec].append(s)
    return notes


def tidy(n):
    out = {"no": n["no"], "title": n["title"], "star": n["star"], "category": n["category"]}
    out["meaning"] = [clean(x) for x in n["meaning"]]
    out["form"] = [re.split(r"\s{2,}", x.strip(), maxsplit=1) for x in n["form"]]
    out["usage"] = [clean(x) for x in n["usage"]]
    ex, last = [], None
    for x in n["examples"]:
        m = re.match(r"^(\d)\.\s*(.+?)\s*(?:\s([A-Z]|なる|する|[^\s]{1,4}))?$", x)
        if x.startswith("🇲🇲") and last is not None:
            last["mm"] = clean(x.replace("🇲🇲", ""))
        elif re.match(r"^\d\.\s", x):
            jp = re.sub(r"^\d\.\s*", "", x)
            tag = ""
            mt = re.match(r"^(.*[。！？!?])\s+(\S{1,4})$", jp)
            if mt:
                jp, tag = mt.group(1), mt.group(2)
            last = {"jp": clean(jp), "tag": tag, "mm": ""}
            ex.append(last)
    out["examples"] = ex
    out["mistakes"] = [clean(x) for x in n["mistakes"] if "❌" in x or "✅" in x]
    out["compare"] = [re.split(r"\s{2,}", x.strip()) for x in n["compare"] if not x.startswith("Grammar")]
    q, cq = [], None
    for x in n["quiz"]:
        if re.match(r"^Q\d", x):
            cq = {"q": clean(re.sub(r"^Q\d\.\s*", "", x)), "choices": []}
            q.append(cq)
        elif cq is not None and re.match(r"^1\s", x):
            cq["choices"] = [clean(c) for c in re.split(r"\s*[1-4]\s+", " " + x) if c.strip()]
    ans = []
    for x in n["answers"]:
        m = re.match(r"^Q(\d)\s*=\s*(\d)\s*(.*)$", x)
        if m:
            ans.append({"q": int(m.group(1)), "answer": int(m.group(2)), "text": clean(m.group(3)), "why": ""})
        elif x.startswith("💭") and ans:
            ans[-1]["why"] = clean(x.replace("💭", ""))
            ans[-1]["last"] = "why"
        elif re.match(r"^[✅❌]", x) and ans:
            mc = re.match(r"^([✅❌])\s*(\d)\s*(\S+)\s*(.*)$", x)
            if mc:
                ans[-1].setdefault("each", []).append({"ok": mc.group(1) == "✅", "n": int(mc.group(2)), "choice": mc.group(3),
                                                       "text": clean(mc.group(4))})
                ans[-1]["last"] = "each"
        elif ans and ans[-1].get("last"):   # wrapped line of the previous explanation
            tgt = ans[-1]["each"][-1] if ans[-1]["last"] == "each" else ans[-1]
            key = "text" if ans[-1]["last"] == "each" else "why"
            prev = tgt[key]
            jp = re.compile("[\u3040-\u30ff\u4e00-\u9fff]")
            sep = "" if prev and jp.match(prev[-1]) and jp.match(x[0]) else " "
            tgt[key] = clean(prev + sep + x)
    for a in ans:
        if 0 < a["q"] <= len(q):
            q[a["q"] - 1].update({"answer": a["answer"], "why": a["why"], "each": a.get("each", [])})
    out["quiz"] = q
    return out


if __name__ == "__main__":
    notes = [tidy(n) for n in parse(open(sys.argv[1], encoding="utf-8").read().splitlines())]
    json.dump(notes, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(notes), "notes")
