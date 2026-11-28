import sys, json
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(sys.argv[1], language="ja", word_timestamps=True, vad_filter=False)
out = []
for s in segs:
    for w in s.words:
        out.append([round(w.start, 2), round(w.end, 2), w.word])
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
print(" ".join("%.2f:%s" % (a, t) for a, b, t in out))
