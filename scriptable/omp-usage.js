// OMP usage widget for Scriptable: native Home Screen quota rings with Now, Forecast, and Recent views, plus Lock Screen views.
// Reads https://openclaw.tail2fec5e.ts.net/usage/widget.json over Tailscale; a tap on the body opens detail.html on the same host.

const BASE = "https://openclaw.tail2fec5e.ts.net/usage/";
const BOT_URL = "tg://resolve?domain=PreiPreiClaudeButlerBot";
const FEED_SCHEMA = 2;
const REFRESH_MS = 5 * 60 * 1000;
const STALE_MS = 20 * 60 * 1000;
const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;
const OUT_STEP_MS = 5 * MINUTE_MS;
const HOME = ["small", "medium", "large"];
const VIEW_IDS = ["now", "forecast", "recent"];
const VIEW_TITLES = { now: "Now", forecast: "Forecast", recent: "Recent" };
const REFRESH_ACTION = "refresh";
const NEXT_ACTION = "forecast-next";
const USAGE_NEXT_ACTION = "usage-next";
const USAGE_MODE = "tokens";
const SYMBOLS = {
  exhausted: "lock.fill",
  run_out: "exclamationmark.triangle.fill",
  gated: "lock",
  hot: "bolt.fill",
  near: "bolt.fill",
  on_pace: "checkmark",
  spare: "leaf.fill",
  unknown: "clock",
};

const CANVAS = new Color("#1C1C1E");
const RAISED = new Color("#2C2C2E");
const SELECTED = new Color("#636366");
const LABEL = new Color("#FFFFFF");
const SECONDARY = new Color("#EBEBF5", 0.6);
const TERTIARY = new Color("#EBEBF5", 0.3);
const HEAT_HEX = "#FF9F0A";
const OUT_HEX = "#FF453A";
const HEAT = new Color(HEAT_HEX);
const OUT = new Color(OUT_HEX);
const AMBER = new Color("#FFD60A");
const GREEN = new Color("#30D158");
const NEUTRAL_HEX = "#8E8E93";
const RAINBOW = ["#FF453A", "#FF9F0A", "#FFD60A", "#30D158", "#0A84FF", "#BF5AF2"];
const TRACK_ALPHA = 0.22;
const GHOST_ALPHA = 0.42;
const INNER_ALPHA = 0.6;
const RING = { small: 58, medium: 56, large: 60 };
const TILE = { medium: 68, large: 70 };
const RECENT_ROWS = { medium: 3, large: 7 };
const LIST_ROWS = 7;
const FETCH_TIMEOUT_S = 8;
const UNREACHABLE = { symbol: "wifi.exclamationmark", title: "Can't reach openclaw", detail: "Nothing saved to show yet" };
const BROKEN = { symbol: "exclamationmark.triangle", title: "Widget couldn't draw", detail: "Run it in Scriptable to see the log" };
const ART_WIDTH = 332;

const PROVIDERS = {
  "openai-codex": { name: "Codex", logo: "openai", tint: "#F2F2F7" },
  openai: { name: "OpenAI", logo: "openai", tint: "#F2F2F7" },
  anthropic: { name: "Claude", logo: "anthropic", tint: "#D97757" },
  "google-antigravity": { name: "Antigravity", logo: "google", tint: "#3186FF" },
  "antigravity-cli": { name: "Antigravity", logo: "google", tint: "#3186FF" },
  "opencode-go": { name: "OpenCode", logo: "opencode", tint: "#AEAEB2" },
  zai: { name: "ZAI", logo: "zai", tint: "#8E93B8" },
  openrouter: { name: "OpenRouter", logo: null, tint: NEUTRAL_HEX },
};
const LOGOS = {
  openai: [
    {
      fill: "#FFFFFF",
      d: "M13.79 23.89Q12.6 23.89 11.53 23.44C10.82 23.14 10.18 22.71 9.63 22.18 9.02 22.39 8.39 22.49 7.75 22.49 6.71 22.5 5.69 22.23 4.8 21.7 3.9 21.19 3.15 20.45 2.61 19.56 2.07 18.65 1.79 17.61 1.8 16.54Q1.8 15.85 1.99 15.04C1.37 14.48 0.87 13.79 0.52 13.02 -0.19 11.46 -0.18 9.67 0.54 8.12 0.9 7.34 1.42 6.64 2.07 6.08 2.73 5.49 3.52 5.08 4.37 4.86 4.54 3.98 4.91 3.15 5.47 2.44Q6.32 1.34 7.56 0.73C8.38 0.32 9.28 0.1 10.2 0.11Q11.39 0.11 12.46 0.56 13.53 1.01 14.36 1.82C14.97 1.61 15.6 1.51 16.24 1.51Q17.83 1.51 19.19 2.3C20.08 2.81 20.83 3.55 21.35 4.44Q22.19 5.79 22.19 7.46 22.19 8.15 22 8.96 22.95 9.83 23.47 11 23.99 12.14 23.99 13.4 23.99 14.69 23.45 15.88C23.08 16.67 22.56 17.37 21.9 17.95 21.25 18.52 20.46 18.93 19.62 19.14 19.45 20.02 19.07 20.86 18.5 21.56 17.95 22.28 17.24 22.87 16.43 23.27 15.61 23.68 14.71 23.9 13.79 23.89M7.91 20.92Q9.1 20.92 9.98 20.42L14.46 17.85C14.61 17.75 14.7 17.58 14.69 17.4V15.35L8.94 18.66C8.62 18.86 8.21 18.86 7.89 18.66L3.4 16.07C3.4 16.12 3.39 16.18 3.37 16.23V16.52Q3.37 17.73 3.94 18.75 4.54 19.75 5.59 20.32C6.3 20.72 7.1 20.93 7.92 20.92M8.15 17.04C8.23 17.09 8.32 17.11 8.42 17.11Q8.53 17.11 8.65 17.04L10.44 16.02 4.7 12.69C4.37 12.5 4.17 12.14 4.18 11.76V6.6Q2.99 7.12 2.28 8.22C1.81 8.92 1.56 9.75 1.57 10.6Q1.57 11.76 2.16 12.83 2.75 13.9 3.71 14.45ZM13.79 22.32Q15.05 22.32 16.07 21.75C17.46 20.99 18.31 19.52 18.29 17.94V12.81C18.3 12.63 18.2 12.46 18.05 12.38L16.24 11.33V17.97C16.26 18.35 16.05 18.71 15.72 18.9L11.22 21.49C11.97 22.03 12.87 22.33 13.79 22.32M14.7 13.62V10.38L12.01 8.86 9.3 10.38V13.62L12.01 15.14ZM7.75 6.03C7.73 5.65 7.94 5.29 8.27 5.1L12.77 2.51C12.02 1.97 11.12 1.67 10.2 1.68Q8.94 1.68 7.92 2.25C7.25 2.62 6.69 3.16 6.3 3.82 5.91 4.5 5.72 5.27 5.73 6.05V11.17Q5.73 11.45 5.97 11.62L7.75 12.67ZM19.83 17.4Q21.02 16.87 21.71 15.78 22.43 14.69 22.43 13.4C22.42 12.62 22.22 11.85 21.83 11.17Q21.24 10.1 20.29 9.55L15.84 6.98Q15.69 6.89 15.58 6.91C15.49 6.91 15.41 6.94 15.34 6.98L13.55 7.98 19.31 11.33C19.47 11.42 19.61 11.55 19.69 11.71 19.79 11.87 19.84 12.05 19.83 12.24ZM15.05 5.32C15.37 5.1 15.79 5.1 16.1 5.32L20.62 7.96V7.53Q20.62 6.39 20.05 5.37C19.69 4.67 19.13 4.09 18.45 3.7Q17.43 3.08 16.08 3.08 14.89 3.08 14.01 3.58L9.53 6.15C9.38 6.25 9.29 6.42 9.3 6.6V8.65Z",
    },
  ],
  anthropic: [
    {
      fill: "#D97757",
      d: "M4.7 15.96L9.43 13.32 9.5 13.08 9.43 12.96H9.19L8.4 12.91 5.71 12.84 3.36 12.72 1.08 12.6 0.5 12.48 0 11.76 0.05 11.4 0.53 11.09 1.22 11.14 2.74 11.26 5.02 11.4 6.67 11.5 9.12 11.78H9.5L9.55 11.62 9.43 11.52 9.34 11.42 6.96 9.84 4.42 8.16 3.07 7.18 2.35 6.7 1.99 6.22 1.85 5.21 2.5 4.49 3.38 4.56 3.6 4.61 4.49 5.3 6.41 6.77 8.88 8.64 9.24 8.93 9.38 8.83 9.41 8.76 9.24 8.5 7.92 6 6.48 3.5 5.83 2.47 5.66 1.85C5.59 1.61 5.57 1.37 5.57 1.13L6.29 0.12 6.72 0 7.73 0.14 8.11 0.48 8.74 1.92 9.72 4.15 11.28 7.18 11.76 8.09 12 8.9 12.07 9.14H12.24V9.02L12.36 7.3 12.6 5.21 12.84 2.52 12.91 1.75 13.3 0.84 14.02 0.36 14.64 0.62 15.12 1.32 15.05 1.75 14.78 3.6 14.16 6.5 13.8 8.47H14.02L14.26 8.21 15.24 6.91 16.9 4.85 17.62 4.01 18.48 3.12 19.03 2.69H20.06L20.81 3.82 20.47 4.99 19.42 6.34 18.53 7.46 17.26 9.17 16.49 10.54 16.56 10.63H16.73L19.61 10.01 21.14 9.74 22.97 9.43 23.81 9.82 23.9 10.2 23.57 11.02 21.6 11.5 19.3 11.98 15.86 12.77 15.82 12.79 15.86 12.86 17.4 13.01 18.07 13.06H19.7L22.73 13.3 23.52 13.78 23.98 14.42 23.9 14.9 22.68 15.53 21.05 15.14 17.21 14.23 15.91 13.92H15.72V14.02L16.82 15.1 18.82 16.9 21.36 19.22 21.48 19.8 21.17 20.28 20.83 20.23 18.62 18.55 17.76 17.83 15.84 16.2H15.72V16.37L16.15 17.02 18.5 20.54 18.62 21.62 18.46 21.96 17.83 22.2 17.18 22.06 15.79 20.14 14.35 17.98 13.22 16.01 13.1 16.1 12.41 23.35 12.1 23.71 11.38 24 10.78 23.52 10.44 22.8 10.78 21.31 11.16 19.39 11.47 17.86 11.76 15.96 11.93 15.34V15.29H11.76L10.32 17.28 8.16 20.23 6.43 22.06 6.02 22.22 5.3 21.86 5.38 21.19 5.76 20.64 8.16 17.57 9.6 15.67 10.56 14.57 10.54 14.45H10.46L4.13 18.58 3 18.72 2.52 18.24 2.57 17.52 2.81 17.28 4.73 15.96Z",
    },
  ],
  google: [
    { fill: "#4285F4", d: "M22.56 12.25C22.56 11.47 22.49 10.72 22.36 10H12V14.26H17.92C17.66 15.63 16.88 16.79 15.71 17.57V20.34H19.28C21.36 18.42 22.56 15.6 22.56 12.25Z" },
    { fill: "#34A853", d: "M12 23C14.97 23 17.46 22.02 19.28 20.34L15.71 17.57C14.73 18.23 13.48 18.63 12 18.63 9.14 18.63 6.71 16.7 5.84 14.1H2.18V16.94C3.99 20.53 7.7 23 12 23Z" },
    { fill: "#FBBC05", d: "M5.84 14.09C5.62 13.43 5.49 12.73 5.49 12 5.49 11.27 5.62 10.57 5.84 9.91V7.07H2.18C1.43 8.55 1 10.22 1 12 1 13.78 1.43 15.45 2.18 16.93L5.03 14.71 5.84 14.09Z" },
    { fill: "#EA4335", d: "M12 5.38C13.62 5.38 15.06 5.94 16.21 7.02L19.36 3.87C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07L5.84 9.91C6.71 7.31 9.14 5.38 12 5.38Z" },
  ],
  opencode: [{ fill: "#FFFFFF", d: "M16.8 4.8H7.2V19.2H16.8V4.8ZM21.6 24H2.4V0H21.6V24Z" }],
  zai: [
    {
      fill: "#2D2D2D",
      stroke: "#FFFFFF",
      d: "M20.45 24H3.55C1.59 24 0 22.41 0 20.45V3.55C0 1.59 1.59 0 3.55 0H20.46C22.42 0 24.01 1.59 24.01 3.55V20.46C24 22.41 22.41 24 20.45 24Z",
    },
    { fill: "#FFFFFF", d: "M12.42 4.98L11.26 6.63C11.09 6.88 10.78 7.04 10.46 7.04H4.16V4.97C4.15 4.98 12.42 4.98 12.42 4.98Z" },
    { fill: "#FFFFFF", d: "M11.58 19.03L12.75 17.37C12.92 17.12 13.23 16.96 13.55 16.96H19.84V19.03H11.58Z" },
    { fill: "#FFFFFF", d: "M20.26 4.98L10.35 19.03 3.74 19.03 13.65 4.98Z" },
  ],
};

