import React from "react";
import { Audio } from "@remotion/media";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Captions } from "./parts";
import { AskScene, EndCard, FrozenScene, HookScene, LibraryScene, ReplayScene, SetupScene, TakeawayScene, TitleScene } from "./Scenes";
import { C, FPS, LEAD } from "./theme";
import { END_FRAMES, END_FROM, SCENES } from "./timeline";

const VISUALS: Record<string, React.FC<{ sentences: { text: string; start: number; end: number }[] }>> = {
  title: TitleScene,
  hook: HookScene,
  setup: SetupScene,
  frozen: FrozenScene,
  replay: ReplayScene,
  library: LibraryScene,
  ask: AskScene,
  takeaway: TakeawayScene,
};

export const Explainer: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      {SCENES.map((s) => {
        const Visual = VISUALS[s.id];
        return (
          <Sequence key={s.id} name={s.id} from={s.from} durationInFrames={s.frames}>
            <Visual sentences={s.sentences} />
            {s.id !== "title" ? <Captions sentences={s.sentences} /> : null}
            <Sequence from={Math.round(LEAD * FPS)} name={`${s.id} voice`}>
              <Audio src={staticFile(`voiceover/${s.id}.wav`)} />
            </Sequence>
          </Sequence>
        );
      })}
      <Sequence name="end" from={END_FROM} durationInFrames={END_FRAMES}>
        <EndCard />
      </Sequence>
    </AbsoluteFill>
  );
};
