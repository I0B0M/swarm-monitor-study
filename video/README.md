# Explainer video

A 3:45 narrated explainer (1920x1080, 30 fps) built with Remotion from the replay viewer's own frames, with numbers taken from the repository's numbers files. Narration is Kokoro-82M, an open-weight text-to-speech model (Apache-2.0), run offline; nothing is sent to a speech service.

**What is in it:** `narration/script.json` holds each scene's spoken text (`tts`) and on-screen caption (`caption`) with the file each number comes from (`sources`); `src/` holds the scenes; `public/frames/` holds the viewer frames.

**Rebuild:**

```bash
npm ci                                            # Node 20.19 or later; Remotion 4.0.541
./make_frames.sh                                  # viewer frames (chrome-headless-shell; needs viewer/ from #17)
KOKORO_DIR=~/models/kokoro-v1.0 python narration/make_voiceover.py   # public/voiceover/*.wav and src/narration.json
npx remotion render Explainer out/explainer.mp4
```

The committed frames were captured from the viewer at commit 028b13c (#17). The replay scene's spotlights and the boxes that cover the monitors' quoted reasons are placed for that layout; a viewer with more monitors in its example bundles lists more verdict cards, so recapture from that commit or move the rectangles in `src/Scenes.tsx`.

**Checks:**

```bash
python narration/check_wer.py                     # word error rate of the narration, per sentence (whisper.cpp)
npx remotion ffmpeg -y -i out/explainer.mp4 -vn -ac 1 -ar 16000 -c:a pcm_s16le out/audio16k.wav
python narration/check_render.py out/audio16k.wav # the rendered audio, cut where the timeline says each sentence plays
```

On the current render: duration 225.05 s; word error rate 3.0% over 540 words on the rendered audio (whisper large-v3-turbo). The ask scene's 12.2% is spelling, not speech: the voice says "Quen 3.8, 27B" for Qwen3.8-27B and whisper writes it that way. The voice synthesises one sentence at a time, which also gives the captions their timing.

Remotion is free for teams of up to three people; see remotion.dev/license.