const files = FileManager.local();
const cacheDir = files.joinPath(files.libraryDirectory(), "omp-usage");
const feedPath = files.joinPath(cacheDir, "widget.json");
const viewPath = files.joinPath(cacheDir, "view.txt");
const turnPath = files.joinPath(cacheDir, "forecast-turn.txt");
const usageTurnPath = files.joinPath(cacheDir, "usage-turn.txt");
const logoCache = {};

function ensureCacheDir() {
  if (!files.fileExists(cacheDir)) files.createDirectory(cacheDir, true);
}

async function fetchFeed() {
  const request = new Request(`${BASE}widget.json`);
  request.timeoutInterval = FETCH_TIMEOUT_S;
  const feed = await request.loadJSON();
  const status = request.response && request.response.statusCode;
  if (status !== 200) throw new Error(`HTTP ${status} for ${request.url}`);
  return feed;
}

function decode(feed, family) {
  if (!feed || feed.schema !== FEED_SCHEMA) throw new Error(`Unsupported schema ${feed && feed.schema}`);
  if (HOME.includes(family) && !(Array.isArray(feed.windows) && Array.isArray(feed.recent))) {
    throw new Error("Feed has no windows or recent activity");
  }
  if (!HOME.includes(family) && !feed.lock) throw new Error("Feed has no lock summary");
  return feed;
}

function readCache(family) {
  if (!files.fileExists(feedPath)) return null;
  try {
    const feed = decode(JSON.parse(files.readString(feedPath)), family);
    return { feed, savedMs: files.modificationDate(feedPath).getTime() };
  } catch (error) {
    console.error(error);
    return null;
  }
}

async function snapshot(family, action) {
  const cached = readCache(family);
  const switching = VIEW_IDS.includes(action) || action === NEXT_ACTION || action === USAGE_NEXT_ACTION;
  if (switching && cached) return { feed: cached.feed, offline: false };
  try {
    const feed = decode(await fetchFeed(), family);
    ensureCacheDir();
    files.writeString(feedPath, JSON.stringify(feed));
    return { feed, offline: false };
  } catch (error) {
    console.error(error);
    return cached ? { feed: cached.feed, offline: true } : null;
  }
}

function savedView() {
  if (!files.fileExists(viewPath)) return "now";
  const view = files.readString(viewPath);
  return VIEW_IDS.includes(view) ? view : "now";
}

function saveView(view) {
  ensureCacheDir();
  files.writeString(viewPath, view);
}

function usageTurn() {
  if (!files.fileExists(usageTurnPath)) return 0;
  const turn = Number.parseInt(files.readString(usageTurnPath), 10);
  return Number.isFinite(turn) ? turn : 0;
}

function advanceUsage() {
  ensureCacheDir();
  files.writeString(usageTurnPath, String(usageTurn() + 1));
}

function forecastTurn() {
  if (!files.fileExists(turnPath)) return 0;
  const turn = Number.parseInt(files.readString(turnPath), 10);
  return Number.isFinite(turn) ? turn : 0;
}

function advanceForecast() {
  ensureCacheDir();
  files.writeString(turnPath, String(forecastTurn() + 1));
}

