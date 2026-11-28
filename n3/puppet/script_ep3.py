"""Puppet EP.3 — 電車の中では… (phone manners on the train). python ep.py script_ep3"""
OUT = "puppet_ep3.mp4"
MUSIC = "n3/snd/out/bgm_monkeys.mp3"
BG = {"two": ("pp_bg_train.png", 3), "cu": ("pp_bg_train.png", 8)}
SWAY = 1            # train rocking
AMB = "train"
HOOK = "ဂျပန် ရထားပေါ်မှာ<br>ဖုန်းပြောလို့ ရလား? 🚃📱"

EP = [
    dict(who="rio", v="v3_01", shot="two", jp="あ、電話《でんわ》だ！ もしもし〜！", mm="အာ… ဖုန်းလာတယ်! ဟဲလို~!", sfx="ring", sfxv=.8,
         ex={"rio": dict(smile=1, eye=1.05, look=.2), "mio": dict(look=-.6, eye=1.15, brow=.6, worry=.5)}, pose={"rio": "phone_ear"}),
    dict(who="mio", v="v3_02", shot="mio", jp="ちょっと！ [電車《でんしゃ》の中《なか》で電話《でんわ》はダメ]だよ！",
         mm="ဟဲ့! ရထားပေါ်မှာ ဖုန်းပြောလို့ မရဘူးလေ!", zoom=[1.0, 1.08],
         ex={"mio": dict(worry=1, brow=.8, smile=0, look=-.4)}, pose={"mio": "shh"}),
    dict(who="rio", v="v3_03", shot="rio", jp="え、そうなの？", mm="ဟင်… ဟုတ်လား?",
         ex={"rio": dict(eye=1.15, brow=.7, smile=.1, sweat=1, tilt=-5)}, pose={"rio": "phone_ear"}),
    dict(who="mio", v="v3_04", shot="two", jp="うん。[マナーモード]にして、あとで[かけ直《なお》す]の。",
         mm="အင်း။ အသံပိတ်ထားပြီး နောက်မှ ပြန်ခေါ်ရတာ။",
         ex={"rio": dict(look=.6, smile=.3, brow=.3), "mio": dict(look=-.6, smile=.4, brow=.3)}, pose={"rio": "phone_ear"}),
    dict(who="rio", v="v3_05", shot="rio", jp="……もしもし、今《いま》、電車《でんしゃ》なので、あとでかけ直《なお》します。",
         mm="…ဟဲလို… အခု ရထားပေါ်မှာမို့ နောက်မှ ပြန်ခေါ်ပါ့မယ်။",
         ex={"rio": dict(smile=.3, eye=.9, look=-.3, brow=.3)}, pose={"rio": "phone_ear"}),
    dict(who="rio", v="v3_06", shot="rio", jp="どう？ [完璧《かんぺき》]でしょ？", mm="ဘယ်လိုလဲ? ပြီးပြည့်စုံတယ်မလား? 😎",
         ex={"rio": dict(smile=1, eye=1.05, blush=.3, spark=1, tilt=4)}, pose={"rio": "thumb"}),
    dict(who="mio", v="v3_07", shot="mio", jp="うん、えらい、えらい。", mm="အင်း… တော်တယ် တော်တယ်။",
         ex={"mio": dict(happy=1, smile=1, blush=.4)}, post=.2),
    dict(who="mio", v="v3_08", shot="mio", jp="あっ！ わ、私《わたし》の……！", mm="အာ! ငါ့… ငါ့ဖုန်း…!", sfx="ring2", sfxv=1.1, sfxat=-.4,
         zoom=[1.0, 1.15], ex={"mio": dict(eye=1.25, brow=1, worry=1, wavy=1, sweat=1, blush=.8, shake=1)}, pose={"mio": "phone_out"}),
    dict(who="rio", v="v3_09", shot="rio", jp="……[電車《でんしゃ》の中《なか》で電話《でんわ》は、ダメ]だよ？",
         mm="…ရထားပေါ်မှာ ဖုန်းပြောလို့ မရဘူးလေ… နော်?", zoom=[1.0, 1.1],
         ex={"rio": dict(eye=.75, smile=.9, brow=.2, look=-.5, tilt=-3)}, pose={"rio": "shh"}, post=.2),
    dict(who="mio", v="v3_10", shot="mio", jp="……すみません。", mm="…တောင်းပန်ပါတယ်။",
         ex={"mio": dict(shut=1, blush=1.4, worry=.7, brow=.4, tilt=-4)}, post=.4),
    dict(shot="two_up", dur=2.4, mm="",
         ex={"rio": dict(smile=1, happy=1, look=.6), "mio": dict(smile=.8, blush=1, look=-.6, happy=1)}, pose={"rio": "wave", "mio": "wave"}),
]
RECAP = ("電車《でんしゃ》のマナー",
         [("〜はダメ", "…လို့ မရဘူး"),
          ("マナーモードにする", "ဖုန်းကို အသံပိတ်ထားတယ်"),
          ("かけ直《なお》す", "ဖုန်း ပြန်ခေါ်တယ်"),
          ("えらい", "တော်တယ် (ချီးကျူးတာ)")])
