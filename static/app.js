const SIZE = 4;
const CELLS = SIZE ** 3;
const GENERATOR_SEED = 0x3b1a1044;

const boardEl = document.querySelector("#board");
const gameCardEl = document.querySelector(".game-card");
const faceNameEl = document.querySelector("#face-name");
const facePickerEl = document.querySelector("#face-picker");
const layerNumberEl = document.querySelector("#layer-number");
const layerPickerEl = document.querySelector("#layer-picker");
const axisXEl = document.querySelector("#axis-x");
const axisYEl = document.querySelector("#axis-y");
const rowSumsEl = document.querySelector("#row-sums");
const columnSumsEl = document.querySelector("#column-sums");
const undoButton = document.querySelector("#undo-button");
const statusText = document.querySelector("#status-text");
const progressBar = document.querySelector("#progress-bar");
const progressText = document.querySelector("#progress-text");
const toast = document.querySelector("#toast");

let solution = [];
let puzzle = [];
let values = [];
let currentFace = "front";
let currentLayer = 0;
let history = [];
let isTurning = false;
let toastTimer;

const indexOf = (x, y, z) => z * 16 + y * 4 + x;
const get = (grid, x, y, z) => grid[indexOf(x, y, z)];
const QUARTER_TURN = Math.SQRT1_2;

const FACE_CONFIGS = {
  front: {
    name: "Front", axis: "z", depthOrder: [0, 1, 2, 3], horizontalAxis: "X", verticalAxis: "Y",
    orientation: [0, 0, 0, 1],
    coordinates: (column, row, slice) => [column, row, slice],
  },
  back: {
    name: "Back", axis: "z", depthOrder: [3, 2, 1, 0], horizontalAxis: "X", verticalAxis: "Y",
    orientation: [0, 1, 0, 0],
    coordinates: (column, row, slice) => [SIZE - 1 - column, row, slice],
  },
  left: {
    name: "Left", axis: "x", depthOrder: [0, 1, 2, 3], horizontalAxis: "Z", verticalAxis: "Y",
    orientation: [0, -QUARTER_TURN, 0, QUARTER_TURN],
    coordinates: (column, row, slice) => [slice, row, SIZE - 1 - column],
  },
  right: {
    name: "Right", axis: "x", depthOrder: [3, 2, 1, 0], horizontalAxis: "Z", verticalAxis: "Y",
    orientation: [0, QUARTER_TURN, 0, QUARTER_TURN],
    coordinates: (column, row, slice) => [slice, row, column],
  },
  up: {
    name: "Up", axis: "y", depthOrder: [0, 1, 2, 3], horizontalAxis: "X", verticalAxis: "Z",
    orientation: [QUARTER_TURN, 0, 0, QUARTER_TURN],
    coordinates: (column, row, slice) => [column, slice, SIZE - 1 - row],
  },
  down: {
    name: "Down", axis: "y", depthOrder: [3, 2, 1, 0], horizontalAxis: "X", verticalAxis: "Z",
    orientation: [-QUARTER_TURN, 0, 0, QUARTER_TURN],
    coordinates: (column, row, slice) => [column, slice, row],
  },
};

function indexForView(column, row, slice) {
  return indexOf(...FACE_CONFIGS[currentFace].coordinates(column, row, slice));
}

function sliceForIndex(index) {
  const z = Math.floor(index / 16);
  const y = Math.floor((index % 16) / 4);
  const x = index % 4;
  return { x, y, z }[FACE_CONFIGS[currentFace].axis];
}

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

function remainingColors(indices) {
  const line = indices.map(index => values[index]);
  return {
    red: Math.max(0, 2 - line.filter(value => value === false).length),
    blue: Math.max(0, 2 - line.filter(value => value === true).length),
  };
}

function sumMarkup(remaining, vertical = false) {
  return `<span class="remaining-red" aria-label="${remaining.red} red remaining">${remaining.red}</span>`
    + (vertical ? '<span class="sum-divider" aria-hidden="true"></span>' : '<span class="sum-divider" aria-hidden="true">|</span>')
    + `<span class="remaining-blue" aria-label="${remaining.blue} blue remaining">${remaining.blue}</span>`;
}