function detailUrl(view) {
  return `${BASE}detail.html#${view}`;
}

function dayOffset(date, now) {
  const start = (moment) => new Date(moment.getFullYear(), moment.getMonth(), moment.getDate()).getTime();
  return Math.round((start(date) - start(now)) / DAY_MS);
}

function formatted(ms, today, week, later) {
  const date = new Date(ms);
  const days = dayOffset(date, new Date());
  const formatter = new DateFormatter();
  if (days === 0) formatter.dateFormat = today;
  else if (days > 0 && days < 7) formatter.dateFormat = week;
  else formatter.dateFormat = later;
  return formatter.string(date);
}

function clock(ms) {
  return formatted(ms, "HH:mm", "EEE HH:mm", "MMM d");
}

function day(ms) {
  return formatted(ms, "HH:mm", "EEE", "MMM d");
}

function age(ms) {
  const minutes = Math.max(1, Math.round(ms / MINUTE_MS));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours}h` : `${Math.round(hours / 24)}d`;
}

function duration(ms) {
  const minutes = Math.max(1, Math.round(ms / MINUTE_MS));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return minutes % 60 ? `${hours}h ${minutes % 60}m` : `${hours}h`;
  const days = Math.floor(hours / 24);
  return hours % 24 ? `${days}d ${hours % 24}h` : `${days}d`;
}

function percent(used) {
  if (used === null) return "–";
  if (used >= 99.95) return "100%";
  if (used > 0 && used < 1) return "<1%";
  return `${Math.floor(used)}%`;
}

function windowName(entry) {
  return `${entry.provider} ${entry.window}`;
}

function status(entry, now) {
  const reset = entry.reset_ms !== null && entry.reset_ms > now ? clock(entry.reset_ms) : "";
  const share = entry.projected !== null ? `~${Math.round(entry.projected)}%` : "";
  switch (entry.state) {
    case "exhausted":
      return reset ? `Out till ${reset}` : "Out";
    case "run_out": {
      const rounded = Math.max(Math.round(entry.out_ms / OUT_STEP_MS) * OUT_STEP_MS, now + OUT_STEP_MS);
      return `Out ~${clock(rounded)}`;
    }
    case "gated":
      return "Gated";
    case "near":
      return "Near limit";
    case "hot":
    case "on_pace":
      if (!share) return reset ? `Resets ${reset}` : "";
      return reset ? `${share} by ${reset}` : `${share} at reset`;
    case "spare":
      return reset ? `Spare till ${reset}` : "Spare";
    default:
      return reset ? `Resets ${reset}` : "";
  }
}

function countdown(entry, now) {
  const within = (target) => target !== null && target > now && target - now < DAY_MS;
  if (entry.state === "run_out" && within(entry.out_ms)) return { prefix: "Out in ", target: entry.out_ms };
  if (entry.state === "exhausted" && within(entry.reset_ms)) return { prefix: "Back in ", target: entry.reset_ms };
  return null;
}

function brief(entry, state) {
  const tail = state ? `, ${state.charAt(0).toLowerCase()}${state.slice(1)}` : "";
  return `${windowName(entry)} ${percent(entry.used)}${tail}`;
}

function symbolImage(name, size) {
  const symbol = SFSymbol.named(name);
  symbol.applyFont(Font.semiboldSystemFont(size));
  return symbol.image;
}

function addSymbol(stack, name, size, color) {
  const image = stack.addImage(symbolImage(name, size));
  image.imageSize = new Size(size, size);
  if (color) image.tintColor = color;
  return image;
}

function addLine(stack, text, font, opacity) {
  const line = stack.addText(text);
  line.font = font;
  line.lineLimit = 1;
  line.minimumScaleFactor = 0.7;
  if (opacity !== undefined) line.textOpacity = opacity;
  return line;
}

function addLabel(stack, text, font, color) {
  const line = stack.addText(text);
  line.font = font;
  line.textColor = color;
  line.lineLimit = 1;
  return line;
}

function addRow(parent) {
  const row = parent.addStack();
  row.layoutHorizontally();
  row.centerAlignContent();
  return row;
}

function addCentered(parent) {
  const row = addRow(parent);
  row.addSpacer();
  const inner = addRow(row);
  row.addSpacer();
  return inner;
}

function providerName(provider) {
  const known = PROVIDERS[provider];
  if (known) return known.name;
  return provider
    .split(/[-_]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function ownerName(entry) {
  const name = providerName(entry.provider);
  return entry.account ? `${name} ${entry.account}` : name;
}

function tintHex(provider) {
  const known = PROVIDERS[provider];
  return known ? known.tint : NEUTRAL_HEX;
}

function modelName(model) {
  return model.replace(/-\d{8}$/, "");
}

function share(value) {
  return Math.min(Math.max(value, 0), 100) / 100;
}

function isOut(entry) {
  return entry.state === "exhausted" || (entry.used !== null && entry.used >= 99.95);
}

function runsDry(entry) {
  return entry.cutoff_ms !== null && (entry.reset_ms === null || entry.cutoff_ms < entry.reset_ms);
}

function stateHex(entry) {
  if (isOut(entry)) return OUT_HEX;
  return entry.signal === "hot" ? HEAT_HEX : tintHex(entry.provider);
}

function figureColor(entry) {
  if (isOut(entry)) return OUT;
  return entry.signal === "hot" ? HEAT : LABEL;
}

function cutoffTime(entry, now) {
  return Math.max(Math.round(entry.cutoff_ms / OUT_STEP_MS) * OUT_STEP_MS, now + OUT_STEP_MS);
}

function risk(entry, now, time) {
  if (isOut(entry)) return entry.reset_ms !== null ? `Back ${time(entry.reset_ms)}` : "Out";
  return runsDry(entry) ? `Out ~${time(cutoffTime(entry, now))}` : "";
}

function verdictColor(entry) {
  if (isOut(entry)) return OUT;
  return runsDry(entry) ? HEAT : SECONDARY;
}

function providerGroups(windows) {
  const owners = new Map();
  for (const entry of windows) {
    if (entry.used === null) continue;
    const key = `${entry.provider}/${entry.account}`;
    if (!owners.has(key)) owners.set(key, []);
    owners.get(key).push(entry);
  }
  return [...owners.values()].map((all) => {
    const hot = all.some((entry) => entry.signal === "hot");
    const chance = hot ? null : all.find((entry) => entry.signal === "opportunity") || null;
    const focus = chance || all[0];
    return { provider: focus.provider, focus, second: all.find((entry) => entry !== focus) || null, hot, chance: chance !== null };
  });
}

function heroGroup(groups) {
  return groups.find((group) => group.hot) || groups.find((group) => group.chance) || groups[0] || null;
}

function forecast(entry, now) {
  const reset = entry.reset_ms;
  if (isOut(entry)) return { kind: "out", cutoff: now, reset };
  if (runsDry(entry)) return { kind: "short", cutoff: entry.cutoff_ms, reset };
  if (reset === null) return null;
  return { kind: entry.projected !== null ? "lasts" : "reset", cutoff: null, reset };
}

function headline(plan, entry, now) {
  switch (plan.kind) {
    case "out":
      return plan.reset !== null ? [duration(plan.reset - now), "until it's back"] : ["Out", "no reset reported"];
    case "short":
      return plan.reset !== null
        ? [duration(plan.reset - plan.cutoff), `dry before reset · out ${clock(plan.cutoff)}`]
        : [duration(plan.cutoff - now), "until it runs out"];
    case "lasts":
      return [`~${Math.round(entry.projected)}%`, `used by ${clock(plan.reset)}`];
    default:
      return [duration(plan.reset - now), "until reset"];
  }
}

function headlineColor(plan) {
  if (plan.kind === "out") return OUT;
  return plan.kind === "short" ? HEAT : LABEL;
}

function forecastBrief(plan, entry) {
  switch (plan.kind) {
    case "out":
      return plan.reset !== null ? `Back ${day(plan.reset)}` : "Out";
    case "short":
      return plan.reset !== null ? `${duration(plan.reset - plan.cutoff)} dry` : `Out ${day(plan.cutoff)}`;
    case "lasts":
      return `~${Math.round(entry.projected)}% by ${day(plan.reset)}`;
    default:
      return `Resets ${day(plan.reset)}`;
  }
}

function canvas(width, height) {
  const context = new DrawContext();
  context.size = new Size(width, height);
  context.opaque = false;
  context.respectScreenScale = true;
  return context;
}

function fillRounded(context, rect, color) {
  const path = new Path();
  path.addRoundedRect(rect, rect.height / 2, rect.height / 2);
  context.addPath(path);
  context.setFillColor(color);
  context.fillPath();
}

function logoPath(d, scale, dx, dy) {
  const tokens = d.match(/[MLHVCQZ]|-?(?:\d+\.?\d*|\.\d+)/g);
  const path = new Path();
  let index = 0;
  let command = "M";
  let x = dx;
  let y = dy;
  const number = () => Number(tokens[index++]) * scale;
  const point = () => {
    const px = number() + dx;
    const py = number() + dy;
    return new Point(px, py);
  };
  while (index < tokens.length) {
    if (/[A-Z]/.test(tokens[index])) command = tokens[index++];
    if (command === "Z") {
      path.closeSubpath();
      continue;
    }
    if (command === "M" || command === "L") {
      const target = point();
      if (command === "M") path.move(target);
      else path.addLine(target);
      command = "L";
      x = target.x;
      y = target.y;
    } else if (command === "H" || command === "V") {
      if (command === "H") x = number() + dx;
      else y = number() + dy;
      path.addLine(new Point(x, y));
    } else if (command === "C") {
      const first = point();
      const second = point();
      const target = point();
      path.addCurve(target, first, second);
      x = target.x;
      y = target.y;
    } else {
      const control = point();
      const target = point();
      path.addQuadCurve(target, control);
      x = target.x;
      y = target.y;
    }
  }
  return path;
}

function drawLogo(context, provider, x, y, size) {
  const known = PROVIDERS[provider];
  const layers = known && known.logo ? LOGOS[known.logo] : null;
  if (!layers) {
    context.setFillColor(new Color(tintHex(provider), 0.35));
    context.fillEllipse(new Rect(x, y, size, size));
    context.setFont(Font.boldRoundedSystemFont(Math.round(size * 0.58)));
    context.setTextColor(LABEL);
    context.setTextAlignedCenter();
    context.drawTextInRect(providerName(provider).charAt(0).toUpperCase(), new Rect(x, y + size * 0.12, size, size));
    return;
  }
  const scale = size / 24;
  for (const layer of layers) {
    context.addPath(logoPath(layer.d, scale, x, y));
    context.setFillColor(new Color(layer.fill));
    context.fillPath();
    if (layer.stroke) {
      context.addPath(logoPath(layer.d, scale, x, y));
      context.setStrokeColor(new Color(layer.stroke));
      context.setLineWidth(0.6 * scale);
      context.strokePath();
    }
  }
}

function logoImage(provider, size) {
  const key = `${provider}@${size}`;
  if (logoCache[key]) return logoCache[key];
  const context = canvas(size, size);
  drawLogo(context, provider, 0, 0, size);
  logoCache[key] = context.getImage();
  return logoCache[key];
}

function addLogo(stack, provider, size) {
  const image = stack.addImage(logoImage(provider, size));
  image.imageSize = new Size(size, size);
  return image;
}

function ringPair(group) {
  const pair = [group.focus, group.second].filter(Boolean);
  return pair.sort((a, b) => (b.window_ms || 0) - (a.window_ms || 0));
}

function segmentCount(entry) {
  if (!entry.window_ms) return 1;
  const unit = entry.window_ms >= DAY_MS ? DAY_MS : HOUR_MS;
  const count = Math.round(entry.window_ms / unit);
  return count >= 2 && count <= 12 ? count : 1;
}

function segmentedArc(context, center, radius, width, entry, strength) {
  const hex = stateHex(entry);
  const count = segmentCount(entry);
  const used = share(entry.used);
  if (count === 1) {
    arc(context, center, radius, 0, 360, new Color(hex, TRACK_ALPHA * strength), width, false);
    if (used > 0) arc(context, center, radius, -90, -90 + 360 * Math.max(used, 0.015), new Color(hex, strength), width, true);
    return;
  }
  const span = 360 / count;
  const gap = Math.min(span * 0.25, (width * 0.9 * 180) / (Math.PI * radius));
  for (let index = 0; index < count; index += 1) {
    const start = -90 + index * span + gap / 2;
    const end = start + span - gap;
    arc(context, center, radius, start, end, new Color(hex, TRACK_ALPHA * strength), width, false);
    const filled = Math.min(Math.max(used * count - index, 0), 1);
    if (filled > 0) arc(context, center, radius, start, start + (end - start) * Math.max(filled, 0.12), new Color(hex, strength), width, false);
  }
}

function ringImage(group, size) {
  const context = canvas(size, size);
  const center = size / 2;
  const gap = 2;
  let width = Math.round(size * 0.115 * 2) / 2;
  let radius = center - width / 2;
  let hole = radius - width / 2;
  ringPair(group).forEach((entry, index) => {
    segmentedArc(context, center, radius, width, entry, index === 0 ? 1 : INNER_ALPHA);
    hole = radius - width / 2;
    const next = Math.max(width - 1.5, 3);
    radius = hole - gap - next / 2;
    width = next;
  });
  const logo = Math.min(Math.floor((hole - 3) * 1.36), Math.round(size * 0.4));
  drawLogo(context, group.provider, center - logo / 2, center - logo / 2, logo);
  return context.getImage();
}

function drawBar(context, entry, top, width, height) {
  const hex = stateHex(entry);
  fillRounded(context, new Rect(0, top, width, height), new Color(hex, TRACK_ALPHA));
  const used = share(entry.used);
  const ghost = entry.projected !== null ? share(entry.projected) : 0;
  if (ghost > used) fillRounded(context, new Rect(0, top, Math.max(height, width * ghost), height), new Color(hex, GHOST_ALPHA));
  if (used > 0) fillRounded(context, new Rect(0, top, Math.max(height, width * used), height), new Color(hex));
}

function barImage(entry, width, height) {
  const context = canvas(width, height);
  drawBar(context, entry, 0, width, height);
  return context.getImage();
}

function timelineImage(plan, entry, now) {
  const width = ART_WIDTH;
  const bar = 8;
  const top = 4;
  const context = canvas(width, 32);
  let left = `${percent(entry.used)} used`;
  let right = plan.reset !== null ? `Resets ${clock(plan.reset)}` : "";
  if (plan.kind === "out" || plan.kind === "short") {
    const end = plan.reset !== null ? plan.reset : plan.cutoff;
    const cut = plan.kind === "out" ? 0 : (Math.min(Math.max(plan.cutoff - now, 0), end - now) / Math.max(end - now, 1)) * width;
    fillRounded(context, new Rect(0, top, width, bar), plan.reset !== null ? OUT : new Color(tintHex(entry.provider), TRACK_ALPHA));
    if (cut > 0) fillRounded(context, new Rect(0, top, Math.max(cut, bar), bar), new Color(tintHex(entry.provider)));
    if (plan.kind === "short") {
      const knob = Math.min(Math.max(cut, 7), width - 7);
      context.setFillColor(CANVAS);
      context.fillEllipse(new Rect(knob - 8, top + bar / 2 - 8, 16, 16));
      context.setFillColor(LABEL);
      context.fillEllipse(new Rect(knob - 5, top + bar / 2 - 5, 10, 10));
    }
    left = plan.kind === "out" ? "Out now" : "Now";
    if (plan.reset === null) right = `Out ${clock(plan.cutoff)}`;
    else if (plan.kind === "out") right = `Back ${clock(plan.reset)}`;
  } else {
    drawBar(context, entry, top, width, bar);
  }
  const below = top + bar + 6;
  context.setFont(Font.mediumSystemFont(11));
  context.setTextColor(SECONDARY);
  context.setTextAlignedLeft();
  context.drawTextInRect(left, new Rect(0, below, width / 2, 14));
  context.setTextAlignedRight();
  context.drawTextInRect(right, new Rect(width / 2, below, width / 2, 14));
  return context.getImage();
}

function rainbow() {
  const gradient = new LinearGradient();
  gradient.colors = RAINBOW.map((hex) => new Color(hex));
  gradient.locations = RAINBOW.map((_, index) => index / (RAINBOW.length - 1));
  gradient.startPoint = new Point(0, 0);
  gradient.endPoint = new Point(1, 1);
  return gradient;
}

function addFlame(stack, entry, size) {
  addSymbol(stack, "flame.fill", size, isOut(entry) ? OUT : HEAT);
}

function addTile(row, group, family, now) {
  const ring = RING[family];
  const frame = row.addStack();
  frame.cornerRadius = 15;
  frame.setPadding(1.5, 1.5, 1.5, 1.5);
  if (group.chance) frame.backgroundGradient = rainbow();
  const tile = frame.addStack();
  tile.layoutVertically();
  tile.backgroundColor = CANVAS;
  tile.cornerRadius = 13.5;
  tile.size = new Size(TILE[family], 0);
  tile.setPadding(4, 0, 4, 0);
  const art = addCentered(tile).addImage(ringImage(group, ring));
  art.imageSize = new Size(ring, ring);
  tile.addSpacer(4);
  ringPair(group).forEach((entry, index) => addRingKey(tile, entry, index === 0 ? "outer" : "inner", entry === group.focus));
  const caption = addCentered(tile);
  if (group.hot) {
    addFlame(caption, group.focus, 9);
    caption.addSpacer(2);
  }
  if (!addVerdict(caption, group.focus, now, day, 10)) addLabel(caption, ownerName(group.focus), Font.mediumSystemFont(10), SECONDARY);
}

function ringKeyImage(which, hex) {
  const size = 10;
  const context = canvas(size, size);
  const center = size / 2;
  arc(context, center, 4, 0, 360, new Color(hex, which === "outer" ? 1 : TRACK_ALPHA), 1.6, false);
  arc(context, center, 1.6, 0, 360, new Color(hex, which === "inner" ? 1 : TRACK_ALPHA), 1.6, false);
  return context.getImage();
}

function addRingKey(tile, entry, which, strong) {
  const line = addCentered(tile);
  line.centerAlignContent();
  line.addImage(ringKeyImage(which, stateHex(entry))).imageSize = new Size(8, 8);
  line.addSpacer(2);
  const figure = addLabel(line, percent(entry.used), strong ? Font.boldRoundedSystemFont(12) : Font.semiboldRoundedSystemFont(11), strong ? figureColor(entry) : SECONDARY);
  figure.lineLimit = 1;
  figure.minimumScaleFactor = 0.6;
  line.addSpacer(2);
  const label = addLabel(line, entry.short, Font.mediumSystemFont(9), SECONDARY);
  label.lineLimit = 1;
  label.minimumScaleFactor = 0.5;
}

function addVerdict(stack, entry, now, time, size) {
  const text = risk(entry, now, time);
  if (text) {
    addLabel(stack, text, Font.mediumSystemFont(size), verdictColor(entry)).minimumScaleFactor = 0.8;
    return true;
  }
  if (entry.reset_ms === null) return false;
  addSymbol(stack, "clock", size - 1, SECONDARY);
  stack.addSpacer(3);
  addLabel(stack, time(entry.reset_ms), Font.mediumSystemFont(size), SECONDARY).minimumScaleFactor = 0.8;
  return true;
}

function addRings(body, groups, family, now) {
  const row = addRow(body);
  const spread = groups.length === 4;
  groups.forEach((group, index) => {
    if (index) row.addSpacer(spread ? null : 10);
    addTile(row, group, family, now);
  });
  if (!spread) row.addSpacer();
}

function addWindowTitle(row, entry, size) {
  addLogo(row, entry.provider, size + 3);
  row.addSpacer(7);
  addLabel(row, ownerName(entry), Font.semiboldSystemFont(size), LABEL);
  row.addSpacer(4);
  addLabel(row, entry.short, Font.regularSystemFont(size), SECONDARY);
  if (entry.signal !== "hot") return;
  row.addSpacer(4);
  addFlame(row, entry, size - 1);
}

function addWindowRow(body, entry, now) {
  const row = addRow(body);
  addWindowTitle(row, entry, 13);
  row.addSpacer();
  if (entry.used === null) {
    addLabel(row, "Limit unknown", Font.regularSystemFont(12), SECONDARY);
    return;
  }
  addVerdict(row, entry, now, day, 12);
  row.addSpacer(8);
  row.addImage(barImage(entry, 48, 5)).imageSize = new Size(48, 5);
  const figure = row.addStack();
  figure.size = new Size(38, 0);
  figure.addSpacer();
  addLabel(figure, percent(entry.used), Font.semiboldRoundedSystemFont(13), figureColor(entry));
}

function addNote(body, text) {
  const row = addRow(body);
  addLabel(row, text, Font.mediumSystemFont(13), SECONDARY);
  row.addSpacer();
}

function nowView(body, family, feed, now) {
  const windows = feed.windows;
  if (!windows.length) return addNote(body, "No quota windows yet");
  const groups = providerGroups(windows);
  if (groups.length) addRings(body, groups.slice(0, 4), family, now);
  else addNote(body, "No provider reports a limit");
  if (family !== "large" && groups.length) return;
  const rows = windows.slice(0, groups.length ? LIST_ROWS : 2);
  body.addSpacer(groups.length ? 16 : 10);
  rows.forEach((entry, index) => {
    if (index) body.addSpacer(10);
    addWindowRow(body, entry, now);
  });
}

function addForecastHero(body, item, now, position, count) {
  const head = addRow(body);
  addWindowTitle(head, item.entry, 14);
  head.addSpacer();
  if (count < 2) return addForecastBody(body, item, now);
  addLabel(head, `${position + 1}/${count}`, Font.semiboldRoundedSystemFont(11), SECONDARY);
  head.addSpacer(3);
  addSymbol(head, "chevron.right", 9, SECONDARY);
  addForecastBody(body, item, now);
}

function addForecastBody(body, item, now) {
  body.addSpacer(3);
  const [value, caption] = headline(item.plan, item.entry, now);
  const figure = body.addStack();
  figure.layoutHorizontally();
  figure.bottomAlignContent();
  addLabel(figure, value, Font.boldRoundedSystemFont(26), headlineColor(item.plan));
  figure.addSpacer(6);
  const note = figure.addStack();
  note.setPadding(0, 0, 4, 0);
  addLabel(note, caption, Font.mediumSystemFont(13), SECONDARY).minimumScaleFactor = 0.75;
  body.addSpacer(5);
  const art = body.addStack();
  art.size = new Size(0, 32);
  art.addImage(timelineImage(item.plan, item.entry, now));
}

function forecastView(body, family, feed, now) {
  const items = feed.windows
    .filter((entry) => entry.used !== null)
    .map((entry) => ({ entry, plan: forecast(entry, now) }))
    .filter((item) => item.plan !== null);
  if (!items.length) return addNote(body, "No resets to forecast yet");
  const owners = new Set();
  const leads = items.filter((item) => {
    const key = `${item.entry.provider}/${item.entry.account}`;
    if (owners.has(key)) return false;
    owners.add(key);
    return true;
  });
  const lead = leads[forecastTurn() % leads.length];
  addForecastHero(body, lead, now, leads.indexOf(lead), leads.length);
  if (family !== "large") return;
  const rest = items.filter((item) => item !== lead).slice(0, LIST_ROWS);
  if (!rest.length) return;
  body.addSpacer(16);
  rest.forEach((item, index) => {
    if (index) body.addSpacer(9);
    const row = addRow(body);
    addWindowTitle(row, item.entry, 13);
    row.addSpacer();
    addLabel(row, forecastBrief(item.plan, item.entry), Font.mediumSystemFont(12), headlineColor(item.plan) === LABEL ? SECONDARY : headlineColor(item.plan));
    row.addSpacer(8);
    row.addImage(barImage(item.entry, 48, 5)).imageSize = new Size(48, 5);
  });
}

function latestPerModel(recent) {
  const seen = new Set();
  return recent.filter((record) => {
    const key = `${record.provider}/${record.model}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function recentView(body, family, feed, now) {
  const records = latestPerModel(feed.recent).slice(0, RECENT_ROWS[family]);
  if (!records.length) return addNote(body, "No sessions in the last 7 days");
  records.forEach((record, index) => {
    if (index) body.addSpacer(family === "large" ? 14 : 6);
    const row = addRow(body);
    addLogo(row, record.provider, 20);
    row.addSpacer(9);
    const text = row.addStack();
    text.layoutVertically();
    addLabel(text, record.title || record.project || "Untitled session", Font.semiboldSystemFont(13), LABEL);
    const detail = addRow(text);
    addLabel(detail, modelName(record.model), Font.regularSystemFont(11), SECONDARY);
    if (record.title && record.project) {
      detail.addSpacer(6);
      addLabel(detail, record.project, Font.regularSystemFont(11), TERTIARY);
    }
    row.addSpacer();
    row.addSpacer(8);
    addLabel(row, age(now - record.at_ms), Font.mediumRoundedSystemFont(12), SECONDARY);
  });
}

