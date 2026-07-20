/**
 * Vim-ish modal editor for pi.
 *
 * Big pieces implemented here:
 * - modes: insert / normal / visual
 * - motions: h j k l w b e 0 ^ $ gg G
 * - edits: x dd D yy p P u Ctrl-R
 * - insert commands: i a I A o O
 * - search: / ? n N * #
 * - operators: d c y with motions + text objects
 * - text objects: iw aw  (ciw/caw/diw/daw/yiw/yaw, etc.)
 * - visual selection rendering + y/d/c/p over selection
 */

import { CustomEditor, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { CURSOR_MARKER, matchesKey, truncateToWidth, visibleWidth } from "@earendil-works/pi-tui";

type Mode = "insert" | "normal" | "visual";
type SearchDirection = 1 | -1;
type Operator = "d" | "c" | "y" | null;
type TextObjectPrefix = "i" | "a" | null;
type Pos = { line: number; col: number };
type Range = { start: Pos; end: Pos };

type Snapshot = {
  text: string;
  cursor: Pos;
};

class VimModalEditor extends CustomEditor {
  private mode: Mode = "insert";
  private visualAnchor: Pos | null = null;
  private register = "";
  private pendingOperator: Operator = null;
  private pendingTextObjectPrefix: TextObjectPrefix = null;
  private pendingG = false;
  private searchPrompt: { direction: SearchDirection; query: string } | null = null;
  private lastSearch: { direction: SearchDirection; query: string } | null = null;
  private undoStackVim: Snapshot[] = [];
  private redoStackVim: Snapshot[] = [];

  private snapshot(): Snapshot {
    return { text: this.getText(), cursor: this.getCursor() };
  }

  private pushUndo(): void {
    this.undoStackVim.push(this.snapshot());
    this.redoStackVim = [];
  }

  private restore(snapshot: Snapshot | undefined): void {
    if (!snapshot) return;
    this.setText(snapshot.text);
    this.setCursor(snapshot.cursor.line, snapshot.cursor.col);
  }

  private get pos(): Pos {
    const { line, col } = this.getCursor();
    return { line, col };
  }

  private setCursor(line: number, col: number): void {
    const lines = this.state.lines;
    const clampedLine = Math.max(0, Math.min(line, lines.length - 1));
    const text = lines[clampedLine] ?? "";
    this.state.cursorLine = clampedLine;
    this.state.cursorCol = Math.max(0, Math.min(col, text.length));
  }

  private clearPending(): void {
    this.pendingOperator = null;
    this.pendingTextObjectPrefix = null;
    this.pendingG = false;
  }

  private enterNormal(): void {
    this.mode = "normal";
    this.visualAnchor = null;
    this.searchPrompt = null;
    this.clearPending();
  }

  private enterInsert(): void {
    this.mode = "insert";
    this.visualAnchor = null;
    this.clearPending();
  }

  private enterVisual(): void {
    this.mode = "visual";
    this.visualAnchor = this.pos;
    this.clearPending();
  }

  private comparePos(a: Pos, b: Pos): number {
    return a.line !== b.line ? a.line - b.line : a.col - b.col;
  }

  private normalizeRange(range: Range): Range {
    return this.comparePos(range.start, range.end) <= 0 ? range : { start: range.end, end: range.start };
  }

  private getVisualRange(): Range | null {
    if (!this.visualAnchor) return null;
    return this.normalizeRange({ start: this.visualAnchor, end: this.pos });
  }

  private lineCount(): number {
    return this.getLines().length;
  }

  private currentLine(): string {
    return this.getLines()[this.state.cursorLine] ?? "";
  }

  private isWordChar(ch: string | undefined): boolean {
    return !!ch && /[A-Za-z0-9_]/.test(ch);
  }

  private moveLeft(): void { super.handleInput("\x1b[D"); }
  private moveRight(): void { super.handleInput("\x1b[C"); }
  private moveUp(): void { super.handleInput("\x1b[A"); }
  private moveDown(): void { super.handleInput("\x1b[B"); }
  private moveWordForwardBuiltin(): void { super.handleInput("\x1bf"); }
  private moveWordBackwardBuiltin(): void { super.handleInput("\x1bb"); }
  private moveLineStartBuiltin(): void { super.handleInput("\x01"); }
  private moveLineEndBuiltin(): void { super.handleInput("\x05"); }
  private deleteCharBuiltin(): void { super.handleInput("\x1b[3~"); }
  private deleteToLineEndBuiltin(): void { super.handleInput("\x0b"); }
  private undoBuiltin(): void { super.handleInput("\x1f"); }
  private redoBuiltin(): void { super.handleInput("\x12"); }

  private moveFirstNonBlank(): void {
    const line = this.currentLine();
    const m = line.match(/\S/);
    this.setCursor(this.state.cursorLine, m?.index ?? 0);
  }

  private moveWordEnd(): void {
    let { line, col } = this.pos;
    const lines = this.getLines();
    while (line < lines.length) {
      const text = lines[line] ?? "";
      let i = line === this.pos.line ? col : 0;
      if (i < text.length && this.isWordChar(text[i])) {
        while (i + 1 < text.length && this.isWordChar(text[i + 1])) i++;
        this.setCursor(line, i);
        return;
      }
      while (i < text.length && !this.isWordChar(text[i])) i++;
      if (i < text.length) {
        while (i + 1 < text.length && this.isWordChar(text[i + 1])) i++;
        this.setCursor(line, i);
        return;
      }
      line++;
      col = 0;
    }
  }

  private moveDocumentStart(): void {
    this.setCursor(0, 0);
  }

  private moveDocumentEnd(): void {
    const lines = this.getLines();
    const line = Math.max(0, lines.length - 1);
    this.setCursor(line, (lines[line] ?? "").length);
  }

  private openBelow(): void {
    this.pushUndo();
    this.moveLineEndBuiltin();
    super.handleInput("\n");
    this.enterInsert();
  }

  private openAbove(): void {
    this.pushUndo();
    this.moveLineStartBuiltin();
    super.handleInput("\n");
    this.moveUp();
    this.enterInsert();
  }

  private posToIndex(pos: Pos): number {
    const lines = this.getLines();
    let idx = 0;
    for (let i = 0; i < pos.line; i++) idx += (lines[i] ?? "").length + 1;
    return idx + pos.col;
  }

  private indexToPos(index: number): Pos {
    const lines = this.getLines();
    let remain = Math.max(0, index);
    for (let i = 0; i < lines.length; i++) {
      const len = (lines[i] ?? "").length;
      if (remain <= len) return { line: i, col: remain };
      remain -= len + 1;
    }
    const last = Math.max(0, lines.length - 1);
    return { line: last, col: (lines[last] ?? "").length };
  }

  private getTextRange(range: Range): string {
    const text = this.getText();
    const norm = this.normalizeRange(range);
    return text.slice(this.posToIndex(norm.start), this.posToIndex(norm.end));
  }

  private replaceRange(range: Range, replacement: string, cursor?: Pos): void {
    const norm = this.normalizeRange(range);
    const text = this.getText();
    const start = this.posToIndex(norm.start);
    const end = this.posToIndex(norm.end);
    const next = text.slice(0, start) + replacement + text.slice(end);
    this.setText(next);
    this.setCursor(cursor?.line ?? norm.start.line, cursor?.col ?? norm.start.col);
  }

  private deleteLine(lineIndex: number): void {
    const lines = [...this.getLines()];
    const deleted = lines[lineIndex] ?? "";
    this.register = deleted + "\n";
    lines.splice(lineIndex, 1);
    if (lines.length === 0) lines.push("");
    this.setText(lines.join("\n"));
    this.setCursor(Math.min(lineIndex, lines.length - 1), 0);
  }

  private yankLine(lineIndex: number): void {
    this.register = (this.getLines()[lineIndex] ?? "") + "\n";
  }

  private paste(after: boolean): void {
    if (!this.register) return;
    this.pushUndo();
    if (this.register.endsWith("\n")) {
      const lines = [...this.getLines()];
      const line = this.state.cursorLine + (after ? 1 : 0);
      lines.splice(line, 0, this.register.slice(0, -1));
      this.setText(lines.join("\n"));
      this.setCursor(line, 0);
      return;
    }
    const at = this.posToIndex(this.pos) + (after ? 1 : 0);
    const pos = this.indexToPos(at);
    this.setCursor(pos.line, pos.col);
    this.insertTextAtCursor(this.register);
  }

  private textObjectWord(prefix: TextObjectPrefix): Range | null {
    const lineIndex = this.state.cursorLine;
    const line = this.currentLine();
    if (!line.length) return null;

    let col = this.state.cursorCol;
    if (col >= line.length) col = Math.max(0, line.length - 1);

    if (!this.isWordChar(line[col])) {
      let probe = col;
      while (probe < line.length && !this.isWordChar(line[probe])) probe++;
      if (probe >= line.length) {
        probe = col - 1;
        while (probe >= 0 && !this.isWordChar(line[probe])) probe--;
      }
      if (probe < 0 || probe >= line.length || !this.isWordChar(line[probe])) return null;
      col = probe;
    }

    let start = col;
    while (start > 0 && this.isWordChar(line[start - 1])) start--;
    let end = col;
    while (end < line.length && this.isWordChar(line[end])) end++;

    if (prefix === "a") {
      while (start > 0 && /\s/.test(line[start - 1] ?? "")) start--;
      while (end < line.length && /\s/.test(line[end] ?? "")) end++;
    }

    return { start: { line: lineIndex, col: start }, end: { line: lineIndex, col: end } };
  }

  private motionTarget(key: string, rawKey: string): Pos | null {
    const start = this.pos;
    const restore = this.snapshot();

    const move = () => {
      switch (key) {
        case "h": this.moveLeft(); break;
        case "j": this.moveDown(); break;
        case "k": this.moveUp(); break;
        case "l": this.moveRight(); break;
        case "w": this.moveWordForwardBuiltin(); break;
        case "b": this.moveWordBackwardBuiltin(); break;
        case "e": this.moveWordEnd(); break;
        case "0": this.moveLineStartBuiltin(); break;
        case "^": this.moveFirstNonBlank(); break;
        case "$": this.moveLineEndBuiltin(); break;
        default:
          switch (rawKey) {
            case "G": this.moveDocumentEnd(); break;
            default: return false;
          }
      }
      return true;
    };

    if (!move()) {
      if (this.pendingG && key === "g") {
        this.moveDocumentStart();
      } else {
        return null;
      }
    }

    const target = this.pos;
    this.restore(restore);
    this.setCursor(start.line, start.col);
    return target;
  }

  private rangeFromMotion(key: string, rawKey: string): Range | null {
    const target = this.motionTarget(key, rawKey);
    if (!target) return null;
    const start = this.pos;
    let end = target;
    if (this.comparePos(start, end) === 0) {
      if (key === "l") end = { line: end.line, col: Math.min((this.getLines()[end.line] ?? "").length, end.col + 1) };
      else return null;
    }
    if (this.comparePos(start, end) < 0) {
      if (key === "e") end = { line: end.line, col: end.col + 1 };
      if (key === "$" || rawKey === "G") end = { line: end.line, col: (this.getLines()[end.line] ?? "").length };
      return { start, end };
    }
    return { start: end, end: start };
  }

  private applyOperatorToRange(op: Exclude<Operator, null>, range: Range): void {
    const text = this.getTextRange(range);
    if (op === "y") {
      this.register = text;
      return;
    }
    this.pushUndo();
    this.register = text;
    this.replaceRange(range, "");
    if (op === "c") this.enterInsert();
  }

  private handleOperatorSequence(key: string, rawKey: string): boolean {
    const op = this.pendingOperator;
    if (!op) return false;

    if (this.pendingTextObjectPrefix) {
      const prefix = this.pendingTextObjectPrefix;
      this.clearPending();
      if (key === "w") {
        const range = this.textObjectWord(prefix);
        if (range) this.applyOperatorToRange(op, range);
        return true;
      }
      return true;
    }

    if (key === "i" || key === "a") {
      this.pendingTextObjectPrefix = key as TextObjectPrefix;
      return true;
    }

    if (key === op) {
      this.clearPending();
      if (op === "d") {
        this.pushUndo();
        this.deleteLine(this.state.cursorLine);
      } else if (op === "y") {
        this.yankLine(this.state.cursorLine);
      } else if (op === "c") {
        this.pushUndo();
        this.deleteLine(this.state.cursorLine);
        this.enterInsert();
      }
      return true;
    }

    const range = this.rangeFromMotion(key, rawKey);
    this.clearPending();
    if (range) {
      this.applyOperatorToRange(op, range);
      return true;
    }
    return true;
  }

  private startSearch(direction: SearchDirection): void {
    this.clearPending();
    this.searchPrompt = { direction, query: "" };
  }

  private find(query: string, direction: SearchDirection, from: Pos): Pos | null {
    const lines = this.getLines();
    if (!query) return null;

    if (direction > 0) {
      for (let line = from.line; line < lines.length; line++) {
        const text = lines[line] ?? "";
        const offset = line === from.line ? Math.min(from.col + 1, text.length) : 0;
        const idx = text.indexOf(query, offset);
        if (idx >= 0) return { line, col: idx };
      }
      for (let line = 0; line <= from.line; line++) {
        const text = lines[line] ?? "";
        const limit = line === from.line ? from.col : text.length;
        const idx = text.indexOf(query);
        if (idx >= 0 && idx < limit) return { line, col: idx };
      }
      return null;
    }

    for (let line = from.line; line >= 0; line--) {
      const text = lines[line] ?? "";
      const hay = text.slice(0, line === from.line ? Math.max(0, from.col) : text.length);
      const idx = hay.lastIndexOf(query);
      if (idx >= 0) return { line, col: idx };
    }
    for (let line = lines.length - 1; line >= from.line; line--) {
      const text = lines[line] ?? "";
      const idx = text.lastIndexOf(query);
      if (idx >= 0 && !(line === from.line && idx >= from.col)) return { line, col: idx };
    }
    return null;
  }

  private runSearch(direction = this.lastSearch?.direction ?? 1, query = this.lastSearch?.query ?? ""): void {
    if (!query) return;
    const found = this.find(query, direction, this.pos);
    this.lastSearch = { direction, query };
    if (found) this.setCursor(found.line, found.col);
  }

  private searchWordUnderCursor(direction: SearchDirection): void {
    const range = this.textObjectWord("i");
    if (!range) return;
    const query = this.getTextRange(range);
    this.lastSearch = { direction, query };
    this.runSearch(direction, query);
  }

  private handleSearchPrompt(data: string): boolean {
    const prompt = this.searchPrompt;
    if (!prompt) return false;

    if (matchesKey(data, "escape")) {
      this.searchPrompt = null;
      return true;
    }
    if (matchesKey(data, "enter") || matchesKey(data, "return")) {
      this.searchPrompt = null;
      this.runSearch(prompt.direction, prompt.query);
      return true;
    }
    if (matchesKey(data, "backspace")) {
      prompt.query = prompt.query.slice(0, -1);
      return true;
    }
    if (data.length === 1 && data.charCodeAt(0) >= 32) {
      prompt.query += data;
      return true;
    }
    return true;
  }

  private handleVisual(data: string): boolean {
    const key = data.length === 1 ? data.toLowerCase() : data;
    const rawKey = data.length === 1 ? data : data;
    const range = this.getVisualRange();

    if (matchesKey(data, "escape") || rawKey === "v" || rawKey === "V") {
      this.enterNormal();
      return true;
    }

    if (range && (rawKey === "y" || rawKey === "Y")) {
      this.register = this.getTextRange(range);
      this.enterNormal();
      return true;
    }
    if (range && (rawKey === "d" || rawKey === "D")) {
      this.pushUndo();
      this.register = this.getTextRange(range);
      this.replaceRange(range, "");
      this.enterNormal();
      return true;
    }
    if (range && (rawKey === "c" || rawKey === "C")) {
      this.pushUndo();
      this.register = this.getTextRange(range);
      this.replaceRange(range, "");
      this.enterInsert();
      return true;
    }
    if (range && (rawKey === "p" || rawKey === "P")) {
      this.pushUndo();
      this.replaceRange(range, this.register);
      this.enterNormal();
      return true;
    }

    return this.handleNormalLike(data, key, rawKey, true);
  }

  private handleNormalLike(data: string, key: string, rawKey: string, visual = false): boolean {
    if (this.handleOperatorSequence(key, rawKey)) return true;

    if (this.pendingG) {
      this.pendingG = false;
      if (key === "g") {
        this.moveDocumentStart();
        return true;
      }
    }

    switch (key) {
      case "h": this.moveLeft(); return true;
      case "j": this.moveDown(); return true;
      case "k": this.moveUp(); return true;
      case "l": this.moveRight(); return true;
      case "w": this.moveWordForwardBuiltin(); return true;
      case "b": this.moveWordBackwardBuiltin(); return true;
      case "e": this.moveWordEnd(); return true;
      case "0": this.moveLineStartBuiltin(); return true;
      case "^": this.moveFirstNonBlank(); return true;
      case "$": this.moveLineEndBuiltin(); return true;
      case "g": this.pendingG = true; return true;
      case "v": if (!visual) this.enterVisual(); return true;
      case "/": if (!visual) this.startSearch(1); return true;
      case "?": if (!visual) this.startSearch(-1); return true;
      case "n": this.runSearch(this.lastSearch?.direction ?? 1, this.lastSearch?.query ?? ""); return true;
      case "x": if (!visual) { this.pushUndo(); this.deleteCharBuiltin(); } return true;
      case "d": if (!visual) { this.pendingOperator = "d"; } return true;
      case "c": if (!visual) { this.pendingOperator = "c"; } return true;
      case "y": if (!visual) { this.pendingOperator = "y"; } return true;
      case "i": if (!visual) { this.enterInsert(); } return true;
      case "a": if (!visual) { this.moveRight(); this.enterInsert(); } return true;
      case "o": if (!visual) { this.openBelow(); } return true;
      case "p": if (!visual) { this.paste(true); } return true;
      case "*": if (!visual) { this.searchWordUnderCursor(1); } return true;
      case "#": if (!visual) { this.searchWordUnderCursor(-1); } return true;
      case "u": if (!visual) {
        const prev = this.undoStackVim.pop();
        if (prev) {
          this.redoStackVim.push(this.snapshot());
          this.restore(prev);
        } else {
          this.undoBuiltin();
        }
      } return true;
    }

    switch (rawKey) {
      case "I": if (!visual) { this.moveFirstNonBlank(); this.enterInsert(); } return true;
      case "A": if (!visual) { this.moveLineEndBuiltin(); this.enterInsert(); } return true;
      case "O": if (!visual) { this.openAbove(); } return true;
      case "D": if (!visual) {
        this.pushUndo();
        this.deleteToLineEndBuiltin();
      } return true;
      case "G": this.moveDocumentEnd(); return true;
      case "N": this.runSearch(((this.lastSearch?.direction ?? 1) * -1) as SearchDirection, this.lastSearch?.query ?? ""); return true;
      case "P": if (!visual) { this.paste(false); } return true;
    }

    if (!visual && matchesKey(data, "ctrl+r")) {
      const next = this.redoStackVim.pop();
      if (next) {
        this.undoStackVim.push(this.snapshot());
        this.restore(next);
      } else {
        this.redoBuiltin();
      }
      return true;
    }

    if (dataIsPrintable(data)) return true;
    return false;
  }

  handleInput(data: string): void {
    if (this.handleSearchPrompt(data)) return;

    if (matchesKey(data, "escape")) {
      if (this.mode === "insert") {
        this.enterNormal();
      } else if (this.mode === "visual") {
        this.enterNormal();
      } else {
        this.clearPending();
        super.handleInput(data);
      }
      return;
    }

    if (this.mode === "insert") {
      super.handleInput(data);
      return;
    }

    const key = data.length === 1 ? data.toLowerCase() : data;
    const rawKey = data.length === 1 ? data : data;
    const handled = this.mode === "visual"
      ? this.handleVisual(data)
      : this.handleNormalLike(data, key, rawKey, false);
    if (handled) return;

    super.handleInput(data);
  }

  private selectionColsForLine(line: number): { start: number; end: number } | null {
    const range = this.getVisualRange();
    if (!range) return null;
    if (line < range.start.line || line > range.end.line) return null;
    const text = this.getLines()[line] ?? "";
    const start = line === range.start.line ? range.start.col : 0;
    const end = line === range.end.line ? range.end.col : text.length;
    return end >= start ? { start, end } : null;
  }

  private styleChunk(lineIndex: number, startCol: number, text: string): string {
    if (!text) return text;

    const sel = this.selectionColsForLine(lineIndex);
    const line = this.getLines()[lineIndex] ?? "";
    const query = this.searchPrompt?.query || this.lastSearch?.query || "";
    const searchRanges: Array<{ start: number; end: number }> = [];

    if (query) {
      let from = 0;
      while (from <= line.length - query.length) {
        const idx = line.indexOf(query, from);
        if (idx < 0) break;
        searchRanges.push({ start: idx, end: idx + query.length });
        from = idx + Math.max(1, query.length);
      }
    }

    let out = "";
    for (let i = 0; i < text.length; i++) {
      const col = startCol + i;
      const ch = text[i] ?? "";
      const inSearchMatch = searchRanges.some((r) => col >= r.start && col < r.end);
      const inSelection = !!sel && col >= sel.start && col < sel.end;

      if (inSelection) {
        out += `\x1b[48;5;238m${ch}\x1b[0m`;
      } else if (inSearchMatch) {
        out += `\x1b[48;5;94m${ch}\x1b[0m`;
      } else {
        out += ch;
      }
    }

    return out;
  }

  render(width: number): string[] {
    const maxPadding = Math.max(0, Math.floor((width - 1) / 2));
    const paddingX = Math.min(this.paddingX ?? 0, maxPadding);
    const contentWidth = Math.max(1, width - paddingX * 2);
    const layoutWidth = Math.max(1, contentWidth - (paddingX ? 0 : 1));
    this.lastWidth = layoutWidth;

    const border = this.theme.borderColor("─");
    const lines = this.getLines();
    const layout: Array<{ text: string; line: number; startCol: number; endCol: number; hasCursor: boolean; cursorPos?: number }> = [];

    if (lines.length === 0 || (lines.length === 1 && lines[0] === "")) {
      layout.push({ text: "", line: 0, startCol: 0, endCol: 0, hasCursor: true, cursorPos: 0 });
    } else {
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i] ?? "";
        if (line.length === 0) {
          layout.push({ text: "", line: i, startCol: 0, endCol: 0, hasCursor: i === this.state.cursorLine, cursorPos: 0 });
          continue;
        }
        for (let start = 0; start < line.length || start === 0; start += layoutWidth) {
          const chunk = line.slice(start, start + layoutWidth);
          const end = start + chunk.length;
          const cursorHere = i === this.state.cursorLine && this.state.cursorCol >= start && this.state.cursorCol <= end;
          layout.push({
            text: chunk,
            line: i,
            startCol: start,
            endCol: end,
            hasCursor: cursorHere,
            cursorPos: cursorHere ? this.state.cursorCol - start : undefined,
          });
          if (line.length === 0) break;
        }
      }
    }

    const terminalRows = this.tui.terminal.rows;
    const maxVisibleLines = Math.max(5, Math.floor(terminalRows * 0.3));
    let cursorLineIndex = layout.findIndex((l) => l.hasCursor);
    if (cursorLineIndex < 0) cursorLineIndex = 0;
    if (cursorLineIndex < this.scrollOffset) this.scrollOffset = cursorLineIndex;
    else if (cursorLineIndex >= this.scrollOffset + maxVisibleLines) this.scrollOffset = cursorLineIndex - maxVisibleLines + 1;
    const maxScrollOffset = Math.max(0, layout.length - maxVisibleLines);
    this.scrollOffset = Math.max(0, Math.min(this.scrollOffset, maxScrollOffset));

    const visible = layout.slice(this.scrollOffset, this.scrollOffset + maxVisibleLines);
    const out: string[] = [];
    const leftPadding = " ".repeat(paddingX);
    const rightPadding = leftPadding;

    if (this.scrollOffset > 0) {
      const indicator = `─── ↑ ${this.scrollOffset} more `;
      const remaining = width - visibleWidth(indicator);
      out.push(this.theme.borderColor(remaining >= 0 ? indicator + "─".repeat(remaining) : truncateToWidth(indicator, width, "")));
    } else {
      out.push(border.repeat(width));
    }

    for (const row of visible) {
      let display = this.styleChunk(row.line, row.startCol, row.text);
      let lineWidth = visibleWidth(row.text);
      let cursorInPadding = false;

      if (row.hasCursor && row.cursorPos !== undefined) {
        const p = Math.max(0, Math.min(row.cursorPos, row.text.length));
        const plain = row.text;
        const before = this.styleChunk(row.line, row.startCol, plain.slice(0, p));
        const at = plain[p] ?? " ";
        const after = this.styleChunk(row.line, row.startCol + Math.min(p + 1, plain.length), plain.slice(p + 1));
        display = `${before}${this.focused ? CURSOR_MARKER : ""}\x1b[7m${at}\x1b[0m${after}`;
        if (p >= plain.length) {
          lineWidth += 1;
          if (lineWidth > contentWidth && paddingX > 0) cursorInPadding = true;
        }
      }

      const pad = " ".repeat(Math.max(0, contentWidth - lineWidth));
      const lineRightPadding = cursorInPadding ? rightPadding.slice(1) : rightPadding;
      const renderedLine = `${leftPadding}${display}${pad}${lineRightPadding}`;
      out.push(visibleWidth(renderedLine) > width ? truncateToWidth(renderedLine, width, "") : renderedLine);
    }

    const below = layout.length - (this.scrollOffset + visible.length);
    if (below > 0) {
      const indicator = `─── ↓ ${below} more `;
      const remaining = width - visibleWidth(indicator);
      out.push(this.theme.borderColor(remaining >= 0 ? indicator + "─".repeat(remaining) : truncateToWidth(indicator, width, "")));
    } else {
      out.push(border.repeat(width));
    }

    if (this.autocompleteState && this.autocompleteList) {
      const autocompleteResult = this.autocompleteList.render(contentWidth);
      for (const line of autocompleteResult) {
        const lineWidth = visibleWidth(line);
        const linePadding = " ".repeat(Math.max(0, contentWidth - lineWidth));
        const renderedLine = `${leftPadding}${line}${linePadding}${rightPadding}`;
        out.push(visibleWidth(renderedLine) > width ? truncateToWidth(renderedLine, width, "") : renderedLine);
      }
    }

    if (out.length > 0) {
      const baseMode = this.searchPrompt
        ? `${this.searchPrompt.direction > 0 ? "/" : "?"}${this.searchPrompt.query}`
        : this.mode === "visual"
          ? " VISUAL "
          : this.mode === "normal"
            ? " NORMAL "
            : " INSERT ";
      const pending = this.pendingOperator ? `${this.pendingOperator}${this.pendingTextObjectPrefix ?? ""}` : this.pendingG ? "g" : "";
      const label = truncateToWidth(`${baseMode}${pending ? ` ${pending}` : ""} `, width, "");
      const last = out.length - 1;
      const available = Math.max(0, width - visibleWidth(label));
      out[last] = visibleWidth(label) >= width ? label : label + truncateToWidth(out[last] ?? "", available, "");
    }

    return out;
  }
}

function dataIsPrintable(data: string): boolean {
  return data.length === 1 && data.charCodeAt(0) >= 32;
}

export default function (pi: ExtensionAPI) {
  pi.on("session_start", (_event, ctx) => {
    ctx.ui.setEditorComponent((tui, theme, keybindings) => new VimModalEditor(tui, theme, keybindings));
  });
}
