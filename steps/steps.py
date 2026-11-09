"""Learn with Rio - "4 Steps" daily video (format D, replaces format A from 2026-11).
Gemini writes a 4-step mini story built on 4 chained sentence patterns (+2 swapped-word examples per step)
-> review -> validate -> TTS -> render -> commit -> post to Telegram (and TikTok/YouTube once ZERNIO_API_KEY exists).
DRY=1 sends the result to the owner's Telegram DM only and does not advance the rotation."""
import datetime as dt, json, os, random, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "daily"))
sys.path.insert(0, os.path.join(ROOT, "story"))
sys.path.insert(0, HERE)
import daily as D  # noqa: E402  (gemini, telegram, zernio, git helpers)
import story as S  # noqa: E402  (ask_json, build_audio: grouped TTS with exact line bounds)
import render_steps as RS  # noqa: E402

DRY = os.environ.get("DRY", "") == "1"
STATE = os.path.join(HERE, "state.json")
MYA = re.compile("[က-႟]")
KANJI = re.compile("[一-鿿々]")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
PUNCT = re.compile(r"[、。！？!?,.\s「」…]")
TRAIL = ("", "よね", "んだよね", "んだよ", "んだ", "よな", "よ", "ね", "な", "の", "わ", "かも", "かな", "なあ")

THEMES = [
    "speaking in front of people", "cooking for yourself", "learning English", "waking up early for a part-time job",
    "riding a bicycle", "making new friends at university", "using keigo at work", "the winter cold",
    "eating natto", "sorting garbage", "crowded trains", "going to an onsen", "singing karaoke",
    "working at a konbini", "living alone", "saving money", "going to the gym", "a part-time job interview",
    "talking on the phone", "learning to swim", "taking an exam", "a morning newspaper delivery job",
    "a first date", "drinking coffee", "sleeping too little", "making onigiri", "shopping at a 100-yen shop",
    "watching anime without subtitles", "texting a crush on LINE", "going to the hospital in Japan",
    "getting lost in a big train station", "ordering at a ramen ticket machine", "dancing at a festival", "camping for the first time",
    "taking photos for Instagram", "playing an online game with strangers", "learning to cook curry from a friend's mom",
    "being afraid of dogs", "talking to a crush", "dyeing your hair", "a part-time job at a cafe", "drawing pictures",
    "playing the guitar", "riding a roller coaster", "spicy food", "eating sushi with your hands", "using chopsticks",
    "making a speech at a wedding", "being shy at a drinking party", "living with a roommate", "keeping your room clean",
    "learning to drive", "taking the night bus", "climbing Mt. Fuji", "the summer heat", "mosquitoes", "earthquakes",
    "writing in a diary", "reading manga in Japanese", "speaking on Instagram Live", "TikTok dancing", "making a YouTube video",
    "taking care of a cat", "growing vegetables", "getting up for sunrise", "running a marathon", "studying at a cafe",
    "asking for directions", "saying no to a senpai", "handling a customer complaint at work", "fixing your own bike",
    "waiting for a LINE reply", "buying clothes online", "a haircut that went wrong", "trying matcha sweets",
]