function offlineText(feed) {
  return `Offline · updated ${clock(feed.generated_at_ms)}`;
}

function addControls(widget, view, result) {
  const row = addRow(widget);
  const control = row.addStack();
  control.backgroundColor = RAISED;
  control.cornerRadius = 9;
  control.setPadding(2, 2, 2, 2);
  for (const id of VIEW_IDS) {
    const segment = control.addStack();
    segment.cornerRadius = 7;
    segment.setPadding(4, 10, 4, 10);
    if (id === view) segment.backgroundColor = SELECTED;
    addLabel(segment, VIEW_TITLES[id], Font.semiboldSystemFont(12), id === view ? LABEL : SECONDARY);
    segment.setAction(VIEW_TITLES[id], { id });
  }
  row.addSpacer();
  addGoTo(row, detailUrl(view));
  row.addSpacer(6);
  const refresh = row.addStack();
  refresh.centerAlignContent();
  refresh.cornerRadius = 12;
  if (result.offline) {
    refresh.setPadding(6, 0, 6, 0);
    addLabel(refresh, offlineText(result.feed), Font.semiboldSystemFont(11), AMBER).minimumScaleFactor = 0.75;
    refresh.setAction("Offline, try again", { id: REFRESH_ACTION });
    return;
  }
  refresh.backgroundColor = RAISED;
  refresh.setPadding(6, 9, 6, 10);
  const time = clock(result.feed.generated_at_ms);
  addSymbol(refresh, "arrow.clockwise", 10, SECONDARY);
  refresh.addSpacer(5);
  addLabel(refresh, time, Font.semiboldRoundedSystemFont(12), SECONDARY);
  refresh.setAction(`Refresh, updated ${time}`, { id: REFRESH_ACTION });
}

