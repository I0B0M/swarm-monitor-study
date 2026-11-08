"""Check the rendered video's own audio: each sentence, cut at the time the timeline says it plays, must transcribe
to its caption (word error rate), so the voice is clear and in sync. Also prints the video's duration.

  npx remotion ffmpeg -y -i out/explainer.mp4 -vn -ac 1 -ar 16000 out/audio16k.wav
  python3 narration/check_render.py out/audio16k.wav
"""
import json
import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_wer import norm, wer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FPS, LEAD, TAIL = 30, 1.0, 1.4
wav = Path(sys.argv[1])
scenes = json.loads((ROOT / "src" / "narration.json").read_text())
with wave.open(str(wav)) as w:
    rate, width, nframes = w.getframerate(), w.getsampwidth(), w.getnframes()
    audio = w.readframes(nframes)
print(f"audio length {nframes / rate:.1f} s")
start = 0
err = ref_n = 0
for s in scenes:
    frames = round((LEAD + s["duration"] + TAIL) * FPS)
    t0 = start / FPS + LEAD
    ref = norm(" ".join(x["text"] for x in s["sentences"]))
    hyp_parts = []
    for x in s["sentences"]:
        a = int(max(0, t0 + x["start"] - 0.05) * rate) * width
        b = int((t0 + x["end"] + 0.15) * rate) * width
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            with wave.open(tmp.name, "wb") as o:
                o.setnchannels(1); o.setsampwidth(width); o.setframerate(rate); o.writeframes(audio[a:b])
            hyp_parts.append(subprocess.run(["whisper-cli", "-m", os.environ.get("WHISPER_MODEL", str(Path.home() / "models" / "ggml-large-v3-turbo.bin")), "-f", tmp.name, "-nt", "-np", "-mc", "0"],
                                            capture_output=True, text=True).stdout)
    hyp = norm(" ".join(hyp_parts))
    w_ = wer(ref, hyp)
    err += w_ * len(ref); ref_n += len(ref)
    print(f"{s['id']:9s} at {t0:6.1f} s  WER {100 * w_:5.1f}%")
    start += frames
print(f"overall WER {100 * err / ref_n:.1f}% over {ref_n} words; video {start / FPS + 7:.1f} s with the end card")
