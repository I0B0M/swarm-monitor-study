"""Word error rate of the narration: whisper large-v3-turbo on each sentence, scene by scene, against the caption text."""
import json
import os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NUM = {"zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "twelve": "12", "fifty": "50",
       "sixty": "60", "hundred": "100", "none": "none"}


def norm(t: str) -> list[str]:
    t = t.lower().replace("gpt-oss-20b", "gptoss20b").replace("gpt oss 20b", "gptoss20b").replace("gpt-oss 20b", "gptoss20b")
    t = t.replace("1,200", "1200").replace("twelve hundred", "1200").replace("fifty-four", "54").replace("seventy-five", "75")
    t = t.replace("twenty-eight", "28").replace("thirty-five", "35").replace("one hundred", "100").replace("pre-registered", "preregistered")
    t = t.replace("key holder", "keyholder").replace("two-agent", "two agent").replace("language-model", "language model").replace("rule-informed", "rule informed")
    t = t.replace("open-weight", "open weight").replace("end-state", "end state")
    words = re.findall(r"[a-z0-9']+", t)
    return [NUM.get(w, w) for w in words]


def wer(ref: list[str], hyp: list[str]) -> float:
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
            prev, d[j] = d[j], cur
    return d[len(hyp)] / max(1, len(ref))


import tempfile, wave

def transcribe(wav: Path, start: float, end: float) -> str:
    """Whisper on one sentence's slice (a 30-second window edge can drop words in a long file)."""
    with wave.open(str(wav)) as w:
        rate, width, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        w.setpos(int(max(0, start - 0.05) * rate)); frames = w.readframes(int((end - start + 0.15) * rate))
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        with wave.open(tmp.name, "wb") as o:
            o.setnchannels(ch); o.setsampwidth(width); o.setframerate(rate); o.writeframes(frames)
        return subprocess.run(["whisper-cli", "-m", os.environ.get("WHISPER_MODEL", str(Path.home() / "models" / "ggml-large-v3-turbo.bin")), "-f", tmp.name, "-nt", "-np", "-mc", "0"],
                              capture_output=True, text=True).stdout


if __name__ == "__main__":
    scenes = json.loads((ROOT / "narration" / "script.json").read_text())
    timing = {x["id"]: x["sentences"] for x in json.loads((ROOT / "src" / "narration.json").read_text())}
    total_err = total_ref = 0
    for s in scenes:
        wav = ROOT / "public" / "voiceover" / f"{s['id']}.wav"
        out = " ".join(transcribe(wav, x["start"], x["end"]) for x in timing[s["id"]])
        ref, hyp = norm(s["caption"]), norm(out)
        w = wer(ref, hyp)
        total_err += w * len(ref); total_ref += len(ref)
        print(f"{s['id']:9s} WER {100 * w:5.1f}%  | {' '.join(out.split())[:160]}")
    print(f"overall WER {100 * total_err / total_ref:.1f}% over {total_ref} words")