function homeWidget(family, view, result) {
  const now = Date.now();
  const widget = new ListWidget();
  widget.backgroundColor = CANVAS;
  widget.setPadding(14, 16, 13, 16);
  widget.url = detailUrl(view);
  const body = widget.addStack();
  body.layoutVertically();
  if (view === "forecast") body.setAction("Next provider", { id: NEXT_ACTION });
  else body.setAction(`Show ${VIEW_TITLES[nextView(view)]}`, { id: nextView(view) });
  if (view === "forecast") forecastView(body, family, result.feed, now);
  else if (view === "recent") recentView(body, family, result.feed, now);
  else nowView(body, family, result.feed, now);
  widget.addSpacer();
  addControls(widget, view, result);
  return widget;
}

function nextView(view) {
  return VIEW_IDS[(VIEW_IDS.indexOf(view) + 1) % VIEW_IDS.length];
}

function addOthers(column, groups) {
  groups.forEach((group, index) => {
    if (index) column.addSpacer(5);
    const row = addRow(column);
    row.addSpacer();
    addLogo(row, group.provider, 12);
    row.addSpacer(4);
    const figure = row.addStack();
    figure.size = new Size(30, 0);
    addLabel(figure, percent(group.focus.used), Font.semiboldRoundedSystemFont(11), figureColor(group.focus) === LABEL ? SECONDARY : figureColor(group.focus));
    figure.addSpacer();
  });
}