GEN = """You write scripts for "Learn with Rio ♡", a channel that teaches REAL spoken Japanese to Burmese (Myanmar) people living in Japan.
Format "4 Steps": Rio (Japanese young man, 20, relaxed and friendly) tells a tiny personal story in exactly 4 sentences.
Each sentence is built on a fixed sentence pattern, and the 4 patterns chain into a story. Viewers learn to talk about THEIR OWN life
by swapping the words inside the slots. After each of Rio's sentences, two example sentences reuse the same pattern with different words,
each example thread continuing its own mini story across the 4 steps (example 1 always about one topic, example 2 always about another topic).

Today's 4 patterns (〜 marks a slot; the text outside the slots must be used EXACTLY, character for character):
@@ARC@@
Story idea for Rio's sentences (inspiration, make it natural and a little warm or funny; if it does not fit the patterns, pick a related everyday situation that does): @@THEME@@
Do NOT reuse these past titles, hooks or their stories, and do not reuse their ideas or example topics: @@AVOID@@
Make today's story feel fresh and interesting: a concrete, relatable situation with a small surprise or a warm/funny detail.

Rules:
- In every sentence ("main" and both "ex"), write the pattern text exactly and put the words that fill each slot inside ASCII square brackets [like this].
  Replacing every [..] with 〜 must give exactly the pattern (punctuation 、。！？ may differ). You may add one sentence-final particle
  (よ, ね, よね, な, んだ) at the very end, AFTER the pattern and OUTSIDE the brackets, nothing else. End every sentence with 。 or ！ or ？.
  Slot words must be natural Japanese that grammatically fit:
  〜てみたら needs a verb te-stem: [作っ]てみたら, [読ん]でみたら (て may become で, た may become だ, ちゃ may become じゃ: [飲ん]じゃった);
  〜ようになってきた needs a potential/plain verb: [自分で作れる]ようになってきた; 〜ようとしたら: [寝]ようとしたら, [帰ろ]うとしたら;
  〜せいで / 〜おかげで: [雨の]せいで, [先輩の]おかげで, [寝坊した]せいで; 〜をきっかけに: [アニメ]をきっかけに.
- Sentences are short and natural (max 32 Japanese characters without brackets), casual spoken style young people really use, never textbook.
- The 4 main sentences make one coherent little story; example 1's 4 sentences make one coherent mini story about ex_tags[0];
  example 2's 4 sentences make one about ex_tags[1]. ex_tags are short Japanese topic words (2-4 characters, e.g. 料理, 漢字, バイト).
- EASY WORDS ONLY (Ye 2026-11-06: "hook and wording are too hard"): a beginner must understand every word at once. Use only JLPT N5-N4
  everyday words (好き, 毎日, 友達, 作る, 話す, 寝る, 起きる, 食べる, 楽しい, 寒い, 高い, 部屋, 電車, お金, 時間 ...). NO N3-N1 words and no rare
  kanji at all (bad: 暖房, 毛布, 電池, 節約, 貯金箱, 雑草, 怠け者 - say it with easy words instead, e.g. エアコン, お金をためる).
  Short sentences: Yui's lines max 14 characters, Rio's lines max 22 characters, the hook max 12 characters. Never use formal, written or rare words such as 日課, 克服, 継続,
  実践, 達成, 徐々に, and avoid rare kanji. Keep sentences SHORT (about 18 characters, max 28). The same for hook and title.
- kana = the full reading, hiragana for kanji, katakana words stay katakana (バイト, スマホ), WITHOUT brackets, matching the Japanese exactly.
  Put a space only between phrases (bunsetsu), never before particles: まえは、ひとまえで はなすのが にがてだった。 (NOT まえ は、 ひと まえ で).
- mm = natural, short, spoken-style Burmese (correct Unicode, no double quotes) meaning of the sentence, in simple everyday words
  (no literary or bookish Burmese). Burmese must sound soft, warm and friendly, like close friends chatting: never harsh, rude, shocking
  or scary words, never strong exaggerations, and NEVER brackets [ ] or other symbols inside Burmese (brackets are only for Japanese slots). Rio says main and ex[1] (a young man),
  Yui says ex[0] (a young woman): if a pronoun or polite ending is needed, use ကျွန်တော် for Rio and ကျွန်မ for Yui.
- pattern_mm = short Burmese gloss of the pattern keeping ~ for the slots, e.g. 前は、〜が苦手だった = အရင်က ~ ကို သိပ်မတော်ခဲ့ဘူး.
- hook = the first 2 seconds of the video, the most important line. Like Ye's favourite 「勉強するつもりだったんだけど…」, it is Rio's own
  FIRST LINE of today's story and it must already promise that something went wrong or surprising: a plan or expectation + けど/のに/はずが/
  ようとしたら, cut off with … right before the funny part, so the viewer must keep watching to hear what happened.
  Good: 勉強するつもりだったのに… / 早く寝たかったのに… / やせたかったのに… / 朝ごはんを作ったら… / 告白しようとしたら…
  Bad (no promise of a twist, boring): 最近、トマト育ててるんだけど… / 今日は料理の話。 Never address the viewer, never a greeting or a lesson title.
  Max 12 characters, only N5-N4 words. With kana and mm (Burmese also cut off with …, same feeling, soft and natural).
- title = Japanese title of Rio's story like 人前で話せるようになった話 (max 16 characters); title_mm its Burmese.
- caption = Burmese, max 180 characters, 1-2 emojis, mentions the 4 patterns chained today.
- No emojis, 笑, w or the 〜 symbol inside any Japanese sentence.

CONVERSATION + COMEDY (most important, Ye 2026-11-03): the 4 main sentences are Rio's answers in a short FUNNY chat with Yui
(Japanese young woman, 20, bright, teasing). Before each main sentence Yui says one short line "q" (max 18 characters, casual, a question
or reaction that makes Rio's next sentence natural: e.g. 富士山、登ったって本当？ / えー、うそ！それで？ / で、どうしたの？ / は？上まで行かなかったの？).
After step 4 add "ending": exactly 2 lines: Yui's sharp tsukkomi (それ、ラーメンの話じゃん！) and Rio's short deadpan punchline
(max 15 characters, e.g. …来年は、ちゃんと登る。). A Burmese viewer around 20 must laugh: build up with a surprise, Rio's story
takes an unexpected turn, never a moral, never a polite ending. Think of 3 premises first and keep the funniest (put it in "idea").
q and ending lines: no brackets, no 〜, with kana and mm like the other lines. Do not write names in the lines (no りお / ゆい).

Output ONLY JSON with exactly this structure:
{"idea": "", "title": "", "title_mm": "", "hook": {"jp": "", "kana": "", "mm": ""}, "ex_tags": ["", ""],
 "steps": [{"pattern": "(copy of pattern 1)", "pattern_mm": "", "q": {"jp": "", "kana": "", "mm": ""}, "main": {"jp": "", "kana": "", "mm": ""},
            "ex": [{"jp": "", "kana": "", "mm": ""}, {"jp": "", "kana": "", "mm": ""}]}  (4 steps)],
 "ending": [{"who": "Yui", "jp": "", "kana": "", "mm": ""}, {"who": "Rio", "jp": "", "kana": "", "mm": ""}],
 "caption": ""}"""

