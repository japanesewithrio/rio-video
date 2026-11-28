"""Puppet EP.4 — 似合ってる (Mio wears Myanmar dress for the first time). python ep.py script_ep4"""
OUT = "puppet_ep4.mp4"
MUSIC = "n3/snd/out/bgm_wholesome.mp3"
BG = {"two": ("pp_bg_park.png", 3), "cu": ("pp_bg_park.png", 8)}
FULL = {"rio": "myanmar", "mio": "myanmar"}
HOOK = "မြန်မာ ဝတ်စုံ ဝတ်လာတဲ့ ဂျပန်မလေးကို<br>ဘာပြောမလဲ? 💕"

EP = [
    dict(who="rio", v="v4_01", shot="two", jp="ミオ、遅《おそ》いなあ……。", mm="Mio… နောက်ကျလိုက်တာ…",
         enter={"mio": (1300, 0.01)}, ex={"rio": dict(look=.5, smile=.2, brow=.3)}, pose={"rio": "scratch"}),
    dict(who="mio", v="v4_02", shot="two", jp="リオくん、[お待《ま》たせ]！ ……どう、かな？", mm="Rio… စောင့်နေရတာ ကြာပြီလား! …ဘယ်လိုလဲ?",
         enter={"mio": (1250, 1.2)}, twirl={"mio": (1.6, .7)}, sfx="twinkle",
         ex={"rio": dict(look=.6, eye=1.15, brow=.6, blush=.6), "mio": dict(smile=.9, blush=.6, look=-.5)}, post=.3),
    dict(who="rio", v="v4_03", inner=1, shot="rio", jp="（心《こころ》の声《こえ》）き、きれい……。", mm="(စိတ်ထဲက) …လှ… လှလိုက်တာ…",
         sfx="heart", zoom=[1.0, 1.12], ex={"rio": dict(eye=1.2, blush=1.4, smile=.3, hearts=1)}, post=.2),
    dict(who="rio", v="v4_04", shot="rio", jp="え、えっと、その……に、にあ……", mm="အ… အဲ့… ဟို… လိုက်… လိုက်…",
         ex={"rio": dict(blush=1.3, worry=.8, brow=.6, sweat=1, look=.5)}, pose={"rio": "scratch"}),
    dict(who="mio", v="v4_05", shot="mio", jp="「にあ」？", mm="「လိုက်」?", ex={"mio": dict(tilt=-9, smile=.6, brow=.4, eye=1.05)}),
    dict(who="rio", v="v4_06", shot="rio", jp="……に、肉《にく》！ 肉《にく》、[食《た》べに行《い》こう]！", mm="…အ… အသား! အသား သွားစားရအောင်! 🍖",
         ex={"rio": dict(smile=1, eye=1.1, blush=1, sweat=1, shake=.3)}, pose={"rio": "thumb"}, post=.2),
    dict(who="mio", v="v4_07", shot="mio", jp="もう……。", mm="ဟွန့်…", ex={"mio": dict(worry=.5, smile=.1, blush=.6, look=-.5, tilt=4)}, post=.2),
    dict(who="mio", v="v4_08", shot="two", jp="ねえ、ミャンマー語《ご》で「きれい」って、[何《なん》て言《い》うの]？",
         mm="ဟေး… မြန်မာလို「きれい」ကို ဘယ်လို ပြောလဲ?",
         ex={"rio": dict(look=.6, blush=.7, smile=.3), "mio": dict(look=-.6, smile=.7, blush=.5)}),
    dict(who="rio", v="v4_09", shot="rio", jp="「လှတယ်（フラデ）」だよ。", mm="「လှတယ်」 လို့ ပြောတယ်။", ex={"rio": dict(smile=.6, look=-.4, blush=.6)}),
    dict(who="mio", v="v4_10", shot="mio", jp="じゃあ……リオくんも、လှတယ်（フラデ）！", mm="ဒါဆို… Rio လည်း လှတယ်! 😊",
         ex={"mio": dict(happy=1, smile=1, blush=1, tilt=-5)}, pose={"mio": "point"}, post=.2),
    dict(who="rio", v="v4_11", shot="rio", jp="えっ……！", mm="ဟင်…!!", sfx="heart", zoom=[1.0, 1.18],
         ex={"rio": dict(shut=1, blush=1.6, hearts=1, shake=.5)}, post=.6),
    dict(shot="two_up", dur=2.6, mm="", ex={"rio": dict(smile=1, blush=1.2, look=.6), "mio": dict(happy=1, smile=1, blush=.8, look=-.6)},
         pose={"mio": "wave"}),
]
RECAP = ("似合《にあ》ってる",
         [("似合《にあ》ってる", "လိုက်တယ် (အဝတ်အစား)"),
          ("お待《ま》たせ", "စောင့်နေရတာ ကြာပြီလား"),
          ("〜に行《い》こう", "…သွားရအောင်"),
          ("何《なん》て言《い》うの？", "ဘယ်လို ပြောလဲ?")])
