"""Puppet EP.6 — かわいい？こわい？ (Rio mixes up kawaii/kowai). AivisSpeech: にせ (Rio) / コハク (Mio). python ep.py script_ep6"""
OUT = "puppet_ep6.mp4"
MUSIC = "n3/snd/out/bgm_wholesome.mp3"
BG = {"two": ("pp_bg_cafe.png", 3), "cu": ("pp_bg_cafe.png", 8)}
TABLE = True
HOOK = "ကြောင်လေးကို ချီးမွမ်းမယ်ဆိုပြီး<br>စကားလုံး မှားသွားတဲ့အခါ… 😱🐱"

EP = [
    dict(who="mio", v="a6_01", shot="two", jp="ねえ、見《み》て！ うちの猫《ねこ》の、新《あたら》しい写真《しゃしん》！", mm="ဟေး ကြည့်! ငါ့အိမ်က ကြောင်လေးရဲ့ ဓာတ်ပုံအသစ်!",
         ex={"mio": dict(happy=1, smile=1, blush=.5, look=-.6), "rio": dict(look=.6, smile=.6)}, pose={"mio": "phone_out"}),
    dict(who="rio", v="a6_02", shot="rio", jp="わあ……すごく[こわい]！", mm="ဝိုး… အရမ်း ကြောက်စရာကောင်းတာပဲ!",
         ex={"rio": dict(smile=1, eye=1.1, blush=.5, spark=1)}, pose={"rio": "thumb"}),
    dict(who="mio", v="a6_03", shot="mio", jp="……え？ こわい？", mm="…ဟင်? ကြောက်စရာ?", sfx="don", zoom=[1.0, 1.12],
         ex={"mio": dict(eye=1.25, brow=1, worry=.6, smile=0, blush=0)}, post=.3),
    dict(who="rio", v="a6_04", shot="rio", jp="うん！ 目《め》も大《おお》きくて、ほんとにこわい！", mm="အင်း! မျက်လုံးလေးတွေလည်း ကြီးကြီး၊ တကယ် ကြောက်စရာကောင်းတယ်!",
         ex={"rio": dict(smile=1, happy=1, nod=6)}, pose={"rio": "point"}),
    dict(who="mio", v="a6_05", shot="mio", jp="……ひどい。", mm="…ရက်စက်လိုက်တာ။", sfx="fall",
         ex={"mio": dict(droop=1, eye=.8, lookup=-.7, worry=1, smile=0, wavy=1)}, post=.5),
    dict(who="rio", v="a6_06", shot="two", jp="え？ ほめたのに……。", mm="ဟင်? ချီးမွမ်းတာလေကွာ…",
         ex={"rio": dict(brow=.8, worry=.7, sweat=1, look=.6, smile=0), "mio": dict(droop=.6, worry=.8, look=-.6)}, pose={"rio": "scratch"}),
    dict(who="mio", v="a6_07", shot="mio", jp="それ、「[かわいい]」でしょ？", mm="အဲ့ဒါ「かわいい」(ချစ်စရာ) လို့ ပြောချင်တာ မဟုတ်လား?",
         ex={"mio": dict(brow=.6, eye=1, smile=.2, tilt=6)}, pose={"mio": "point"}),
    dict(who="rio", v="a6_08", shot="rio", jp="あっ……！ かわいい！ すごくかわいい！", mm="အာ…! ချစ်စရာ! အရမ်း ချစ်စရာကောင်းတယ်!", sfx="ring",
         ex={"rio": dict(eye=1.25, blush=1.3, sweat=1, shake=1, smile=.4)}, pose={"rio": "facepalm"}),
    dict(who="mio", v="a6_09", shot="mio", jp="もう、おそいよ。", mm="အခုမှ… နောက်ကျသွားပြီ။",
         ex={"mio": dict(shut=1, smile=.6, blush=.6, tilt=-6, look=.3)}),
    dict(who="rio", v="a6_10", shot="two", jp="ごめん！ 猫《ねこ》にも、あやまるから！", mm="ဆောရီး! ကြောင်လေးကိုလည်း တောင်းပန်ပါ့မယ်!",
         ex={"rio": dict(bow=1, worry=.8, blush=.8, look=.6), "mio": dict(smile=.7, look=-.6, blush=.5)}),
    dict(who="mio", v="a6_11", shot="mio", jp="じゃあ、[今度《こんど》会《あ》いに来《き》て]。", mm="ဒါဆို နောက်တစ်ခါ လာတွေ့လိုက်ပါ။",
         ex={"mio": dict(smile=1, blush=1, eye=.95, lookup=.2)}, end={"mio": dict(happy=1, smile=1, blush=1.2, hearts=1)}, post=.4),
    dict(shot="two_up", dur=2.4, mm="", ex={"rio": dict(happy=1, smile=1, blush=.8, look=.6), "mio": dict(happy=1, smile=1, blush=.8, look=-.6)},
         pose={"rio": "wave", "mio": "wave"}),
]
RECAP = ("かわいい？こわい？",
         [("かわいい", "ချစ်စရာကောင်းတယ်"),
          ("こわい", "ကြောက်စရာကောင်းတယ် ⚠️"),
          ("〜でしょ？", "…မဟုတ်လား?"),
          ("今度《こんど》〜て", "နောက်တစ်ခါ …ပါ")])
