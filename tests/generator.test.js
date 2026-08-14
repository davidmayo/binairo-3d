const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("static/app.js", "utf8");
const source = app.split("const boardEl")[0]
  + app.slice(app.indexOf("const indexOf"), app.indexOf("function valueClass"));

eval(`${source}
  const started = performance.now();
  for (const size of [4, 6, 8, 10]) {
    SIZE = size;
    CELLS = SIZE ** 3;
    resetGenerator();
    const cube = generateSolution();
    assert.equal(cube.length, CELLS);
    assert.equal(allPlanesValid(cube, true), true);

    const clues = makePuzzle(cube);
    const clueCount = clues.filter(value => value !== null).length;
    assert.equal(clueCount < CELLS, true);
    assert.equal(countSolutions(clues), 1);
    resetGenerator();
    const repeatedCube = generateSolution();
    const repeatedClues = makePuzzle(repeatedCube);
    assert.deepEqual(repeatedCube, cube);
    assert.deepEqual(repeatedClues, clues);
    console.log(\`\${size}x\${size}x\${size}: \${clueCount} clues\`);
  }
  console.log(\`Generator tests passed in \${Math.round(performance.now() - started)}ms\`);
`);
