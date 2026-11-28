"""Puppet EP.2 — バイトの面接練習 (interview practice). Used by: python ep.py script_ep2"""
OUT = "puppet_ep2.mp4"
MUSIC = "n3/snd/out/bgm_carefree.mp3"
BG = {"two": ("pp_bg_cafe.png", 4), "cu": ("pp_bg_cafe.png", 9)}
HOOK = "ဂျပန် အလုပ် interview မှာ<br>ဒီလို မဖြေမိစေနဲ့နော် 😂"

EP = [
    dict(who="mio", v="v2_01", shot="two", jp="じゃあ、[面接《めんせつ》の練習《れんしゅう》]しよう！ 私《わたし》が店長《てんちょう》ね。",
         mm="ကဲ… interview လေ့ကျင့်ရအောင်! ငါက ဆိုင်မန်နေဂျာနော်။",
         ex={"rio": dict(look=.6, smile=.5), "mio": dict(look=-.6, smile=.9, brow=.3)}, pose={"mio": "point_self"}),
    dict(who="rio", v="v2_02", shot="two", jp="よろしくお願《ねが》いします！", mm="လေးစားစွာ တောင်းဆိုပါတယ်ခင်ဗျာ!",
         ex={"rio": dict(bow=1, smile=.6, eye=.8), "mio": dict(look=-.6, smile=.9)}, post=.2),
    dict(who="mio", v="v2_03", shot="mio", jp="では、[志望動機《しぼうどうき》]を教《おし》えてください。",
         mm="ဒါဆို… ဒီဆိုင်မှာ ဘာလို့ အလုပ်လုပ်ချင်တာလဲ ပြောပြပါ။", ex={"mio": dict(smile=.3, brow=.2, eye=.95)}),
    dict(who="rio", v="v2_04", shot="rio", jp="えっと……お腹《なか》が空《す》いている[からです]！",
         mm="အဲ့… ဗိုက်ဆာနေလို့ပါ!", ex={"rio": dict(smile=1, eye=1.05, blush=.3)}, pose={"rio": "thumb"}, post=.2),
    dict(who="mio", v="v2_05", shot="mio", jp="……[正直《しょうじき》すぎ]！", mm="…ပွင့်လင်းလွန်းတယ်ဟ!", sfx="don",
         ex={"mio": dict(worry=1, brow=.6, smile=0, wavy=1)}, pose={"mio": "facepalm"}, post=.3),
    dict(who="rio", v="v2_06", shot="rio", jp="え、だめ？", mm="ဟင်… မရဘူးလား?",
         ex={"rio": dict(worry=.7, brow=.6, smile=.2, sweat=1, tilt=-6)}, pose={"rio": "scratch"}),
    dict(who="mio", v="v2_07", shot="two", jp="「[御社《おんしゃ》]で成長《せいちょう》したいからです」って言《い》うの。",
         mm="「ကုမ္ပဏီမှာ တိုးတက်ချင်လို့ပါ」 လို့ ပြောရတာ။",
         ex={"rio": dict(look=.6, smile=.3, brow=.3), "mio": dict(look=-.6, smile=.6, brow=.3)}),
    dict(who="rio", v="v2_08", shot="rio", jp="おんしゃ……？", mm="အွန်ရှ…?",
         ex={"rio": dict(eye=1.15, brow=.8, smile=0, tilt=8, lookup=.6)}, post=.2),
    dict(who="mio", v="v2_09", shot="mio", jp="じゃあ、もう一回《いっかい》。志望動機《しぼうどうき》は？", mm="ကဲ… နောက်တစ်ခါ။ ဘာလို့ အလုပ်လုပ်ချင်တာလဲ?",
         ex={"mio": dict(smile=.5, brow=.3)}),
    dict(who="rio", v="v2_10", shot="rio", jp="御社《おんしゃ》で、まかないを食《た》べて[成長《せいちょう》したいからです]！",
         mm="ကုမ္ပဏီမှာ ဝန်ထမ်းထမင်း စားပြီး ကြီးထွားချင်လို့ပါ! 🍚",
         ex={"rio": dict(smile=1, eye=1.05, blush=.4, brow=.3)}, pose={"rio": "thumb"}, post=.3),
    dict(who="mio", v="v2_11", shot="mio", jp="あはは！……合格《ごうかく》、かも。", mm="ဟားဟား!… အောင်တယ်… ဖြစ်မယ်ထင်တယ်။",
         ex={"mio": dict(happy=1, smile=1, blush=.6, bounce=1)}, end={"mio": dict(happy=0, bounce=0, eye=.95, smile=.8)}, pose={"mio": "clap"}),
    dict(who="rio", v="v2_12", inner=1, shot="rio", jp="（心《こころ》の声《こえ》）やった……のかな？", mm="(စိတ်ထဲက) အောင်ပြီ… လားမသိ?",
         ex={"rio": dict(smile=.7, blush=.6, look=.4, brow=.4)}, pose={"rio": "scratch"}, post=.4),
    dict(shot="two_up", dur=2.4, mm="", ex={"rio": dict(smile=1, blush=.6, look=.6), "mio": dict(smile=1, look=-.6, happy=1)},
         pose={"rio": "wave", "mio": "wave"}),
]
RECAP = ("バイトの面接《めんせつ》",
         [("〜からです", "…လို့ပါ (အကြောင်းပြချက်)"),
          ("〜すぎ", "…လွန်းတယ်"),
          ("御社《おんしゃ》", "လူကြီးမင်းတို့ ကုမ္ပဏီ (ယဉ်ကျေးစကား)"),
          ("志望動機《しぼうどうき》", "လျှောက်ရတဲ့ အကြောင်းရင်း")])