function smallBody(container, result, now) {
  const windows = result.feed.windows;
  const groups = providerGroups(windows);
  const hero = heroGroup(groups);
  if (!hero) {
    container.addSpacer();
    const note = windows.length ? "No provider reports a limit" : "No quota windows yet";
    addLabel(container, note, Font.semiboldSystemFont(15), LABEL).lineLimit = 2;
    if (result.offline) addLabel(container, offlineText(result.feed), Font.semiboldSystemFont(11), AMBER).minimumScaleFactor = 0.75;
    return;
  }
  const top = container.addStack();
  top.layoutHorizontally();
  top.topAlignContent();
  top.addImage(ringImage(hero, RING.small)).imageSize = new Size(RING.small, RING.small);
  const others = top.addStack();
  others.layoutVertically();
  addOthers(others, groups.filter((group) => group !== hero).slice(0, 3));
  container.addSpacer();
  const figure = addRow(container);
  const entry = hero.focus;
  const left = hero.chance;
  addLabel(figure, percent(left ? Math.max(100 - entry.used, 0) : entry.used), Font.boldRoundedSystemFont(27), figureColor(entry));
  figure.addSpacer(4);
  if (hero.hot) addFlame(figure, entry, 15);
  else addLabel(figure, left ? "left" : "used", Font.semiboldSystemFont(12), SECONDARY);
  figure.addSpacer();
  const name = addRow(container);
  addLabel(name, ownerName(entry), Font.semiboldSystemFont(13), LABEL);
  name.addSpacer(4);
  addLabel(name, entry.short, Font.regularSystemFont(13), SECONDARY);
  name.addSpacer();
  if (result.offline) {
    addLabel(container, offlineText(result.feed), Font.semiboldSystemFont(11), AMBER).minimumScaleFactor = 0.75;
    return;
  }
  addVerdict(addRow(container), entry, now, clock, 12);
}

function smallWidget(result) {
  const widget = new ListWidget();
  widget.backgroundColor = CANVAS;
  widget.url = detailUrl("now");
  const hero = heroGroup(providerGroups(result.feed.windows));
  if (!hero || !hero.chance) {
    widget.setPadding(14, 14, 13, 14);
    smallBody(widget, result, Date.now());
    return widget;
  }
  widget.setPadding(3, 3, 3, 3);
  widget.backgroundGradient = rainbow();
  const container = widget.addStack();
  container.layoutVertically();
  container.backgroundColor = CANVAS;
  container.cornerRadius = 19;
  container.setPadding(11, 11, 10, 11);
  smallBody(container, result, Date.now());
  return widget;
}

function errorWidget(family, problem) {
  const widget = new ListWidget();
  if (family === "accessoryCircular") {
    widget.addAccessoryWidgetBackground = true;
    addSymbol(widget, "exclamationmark.triangle", 20);
    return widget;
  }
  if (family === "accessoryInline") {
    widget.addImage(symbolImage("exclamationmark.triangle", 12));
    widget.addText(problem.title);
    return widget;
  }
  if (family === "accessoryRectangular") {
    addLine(widget, "OMP usage", Font.semiboldRoundedSystemFont(15));
    addLine(widget, problem.title, Font.mediumSystemFont(13), 0.75);
    return widget;
  }
  widget.backgroundColor = CANVAS;
  widget.setPadding(16, 16, 13, 16);
  widget.url = detailUrl("now");
  addSymbol(widget, problem.symbol, 22, AMBER);
  widget.addSpacer(10);
  addLabel(widget, problem.title, Font.semiboldSystemFont(15), LABEL).lineLimit = 2;
  if (family !== "small") {
    widget.addSpacer(3);
    addLabel(widget, problem.detail, Font.regularSystemFont(12), SECONDARY).lineLimit = 2;
  }
  widget.addSpacer();
  const row = addRow(widget);
  const retry = row.addStack();
  retry.backgroundColor = RAISED;
  retry.cornerRadius = 12;
  retry.setPadding(6, 9, 6, 10);
  retry.centerAlignContent();
  addSymbol(retry, "arrow.clockwise", 10, SECONDARY);
  retry.addSpacer(5);
  addLabel(retry, "Try again", Font.semiboldSystemFont(12), LABEL);
  retry.setAction("Try again", { id: REFRESH_ACTION });
  row.addSpacer();
  return widget;
}