function renderSums() {
  rowSumsEl.innerHTML = "";
  columnSumsEl.innerHTML = "";
  for (let row = 0; row < SIZE; row++) {
    const indices = Array.from({ length: SIZE }, (_, column) => indexForView(column, row, currentLayer));
    const remaining = remainingColors(indices);
    const sum = document.createElement("div");
    sum.className = "row-sum";
    sum.innerHTML = sumMarkup(remaining);
    sum.setAttribute("aria-label", `Row ${row + 1}: ${remaining.red} red and ${remaining.blue} blue remaining`);
    rowSumsEl.appendChild(sum);
  }
  for (let column = 0; column < SIZE; column++) {
    const indices = Array.from({ length: SIZE }, (_, row) => indexForView(column, row, currentLayer));
    const remaining = remainingColors(indices);
    const sum = document.createElement("div");
    sum.className = "column-sum";
    sum.innerHTML = sumMarkup(remaining, true);
    sum.setAttribute("aria-label", `Column ${column + 1}: ${remaining.red} red and ${remaining.blue} blue remaining`);
    columnSumsEl.appendChild(sum);
  }
}

function alignSumsWithSelectedDepth() {
  const firstCell = boardEl.querySelector(".cell-button");
  const activeOrb = firstCell?.querySelector(".orb.active");
  if (!firstCell || !activeOrb) return;
  const cellBounds = firstCell.getBoundingClientRect();
  const orbBounds = activeOrb.getBoundingClientRect();
  const cellCenterX = cellBounds.left + cellBounds.width / 2;
  const cellCenterY = cellBounds.top + cellBounds.height / 2;
  const orbCenterX = orbBounds.left + orbBounds.width / 2;
  const orbCenterY = orbBounds.top + orbBounds.height / 2;
  rowSumsEl.style.transform = `translateY(${orbCenterY - cellCenterY}px)`;
  columnSumsEl.style.transform = `translateX(${orbCenterX - cellCenterX}px)`;
}

