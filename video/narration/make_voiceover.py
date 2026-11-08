"""Narration: Kokoro-82M (local, Apache-2.0), one sentence at a time, joined per scene with short pauses.

  pip install kokoro-onnx soundfile   # in a Python 3.12 environment
  KOKORO_DIR=~/models/kokoro-v1.0 python narration/make_voiceover.py

The model files are kokoro-v1.0.onnx and voices-v1.0.bin from the kokoro-onnx release "model-files-v1.0"
(SHA-256 7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5 and
bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d).

Writes public/voiceover/<scene>.wav and src/narration.json: each scene's duration and, per sentence, the caption text
with its start and end in seconds, so captions follow the voice exactly.
"""
import json
import os
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = Path(__file__).resolve().parent.parent
PAUSE = 0.32  # seconds of silence between sentences
SPLIT = re.compile(r"(?<=[.?!])\s+(?=[A-Z0-9])")
KOKORO_DIR = Path(os.environ.get("KOKORO_DIR", Path.home() / "models" / "kokoro-v1.0"))
k = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))
scenes = json.loads((ROOT / "narration" / "script.json").read_text())
out = []
for s in scenes:
    caps, tts = SPLIT.split(s["caption"]), SPLIT.split(s["tts"])
    assert len(caps) == len(tts), (s["id"], len(caps), len(tts))
    parts, timing, t, rate = [], [], 0.0, 24000
    for cap, say in zip(caps, tts):
        samples, rate = k.create(say, voice="af_heart", speed=1.0, lang="en-us")
        dur = len(samples) / rate
        timing.append({"text": cap, "start": round(t, 3), "end": round(t + dur, 3)})
        parts += [samples, np.zeros(int(PAUSE * rate), dtype=samples.dtype)]
        t += dur + PAUSE
    audio = np.concatenate(parts[:-1])
    sf.write(ROOT / "public" / "voiceover" / f"{s['id']}.wav", audio, rate)
    out.append({"id": s["id"], "duration": round(len(audio) / rate, 3), "sentences": timing})
    print(f"{s['id']:10s} {len(audio) / rate:6.2f} s  {len(caps)} sentences")
(ROOT / "src" / "narration.json").write_text(json.dumps(out, indent=1) + "\n")
print(f"total {sum(x['duration'] for x in out):.1f} s")
