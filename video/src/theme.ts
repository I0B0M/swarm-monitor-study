// Colours are the replay viewer's dark theme, so the video and the viewer read as one system.
// naive / informed are Figure 2's validated dark-mode categorical pair.
export const C = {
  paper: "#0E1116",
  surface: "#151A21",
  surface2: "#1A2029",
  surface3: "#252C37",
  ink: "#E6E9EE",
  ink2: "#A7B0BC",
  rule: "#2A2F37",
  rule2: "#434B57",
  a: "#7AA7FF",
  b: "#FB923C",
  viol: "#FF7B7B",
  flag: "#FBBF24",
  clean: "#34D3BE",
  naive: "#3987e5",
  informed: "#d95926",
};

export const FONT =
  'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
export const MONO =
  'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace';

export const FPS = 30;
export const LEAD = 1.0; // seconds of picture before a scene's narration starts
export const TAIL = 1.4; // seconds after it ends
export const END_CARD = 7; // seconds
