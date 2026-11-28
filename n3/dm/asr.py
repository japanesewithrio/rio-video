import sys, json, subprocess
import numpy as np
from faster_whisper import WhisperModel
pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True, check=True).stdout
audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, _ = m.transcribe(audio, language="ja", word_timestamps=True, vad_filter=False)
out = [[round(w.start, 2), round(w.end, 2), w.word] for s in segs for w in s.words]
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False)
print(" ".join("%.2f:%s" % (a, t) for a, b, t in out))