function render() {
  const conflicts = findConflicts(values);
  const face = FACE_CONFIGS[currentFace];
  boardEl.innerHTML = "";
  boardEl.setAttribute("aria-label", `${face.name} face, slice ${currentLayer + 1} of the puzzle`);
  faceNameEl.textContent = face.name;
  layerNumberEl.textContent = currentLayer + 1;
  axisXEl.textContent = face.horizontalAxis;
  axisYEl.textContent = face.verticalAxis;

  facePickerEl.innerHTML = "";
  for (const [faceKey, config] of Object.entries(FACE_CONFIGS)) {
    const faceButton = document.createElement("button");
    faceButton.className = `face-button${faceKey === currentFace ? " active" : ""}`;
    faceButton.textContent = config.name;
    faceButton.setAttribute("aria-label", `View ${config.name} face`);
    faceButton.setAttribute("aria-pressed", String(faceKey === currentFace));
    faceButton.addEventListener("click", () => setFace(faceKey));
    facePickerEl.appendChild(faceButton);
  }

  for (let row = 0; row < SIZE; row++) {
    for (let column = 0; column < SIZE; column++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.setAttribute("role", "gridcell");
      const button = document.createElement("button");
      const activeIndex = indexForView(column, row, currentLayer);
      const fixed = puzzle[activeIndex] !== null;
      button.className = `cell-button${fixed ? " fixed" : ""}${conflicts.has(activeIndex) ? " invalid" : ""}`;
      button.dataset.index = activeIndex;
      button.disabled = fixed;
      button.setAttribute("aria-label", `${fixed ? "Given" : "Cell"}, row ${row + 1}, column ${column + 1}: ${valueClass(values[activeIndex])}`);

      for (let depth = 0; depth < SIZE; depth++) {
        const slice = face.depthOrder[depth];
        const index = indexForView(column, row, slice);
        const orb = document.createElement("span");
        const value = values[index];
        const isFixed = puzzle[index] !== null;
        orb.className = `orb layer-${depth}${slice === currentLayer ? " active" : ""} ${valueClass(value)}${isFixed ? " fixed" : ""}`;
        orb.dataset.index = index;
        orb.dataset.slice = slice + 1;
        button.appendChild(orb);
      }
      button.addEventListener("click", onCellClick);
      button.addEventListener("contextmenu", onCellRightClick);
      cell.appendChild(button);
      boardEl.appendChild(cell);
    }
  }

  renderSums();
  alignSumsWithSelectedDepth();

  layerPickerEl.innerHTML = "";
  for (const slice of face.depthOrder) {
    const chip = document.createElement("button");
    chip.className = `layer-chip${slice === currentLayer ? " active" : ""}`;
    chip.textContent = slice + 1;
    chip.setAttribute("aria-label", `Show slice ${slice + 1}`);
    chip.addEventListener("click", () => setLayer(slice));
    layerPickerEl.appendChild(chip);
  }

  const filled = values.filter(v => v !== null).length;
  progressText.textContent = `${filled} / ${CELLS}`;
  progressBar.style.width = `${(filled / CELLS) * 100}%`;
  undoButton.disabled = history.length === 0;

  if (filled === CELLS && conflicts.size === 0 && values.every((v, i) => v === solution[i])) {
    statusText.textContent = "Cube complete";
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
  if (isTurning) return;
  const index = Number(event.currentTarget.dataset.index);
  cycleCell(index, 1);
}

function onCellRightClick(event) {
  event.preventDefault();
  if (isTurning) return;
  const index = Number(event.currentTarget.dataset.index);
  cycleCell(index, -1);
}

function cycleCell(index, direction) {
  history.push({ index, previous: values[index] });
  const cycle = direction > 0 ? [null, false, true] : [null, true, false];
  values[index] = cycle[(cycle.indexOf(values[index]) + 1) % cycle.length];
  render();
}

function setLayer(layer) {
  currentLayer = (layer + SIZE) % SIZE;
  render();
}

function moveLayer(offset) {
  if (isTurning) return;
  const order = FACE_CONFIGS[currentFace].depthOrder;
  const position = order.indexOf(currentLayer);
  setLayer(order[(position + offset + SIZE) % SIZE]);
}

function captureOrbCenters() {
  return new Map(Array.from(boardEl.querySelectorAll(".orb"), orb => {
    const bounds = orb.getBoundingClientRect();
    return [orb.dataset.index, {
      x: bounds.left + bounds.width / 2,
      y: bounds.top + bounds.height / 2,
    }];
  }));
}

function cubeCoordinates(index) {
  return [
    index % 4 - 1.5,
    Math.floor((index % 16) / 4) - 1.5,
    Math.floor(index / 16) - 1.5,
  ];
}

function quaternionDot(first, second) {
  return first.reduce((sum, value, index) => sum + value * second[index], 0);
}

function slerpQuaternion(start, finish, progress) {
  let end = finish;
  let dot = quaternionDot(start, end);
  if (dot < 0) {
    end = end.map(value => -value);
    dot = -dot;
  }
  dot = Math.min(1, Math.max(-1, dot));
  if (dot > .9995) {
    const mixed = start.map((value, index) => value + progress * (end[index] - value));
    const length = Math.hypot(...mixed);
    return mixed.map(value => value / length);
  }
  const angle = Math.acos(dot);
  const denominator = Math.sin(angle);
  const startWeight = Math.sin((1 - progress) * angle) / denominator;
  const endWeight = Math.sin(progress * angle) / denominator;
  return start.map((value, index) => startWeight * value + endWeight * end[index]);
}

function rotateVector(quaternion, vector) {
  const [qx, qy, qz, qw] = quaternion;
  const [vx, vy, vz] = vector;
  const tx = 2 * (qy * vz - qz * vy);
  const ty = 2 * (qz * vx - qx * vz);
  const tz = 2 * (qx * vy - qy * vx);
  return [
    vx + qw * tx + qy * tz - qz * ty,
    vy + qw * ty + qz * tx - qx * tz,
    vz + qw * tz + qx * ty - qy * tx,
  ];
}

function projectionGeometry() {
  const boardBounds = boardEl.getBoundingClientRect();
  const buttonWidth = boardEl.querySelector(".cell-button").getBoundingClientRect().width;
  return {
    centerX: boardBounds.left + boardBounds.width / 2,
    centerY: boardBounds.top + boardBounds.height / 2,
    gridX: boardBounds.width / SIZE,
    gridY: boardBounds.height / SIZE,
    depthX: buttonWidth * .10,
    depthY: buttonWidth * (-.64 / 3),
  };
}

function projectCubePoint(index, orientation, geometry) {
  const [horizontal, vertical, depth] = rotateVector(orientation, cubeCoordinates(index));
  return {
    x: geometry.centerX + horizontal * geometry.gridX + depth * geometry.depthX,
    y: geometry.centerY + vertical * geometry.gridY + depth * geometry.depthY,
  };
}

function turnKeyframes(index, startOrientation, endOrientation, oldCenter, newCenter, geometry) {
  const frameCount = 25;
  const projectedStart = projectCubePoint(index, startOrientation, geometry);
  const projectedEnd = projectCubePoint(index, endOrientation, geometry);
  return Array.from({ length: frameCount }, (_, frame) => {
    const progress = frame / (frameCount - 1);
    const orientation = slerpQuaternion(startOrientation, endOrientation, progress);
    const projected = projectCubePoint(index, orientation, geometry);

    // Small endpoint corrections make the sampled 3D projection meet the
    // exact CSS layout without a jump at either end of the animation.
    const x = projected.x
      + (1 - progress) * (oldCenter.x - projectedStart.x)
      + progress * (newCenter.x - projectedEnd.x);
    const y = projected.y
      + (1 - progress) * (oldCenter.y - projectedStart.y)
      + progress * (newCenter.y - projectedEnd.y);
    const deltaX = x - newCenter.x;
    const deltaY = y - newCenter.y;
    return {
      offset: progress,
      transform: `translate(calc(-50% + ${deltaX}px), calc(-50% + ${deltaY}px))`,
    };
  });
}

function pause(milliseconds) {
  return new Promise(resolve => setTimeout(resolve, milliseconds));
}

async function setFace(face) {
  if (face === currentFace || isTurning) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    currentFace = face;
    render();
    return;
  }

  isTurning = true;
  const startOrientation = FACE_CONFIGS[currentFace].orientation;
  const endOrientation = FACE_CONFIGS[face].orientation;
  gameCardEl.classList.add("turning", "equalized");
  gameCardEl.setAttribute("aria-busy", "true");

  // First let the selected and unselected markers become visually equivalent.
  await pause(170);
  const oldCenters = captureOrbCenters();

  // Render the target projection, then place every physical marker back at
  // its old screen position so the browser can animate it into the new one.
  currentFace = face;
  render();
  const geometry = projectionGeometry();
  const turnAngle = 2 * Math.acos(Math.min(1, Math.abs(quaternionDot(startOrientation, endOrientation))));
  const duration = turnAngle > Math.PI * .75 ? 520 : 430;
  const animations = Array.from(boardEl.querySelectorAll(".orb"), orb => {
    const oldCenter = oldCenters.get(orb.dataset.index);
    const bounds = orb.getBoundingClientRect();
    const newCenter = {
      x: bounds.left + bounds.width / 2,
      y: bounds.top + bounds.height / 2,
    };
    const keyframes = turnKeyframes(
      Number(orb.dataset.index),
      startOrientation,
      endOrientation,
      oldCenter,
      newCenter,
      geometry,
    );
    return orb.animate(keyframes, {
      duration,
      easing: "cubic-bezier(.45, 0, .2, 1)",
      fill: "both",
    });
  });

  await Promise.all(animations.map(animation => animation.finished.catch(() => undefined)));
  animations.forEach(animation => animation.cancel());

  // Restore colors and selected-slice emphasis once the turn has landed.
  gameCardEl.classList.remove("equalized");
  await pause(170);
  gameCardEl.classList.remove("turning");
  gameCardEl.removeAttribute("aria-busy");
  isTurning = false;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 2800);
}

function newGame() {
  if (isTurning) return;
  const button = document.querySelector("#new-button");
  button.disabled = true;
  button.textContent = "Building…";
  requestAnimationFrame(() => setTimeout(() => {
    resetGenerator();
    solution = generateSolution();
    puzzle = makePuzzle(solution);
    values = [...puzzle];
    history = [];
    currentFace = "front";
    currentLayer = 0;
    button.disabled = false;
    button.textContent = "New game";
    render();
    showToast("A fresh cube is ready.");
  }, 20));
}

document.querySelector("#prev-layer").addEventListener("click", () => moveLayer(-1));
document.querySelector("#next-layer").addEventListener("click", () => moveLayer(1));
document.querySelector("#new-button").addEventListener("click", newGame);
undoButton.addEventListener("click", () => {
  if (isTurning) return;
  const move = history.pop();
  if (!move) return;
  values[move.index] = move.previous;
  currentLayer = sliceForIndex(move.index);
  render();
});

document.addEventListener("keydown", event => {
  if (event.key === "ArrowLeft") moveLayer(-1);
  if (event.key === "ArrowRight") moveLayer(1);
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