REV = """You are a strict editor, a native speaker of both Japanese and Burmese (Myanmar). Below is a "4 Steps" script (JSON) for a channel teaching
real spoken Japanese to Burmese learners. Check EVERYTHING and fix every problem:
1. Every Japanese sentence is 100% natural Japanese that young people really say, grammatically correct, and fits its slot pattern.
2. Each sentence uses its step's pattern text exactly, with the slot words inside [brackets]; replacing each [..] with 〜 gives the pattern
   (only punctuation and one final particle よ/ね/よね/な may differ). Allowed patterns: @@ARC@@
3. Rio's 4 main sentences tell one coherent story; example 1's 4 sentences one mini story about ex_tags[0]; example 2's about ex_tags[1].
4. Every kana is the exact full reading (hiragana for kanji, katakana words stay katakana, spaces only between phrases, no brackets, no kanji).
4b. Sentence-final particles (よ, ね ...) are outside the brackets; brackets are ASCII [ ].
5. All Burmese is correct, natural, soft and friendly spoken-style Unicode Burmese (no harsh or scary words, no brackets or symbols, no double quotes) and matches the Japanese.
5b. EASY WORDS: replace every word that is harder than JLPT N4 or formal/written (e.g. 日課, 克服, 習慣, 継続, 達成) with an easy everyday word
   a beginner knows, in hook, title and all sentences; make Burmese simple spoken words too. Keep each sentence short (about 20 characters).
5c. CONVERSATION + COMEDY: each step has Yui's short line q (max 18 characters) that leads naturally into Rio's main sentence; "ending" has
   exactly 2 lines (Yui tsukkomi, Rio deadpan punchline max 15 characters). Honestly rate how funny it is for a Burmese viewer around 20 (1-10);
   if below 9, rewrite q lines, Rio's slot words and the ending to be much funnier (unexpected turn, callback), keeping every pattern exact.
6. Max 32 characters per sentence (without brackets). No emojis, 笑 or 〜 inside sentences. title max 16, ex_tags 2-4 characters.
6b. HOOK: it must be Rio's relatable first line of the story that already promises a twist (plan/expectation + けど/のに/はずが/ようとしたら),
   cut off with … right before the funny part (like 勉強するつもりだったんだけど…; NOT a plain statement like 最近、トマト育ててるんだけど…),
   max 16 characters, not addressed to the viewer. Rate 1-10 how strongly a young Burmese TikTok viewer would stop scrolling; if below 9, rewrite it.
@@ERRORS@@
Output ONLY the full corrected JSON with exactly the same structure.

JSON:
@@JSON@@"""


EASY_KANJI = set('一二三四五六七八九十百千万円年月日時分半週今先毎午前後上下左右中外東西南北名人子女男学生校友会社国語本話読書聞見言行来出入食飲買休立山川田天気雨電車駅道店長高安新古大小白何多少早間手足目口耳花水火木金土空家父母近遠親兄弟姉妹私自同所去朝昼夜夕方晩起寝着帰待持使作住知思考教習勉強試験問題答質説明意味字文漢映画音楽歌写真旅仕事場銀病院医者薬体頭顔声首心色赤青黒茶犬猫鳥魚肉野菜料理牛豚味品物服洋和室部屋窓門台洗弁当飯注暑寒冷熱重軽弱短暗広悪良好楽悲痛速遅静便利不特別急最初終始止乗降運転走歩通送届開閉切貸借払売返計歳才代度番号回発集末曜昨夏冬春秋頃全以内主力元活世界地図町村市区県都京員究英工業様自転飛機港館合格準備予定約束忘覚泳遊踊祭戻授宿題鉛筆紙箱誕達緒結局然丈夫頑張疲実際心配楽好嫌寂怖笑泣怒困夢会社員彼週末今度一回次的無温晴曇雪風引押違助調')


def hard_kanji(text):
    return sorted(set(c for c in text if KANJI.match(c) and c not in EASY_KANJI))


def norm(t):
    return PUNCT.sub("", t.replace("～", "〜"))


def brackets(t):
    return t.replace("［", "[").replace("］", "]").replace("【", "[").replace("】", "]")


def pattern_re(pattern):
    """Regex for a filled pattern (slots = 〜). Right after a slot, sound changes of the verb are allowed:
    て→で (読んで), た→だ (休んだら), ちゃ→じゃ (飲んじゃった), よう→う (帰ろうとしたら)."""
    parts = norm(pattern).split("〜")
    out = [re.escape(parts[0])]
    for fixed in parts[1:]:
        alt = re.escape(fixed)
        for a, b in (("ちゃ", "(?:ちゃ|じゃ)"), ("て", "[てで]"), ("た", "[ただ]"), ("よう", "よ?う")):
            if fixed.startswith(a):
                alt = b + re.escape(fixed[len(a):])
                break
        out.append("〜" + alt)
    return re.compile("".join(out) + "(?:" + "|".join(TRAIL) + ")")


def fits(sentence, pattern):
    """True if sentence (with [slots]) follows pattern exactly, allowing punctuation, verb sound changes and a final particle."""
    sentence = brackets(sentence)
    if sentence.count("[") != sentence.count("]") or re.search(r"\[[^\]]*\[|\[\s*\]|\][^\[]*\]", sentence):
        return False
    filled = norm(re.sub(r"\[[^\]]*\]", "〜", sentence))
    return bool(pattern_re(pattern).fullmatch(filled))