function arc(context, center, radius, from, to, color, width, capped) {
  const steps = Math.max(2, Math.ceil(Math.abs(to - from) / 3));
  const points = [];
  for (let index = 0; index <= steps; index += 1) {
    const angle = ((from + ((to - from) * index) / steps) * Math.PI) / 180;
    points.push(new Point(center + radius * Math.cos(angle), center + radius * Math.sin(angle)));
  }
  const path = new Path();
  path.addLines(points);
  context.addPath(path);
  context.setStrokeColor(color);
  context.setLineWidth(width);
  context.strokePath();
  if (!capped) return;
  context.setFillColor(color);
  for (const point of [points[0], points[points.length - 1]]) {
    context.fillEllipse(new Rect(point.x - width / 2, point.y - width / 2, width, width));
  }
}

function gauge(used) {
  const size = 72;
  const line = 6;
  const context = new DrawContext();
  context.size = new Size(size, size);
  context.opaque = false;
  context.respectScreenScale = true;
  const center = size / 2;
  const radius = center - line;
  arc(context, center, radius, 135, 405, new Color("#FFFFFF", 0.3), line, false);
  if (used !== null && used > 0) {
    const share = Math.min(used, 100) / 100;
    arc(context, center, radius, 135, 135 + 270 * share, Color.white(), line, true);
  }
  return context.getImage();
}

function circularWidget(lock, stale, ageText) {
  const widget = new ListWidget();
  widget.addAccessoryWidgetBackground = true;
  const focus = lock.focus;
  if (!focus) {
    addSymbol(widget, emptySymbol(lock), 20);
    return widget;
  }
  widget.backgroundImage = gauge(focus.used);
  const number = addLine(widget, percent(focus.used), Font.semiboldRoundedSystemFont(18));
  number.centerAlignText();
  const label = addLine(widget, stale ? `${ageText} old` : focus.window, Font.mediumRoundedSystemFont(10), 0.8);
  label.centerAlignText();
  return widget;
}

function rectangularWidget(lock, now, stale, ageText) {
  const widget = new ListWidget();
  const focus = lock.focus;
  if (!focus) {
    addLine(widget, "OMP usage", Font.semiboldRoundedSystemFont(15));
    addLine(widget, lock.issue || "No quota windows", Font.mediumSystemFont(13), 0.75);
    return widget;
  }
  const head = widget.addStack();
  head.centerAlignContent();
  addLine(head, windowName(focus), Font.semiboldRoundedSystemFont(15));
  head.addSpacer();
  if (focus.heat > 0) {
    addSymbol(head, "flame.fill", 12);
    head.addSpacer(3);
  }
  addLine(head, percent(focus.used), Font.semiboldRoundedSystemFont(15));

  const detail = widget.addStack();
  detail.centerAlignContent();
  detail.spacing = 4;
  addSymbol(detail, SYMBOLS[focus.state] || SYMBOLS.unknown, 11);
  const timer = countdown(focus, now);
  if (timer) {
    addLine(detail, timer.prefix, Font.mediumSystemFont(13));
    const date = detail.addDate(new Date(timer.target));
    date.applyTimerStyle();
    date.font = Font.mediumMonospacedSystemFont(13);
    date.lineLimit = 1;
  } else {
    addLine(detail, status(focus, now) || percent(focus.used), Font.mediumSystemFont(13));
  }

  const foot = widget.addStack();
  foot.centerAlignContent();
  foot.spacing = 4;
  const next = lock.next[0];
  if (stale) {
    addSymbol(foot, "clock.badge.exclamationmark", 10);
    addLine(foot, `${ageText} old`, Font.regularSystemFont(12), 0.75);
  } else if (next) {
    addLine(foot, brief(next, status(next, now)), Font.regularSystemFont(12), 0.75);
  }
  return widget;
}

function emptySymbol(lock) {
  return lock.issue ? "exclamationmark.triangle" : "minus.circle";
}

function inlineWidget(lock, now, stale, ageText) {
  const widget = new ListWidget();
  const focus = lock.focus;
  if (!focus) {
    widget.addImage(symbolImage(emptySymbol(lock), 12));
    widget.addText(lock.issue || "No quota windows");
    return widget;
  }
  const symbol = stale ? "clock.badge.exclamationmark" : SYMBOLS[focus.state] || SYMBOLS.unknown;
  widget.addImage(symbolImage(symbol, 12));
  widget.addText(brief(focus, stale ? `${ageText} old` : status(focus, now)));
  return widget;
}

function lockWidget(family, result) {
  const now = Date.now();
  const lock = result.feed.lock;
  const dataMs = lock.updated_ms !== null ? lock.updated_ms : result.feed.generated_at_ms;
  const stale = result.offline || now - dataMs > STALE_MS;
  const ageText = age(now - dataMs);
  if (family === "accessoryCircular") return circularWidget(lock, stale, ageText);
  if (family === "accessoryInline") return inlineWidget(lock, now, stale, ageText);
  return rectangularWidget(lock, now, stale, ageText);
}

function tokenText(tokens) {
  if (tokens >= 1e9) return `${(tokens / 1e9).toFixed(tokens >= 1e10 ? 0 : 1)}B`;
  if (tokens >= 1e6) return `${(tokens / 1e6).toFixed(tokens >= 1e7 ? 0 : 1)}M`;
  if (tokens >= 1e3) return `${Math.round(tokens / 1e3)}K`;
  return String(tokens);
}

function usdText(usd) {
  if (usd <= 0) return "$0";
  if (usd < 0.01) return "<$0.01";
  if (usd >= 100) return `$${Math.round(usd)}`;
  return `$${usd.toFixed(2)}`;
}

const BUCKET_HOURS = 3;

function usageSlides(usage) {
  const total = { provider: null, tokens: usage.total.tokens, estimated_usd: usage.total.estimated_usd, parts: usage.providers };
  return [total, ...usage.providers.map((provider) => ({ ...provider, parts: [provider] }))];
}

function bucketed(series) {
  const buckets = [];
  for (let index = 0; index < series.length; index += BUCKET_HOURS) {
    buckets.push(series.slice(index, index + BUCKET_HOURS).reduce((sum, value) => sum + value, 0));
  }
  return buckets;
}

function partSeries(part, metric) {
  return bucketed(metric === "usd" ? part.usd_by_hour : part.tokens_by_hour);
}

function bucketUsd(usd) {
  if (usd <= 0) return "";
  if (usd >= 10) return `$${Math.round(usd)}`;
  if (usd >= 0.1) return `$${usd.toFixed(1)}`;
  return "<$0.1";
}

function bucketText(value, metric) {
  if (metric === "usd") return bucketUsd(value);
  return value > 0 ? tokenText(value) : "";
}

function hourLabel(ms) {
  const formatter = new DateFormatter();
  formatter.dateFormat = "HH:mm";
  return formatter.string(new Date(ms));
}

function fillBar(context, rect, color) {
  const path = new Path();
  const radius = Math.min(rect.width / 2, rect.height / 2, 4);
  path.addRoundedRect(rect, radius, radius);
  context.addPath(path);
  context.setFillColor(color);
  context.fillPath();
}

function drawCentered(context, text, rect, font, color) {
  context.setFont(font);
  context.setTextColor(color);
  context.setTextAlignedCenter();
  context.drawTextInRect(text, rect);
}

