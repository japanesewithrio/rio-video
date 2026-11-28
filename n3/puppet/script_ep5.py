"""Puppet EP.5 — からい？ (Rio cooks mohinga for Mio). python ep.py script_ep5"""
OUT = "puppet_ep5.mp4"
MUSIC = "n3/snd/out/bgm_wholesome.mp3"
BG = {"two": ("pp_bg_room.png", 3), "cu": ("pp_bg_room.png", 8), "moon": "pp_mohinga.png"}
TABLE = True
HOOK = "ဂျပန်မလေးကို မုန့်ဟင်းခါး<br>ချက်ကျွေးကြည့်တဲ့အခါ… 🍜🌶"

EP = [
    dict(who="rio", v="v5_01", shot="two", jp="今日《きょう》は、ミャンマー料理《りょうり》を[作《つく》ったよ]！", mm="ဒီနေ့ မြန်မာ အစားအစာ ချက်ထားတယ်!",
         ex={"rio": dict(smile=1, eye=1.05, look=.6), "mio": dict(look=-.6, eye=1.1, smile=.8)}, pose={"rio": "thumb"}),
    dict(who="mio", v="v5_02", shot="mio", jp="わあ、いいにおい！ これ、なに？", mm="ဝိုး… မွှေးလိုက်တာ! ဒါ ဘာလဲ?",
         ex={"mio": dict(happy=1, smile=1, blush=.4, lookup=.3)}),
    dict(shot="moon", dur=1.8, mm="မုန့်ဟင်းခါး 🍜", sfx="twinkle"),
    dict(who="rio", v="v5_03", shot="rio", jp="モヒンガー。ミャンマーの朝《あさ》ごはんなんだ。", mm="မုန့်ဟင်းခါး။ မြန်မာရဲ့ မနက်စာလေ။",
         ex={"rio": dict(smile=.8, blush=.3, look=-.3)}),
    dict(who="mio", v="v5_04", shot="mio", jp="いただきます！ ん、おいしい！", mm="စားပါမယ်! အင်း… အရသာရှိလိုက်တာ!",
         ex={"mio": dict(smile=1, eye=1.05)}, end={"mio": dict(happy=1, blush=.7)}, pose={"mio": "spoon"}),
    dict(who="rio", v="v5_05", shot="rio", jp="でしょ？ ちょっと[辛《から》いけど、大丈夫《だいじょうぶ》]？", mm="ဟုတ်တယ်မလား? နည်းနည်း စပ်တယ်… ရရဲ့လား?",
         ex={"rio": dict(smile=.7, brow=.4, worry=.3)}),
    dict(who="mio", v="v5_06", shot="mio", jp="うん、ぜんぜん大丈夫《だいじょうぶ》。", mm="အင်း… လုံးဝ ရပါတယ်။",
         ex={"mio": dict(smile=.9, eye=.95)}, post=.6),
    dict(who="mio", v="v5_07", shot="mio", jp="からい！ 水《みず》、水《みず》！", mm="စပ်တယ်!! ရေ… ရေ!", sfx="don", zoom=[1.0, 1.15],
         ex={"mio": dict(eye=1.25, brow=1, worry=1, blush=1.4, sweat=1, shake=1, smile=0)}, pose={"mio": "fan"}),
    dict(who="rio", v="v5_08", shot="two", jp="ごめんごめん！ はい、お水《みず》。", mm="ဆောရီး ဆောရီး! ရော့… ရေ။",
         ex={"rio": dict(happy=1, smile=1, look=.6, bounce=1, shake=.4), "mio": dict(blush=1.3, worry=.8, sweat=1, look=-.6)},
         pose={"rio": "glass", "mio": "fan"}),
    dict(who="mio", v="v5_09", shot="mio", jp="ふう……。でも、[また食《た》べたい]な。", mm="ဖူး… ဒါပေမဲ့ နောက်ထပ် စားချင်သေးတယ်။",
         ex={"mio": dict(eye=.95, smile=.9, blush=.8, lookup=-.3, tilt=-5)}, end={"mio": dict(happy=1, smile=1, blush=1.2, tilt=-8, bounce=.6)}, post=.3),
    dict(who="rio", v="v5_10", shot="rio", jp="ほんと？ じゃあ、また作《つく》るね！", mm="တကယ်လား? ဒါဆို နောက်တစ်ခါ ထပ်ချက်ပေးမယ်!",
         ex={"rio": dict(eye=1.15, brow=.6, smile=.8, blush=.6)}, end={"rio": dict(happy=1, smile=1, blush=1, spark=1)}, post=.4),
    dict(shot="two_up", dur=2.4, mm="", ex={"rio": dict(happy=1, smile=1, blush=.6, look=.6), "mio": dict(happy=1, smile=1, blush=.8, look=-.6)},
         pose={"rio": "wave", "mio": "wave"}),
]
RECAP = ("からい？",
         [("〜を作《つく》った", "…ကို ချက်ခဲ့တယ်/လုပ်ခဲ့တယ်"),
          ("いただきます", "စားပါမယ် (မစားခင် ပြောတဲ့စကား)"),
          ("〜けど、大丈夫《だいじょうぶ》？", "…ပေမဲ့ ရရဲ့လား?"),
          ("また〜たい", "နောက်တစ်ခါ …ချင်တယ်")])
