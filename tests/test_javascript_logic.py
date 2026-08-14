from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[1]


def test_javascript_rule_and_generator_suite() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required to run the JavaScript logic tests")

    result = subprocess.run(
        [node, "tests/generator.test.js"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "JavaScript logic tests passed" in result.stdout