function bucketChart(slide, usage, metric, width, height, labelled) {
  const context = canvas(width, height);
  const parts = slide.parts.map((part) => ({ provider: part.provider, values: partSeries(part, metric) }));
  const count = parts.length ? parts[0].values.length : usage.hours / BUCKET_HOURS;
  const totals = Array.from({ length: count }, (_, index) => parts.reduce((sum, part) => sum + part.values[index], 0));
  const peak = Math.max(...totals) || 1;
  const band = labelled ? 13 : 0;
  const top = band;
  const floor = height - band;
  const room = floor - top - band;
  const slot = width / count;
  const bar = Math.max(slot * 0.56, 3);
  for (let index = 0; index < count; index += 1) {
    const x = index * slot + (slot - bar) / 2;
    const current = index === count - 1;
    if (!totals[index]) {
      fillBar(context, new Rect(x, floor - 3, bar, 3), new Color(NEUTRAL_HEX, 0.25));
    }
    let cursor = floor;
    for (const part of parts) {
      const value = part.values[index];
      if (!value) continue;
      const size = Math.max((value / peak) * room, 2);
      cursor -= size;
      fillBar(context, new Rect(x, cursor, bar, size), new Color(tintHex(part.provider), current ? 1 : 0.8));
    }
    if (!labelled) continue;
    const text = bucketText(totals[index], metric);
    if (text) drawCentered(context, text, new Rect(index * slot, cursor - band, slot, band), Font.semiboldRoundedSystemFont(9), current ? LABEL : SECONDARY);
    const start = usage.end_ms - usage.hours * usage.hour_ms + index * BUCKET_HOURS * usage.hour_ms;
    drawCentered(context, current ? "now" : hourLabel(start), new Rect(index * slot, floor + 2, slot, band), Font.mediumSystemFont(9), current ? LABEL : SECONDARY);
  }
  return context.getImage();
}

function addGoTo(row, url) {
  const button = row.addStack();
  button.backgroundColor = RAISED;
  button.cornerRadius = 10;
  button.setPadding(4, 5, 4, 5);
  addSymbol(button, "arrow.up.right", 10, SECONDARY);
  button.url = url;
}

function addUsageHeader(widget, slide, metric, position, count) {
  const head = addRow(widget);
  if (slide.provider) addLogo(head, slide.provider, 16);
  else addSymbol(head, "chart.bar.fill", 13, SECONDARY);
  head.addSpacer(6);
  addLabel(head, slide.provider ? providerName(slide.provider) : "All providers", Font.semiboldSystemFont(14), LABEL);
  head.addSpacer(5);
  addLabel(head, metric === "usd" ? "API $ per 3h" : "tokens per 3h", Font.regularSystemFont(12), SECONDARY);
  head.addSpacer();
  if (count > 1) {
    addLabel(head, `${position + 1}/${count}`, Font.semiboldRoundedSystemFont(11), SECONDARY);
    head.addSpacer(6);
  }
  addGoTo(head, detailUrl("recent"));
}

function addUsageFigures(body, slide, metric, size) {
  const figures = body.addStack();
  figures.layoutHorizontally();
  figures.bottomAlignContent();
  addLabel(figures, tokenText(slide.tokens), Font.boldRoundedSystemFont(size), metric === "usd" ? SECONDARY : LABEL);
  figures.addSpacer(4);
  const unit = figures.addStack();
  unit.setPadding(0, 0, 3, 0);
  addLabel(unit, "tokens", Font.mediumSystemFont(12), SECONDARY);
  figures.addSpacer();
  addLabel(figures, usdText(slide.estimated_usd), Font.boldRoundedSystemFont(size - 4), metric === "usd" ? GREEN : new Color("#30D158", 0.6));
  figures.addSpacer(3);
  const est = figures.addStack();
  est.setPadding(0, 0, 3, 0);
  addLabel(est, "API est.", Font.mediumSystemFont(11), SECONDARY);
}

function addUsageList(body, usage, slide) {
  body.addSpacer(12);
  usage.providers.slice(0, 5).forEach((provider, index) => {
    if (index) body.addSpacer(8);
    const row = addRow(body);
    const active = slide.provider === provider.provider;
    addLogo(row, provider.provider, 15);
    row.addSpacer(7);
    addLabel(row, providerName(provider.provider), Font.semiboldSystemFont(13), active ? LABEL : SECONDARY);
    row.addSpacer();
    addLabel(row, tokenText(provider.tokens), Font.semiboldRoundedSystemFont(13), active ? LABEL : SECONDARY);
    const money = row.addStack();
    money.size = new Size(62, 0);
    money.addSpacer();
    addLabel(money, usdText(provider.estimated_usd), Font.semiboldRoundedSystemFont(13), GREEN);
  });
}

function usageBody(widget) {
  const body = widget.addStack();
  body.layoutVertically();
  body.setAction("Next provider", { id: USAGE_NEXT_ACTION });
  return body;
}

function usageWidget(family, result) {
  const widget = new ListWidget();
  widget.backgroundColor = CANVAS;
  const usage = result.feed.usage;
  if (!usage || !usage.providers.length) {
    widget.setPadding(14, 16, 13, 16);
    addNote(widget, usage ? "No tokens in the last 24 hours" : "Token usage unavailable");
    widget.addSpacer();
    return widget;
  }
  const slides = usageSlides(usage);
  const turn = usageTurn();
  const position = Math.floor(turn / 2) % slides.length;
  const metric = turn % 2 ? "usd" : "tokens";
  const slide = slides[position];
  if (family === "small") {
    widget.setPadding(14, 14, 13, 14);
    const body = usageBody(widget);
    const head = addRow(body);
    if (slide.provider) addLogo(head, slide.provider, 14);
    else addSymbol(head, "chart.bar.fill", 12, SECONDARY);
    head.addSpacer(5);
    addLabel(head, slide.provider ? providerName(slide.provider) : "All", Font.semiboldSystemFont(13), LABEL);
    head.addSpacer();
    addLabel(head, `${position + 1}/${slides.length}`, Font.semiboldRoundedSystemFont(11), SECONDARY);
    body.addSpacer();
    addLabel(body, tokenText(slide.tokens), Font.boldRoundedSystemFont(26), LABEL);
    addLabel(body, `${usdText(slide.estimated_usd)} API est.`, Font.semiboldRoundedSystemFont(13), GREEN);
    body.addSpacer(8);
    body.addImage(bucketChart(slide, usage, metric, 142, 30, false)).imageSize = new Size(142, 30);
    if (result.offline) addLabel(widget, offlineText(result.feed), Font.semiboldSystemFont(10), AMBER).minimumScaleFactor = 0.7;
    return widget;
  }
  widget.setPadding(13, 16, 12, 16);
  addUsageHeader(widget, slide, metric, position, slides.length);
  widget.addSpacer(5);
  const body = usageBody(widget);
  addUsageFigures(body, slide, metric, family === "large" ? 28 : 24);
  body.addSpacer(4);
  const chartHeight = family === "large" ? 140 : 66;
  body.addImage(bucketChart(slide, usage, metric, ART_WIDTH, chartHeight, true)).imageSize = new Size(ART_WIDTH, chartHeight);
  if (family === "large") addUsageList(body, usage, slide);
  widget.addSpacer();
  if (result.offline) addLabel(widget, offlineText(result.feed), Font.semiboldSystemFont(11), AMBER).minimumScaleFactor = 0.75;
  return widget;
}

function usageMode(family) {
  return HOME.includes(family) && String(args.widgetParameter || "").trim().toLowerCase() === USAGE_MODE;
}

async function buildUsage(family, action) {
  if (action === null) advanceUsage();
  if (action === USAGE_NEXT_ACTION) {
    advanceUsage();
    advanceUsage();
  }
  const result = await snapshot(family, action);
  if (!result) return errorWidget(family, UNREACHABLE);
  return usageWidget(family, result);
}

async function build(family, action) {
  if (usageMode(family)) return buildUsage(family, action);
  if (VIEW_IDS.includes(action)) saveView(action);
  if (action === NEXT_ACTION) saveView("forecast");
  if ((action === null && HOME.includes(family)) || action === NEXT_ACTION) advanceForecast();
  const result = await snapshot(family, action);
  if (!result) return errorWidget(family, UNREACHABLE);
  if (!HOME.includes(family)) return lockWidget(family, result);
  return family === "small" ? smallWidget(result) : homeWidget(family, savedView(), result);
}

async function render(family, action) {
  try {
    return await build(family, action);
  } catch (error) {
    console.error(error);
    return errorWidget(family, BROKEN);
  }
}

const requested = config.runsInApp ? "medium" : config.widgetFamily || "medium";
const family = requested === "extraLarge" ? "large" : requested;
const action = args.widgetAction ? args.widgetAction.id : null;
const widget = await render(family, action);
if (!HOME.includes(family)) widget.url = BOT_URL;
widget.refreshAfterDate = new Date(Date.now() + REFRESH_MS);
if (config.runsInApp) {
  await widget.presentMedium();
} else {
  Script.setWidget(widget);
}
Script.complete();
