import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { C, FONT, FPS } from "./theme";
import { Sentence, sentenceAt, spokenTime } from "./timeline";

const ease = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// Burned-in captions: the sentence being spoken, timed from the narration's own sentence timings.
export const Captions: React.FC<{ sentences: Sentence[] }> = ({ sentences }) => {
  const frame = useCurrentFrame();
  const t = spokenTime(frame);
  const cur = sentences.find((s) => t >= s.start - 0.1 && t <= s.end + 0.25);
  if (!cur) return null;
  const opacity = Math.min(
    interpolate(t, [cur.start - 0.1, cur.start + 0.15], [0, 1], ease),
    interpolate(t, [cur.end, cur.end + 0.25], [1, 0], ease),
  );
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 54 }}>
      <div
        style={{
          opacity,
          maxWidth: 1560,
          padding: "14px 30px",
          borderRadius: 14,
          background: "rgba(10, 12, 16, 0.86)",
          border: `1px solid ${C.rule2}`,
          color: C.ink,
          fontFamily: FONT,
          fontSize: 38,
          lineHeight: 1.32,
          textAlign: "center",
          fontWeight: 500,
        }}
      >
        {cur.text}
      </div>
    </AbsoluteFill>
  );
};

export type Rect = { x: number; y: number; w: number; h: number };

// Dims everything but the given rectangles and rings them; strength 0 to 1.
export const Spotlight: React.FC<{ rects: Rect[]; strength: number }> = ({ rects, strength }) => {
  if (strength <= 0.001 || rects.length === 0) return null;
  return (
    <AbsoluteFill>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080">
        <defs>
          <mask id="spot">
            <rect x={0} y={0} width={1920} height={1080} fill="white" />
            {rects.map((r, i) => (
              <rect key={i} x={r.x - 8} y={r.y - 8} width={r.w + 16} height={r.h + 16} rx={12} fill="black" />
            ))}
          </mask>
        </defs>
        <rect x={0} y={0} width={1920} height={1080} fill="black" opacity={0.62 * strength} mask="url(#spot)" />
        {rects.map((r, i) => (
          <rect
            key={i}
            x={r.x - 8}
            y={r.y - 8}
            width={r.w + 16}
            height={r.h + 16}
            rx={12}
            fill="none"
            stroke={C.flag}
            strokeWidth={4}
            opacity={strength}
          />
        ))}
      </svg>
    </AbsoluteFill>
  );
};

// A viewer frame, faded in at `from` seconds of the scene's spoken time; the latest one wins.
export const Frames: React.FC<{ frames: { src: string; from: number }[]; zoom?: number }> = ({ frames, zoom = 0.025 }) => {
  const frame = useCurrentFrame();
  const t = spokenTime(frame);
  const scale = 1 + zoom * interpolate(frame, [0, 40 * FPS], [0, 1], ease);
  return (
    <AbsoluteFill style={{ transform: `scale(${scale})` }}>
      {frames.map((f, i) => {
        const opacity = i === 0 ? 1 : interpolate(t, [f.from, f.from + 0.35], [0, 1], ease);
        return (
          <AbsoluteFill key={f.src} style={{ opacity }}>
            <Img src={staticFile(`frames/${f.src}`)} style={{ width: 1920, height: 1080 }} />
          </AbsoluteFill>
        );
      })}
    </AbsoluteFill>
  );
};

// Opacity for a sentence-driven element: on from sentence i's start until sentence j ends.
export const useSentenceOpacity = (sentences: Sentence[], i: number, j = i) => {
  const t = spokenTime(useCurrentFrame());
  const a = sentences[i].start - 0.2;
  const b = sentences[Math.min(j, sentences.length - 1)].end + 0.2;
  return Math.min(interpolate(t, [a, a + 0.35], [0, 1], ease), interpolate(t, [b, b + 0.35], [1, 0], ease));
};

export const useAppear = (sentences: Sentence[], i: number, offset = 0) => {
  const t = spokenTime(useCurrentFrame());
  const a = sentences[i].start + offset - 0.15;
  return interpolate(t, [a, a + 0.45], [0, 1], ease);
};

export const currentSentence = (sentences: Sentence[], frame: number) => sentenceAt(sentences, spokenTime(frame));

export const Source: React.FC<{ children: React.ReactNode; opacity?: number }> = ({ children, opacity = 1 }) => (
  <div
    style={{
      position: "absolute",
      left: 120,
      top: 64,
      color: C.ink2,
      fontFamily: FONT,
      fontSize: 24,
      opacity,
      letterSpacing: 0.2,
    }}
  >
    {children}
  </div>
);
