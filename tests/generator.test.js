const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("static/app.js", "utf8");
const preamble = app.slice(0, app.indexOf("const boardEl"));
const logic = app.slice(app.indexOf("const indexOf"), app.indexOf("function renderSums"));

const tests = String.raw`
let currentFace = "front";
let values = [];

function setSize(size) {
  SIZE = size;
  CELLS = SIZE ** 3;
  currentFace = "front";
  values = Array(CELLS).fill(null);
  resetGenerator();
}

function sorted(set) {
  return Array.from(set).sort((a, b) => a - b);
}

function assertEveryPlaneHasUniqueLines(cube) {
  for (const axis of ["x", "y", "z"]) {
    for (let fixed = 0; fixed < SIZE; fixed++) {
      const lines = planeLines(cube, axis, fixed);
      assert.equal(lines.length, SIZE * 2);
      for (const group of [lines.slice(0, SIZE), lines.slice(SIZE)]) {
        const signatures = group.map(line => line.map(Number).join(""));
        assert.equal(new Set(signatures).size, SIZE);
      }
    }
  }
}

// Individual line rules: balance, triples, and completion.
setSize(4);
assert.equal(validLine([false, false, true, true], true), true);
assert.equal(validLine([false, true, false, true], true), true);
assert.equal(validLine([false, null, true, null]), true);
assert.equal(validLine([false, null, true, null], true), false);
assert.equal(validLine([false, false, false, null]), false);
assert.equal(validLine([true, true, true, null]), false);
assert.equal(validLine([false, false, false, true]), false);
assert.equal(validLine([true, false, false, false]), false);

setSize(6);
assert.equal(validLine([false, false, true, false, true, true], true), true);
assert.equal(validLine([false, false, false, true, true, true], true), false);
assert.equal(validLine([false, true, true, true, false, false], true), false);
assert.equal(validLine([false, true, false, true, false, true], true), true);

// planeLines must select the correct physical rows and columns on every axis.
setSize(4);
const numberedCube = Array.from({ length: CELLS }, (_, index) => index);
assert.deepEqual(planeLines(numberedCube, "z", 1)[0], [16, 17, 18, 19]);
assert.deepEqual(planeLines(numberedCube, "z", 1)[4], [16, 20, 24, 28]);
assert.deepEqual(planeLines(numberedCube, "y", 1)[0], [4, 5, 6, 7]);
assert.deepEqual(planeLines(numberedCube, "y", 1)[4], [4, 20, 36, 52]);
assert.deepEqual(planeLines(numberedCube, "x", 1)[0], [1, 5, 9, 13]);
assert.deepEqual(planeLines(numberedCube, "x", 1)[4], [1, 17, 33, 49]);

// Every face projection is a bijection over the same physical cube.
for (const face of Object.keys(FACE_CONFIGS)) {
  currentFace = face;
  const seen = new Set();
  for (let slice = 0; slice < SIZE; slice++) {
    for (let row = 0; row < SIZE; row++) {
      for (let column = 0; column < SIZE; column++) {
        const index = indexForView(column, row, slice);
        assert.equal(index >= 0 && index < CELLS, true);
        seen.add(index);
        assert.equal(sliceForIndex(index), slice);
      }
    }
  }
  assert.equal(seen.size, CELLS);
}
assert.deepEqual(depthOrder(FACE_CONFIGS.front), [0, 1, 2, 3]);
assert.deepEqual(depthOrder(FACE_CONFIGS.back), [3, 2, 1, 0]);
assert.deepEqual(depthOrder(FACE_CONFIGS.left), [0, 1, 2, 3]);
assert.deepEqual(depthOrder(FACE_CONFIGS.right), [3, 2, 1, 0]);
assert.deepEqual(depthOrder(FACE_CONFIGS.up), [0, 1, 2, 3]);
assert.deepEqual(depthOrder(FACE_CONFIGS.down), [3, 2, 1, 0]);

// Duplicate-line and conflict reporting should identify all implicated cells.
const duplicateLines = [
  [false, false, true, true],
  [false, false, true, true],
  [false, true, false, true],
  [true, false, true, false],
  [false, false, true, true],
  [false, true, false, true],
  [true, false, true, false],
  [true, true, false, false],
];
assert.equal(duplicateInGroup(duplicateLines, 0), true);
assert.equal(duplicateInGroup(duplicateLines, 2), false);
assert.equal(duplicateInGroup(duplicateLines, 4), false);

let conflictGrid = Array(CELLS).fill(null);
conflictGrid[0] = conflictGrid[1] = conflictGrid[2] = false;
assert.deepEqual(sorted(findConflicts(conflictGrid)), [0, 1, 2]);

conflictGrid = Array(CELLS).fill(null);
for (const index of [0, 1, 2, 3, 4, 5, 6, 7]) {
  conflictGrid[index] = [false, false, true, true][index % 4];
}
assert.deepEqual(sorted(findConflicts(conflictGrid)), [0, 1, 2, 3, 4, 5, 6, 7]);

// Remaining-count helpers clamp overfilled lines and use a check for completion.
values = Array(CELLS).fill(null);
values[0] = false;
values[1] = true;
assert.deepEqual(remainingColors([0, 1, 2, 3]), { red: 1, blue: 1 });
values[2] = false;
values[3] = true;
assert.deepEqual(remainingColors([0, 1, 2, 3]), { red: 0, blue: 0 });
assert.match(sumMarkup({ red: 0, blue: 0 }), /remaining-check/);
assert.doesNotMatch(sumMarkup({ red: 2, blue: 1 }, true), />\|</);
assert.match(sumMarkup({ red: 2, blue: 1 }), />\|</);

// Seeded generation must be deterministic, valid, balanced, and playable.
const started = performance.now();
for (const size of [4, 6, 8, 10]) {
  setSize(size);
  const cube = generateSolution();
  assert.equal(cube.length, CELLS);
  assert.equal(cube.every(value => typeof value === "boolean"), true);
  assert.equal(cube.filter(Boolean).length, CELLS / 2);
  assert.equal(allPlanesValid(cube, true), true);
  assert.equal(findConflicts(cube).size, 0);
  assertEveryPlaneHasUniqueLines(cube);

  const clues = makePuzzle(cube);
  const clueCount = clues.filter(value => value !== null).length;
  assert.equal(clueCount > 0 && clueCount < CELLS, true);
  assert.equal(clues.every((value, index) => value === null || value === cube[index]), true);
  if (size <= 6) {
    assert.equal(countSolutions(clues), 1);
  } else {
    assert.equal(CELLS - clueCount, SIZE * SIZE);
    for (const axis of ["x", "y", "z"]) {
      for (let fixed = 0; fixed < SIZE; fixed++) {
        for (const line of planeLines(clues, axis, fixed)) {
          assert.equal(line.filter(value => value === null).length, 1);
        }
      }
    }
  }

  resetGenerator();
  const repeatedCube = generateSolution();
  const repeatedClues = makePuzzle(repeatedCube);
  assert.deepEqual(repeatedCube, cube);
  assert.deepEqual(repeatedClues, clues);
  console.log(String(size) + "x" + String(size) + "x" + String(size) + ": " + String(clueCount) + " clues");
}

setSize(4);
assert.equal(countSolutions(Array(CELLS).fill(null), 2), 2);
console.log("JavaScript logic tests passed in " + String(Math.round(performance.now() - started)) + "ms");
`;

new Function("assert", [preamble, logic, tests].join("\n"))(assert);
