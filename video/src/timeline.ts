import narration from "./narration.json";
import { END_CARD, FPS, LEAD, TAIL } from "./theme";

export type Sentence = { text: string; start: number; end: number };
export type SceneTiming = {
  id: string;
  from: number; // frame
  frames: number;
  duration: number; // seconds of narration
  sentences: Sentence[];
};

const raw = narration as { id: string; duration: number; sentences: Sentence[] }[];

let cursor = 0;
export const SCENES: SceneTiming[] = raw.map((s) => {
  const frames = Math.round((LEAD + s.duration + TAIL) * FPS);
  const t = { id: s.id, from: cursor, frames, duration: s.duration, sentences: s.sentences };
  cursor += frames;
  return t;
});

export const END_FROM = cursor;
export const END_FRAMES = END_CARD * FPS;
export const TOTAL_FRAMES = cursor + END_FRAMES;

export const scene = (id: string): SceneTiming => {
  const s = SCENES.find((x) => x.id === id);
  if (!s) throw new Error(`no scene ${id}`);
  return s;
};

// Seconds since this scene's narration started (negative during the lead-in).
export const spokenTime = (frame: number) => frame / FPS - LEAD;

// Index of the sentence being spoken (or the last one spoken) at time t.
export const sentenceAt = (sentences: Sentence[], t: number) => {
  let i = 0;
  for (let k = 0; k < sentences.length; k++) if (t >= sentences[k].start - 0.15) i = k;
  return i;
};