def validate(s, arc):
    err = []
    try:
        for k in ("title", "title_mm", "hook", "steps", "caption", "ex_tags"):
            if not s.get(k):
                err.append("field %s is missing or empty" % k)
        if err:
            return err
        if len(s["steps"]) != 4:
            return ["there must be exactly 4 steps, there are %d" % len(s["steps"])]
        tags = s["ex_tags"]
        if not isinstance(tags, list) or len(tags) != 2 or not all(isinstance(t, str) and 1 <= len(t) <= 6 for t in tags) or tags[0] == tags[1]:
            err.append("ex_tags must be 2 different short Japanese topic words")
        if len(s["title"]) > 18:
            err.append("title too long (max 16 characters)")
        h = s["hook"]
        if not h.get("jp") or len(h["jp"]) > 30 or EMOJI.search(h["jp"]) or "〜" in h["jp"]:
            err.append("hook must be one short line (max 26 characters) without emoji or 〜")
        if KANJI.search(h.get("jp", "")) and (not h.get("kana") or KANJI.search(h["kana"])):
            err.append("hook kana must be the full kana reading")
        if not MYA.search(h.get("mm", "")):
            err.append("hook needs Burmese mm")
        for k, st in enumerate(s["steps"]):
            pat = arc[k]
            if norm(st.get("pattern", "")) != norm(pat):
                err.append("step %d pattern must be exactly %s" % (k + 1, pat))
            st["pattern"] = pat
            if not MYA.search(st.get("pattern_mm", "")):
                err.append("step %d needs Burmese pattern_mm" % (k + 1))
            ex = st.get("ex") or []
            if len(ex) != 2:
                err.append("step %d must have exactly 2 examples" % (k + 1))
            for name, l in [("main", st.get("main") or {})] + [("example %d" % (j + 1), e) for j, e in enumerate(ex)]:
                jp = l["jp"] = brackets(l.get("jp", ""))
                where = "step %d %s" % (k + 1, name)
                if not fits(jp, pat):
                    err.append("%s does not follow the pattern %s with [slot] words: %s" % (where, pat, jp))
                elif "[" not in jp and "〜" in pat:
                    err.append("%s has no [slot] words: %s" % (where, jp))
                pj = RS.plain(jp)
                if len(pj) > 34:
                    err.append("%s too long (max 32 characters): %s" % (where, pj))
                if EMOJI.search(pj) or "〜" in pj or re.search(r"笑(?![いうえわっ])", pj):
                    err.append("%s: no emoji, 笑 or 〜 inside: %s" % (where, pj))
                kana = l.get("kana", "")
                if "[" in kana or "]" in kana:
                    l["kana"] = kana = RS.plain(kana)
                if KANJI.search(pj) and (not kana or KANJI.search(kana)):
                    err.append("%s kana must be the full kana reading (no kanji): %s" % (where, pj))
                if not MYA.search(l.get("mm", "")):
                    err.append("%s needs a Burmese translation: %s" % (where, pj))
        if s.get("mode") == "talk" or any(st.get("q") for st in s["steps"]):
            talk_lines = [("step %d q" % (k + 1), st.get("q") or {}) for k, st in enumerate(s["steps"])]
            end = s.get("ending") or []
            if len(end) != 2:
                err.append("ending must have exactly 2 lines (Yui tsukkomi, Rio punchline)")
            talk_lines += [("ending %d" % (i + 1), e) for i, e in enumerate(end)]
            for where, l in talk_lines:
                jp = l.get("jp", "") if isinstance(l, dict) else ""
                if not jp:
                    err.append("%s is missing" % where)
                    continue
                if len(jp) > 24 or "[" in jp or "〜" in jp or EMOJI.search(jp):
                    err.append("%s must be short (max 18 characters), without brackets, 〜 or emoji: %s" % (where, jp))
                if KANJI.search(jp) and (not l.get("kana") or KANJI.search(l.get("kana", ""))):
                    err.append("%s kana must be the full kana reading: %s" % (where, jp))
                if not MYA.search(l.get("mm", "")):
                    err.append("%s needs Burmese mm: %s" % (where, jp))
        # easy words only (Ye 2026-11-06: hook and wording were too hard): kanji outside N5-N4 (+ the pattern text itself) are not allowed
        fixed = set(c for st in s["steps"] for c in st.get("pattern", ""))
        texts = [("hook", s["hook"].get("jp", ""))] + [("title", s.get("title", ""))]
        for k, st in enumerate(s["steps"]):
            texts += [("step %d q" % (k + 1), (st.get("q") or {}).get("jp", "")), ("step %d main" % (k + 1), st["main"].get("jp", "")),
                      ("step %d example 1" % (k + 1), (st.get("ex") or [{}])[0].get("jp", ""))]
        texts += [("ending %d" % (i + 1), e.get("jp", "")) for i, e in enumerate(s.get("ending") or []) if isinstance(e, dict)]
        for where, t in texts:
            bad = [c for c in hard_kanji(t) if c not in fixed]
            if bad:
                err.append("%s uses difficult kanji/words (%s) - replace them with easy everyday words a beginner knows (too hard: %s)"
                           % (where, "".join(bad), t))
        if len(RS.plain(s["hook"].get("jp", ""))) > 14:
            err.append("hook too long: max 12 characters, very easy words")
        if not MYA.search(s["caption"]):
            err.append("caption must be written in Burmese")
    except Exception as e:  # malformed structure
        err.append("JSON structure is wrong: %s" % e)
    return err


