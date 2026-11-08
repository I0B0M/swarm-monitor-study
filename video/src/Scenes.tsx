import React from "react";
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Frames, Rect, Source, Spotlight, currentSentence, useAppear, useSentenceOpacity } from "./parts";
import { C, FONT, MONO } from "./theme";
import { Sentence, spokenTime } from "./timeline";

type P = { sentences: Sentence[] };
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
// A scene's headline fades in at the cut, so no scene opens on an empty frame.
const useIntro = () => interpolate(useCurrentFrame(), [0, 10], [0, 1], clamp);

const Headline: React.FC<{ children: React.ReactNode; top?: number; size?: number; opacity?: number }> = ({ children, top = 150, size = 76, opacity = 1 }) => (
  <div style={{ position: "absolute", left: 120, right: 120, top, color: C.ink, fontFamily: FONT, fontSize: size, fontWeight: 800, lineHeight: 1.12, letterSpacing: -0.5, opacity }}>
    {children}
  </div>
);

// ---------------------------------------------------------------- title
export const TitleScene: React.FC<P> = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 200 } });
  const sub = interpolate(frame, [18, 36], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: C.paper, justifyContent: "center", padding: "0 160px" }}>
      <div style={{ color: C.ink2, fontFamily: FONT, fontSize: 32, letterSpacing: 4, textTransform: "uppercase", opacity: sub, marginBottom: 28 }}>
        A two-agent proof of concept
      </div>
      <div style={{ color: C.ink, fontFamily: FONT, fontSize: 104, fontWeight: 850, lineHeight: 1.04, letterSpacing: -1.5, transform: `translateY(${(1 - s) * 30}px)`, opacity: s }}>
        What is a monitor's
        <br />
        secrecy worth?
      </div>
      <div style={{ color: C.ink2, fontFamily: FONT, fontSize: 40, marginTop: 34, opacity: sub, maxWidth: 1400, lineHeight: 1.3 }}>
        Rule knowledge, spread and evasion in a two-agent control setting
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- hook
const AGENTS = 1200; // METR (2026): about 1,200 agents in the incident; the dots are an illustration of that count
export const HookScene: React.FC<P> = ({ sentences }) => {
  const frame = useCurrentFrame();
  const t = spokenTime(frame);
  const gather = interpolate(t, [sentences[1].start, sentences[1].end], [0, 1], clamp);
  const fadeDots = interpolate(t, [sentences[2].start - 0.3, sentences[2].start + 0.4], [1, 0], clamp);
  const q1 = useAppear(sentences, 2);
  const q2 = useAppear(sentences, 3);
  const cx = 1360, cy = 470;
  const dots = [];
  for (let i = 0; i < AGENTS; i++) {
    const x0 = 120 + random(`x${i}`) * 1680, y0 = 120 + random(`y${i}`) * 760;
    const ang = random(`a${i}`) * Math.PI * 2, r = 70 + random(`r${i}`) * 150;
    const x1 = cx + Math.cos(ang) * r * 1.5, y1 = cy + Math.sin(ang) * r;
    const k = Math.min(1, Math.max(0, gather * 1.4 - random(`d${i}`) * 0.4));
    dots.push(<circle key={i} cx={x0 + (x1 - x0) * k} cy={y0 + (y1 - y0) * k} r={3.2} fill={i % 7 === 0 ? C.b : C.a} opacity={0.8} />);
  }
  const box = interpolate(t, [sentences[1].start, sentences[1].start + 0.6], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <svg width={1920} height={1080} style={{ position: "absolute", opacity: fadeDots }}>
        {dots}
        <g opacity={box}>
          <rect x={cx - 120} y={cy - 70} width={240} height={140} rx={18} fill={C.surface2} stroke={C.flag} strokeWidth={4} />
          <text x={cx} y={cy - 6} textAnchor="middle" fill={C.ink} fontFamily={FONT} fontSize={34} fontWeight={800}>shared cache</text>
          <text x={cx} y={cy + 36} textAnchor="middle" fill={C.ink2} fontFamily={FONT} fontSize={26}>a message board</text>
        </g>
      </svg>
      <Headline top={140} size={64} opacity={interpolate(t, [-0.5, 0.2], [0, 1], clamp) * interpolate(t, [sentences[2].start - 0.4, sentences[2].start], [1, 0], clamp)}>
        Agents share workspaces.
      </Headline>
      <Source opacity={box * interpolate(t, [sentences[2].start - 0.4, sentences[2].start], [1, 0], clamp)}>About 1,200 agents in one security evaluation (METR, 2026)</Source>
      <div style={{ position: "absolute", left: 160, right: 160, top: 290, fontFamily: FONT, color: C.ink }}>
        <div style={{ fontSize: 70, fontWeight: 800, lineHeight: 1.15, opacity: q1 }}>
          If one agent can read the monitor's rules, does that knowledge spread to a saboteur?
        </div>
        <div style={{ fontSize: 70, fontWeight: 800, lineHeight: 1.15, marginTop: 40, color: C.flag, opacity: q2 }}>And how much does it help?</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- setup (viewer frames with spotlights)
const R = (x: number, y: number, x2: number, y2: number): Rect => ({ x, y, w: x2 - x, h: y2 - y });
const SETUP_SPOTS: Rect[][] = [
  [],
  [R(130, 197, 880, 322), R(360, 350, 700, 472)],
  [R(133, 503, 333, 595), R(775, 474, 982, 646)],
  [R(365, 352, 465, 472)],
  [R(130, 702, 1003, 800)],
  [R(672, 650, 982, 695), R(778, 502, 880, 550)],
  [R(890, 197, 1003, 322)],
];
export const SetupScene: React.FC<P> = ({ sentences }) => {
  const frame = useCurrentFrame();
  const t = spokenTime(frame);
  const i = currentSentence(sentences, frame);
  const s = sentences[i];
  const strength = Math.min(interpolate(t, [s.start - 0.1, s.start + 0.35], [0, 1], clamp), interpolate(t, [s.end + 0.1, s.end + 0.4], [1, 0], clamp));
  const table = useSentenceOpacity(sentences, 6);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Frames frames={[{ src: "cover205-e0.png", from: -10 }, { src: "cover205-e3.png", from: sentences[5].start - 0.2 }]} zoom={0} />
      <Spotlight rects={SETUP_SPOTS[i] || []} strength={i === 0 ? 0 : strength} />
      <div style={{ position: "absolute", left: 1112, top: 180, width: 776, opacity: table, background: C.surface, border: `2px solid ${C.rule2}`, borderRadius: 18, padding: "26px 30px", fontFamily: FONT, color: C.ink }}>
        <div style={{ fontSize: 30, fontWeight: 800, marginBottom: 14 }}>Who holds the key</div>
        {[
          ["Note (S2)", "an unrelated note", "either agent"],
          ["Honest key (S3b)", "the monitor's checklist", "the honest agent"],
          ["Saboteur key (S3a)", "the monitor's checklist", "the saboteur"],
        ].map(([c, h, k]) => (
          <div key={c} style={{ display: "flex", gap: 18, borderTop: `1px solid ${C.rule2}`, padding: "14px 0", fontSize: 25 }}>
            <div style={{ width: 230, fontWeight: 800 }}>{c}</div>
            <div style={{ width: 280, color: C.ink2 }}>{h}</div>
            <div style={{ color: k === "the saboteur" ? C.b : k === "the honest agent" ? C.a : C.ink2 }}>{k}</div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- frozen study (provisional counts, issue #4)
const Stat: React.FC<{ big: string; label: string; color?: string; opacity: number }> = ({ big, label, color = C.ink, opacity }) => (
  <div style={{ opacity, transform: `translateY(${(1 - opacity) * 16}px)`, background: C.surface, border: `2px solid ${C.rule2}`, borderRadius: 20, padding: "26px 30px", width: 500 }}>
    <div style={{ fontFamily: FONT, fontSize: 92, fontWeight: 850, color, letterSpacing: -1, fontVariantNumeric: "tabular-nums" }}>{big}</div>
    <div style={{ fontFamily: FONT, fontSize: 30, color: C.ink2, marginTop: 6, lineHeight: 1.25 }}>{label}</div>
  </div>
);
export const FrozenScene: React.FC<P> = ({ sentences }) => {
  const a = useAppear(sentences, 1), b = useAppear(sentences, 1, 2.2), c = useAppear(sentences, 2), d = useAppear(sentences, 3), e = useAppear(sentences, 4);
  const head = useIntro();
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Headline top={110} size={62} opacity={head}>The pre-registered two-agent study</Headline>
      <div style={{ position: "absolute", left: 120, top: 260, display: "flex", gap: 40 }}>
        <Stat big="0/50" label="undetected sabotage, note in the store" opacity={a} />
        <Stat big="0/54" label="undetected sabotage, honest agent holds the checklist" opacity={b} />
        <Stat big="0/54" label="honest keyholders who opened the store" color={C.flag} opacity={c} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 600, display: "flex", gap: 40, opacity: d }}>
        <div style={{ fontFamily: FONT, fontSize: 40, color: C.ink, lineHeight: 1.4, maxWidth: 1600 }}>
          Saboteur holds the key: <b style={{ color: C.b }}>5/6</b> opened the store, <b style={{ color: C.b }}>5/6</b> laundered a tag
          <span style={{ opacity: e }}> · monitor flagged <b style={{ color: C.clean }}>6/6</b></span>
        </div>
      </div>
      <Source opacity={head}>Provisional counts (issue #4) until the final results; exact 95% intervals in the paper</Source>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- replay of one library game
export const ReplayScene: React.FC<P> = ({ sentences }) => {
  const frame = useCurrentFrame();
  const t = spokenTime(frame);
  const s1 = sentences[1];
  const third = (s1.end - s1.start) / 3;
  const intro = useSentenceOpacity(sentences, 0);
  const i = currentSentence(sentences, frame);
  const strength = (k: number) => {
    const s = sentences[k];
    return Math.min(interpolate(t, [s.start - 0.1, s.start + 0.3], [0, 1], clamp), interpolate(t, [s.end + 0.2, s.end + 0.5], [1, 0], clamp));
  };
  const spots: Rect[] =
    i === 1 ? (t < s1.start + third ? [R(1131, 272, 1870, 340)] : t < s1.start + 2 * third ? [R(128, 652, 400, 694), R(133, 504, 232, 548)] : [R(672, 650, 982, 695), R(778, 502, 880, 550)])
      : i === 2 ? [R(1368, 270, 1871, 562)] : i === 3 ? [R(1368, 572, 1871, 842)] : [];
  const chip = useSentenceOpacity(sentences, 3);
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Frames
        frames={[
          { src: "cover205-e0.png", from: -10 },
          { src: "cover205-e1.png", from: s1.start - 0.1 },
          { src: "cover205-e2.png", from: s1.start + third },
          { src: "cover205-e3.png", from: s1.start + 2 * third },
          { src: "cover205-last.png", from: sentences[2].start - 0.2 },
        ]}
        zoom={0}
      />
      {/* The monitors' reason quotes use the code's own words for records and the exit; cover them so on-screen text stays neutral. */}
      {t >= sentences[2].start - 0.2 ? (
        <svg width={1920} height={1080} style={{ position: "absolute" }}>
          {[[348, 420], [506, 556], [650, 702], [786, 838]].map(([y1, y2]) => (
            <rect key={y1} x={1378} y={y1} width={486} height={y2 - y1} fill="#151A21" />
          ))}
        </svg>
      ) : null}
      <Spotlight rects={spots} strength={i === 0 ? 0 : strength(i)} />
      <AbsoluteFill style={{ opacity: intro, background: "rgba(10,12,16,0.82)", justifyContent: "center", alignItems: "center" }}>
        <div style={{ fontFamily: FONT, color: C.ink, textAlign: "center" }}>
          <div style={{ fontSize: 78, fontWeight: 850 }}>An attack library</div>
          <div style={{ fontSize: 40, color: C.ink2, marginTop: 22, lineHeight: 1.4 }}>
            scripted saboteur policies on 25 fresh layouts
            <br />
            the same games, replayed through every monitor
          </div>
        </div>
      </AbsoluteFill>
      <div style={{ position: "absolute", left: 1118, top: 858, width: 753, opacity: chip, background: C.surface, border: `2px solid ${C.flag}`, borderRadius: 14, padding: "10px 18px", fontFamily: FONT, fontSize: 24, color: C.ink, whiteSpace: "nowrap" }}>
        Outcome monitor: <b style={{ color: C.flag }}>flag 95</b> (Sonnet 5.5), <b style={{ color: C.flag }}>flag 90</b> (gpt-oss-20b)
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- library results (numbers from replays/REPLAY_NUMBERS.md)
type Row = { label: string; naive: [number, number]; informed: [number, number]; at?: number };
const ROWS: Row[] = [
  { label: "gpt-oss-20b · checklist", naive: [0, 50], informed: [75, 100], at: 1 },
  { label: "gpt-oss-20b · no checklist", naive: [1, 50], informed: [1, 100], at: 2 },
  { label: "Sonnet 5.5 · checklist verdict", naive: [0, 25], informed: [28, 50], at: 3 },
  { label: "Sonnet 5.5 · checklist score, 5% threshold", naive: [0, 25], informed: [0, 50], at: 3 },
  { label: "Sonnet 5.5 · last rule asks for judgement", naive: [0, 25], informed: [0, 50], at: 4 },
];
export const LibraryScene: React.FC<P> = ({ sentences }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = spokenTime(frame);
  const head = useIntro();
  const x0 = 760, w = 960;
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Headline top={100} size={56} opacity={head}>Undetected, by monitor: naive vs informed attacks</Headline>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        {[0, 0.5, 1].map((p) => (
          <g key={p} opacity={head}>
            <line x1={x0 + p * w} y1={240} x2={x0 + p * w} y2={740} stroke={C.rule2} strokeWidth={2} />
            <text x={x0 + p * w} y={778} textAnchor="middle" fill={C.ink2} fontFamily={FONT} fontSize={28}>{`${p * 100}%`}</text>
          </g>
        ))}
        {ROWS.map((r, k) => {
          const start = sentences[Math.min(r.at ?? 1, sentences.length - 1)].start + (k === 3 ? 2.6 : 0);
          const appear = spring({ frame: Math.max(0, Math.round((t - start + 0.2) * fps)), fps, config: { damping: 200 } });
          const y = 270 + k * 98;
          const pn = r.naive[0] / r.naive[1], pi = r.informed[0] / r.informed[1];
          return (
            <g key={r.label} opacity={t < start - 0.2 ? 0 : appear}>
              <text x={x0 - 36} y={y + 12} textAnchor="end" fill={C.ink} fontFamily={FONT} fontSize={32} fontWeight={700}>{r.label}</text>
              <circle cx={x0 + pn * w * appear} cy={y - 16} r={13} fill={C.paper} stroke={C.naive} strokeWidth={6} />
              <path d={`M ${x0 + pi * w * appear} ${y + 4} l 17 17 l -17 17 l -17 -17 z`} fill={C.informed} />
              <text x={x0 + pi * w * appear + (pi > 0.8 ? -30 : 30)} y={y + 32} textAnchor={pi > 0.8 ? "end" : "start"} fill={C.ink} fontFamily={MONO} fontSize={30} fontWeight={700}>
                {`${r.informed[0]}/${r.informed[1]}`}
              </text>
            </g>
          );
        })}
        <g opacity={head}>
          <circle cx={x0 + 12} cy={830} r={12} fill={C.paper} stroke={C.naive} strokeWidth={6} />
          <text x={x0 + 40} y={840} fill={C.ink2} fontFamily={FONT} fontSize={28}>naive: tag left unchanged</text>
          <path d={`M ${x0 + 440} 813 l 17 17 l -17 17 l -17 -17 z`} fill={C.informed} />
          <text x={x0 + 468} y={840} fill={C.ink2} fontFamily={FONT} fontSize={28}>informed: tag changed first</text>
        </g>
      </svg>
      <Source opacity={head}>Attack library, 25 fresh layouts · replays/REPLAY_NUMBERS.md</Source>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- ask probe (replays/ASK_NUMBERS.md)
export const AskScene: React.FC<P> = ({ sentences }) => {
  const head = useIntro();
  const g = useAppear(sentences, 1), h = useAppear(sentences, 2);
  const Bar: React.FC<{ label: string; k: number; n: number; color: string; o: number; note: string }> = ({ label, k, n, color, o, note }) => (
    <div style={{ opacity: o, marginBottom: 54 }}>
      <div style={{ fontFamily: FONT, fontSize: 36, color: C.ink, fontWeight: 800, marginBottom: 14 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "center", gap: 28 }}>
        <div style={{ width: 1100, height: 46, background: C.surface2, borderRadius: 8, overflow: "hidden" }}>
          <div style={{ width: `${(100 * k * o) / n}%`, height: "100%", background: color }} />
        </div>
        <div style={{ fontFamily: MONO, fontSize: 40, color: C.ink, fontWeight: 700 }}>{`${k}/${n}`}</div>
      </div>
      <div style={{ fontFamily: FONT, fontSize: 28, color: C.ink2, marginTop: 10 }}>{note}</div>
    </div>
  );
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Headline top={110} size={60} opacity={head}>A teammate asks for the store's contents</Headline>
      <div style={{ position: "absolute", left: 120, top: 300 }}>
        <Bar label="gpt-oss-20b as keyholder: opened the store" k={35} n={60} color={C.b} o={g} note="repeated the checklist's wording: 0/60" />
        <Bar label="Claude Haiku 5.5 as keyholder: opened the store" k={0} n={60} color={C.a} o={h} note="repeated the checklist's wording: 0/60" />
      </div>
      <Source opacity={head}>Ask probe, 20 fresh layouts × 3 framings · replays/ASK_NUMBERS.md</Source>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- takeaway
export const TakeawayScene: React.FC<P> = ({ sentences }) => {
  const len1 = sentences[1].end - sentences[1].start;
  const a = useIntro(), b = useAppear(sentences, 1), c = useAppear(sentences, 1, len1 * 0.42), d = useAppear(sentences, 1, len1 * 0.78);
  const lim = useAppear(sentences, 2), code = useAppear(sentences, 3);
  const Card: React.FC<{ o: number; children: React.ReactNode }> = ({ o, children }) => (
    <div style={{ opacity: o, transform: `translateY(${(1 - o) * 14}px)`, background: C.surface, border: `2px solid ${C.rule2}`, borderRadius: 18, padding: "22px 28px", fontFamily: FONT, fontSize: 36, color: C.ink, lineHeight: 1.3, marginBottom: 22, width: 1640 }}>
      {children}
    </div>
  );
  return (
    <AbsoluteFill style={{ background: C.paper }}>
      <Headline top={100} size={62} opacity={a}>Secrecy protects only monitors that obey their rules.</Headline>
      <div style={{ position: "absolute", left: 120, top: 250 }}>
        <Card o={b}>{'Don\'t end a monitor\'s checklist with "mark everything else clean".'}</Card>
        <Card o={c}>Use calibrated scores where they separate attacks from honest runs.</Card>
        <Card o={d}>Check the end state when you can.</Card>
        <div style={{ opacity: lim, fontFamily: FONT, fontSize: 30, color: C.ink2, marginTop: 16, width: 1640, lineHeight: 1.35 }}>
          Limits: one fictional task, two agents, hand-written attacks, provisional two-agent counts.
        </div>
        <div style={{ opacity: code, fontFamily: MONO, fontSize: 32, color: C.flag, marginTop: 26 }}>github.com/I0B0M/swarm-monitor-study</div>
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- end card
export const EndCard: React.FC = () => {
  const frame = useCurrentFrame();
  const o = interpolate(frame, [0, 20], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: C.paper, justifyContent: "center", padding: "0 160px", opacity: o }}>
      <div style={{ fontFamily: FONT, fontSize: 64, fontWeight: 850, color: C.ink, lineHeight: 1.12 }}>Knowing the checklist beats monitors that obey it</div>
      <div style={{ fontFamily: FONT, fontSize: 34, color: C.ink2, marginTop: 14 }}>Verdicts, scores and spread in a two-agent control setting</div>
      <div style={{ fontFamily: FONT, fontSize: 36, color: C.ink2, marginTop: 26, lineHeight: 1.45 }}>
        Paper, code, data and the replay viewer:
        <br />
        <span style={{ fontFamily: MONO, color: C.flag }}>github.com/I0B0M/swarm-monitor-study</span>
      </div>
      <div style={{ fontFamily: FONT, fontSize: 30, color: C.ink2, marginTop: 60 }}>
        Ibrahim and Bryan Londres · Apart Research Swarm Alignment Hackathon · November 2026
      </div>
      <div style={{ fontFamily: FONT, fontSize: 24, color: C.ink2, marginTop: 18, opacity: 0.8 }}>
        Narration: Kokoro-82M, an open-weight text-to-speech model. Viewer frames: the project's own replay viewer.
      </div>
    </AbsoluteFill>
  );
};
