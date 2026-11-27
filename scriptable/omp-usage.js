// OMP usage widget for Scriptable: home screen images and native Lock Screen views of the OMP quota reporter.
// Served from https://openclaw.tail2fec5e.ts.net/usage/ (widget.json, small.png, medium.png, large.png) over Tailscale.

const BASE = "https://openclaw.tail2fec5e.ts.net/usage/";
const BOT_URL = "tg://resolve?domain=PreiPreiClaudeButlerBot";
const REFRESH_MS = 15 * 60 * 1000;
const STALE_MS = 20 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;
const OUT_STEP_MS = 5 * 60 * 1000;
const HOME = ["small", "medium", "large"];
const INK = new Color("#0A0F1F");
const MUTED = new Color("#B3BDD6");
const AMBER = new Color("#FFC75F");
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

const files = FileManager.local();
const cacheDir = files.joinPath(files.libraryDirectory(), "omp-usage");
const feedPath = files.joinPath(cacheDir, "widget.json");

function imagePath(family) {
  return files.joinPath(cacheDir, `${family}.png`);
}

function stampPath(family) {
  return files.joinPath(cacheDir, `${family}.ms`);
}

async function load(request, read) {
  request.timeoutInterval = 15;
  const body = await read(request);
  const status = request.response && request.response.statusCode;
  if (status !== 200) throw new Error(`HTTP ${status} for ${request.url}`);
  return body;
}

async function refresh(family) {
  const feed = await load(new Request(`${BASE}widget.json`), (request) => request.loadJSON());
  if (feed.schema !== 1) throw new Error(`Unsupported schema ${feed.schema}`);
  let image = null;
  if (HOME.includes(family)) {
    const url = `${BASE}${feed.images[family]}?t=${feed.generated_at_ms}`;
    image = await load(new Request(url), (request) => request.loadImage());
  }
  if (!files.fileExists(cacheDir)) files.createDirectory(cacheDir, true);
  if (image) {
    files.writeImage(imagePath(family), image);
    files.writeString(stampPath(family), String(feed.generated_at_ms));
  }
  files.writeString(feedPath, JSON.stringify(feed));
  return { feed, image, imageMs: feed.generated_at_ms, offline: false };
}

function fromCache(family) {
  if (HOME.includes(family)) {
    if (!files.fileExists(imagePath(family)) || !files.fileExists(stampPath(family))) return null;
    const imageMs = Number(files.readString(stampPath(family)));
    return { feed: null, image: files.readImage(imagePath(family)), imageMs, offline: true };
  }
  if (!files.fileExists(feedPath)) return null;
  return { feed: JSON.parse(files.readString(feedPath)), image: null, imageMs: null, offline: true };
}

function dayOffset(date, now) {
  const start = (moment) => new Date(moment.getFullYear(), moment.getMonth(), moment.getDate()).getTime();
  return Math.round((start(date) - start(now)) / DAY_MS);
}

function clock(ms) {
  const date = new Date(ms);
  const days = dayOffset(date, new Date());
  const formatter = new DateFormatter();
  if (days === 0) formatter.dateFormat = "HH:mm";
  else if (days > 0 && days < 7) formatter.dateFormat = "EEE HH:mm";
  else formatter.dateFormat = "MMM d";
  return formatter.string(date);
}

function age(ms) {
  const minutes = Math.max(1, Math.round(ms / 60000));
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours}h` : `${Math.round(hours / 24)}d`;
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

function finish(widget) {
  widget.refreshAfterDate = new Date(Date.now() + REFRESH_MS);
  widget.url = BOT_URL;
  return widget;
}

function homeWidget(result) {
  const widget = new ListWidget();
  widget.backgroundColor = INK;
  widget.backgroundImage = result.image;
  widget.setPadding(0, 0, 10, 12);
  if (result.offline) {
    widget.addSpacer();
    const row = widget.addStack();
    row.addSpacer();
    const pill = row.addStack();
    pill.backgroundColor = INK;
    pill.cornerRadius = 10;
    pill.setPadding(4, 10, 4, 10);
    pill.spacing = 5;
    pill.centerAlignContent();
    addSymbol(pill, "clock.badge.exclamationmark", 12, AMBER);
    const text = addLine(pill, `${age(Date.now() - result.imageMs)} old`, Font.semiboldSystemFont(12));
    text.textColor = AMBER;
  }
  return widget;
}

function errorWidget(family) {
  const widget = new ListWidget();
  if (family === "accessoryCircular") {
    widget.addAccessoryWidgetBackground = true;
    addSymbol(widget, "exclamationmark.triangle", 20);
    return widget;
  }
  if (family === "accessoryInline") {
    widget.addImage(symbolImage("exclamationmark.triangle", 12));
    widget.addText("Can't reach openclaw");
    return widget;
  }
  if (family === "accessoryRectangular") {
    addLine(widget, "OMP usage", Font.semiboldRoundedSystemFont(15));
    addLine(widget, "Can't reach openclaw", Font.mediumSystemFont(13), 0.75);
    return widget;
  }
  widget.backgroundColor = INK;
  addSymbol(widget, "exclamationmark.triangle", 22, AMBER).centerAlignImage();
  widget.addSpacer(8);
  const text = addLine(widget, "Can't reach openclaw", Font.semiboldSystemFont(14));
  text.textColor = MUTED;
  text.centerAlignText();
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

function brief(entry, state) {
  const tail = state ? `, ${state.charAt(0).toLowerCase()}${state.slice(1)}` : "";
  return `${windowName(entry)} ${percent(entry.used)}${tail}`;
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

async function build(family) {
  let result;
  try {
    result = await refresh(family);
  } catch (error) {
    console.error(error);
    result = fromCache(family);
  }
  if (!result) return errorWidget(family);
  return HOME.includes(family) ? homeWidget(result) : lockWidget(family, result);
}

const requested = config.runsInApp ? "medium" : config.widgetFamily || "medium";
const family = requested === "extraLarge" ? "large" : requested;
const widget = finish(await build(family));
if (config.runsInApp) {
  await widget.presentMedium();
} else {
  Script.setWidget(widget);
}
Script.complete();
