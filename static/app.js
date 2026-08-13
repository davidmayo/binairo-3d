const SIZE = 4;
const CELLS = SIZE ** 3;
const GENERATOR_SEED = 0x3b1a1044;

const boardEl = document.querySelector("#board");
const layerNumberEl = document.querySelector("#layer-number");
const layerPickerEl = document.querySelector("#layer-picker");
const undoButton = document.querySelector("#undo-button");
const statusText = document.querySelector("#status-text");
const progressBar = document.querySelector("#progress-bar");
const progressText = document.querySelector("#progress-text");
const toast = document.querySelector("#toast");

let solution = [];
let puzzle = [];
let values = [];
let currentLayer = 0;
let history = [];
let toastTimer;

const indexOf = (x, y, z) => z * 16 + y * 4 + x;
const get = (grid, x, y, z) => grid[indexOf(x, y, z)];

function seededRandom(seed) {
  return function random() {
    seed |= 0;
    seed = seed + 0x6d2b79f5 | 0;
    let value = Math.imul(seed ^ seed >>> 15, 1 | seed);
    value = value + Math.imul(value ^ value >>> 7, 61 | value) ^ value;
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

let random = seededRandom(GENERATOR_SEED);

function resetGenerator() {
  random = seededRandom(GENERATOR_SEED);
}

function validLine(line, complete = false) {
  const filled = line.filter(v => v !== null);
  const ones = filled.filter(Boolean).length;
  const zeros = filled.length - ones;
  if (ones > 2 || zeros > 2) return false;
  for (let i = 0; i < 2; i++) {
    if (line[i] !== null && line[i] === line[i + 1] && line[i] === line[i + 2]) return false;
  }
  return !complete || filled.length === 4;
}

function planeLines(grid, axis, fixed) {
  const rows = [];
  const cols = [];
  for (let a = 0; a < SIZE; a++) {
    const row = [];
    const col = [];
    for (let b = 0; b < SIZE; b++) {
      if (axis === "z") {
        row.push(get(grid, b, a, fixed));
        col.push(get(grid, a, b, fixed));
      } else if (axis === "y") {
        row.push(get(grid, b, fixed, a));
        col.push(get(grid, a, fixed, b));
      } else {
        row.push(get(grid, fixed, b, a));
        col.push(get(grid, fixed, a, b));
      }
    }
    rows.push(row);
    cols.push(col);
  }
  return [...rows, ...cols];
}

function validPlane(grid, axis, fixed, requireComplete = false) {
  const lines = planeLines(grid, axis, fixed);
  if (!lines.every(line => validLine(line, requireComplete))) return false;
  for (const group of [lines.slice(0, 4), lines.slice(4)]) {
    const complete = group.filter(line => line.every(v => v !== null));
    const signatures = complete.map(line => line.map(Number).join(""));
    if (new Set(signatures).size !== signatures.length) return false;
  }
  return true;
}

function allPlanesValid(grid, requireComplete = false) {
  return ["x", "y", "z"].every(axis =>
    Array.from({ length: SIZE }, (_, fixed) => validPlane(grid, axis, fixed, requireComplete)).every(Boolean)
  );
}

function generateBoards() {
  const lines = [];
  for (let bits = 0; bits < 16; bits++) {
    const line = Array.from({ length: 4 }, (_, i) => Boolean((bits >> i) & 1));
    if (validLine(line, true)) lines.push(line);
  }
  const boards = [];
  for (const a of lines) for (const b of lines) for (const c of lines) for (const d of lines) {
    const flat = [...a, ...b, ...c, ...d];
    if (validPlane(flat, "z", 0, true)) boards.push(flat);
  }
  return boards;
}

const VALID_BOARDS = generateBoards();

function shuffle(items) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function generateSolution() {
  const grid = Array(CELLS).fill(null);
  const candidates = shuffle(VALID_BOARDS);

  function placeLayer(z) {
    if (z === SIZE) return allPlanesValid(grid, true);
    for (const candidate of shuffle(candidates)) {
      for (let i = 0; i < 16; i++) grid[z * 16 + i] = candidate[i];
      const relevant = ["x", "y"].every(axis =>
        Array.from({ length: SIZE }, (_, fixed) => validPlane(grid, axis, fixed)).every(Boolean)
      );
      if (relevant && placeLayer(z + 1)) return true;
      for (let i = 0; i < 16; i++) grid[z * 16 + i] = null;
    }
    return false;
  }

  if (!placeLayer(0)) throw new Error("Could not generate a valid cube");
  return grid;
}

function countSolutions(start, limit = 2) {
  const grid = [...start];
  let count = 0;

  function solve() {
    if (count >= limit) return;
    let bestIndex = -1;
    let bestOptions = null;
    for (let i = 0; i < CELLS; i++) {
      if (grid[i] !== null) continue;
      const options = [false, true].filter(value => {
        grid[i] = value;
        const ok = allPlanesValid(grid);
        grid[i] = null;
        return ok;
      });
      if (!options.length) return;
      if (!bestOptions || options.length < bestOptions.length) {
        bestIndex = i;
        bestOptions = options;
        if (options.length === 1) break;
      }
    }
    if (bestIndex < 0) {
      count++;
      return;
    }
    for (const value of bestOptions) {
      grid[bestIndex] = value;
      solve();
      grid[bestIndex] = null;
      if (count >= limit) return;
    }
  }

  solve();
  return count;
}

function makePuzzle(full) {
  const clues = [...full];
  const order = shuffle(Array.from({ length: CELLS }, (_, i) => i));
  const targetClues = 22 + Math.floor(random() * 4);
  for (const index of order) {
    if (clues.filter(v => v !== null).length <= targetClues) break;
    const saved = clues[index];
    clues[index] = null;
    if (countSolutions(clues, 2) !== 1) clues[index] = saved;
  }
  return clues;
}

function valueClass(value) {
  return value === null ? "empty" : value ? "blue" : "coral";
}

function findConflicts(grid) {
  const conflicts = new Set();
  for (const axis of ["x", "y", "z"]) {
    for (let fixed = 0; fixed < SIZE; fixed++) {
      const lines = planeLines(grid, axis, fixed);
      lines.forEach((line, lineIndex) => {
        if (validLine(line) && !(line.every(v => v !== null) && duplicateInGroup(lines, lineIndex))) return;
        line.forEach((value, position) => {
          if (value === null) return;
          let x, y, z;
          const isColumn = lineIndex >= 4;
          const a = lineIndex % 4;
          const b = position;
          if (axis === "z") [x, y, z] = isColumn ? [a, b, fixed] : [b, a, fixed];
          if (axis === "y") [x, y, z] = isColumn ? [a, fixed, b] : [b, fixed, a];
          if (axis === "x") [x, y, z] = isColumn ? [fixed, a, b] : [fixed, b, a];
          conflicts.add(indexOf(x, y, z));
        });
      });
    }
  }
  return conflicts;
}

function duplicateInGroup(lines, lineIndex) {
  const line = lines[lineIndex];
  if (!line.every(v => v !== null)) return false;
  const start = lineIndex < 4 ? 0 : 4;
  const signature = line.map(Number).join("");
  return lines.slice(start, start + 4).filter(other => other.every(v => v !== null) && other.map(Number).join("") === signature).length > 1;
}

function render() {
  const conflicts = findConflicts(values);
  boardEl.innerHTML = "";
  boardEl.setAttribute("aria-label", `Layer ${currentLayer + 1} of the puzzle`);
  layerNumberEl.textContent = currentLayer + 1;

  for (let y = 0; y < SIZE; y++) {
    for (let x = 0; x < SIZE; x++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.setAttribute("role", "gridcell");
      const button = document.createElement("button");
      const activeIndex = indexOf(x, y, currentLayer);
      const fixed = puzzle[activeIndex] !== null;
      button.className = `cell-button${fixed ? " fixed" : ""}${conflicts.has(activeIndex) ? " invalid" : ""}`;
      button.dataset.index = activeIndex;
      button.disabled = fixed;
      button.setAttribute("aria-label", `${fixed ? "Given" : "Cell"}, row ${y + 1}, column ${x + 1}: ${valueClass(values[activeIndex])}`);

      for (let z = 0; z < SIZE; z++) {
        const orb = document.createElement("span");
        const value = get(values, x, y, z);
        const isFixed = puzzle[indexOf(x, y, z)] !== null;
        orb.className = `orb layer-${z}${z === currentLayer ? " active" : ""} ${valueClass(value)}${isFixed ? " fixed" : ""}`;
        button.appendChild(orb);
      }
      button.addEventListener("click", onCellClick);
      cell.appendChild(button);
      boardEl.appendChild(cell);
    }
  }

  layerPickerEl.innerHTML = "";
  for (let z = 0; z < SIZE; z++) {
    const chip = document.createElement("button");
    chip.className = `layer-chip${z === currentLayer ? " active" : ""}`;
    chip.textContent = z + 1;
    chip.setAttribute("aria-label", `Show layer ${z + 1}`);
    chip.addEventListener("click", () => setLayer(z));
    layerPickerEl.appendChild(chip);
  }

  const filled = values.filter(v => v !== null).length;
  progressText.textContent = `${filled} / ${CELLS}`;
  progressBar.style.width = `${(filled / CELLS) * 100}%`;
  undoButton.disabled = history.length === 0;

  if (filled === CELLS && conflicts.size === 0 && values.every((v, i) => v === solution[i])) {
    statusText.textContent = "Cube complete — beautifully done";
    document.querySelector(".status-dot").style.background = "var(--blue)";
    showToast("Cube solved! Every slice is valid.");
  } else if (conflicts.size) {
    statusText.textContent = `${conflicts.size} conflicting circle${conflicts.size === 1 ? "" : "s"}`;
    document.querySelector(".status-dot").style.background = "var(--coral)";
  } else {
    statusText.textContent = "Cube in progress";
    document.querySelector(".status-dot").style.background = "var(--acid)";
  }
}

function onCellClick(event) {
  const index = Number(event.currentTarget.dataset.index);
  history.push({ index, previous: values[index] });
  values[index] = values[index] === null ? false : values[index] === false ? true : null;
  render();
}

function setLayer(layer) {
  currentLayer = (layer + SIZE) % SIZE;
  render();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

function newGame() {
  const button = document.querySelector("#new-button");
  button.disabled = true;
  button.textContent = "Building…";
  requestAnimationFrame(() => setTimeout(() => {
    resetGenerator();
    solution = generateSolution();
    puzzle = makePuzzle(solution);
    values = [...puzzle];
    history = [];
    currentLayer = 0;
    button.disabled = false;
    button.textContent = "New game";
    render();
    showToast("A fresh cube is ready.");
  }, 20));
}

document.querySelector("#prev-layer").addEventListener("click", () => setLayer(currentLayer - 1));
document.querySelector("#next-layer").addEventListener("click", () => setLayer(currentLayer + 1));
document.querySelector("#new-button").addEventListener("click", newGame);
undoButton.addEventListener("click", () => {
  const move = history.pop();
  if (!move) return;
  values[move.index] = move.previous;
  currentLayer = Math.floor(move.index / 16);
  render();
});

document.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft") setLayer(currentLayer - 1);
  if (event.key === "ArrowRight") setLayer(currentLayer + 1);
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
    event.preventDefault();
    undoButton.click();
  }
});

resetGenerator();
solution = generateSolution();
puzzle = makePuzzle(solution);
values = [...puzzle];
render();
