import sys, json, subprocess
import numpy as np
from faster_whisper import WhisperModel
import wave
w = wave.open(sys.argv[1]); sr = w.getframerate()
x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
n = int(len(x) * 16000 / sr)
audio = np.interp(np.arange(n) * sr / 16000, np.arange(len(x)), x).astype(np.float32)
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio, language="ja", word_timestamps=True, vad_filter=False)
out = [[round(w.start, 2), round(w.end, 2), w.word] for s in segs for w in s.words]
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
print(" ".join("%.2f:%s" % (a, t) for a, b, t in out))
# check
