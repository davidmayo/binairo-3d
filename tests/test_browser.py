import math
import re
import socket
import subprocess
import sys
import time

import httpx
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def live_server() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(50):
            try:
                if httpx.get(url).status_code == 200:
                    break
            except httpx.ConnectError:
                time.sleep(0.1)
        else:
            raise RuntimeError("Test server did not start")
        yield url
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_game_in_firefox(page: Page, live_server: str) -> None:
    page.goto(live_server)
    expect(page.locator(".cell-button")).to_have_count(16)

    initial_board = page.locator(".orb").evaluate_all("orbs => orbs.map(orb => orb.className)")
    page.locator("#new-button").click()
    page.wait_for_function("!document.querySelector('#new-button').disabled")
    repeated_board = page.locator(".orb").evaluate_all("orbs => orbs.map(orb => orb.className)")
    assert repeated_board == initial_board

    first_cell = page.locator(".cell-button").first
    layer_1 = first_cell.locator(".layer-0")
    layer_4 = first_cell.locator(".layer-3")
    first_box = layer_1.bounding_box()
    fourth_box = layer_4.bounding_box()
    cell_box = first_cell.bounding_box()
    assert first_box is not None and fourth_box is not None and cell_box is not None
    assert first_box["width"] / cell_box["width"] == pytest.approx(0.406, abs=0.005)
    delta_x = fourth_box["x"] + fourth_box["width"] / 2 - first_box["x"] - first_box["width"] / 2
    delta_y = fourth_box["y"] + fourth_box["height"] / 2 - first_box["y"] - first_box["height"] / 2
    angle = math.degrees(math.atan2(abs(delta_y), abs(delta_x)))
    assert angle == pytest.approx(65, abs=1)

    selected_style = layer_1.evaluate(
        "orb => ({ background: getComputedStyle(orb).backgroundColor, "
        "borderColor: getComputedStyle(orb).borderTopColor, "
        "borderWidth: getComputedStyle(orb).borderTopWidth })"
    )
    assert selected_style == {
        "background": "rgba(36, 39, 38, 0.15)",
        "borderColor": "rgb(36, 39, 38)",
        "borderWidth": "1px",
    }

    page.locator(".layer-chip").nth(2).click()
    expect(first_cell.locator(".layer-2")).to_have_class(re.compile(r"\bactive\b"))