def finish(s):
    """Speakers (fixed: Rio tells his story, Yui says example 1, Rio example 2) and Burmese punctuation."""
    if any(st.get("q") for st in s["steps"]):
        s["mode"] = "talk"
        for st in s["steps"]:
            st["q"]["who"] = "Yui"
        for i, e in enumerate(s.get("ending", [])):
            e["who"] = e.get("who") if e.get("who") in ("Rio", "Yui") else ("Yui" if i == 0 else "Rio")
    for st in s["steps"]:
        st["main"]["who"] = "Rio"
        st["ex"][0]["who"] = "Yui"
        st["ex"][1]["who"] = "Rio"

    def fix(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("mm", "pattern_mm", "title_mm", "caption") and isinstance(v, str):
                    v = re.sub(r"[\[\]［］【】「」『』]", "", v).replace("。", "။").replace("、", "၊")
                    o[k] = v.replace("！", "!").replace("？", "?").replace('"', "")
                else:
                    fix(v)
        elif isinstance(o, list):
            for v in o:
                fix(v)
    fix(s)
    return s


POOL = os.path.join(HERE, "pattern_pool.json")
NEED = {"start": 1, "middle": 2, "end": 1}


def available(st):
    """Unused frames per category (Ye 2026-11-03: patterns must never repeat). Resets only when a category runs out."""
    pool = json.load(open(POOL, encoding="utf-8"))
    used = set(st.get("used_patterns", []))
    avail = {c: [p for p in pool[c] if p not in used] for c in NEED}
    if any(len(avail[c]) < n for c, n in NEED.items()):
        D.WARN.append("pattern pool used up - starting again from the top; please add new frames to steps/pattern_pool.json")
        st["used_patterns"] = []
        avail = {c: list(pool[c]) for c in NEED}
    return avail


def pool_text(avail):
    return ("Choose them yourself from these lists of patterns that were NEVER used before on the channel. Step 1 from START, steps 2 and 3 "
            "from MIDDLE (two different ones), step 4 from END. Pick the 4 that chain into the most natural and funniest story; "
            "copy each chosen pattern exactly into \"pattern\".\nSTART: " + " / ".join(avail["start"]) +
            "\nMIDDLE: " + " / ".join(avail["middle"]) + "\nEND: " + " / ".join(avail["end"]))


def pool_errors(s, avail):
    err = []
    try:
        pats = [st.get("pattern", "") for st in s["steps"]]
    except Exception:
        return ["steps are missing"]
    want = ["start", "middle", "middle", "end"]
    for k, (p, c) in enumerate(zip(pats, want)):
        hit = [x for x in avail[c] if norm(x) == norm(p)]
        if not hit:
            err.append("step %d pattern %s must be copied exactly from the %s list (patterns already used on the channel are not allowed)"
                       % (k + 1, p, c.upper()))
        else:
            s["steps"][k]["pattern"] = hit[0]
    if len(set(norm(p) for p in pats)) != len(pats):
        err.append("the 4 patterns must all be different")
    return err


def make_lesson(arc, theme, avoid):
    """arc: a fixed list of 4 patterns, or a dict of available frames per category (pool mode)."""
    pool = isinstance(arc, dict)
    arc_txt = pool_text(arc) if pool else "\n".join("%d. %s" % (i + 1, p) for i, p in enumerate(arc))
    prompt = GEN.replace("@@ARC@@", arc_txt).replace("@@THEME@@", theme).replace("@@AVOID@@", "、".join(avoid[-80:]) or "(none)")
    rev = REV.replace("@@ARC@@", "keep the 4 chosen patterns (each copied exactly from these lists) - " + pool_text(arc) if pool else " / ".join(arc))

    def check(x):
        if pool:
            e = pool_errors(x, arc)
            if e:
                return e
            return validate(x, [st["pattern"] for st in x["steps"]])
        return validate(x, arc)
    best, best_err = None, None
    for attempt in range(2):
        try:
            s = S.ask_json(prompt)
        except Exception as e:
            D.log("generation failed", e)
            continue
        try:
            s = S.ask_json(rev.replace("@@ERRORS@@", "").replace("@@JSON@@", json.dumps(s, ensure_ascii=False)))
        except Exception as e:
            D.log("review failed", e)
        for fix in range(3):
            err = check(s)
            D.log("attempt", attempt, "fix", fix, "errors", err)
            if not err:
                return s
            if best_err is None or len(err) < len(best_err):
                best, best_err = s, err
            extra = "7. IMPORTANT - an automatic check found these problems, fix ALL of them:\n- " + "\n- ".join(err)
            try:
                s = S.ask_json(rev.replace("@@ERRORS@@", extra).replace("@@JSON@@", json.dumps(s, ensure_ascii=False)))
            except Exception as e:
                D.log("fix failed", e)
    if best_err is None:
        raise RuntimeError("Gemini gave no usable lesson")
    soft = [e for e in best_err if " too long " in e or "difficult kanji" in e or "hook too long" in e]
    if len(soft) != len(best_err):
        raise RuntimeError("lesson failed validation: %s" % best_err)
    D.WARN.extend(best_err)
    return best


def squeeze_silence(path, keep=0.6, longest=0.9, thr=0.012):
    """Gemini TTS sometimes leaves a very long silence inside a group (seen: 25 s). Shorten any pause over `longest` s to `keep` s."""
    import wave
    import numpy as np
    with wave.open(path, "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    hop = int(sr * 0.02)
    m = len(x) // hop
    if m < 3:
        return 0.0
    loud = np.abs(x[:m * hop]).reshape(m, hop).max(1) > thr
    out, i, cut = [], 0, 0.0
    while i < m:
        j = i
        while j < m and loud[j] == loud[i]:
            j += 1
        seg = x[i * hop:j * hop]
        if not loud[i] and (j - i) * hop / sr > longest and i > 0 and j < m:
            k = int(keep * sr / 2)
            out += [seg[:k], seg[-k:]]
            cut += len(seg) / sr - keep
        elif not loud[i] and (i == 0 or j == m) and len(seg) / sr > 0.3:
            # leading/trailing silence of a TTS group (seen: 2.3 s dead air right after the hook) -> 0.15 s
            k = int(0.15 * sr)
            out.append(seg[-k:] if i == 0 else seg[:k])
            cut += len(seg) / sr - 0.15
        else:
            out.append(seg)
        i = j
    out.append(x[m * hop:])
    if cut > 0:
        y = (np.clip(np.concatenate(out), -1, 1) * 32767).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())
        D.log("squeezed %.1f s of silence out of %s" % (cut, os.path.basename(path)))
    return cut


VOICE_MODELS = ["gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"]
_gemini = D.gemini


def patient_gemini(models, body, tries=3):
    """TTS: wait longer on 'too many requests' instead of switching to a model with a different voice."""
    first = models if isinstance(models, str) else (models[0] if models else "")
    return _gemini(models, body, tries=6 if "tts" in first else tries)


D.gemini = patient_gemini

_tts_lines = S.tts_lines


def tts_lines_squeezed(prompt_multi, prompt_one, turns, path):
    _tts_lines(prompt_multi, prompt_one, turns, path)
    squeeze_silence(path)


S.tts_lines = tts_lines_squeezed

P_MULTI = ("TTS the following lines by two close Japanese friends around 20 years old, chatting. Rio: a young man, relaxed and friendly, "
           "telling a short funny story about himself. Yui: a young woman, bright, friendly and a bit teasing, reacting to him or saying her own "
           "example sentence. "
           "Speak naturally like real young people, normal natural speed, very clear. Do NOT act and do NOT exaggerate; not like an "
           "announcer, a teacher or anime. Leave a clear pause of about one second between lines.\n")
P_ONE = S.P_ONE


def transcript(s):
    out = ["🎬 %s" % s["title"], s.get("title_mm", ""), ""]
    for k, st in enumerate(s["steps"]):
        out.append("%s %s — %s" % ("①②③④"[k], st["pattern"], st.get("pattern_mm", "")))
        m = st["main"]
        if st.get("q"):
            out.append("Yui: " + st["q"]["jp"] + "  (" + st["q"].get("mm", "") + ")")
        out.append("Rio: " + m["jp"])
        if m.get("kana"):
            out.append("   " + m["kana"])
        out.append("   🇲🇲 " + m["mm"])
        for j, e in enumerate(st["ex"]):
            out.append("  %s: %s  (%s)" % (s["ex_tags"][j], RS.plain(e["jp"]), e["mm"]))
        out.append("")
    out.append("🗣 つなげて話すと…")
    out.append("\n".join(RS.plain(st["main"]["jp"]) for st in s["steps"]))
    out += ["", "💡 [ ] ထဲက စကားလုံးတွေကို ကိုယ့်အကြောင်းနဲ့ ပြောင်းပြီး comment မှာ ရေးပြကြနော်!"]
    out += ["", "#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui"]
    return "\n".join(out)[:4000]


def post_n3(st, key, now):
    sys.path.insert(0, os.path.join(ROOT, "n3"))
    import n3 as N3
    vid, title, cap, secs, tr = N3.daily(st, key, DRY)
    if not DRY:
        st["done"].append({"key": key, "title": title, "n3": st.get("n3_last"), "date": now.strftime("%Y-%m-%d")})
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.chdir(ROOT)
    old = sorted(f for f in os.listdir("videos") if re.match(r"FT?\d+\.mp4$", f))
    for f in old[:-10]:
        os.remove(os.path.join("videos", f))
    D.push("steps %s" % key, ["text", "videos", "steps/state.json", "n3/out"])
    chat = D.OWNER if DRY else D.CHANNEL
    if not D.tg("sendVideo", {"chat_id": chat, "caption": ("🎬 %s\n%s" % (title, cap))[:1020], "supports_streaming": "true"},
                {"video": open(vid, "rb")}):
        D.WARN.append("Telegram sendVideo failed")
    D.tg("sendMessage", {"chat_id": chat, "text": tr})
    summary = "✅ N3 video %s %s\n%s (%ds)\n%s" % ("TEST" if DRY else "posted to Telegram", key, title, secs,
                                                 "(test only - not posted)" if DRY else "Facebook / TikTok / YouTube: Make posts it at 19:00")
    if D.WARN:
        summary += "\n(small problems: %s)" % "; ".join(D.WARN)[:600]
    if D.OWNER:
        D.tg("sendMessage", {"chat_id": D.OWNER, "text": summary})
    D.log(summary)


def post_n3chat(st, key, now):
    """Ye 11/09: 2 N3 chat-style videos a day (A = <key> at 19:00, B = <key>b: TikTok/YouTube 12:00 next day)."""
    sys.path.insert(0, os.path.join(ROOT, "n3"))
    import chat3 as C3
    res = C3.daily(st, key, DRY)
    if not DRY:
        for vid, title, cap, secs, tr, no, k in res:
            st["done"].append({"key": k, "title": title, "n3chat": no, "date": now.strftime("%Y-%m-%d")})
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.chdir(ROOT)
    old = sorted(f for f in os.listdir("videos") if re.match(r"FT?\d+b?\.mp4$", f))
    for f in old[:-12]:
        os.remove(os.path.join("videos", f))
    # B first: Make reads the newest commit on text/ and takes its message "steps <key>" as video A
    D.push("steps %s" % key, ["text", "videos", "steps/state.json"])
    chat = D.OWNER if DRY else D.CHANNEL
    for vid, title, cap, secs, tr, no, k in res:
        if not D.tg("sendVideo", {"chat_id": chat, "caption": ("🎬 %s\n%s" % (title, cap))[:1020], "supports_streaming": "true"},
                    {"video": open(vid, "rb")}):
            D.WARN.append("Telegram sendVideo failed " + k)
        D.tg("sendMessage", {"chat_id": chat, "text": tr})
    summary = "✅ N3 chat videos %s\n%s\n%s" % ("TEST" if DRY else "posted to Telegram",
                                              "\n".join("%s No.%d %s (%ds)" % (k, no, t, s) for _, t, _, s, _, no, k in res),
                                              "(test only - not posted)" if DRY else "Make 19:00: A -> FB/TikTok/YouTube, B -> FB now, TikTok/YouTube 12:00 tomorrow")
    if D.WARN:
        summary += "\n(small problems: %s)" % "; ".join(D.WARN)[:600]
    if D.OWNER:
        D.tg("sendMessage", {"chat_id": D.OWNER, "text": summary})
    D.log(summary)


def main():
    ms = D.list_models()
    if ms:
        D.TEXT_CHAIN = [m for m in D.TEXT_CHAIN if m in ms] or [D.pick(ms, "none", r"^gemini-[\d.]+-(pro|flash)")]
        D.FAST_CHAIN = [m for m in D.FAST_CHAIN if m in ms] or [D.pick(ms, "none", r"^gemini-[\d.]+-flash")]
        D.TTS_CHAIN = [m for m in D.TTS_CHAIN if m in ms] or [D.pick(ms, "none", r"tts", avoid=())]
    # Ye (2026-11-03): always use the Rio/Yui voice from F261102 = gemini-2.5-flash-preview-tts (Achird / Laomedeia).
    # Other TTS models sound different, so they are only a last resort.
    D.TTS_CHAIN = [m for m in VOICE_MODELS if not ms or m in ms] + [m for m in D.TTS_CHAIN if m not in VOICE_MODELS]
    vf = os.path.join(ROOT, "story", "voices.json")
    if os.path.exists(vf):
        vv = json.load(open(vf))
        for c in D.VOICES["multiSpeakerVoiceConfig"]["speakerVoiceConfigs"]:
            c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"] = vv.get(c["speaker"], c["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
    D.log("using", D.TEXT_CHAIN, D.TTS_CHAIN, D.VOICES)
    st = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"done": []}
    now = dt.datetime.now(D.JST)
    branch = os.environ.get("GITHUB_REF_NAME", "main")
    if not DRY and branch != "main":
        raise RuntimeError("real posting only from main (this is %s); use DRY in steps/trigger.txt" % branch)
    if os.environ.get("GITHUB_EVENT_NAME") == "schedule" and not 17 <= now.hour <= 23:
        D.log("backup cron started at %s JST - too late/early to post, skipping" % now.strftime("%H:%M"))
        return
    if not DRY and any(d.get("date") == now.strftime("%Y-%m-%d") and not d.get("skipped") for d in st["done"]):
        D.log("today's video was already posted - nothing to do")  # GitHub cron can start hours late; never post twice a day
        return
    key = ("FT" + now.strftime("%y%m%d%H%M")) if DRY else ("F" + now.strftime("%y%m%d"))
    if any(d["key"] == key for d in st["done"]):
        key = "F" + now.strftime("%y%m%d%H%M")
    if st.get("format") == "n3chat":  # Ye 11/09: Rio & Yui chat-style N3 video, 2 a day
        return post_n3chat(st, key, now)
    if st.get("format") == "n3":  # Ye 11/06: one N3 grammar from his note per day (Rio先生 video) instead of 4 Steps
        return post_n3(st, key, now)
    avail = available(st)
    # never repeat a story theme until all of them were used (Ye 2026-11-01: "content မထပ်စေနဲ့")
    used = set(st.get("themes", []))
    fresh = [t for t in THEMES if t not in used] or list(THEMES)
    if len(fresh) == len(THEMES):
        st["themes"] = []
    theme = random.choice(fresh)
    D.log("key", key, "unused patterns", {c: len(v) for c, v in avail.items()}, "theme", theme)
    inp = os.environ.get("STEPS_INPUT", "")
    use_inp = bool(inp and os.path.exists(os.path.join(ROOT, inp)))
    if use_inp:
        s = json.load(open(os.path.join(ROOT, inp), encoding="utf-8"))
        arc = [x["pattern"] for x in s["steps"]]
        D.log("using prepared lesson", inp, "errors", validate(s, arc))
    else:
        s = make_lesson(avail, theme, [d["title"] for d in st["done"]] + [d.get("hook", "") for d in st["done"] if d.get("hook")]
                        + ["example topic " + t for d in st["done"][-6:] for t in d.get("tags", [])])
    s = finish(s)
    os.makedirs(os.path.join(ROOT, "text"), exist_ok=True)
    jpath = os.path.join(ROOT, "text", key + ".json")
    json.dump(s, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # small text file in the old ===SECTION=== layout: the Make scenario "Rio ④" reads it to post to Facebook / TikTok / YouTube
    with open(os.path.join(ROOT, "text", key + ".txt"), "w", encoding="utf-8") as f:
        f.write("===TITLE===\n%s\n===CAPTION===\n%s\n===END===\n" % (s["title"], s["caption"].strip()))
    work = os.path.join(ROOT, "work", "steps")
    os.makedirs(work, exist_ok=True)
    main_wav = os.path.join(work, "main.wav")
    S.build_audio(RS.audio_groups(s), P_MULTI, P_ONE, main_wav)
    os.makedirs(os.path.join(ROOT, "videos"), exist_ok=True)
    vid = os.path.join("videos", key + ".mp4")
    secs = RS.render(jpath, main_wav, os.path.join(ROOT, vid))
    if not DRY and not use_inp:
        pats = [x["pattern"] for x in s["steps"]]
        st["done"].append({"key": key, "title": s["title"], "hook": s["hook"]["jp"], "tags": s.get("ex_tags", []), "patterns": pats,
                           "date": now.strftime("%Y-%m-%d")})
        st.setdefault("themes", []).append(theme)
        st.setdefault("used_patterns", []).extend(p for p in pats if p not in st["used_patterns"])
        json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.chdir(ROOT)
    old = sorted(f for f in os.listdir("videos") if re.match(r"FT?\d+\.mp4$", f))
    for f in old[:-10]:
        os.remove(os.path.join("videos", f))
    D.push("steps %s" % key, ["text", "videos", "steps/state.json"])

    title, cap = s["title"], s["caption"]
    chat = D.OWNER if DRY else D.CHANNEL
    if not D.tg("sendVideo", {"chat_id": chat, "caption": ("🎬 %s\n%s" % (title, cap))[:1020], "supports_streaming": "true"}, {"video": open(vid, "rb")}):
        D.WARN.append("Telegram sendVideo failed")
    D.tg("sendMessage", {"chat_id": chat, "text": transcript(s)})
    ok = {}
    if not DRY and D.ZKEY:  # normally empty: TikTok/YouTube are posted by the Make scenario "Rio ④" at 19:00
        import time
        url = D.REPO_RAW + vid
        time.sleep(20)
        tags = "#ဂျပန်စာ #日本語 #LearnWithRio #RioAndYui #リアル日本語 #JLPT #fyp"
        ok["tiktok"] = D.zernio({"content": "🎬 %s\n%s\n\n%s" % (title, cap, tags), "mediaItems": [{"type": "video", "url": url}],
                                 "platforms": [{"platform": "tiktok", "accountId": D.TIKTOK_ID}],
                                 "tiktokSettings": {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": True,
                                                    "allow_stitch": True, "content_preview_confirmed": True, "express_consent_given": True},
                                 "publishNow": True})
        ok["youtube"] = D.zernio({"content": "%s\n\n%s" % (cap, transcript(s)[:3000]),
                                  "mediaItems": [{"type": "video", "url": url}],
                                  "platforms": [{"platform": "youtube", "accountId": D.YOUTUBE_ID,
                                                 "platformSpecificData": {"title": ("%s｜4つの文で話そう #shorts" % title)[:100],
                                                                          "visibility": "public", "madeForKids": False,
                                                                          "containsSyntheticMedia": True}}],
                                  "publishNow": True})
    summary = "✅ 4 Steps video %s %s\n%s (%ds)\n%s" % (
        "TEST" if DRY else "posted to Telegram", key, title, secs,
        "(test only - not posted)" if DRY else "Facebook / TikTok / YouTube: Make posts it at 19:00")
    if D.WARN:
        summary += "\n(small problems: %s)" % "; ".join(D.WARN)[:600]
    if D.OWNER:
        D.tg("sendMessage", {"chat_id": D.OWNER, "text": summary})
    D.log(summary)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        D.log("FAILED", type(e).__name__, e)
        if D.OWNER and D.TG:
            D.tg("sendMessage", {"chat_id": D.OWNER, "text": "⚠️ 4 Steps video: error\n%s: %s" % (type(e).__name__, str(e)[:500])})
        raise
