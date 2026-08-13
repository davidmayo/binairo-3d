const fs = require("node:fs");
const assert = require("node:assert/strict");

const app = fs.readFileSync("static/app.js", "utf8");
const source = app.split("const boardEl")[0]
  + app.slice(app.indexOf("const indexOf"), app.indexOf("function valueClass"));

eval(`${source}
  const started = performance.now();
  const cube = generateSolution();
  assert.equal(VALID_BOARDS.length > 0, true);
  assert.equal(allPlanesValid(cube, true), true);

  const clues = makePuzzle(cube);
  const clueCount = clues.filter(value => value !== null).length;
  assert.equal(clueCount >= 22, true);
  assert.equal(clueCount <= 30, true);
  assert.equal(countSolutions(clues), 1);
  console.log(\`Generator test passed: \${clueCount} clues in \${Math.round(performance.now() - started)}ms\`);
`);
