const SOURCE = "https://openclaw.tail2fec5e.ts.net/omp-usage.js";
const files = FileManager.local();
const directory = files.joinPath(files.libraryDirectory(), "omp-usage");
const codePath = files.joinPath(directory, "widget-code.js");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;

async function download() {
  const request = new Request(SOURCE);
  request.timeoutInterval = 5;
  const code = await request.loadString();
  if (request.response.statusCode !== 200) throw new Error(`HTTP ${request.response.statusCode} for ${SOURCE}`);
  const program = new AsyncFunction(code);
  if (!files.fileExists(directory)) files.createDirectory(directory, true);
  files.writeString(codePath, code);
  return program;
}

function cached() {
  if (!files.fileExists(codePath)) return null;
  return new AsyncFunction(files.readString(codePath));
}

async function program() {
  const tapped = args.widgetAction && args.widgetAction.id !== "refresh";
  if (tapped && files.fileExists(codePath)) return cached();
  try {
    return await download();
  } catch (error) {
    console.error(error);
    return cached();
  }
}

const widgetProgram = await program();
if (widgetProgram) {
  await widgetProgram();
} else {
  const widget = new ListWidget();
  widget.backgroundColor = new Color("#1C1C1E");
  const title = widget.addText("Can't reach openclaw");
  title.font = Font.semiboldSystemFont(15);
  title.textColor = Color.white();
  widget.addSpacer(4);
  const detail = widget.addText("Connect Tailscale to load the widget");
  detail.font = Font.regularSystemFont(12);
  detail.textColor = new Color("#EBEBF5", 0.6);
  widget.refreshAfterDate = new Date(Date.now() + 5 * 60 * 1000);
  if (config.runsInApp) await widget.presentMedium();
  else Script.setWidget(widget);
  Script.complete();
}
