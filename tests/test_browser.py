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

    expect(page.locator(".face-button")).to_have_count(6)
    expect(page.locator(".layer-chip")).to_have_text(["1", "2", "3", "4"])
    expect(page.locator(".row-sum")).to_have_count(4)
    expect(page.locator(".column-sum")).to_have_count(4)
    expect(page.locator(".row-sum").first).to_have_css("font-size", "16px")
    expect(page.locator(".row-sum").first).to_have_css("font-weight", "600")

    def assert_sums_aligned() -> None:
        cell_box = page.locator(".cell-button").first.bounding_box()
        orb_box = page.locator(".cell-button").first.locator(".orb.active").bounding_box()
        row_box = page.locator(".row-sum").first.bounding_box()
        column_box = page.locator(".column-sum").first.bounding_box()
        assert cell_box and orb_box and row_box and column_box
        assert row_box["y"] + row_box["height"] / 2 == pytest.approx(
            orb_box["y"] + orb_box["height"] / 2, abs=1
        )
        assert column_box["x"] + column_box["width"] / 2 == pytest.approx(
            orb_box["x"] + orb_box["width"] / 2, abs=1
        )

    assert_sums_aligned()
    page.locator(".layer-chip").nth(2).click()
    assert_sums_aligned()
    page.locator(".layer-chip").first.click()

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

    editable = page.locator(".cell-button:not(.fixed)").first
    editable_position = editable.evaluate("button => Array.from(document.querySelectorAll('.cell-button')).indexOf(button)")
    editable_row = editable_position // 4
    editable_column = editable_position % 4
    row_red_before = int(page.locator(".row-sum").nth(editable_row).locator(".remaining-red").text_content())
    column_red_before = int(page.locator(".column-sum").nth(editable_column).locator(".remaining-red").text_content())
    edited_index = int(editable.get_attribute("data-index"))
    edited_x = edited_index % 4
    edited_y = (edited_index % 16) // 4
    editable.click()
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bcoral\b"))
    expect(page.locator(".row-sum").nth(editable_row).locator(".remaining-red")).to_have_text(str(row_red_before - 1))
    expect(page.locator(".column-sum").nth(editable_column).locator(".remaining-red")).to_have_text(str(column_red_before - 1))
    editable.click(button="right")
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bempty\b"))
    page.locator(f'.cell-button[data-index="{edited_index}"]').click(button="right")
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bblue\b"))
    page.locator(f'.cell-button[data-index="{edited_index}"]').click(button="right")
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bcoral\b"))

    page.get_by_role("button", name="View Back face").click()
    expect(page.locator(".game-card")).to_have_class(re.compile(r"\bturning\b"))
    expect(page.locator(".game-card")).to_have_class(re.compile(r"\bequalized\b"))
    expect(page.locator(".orb.coral").first).to_have_css("background-color", "rgb(242, 85, 74)")
    expect(page.locator(".orb.blue").first).to_have_css("background-color", "rgb(40, 199, 206)")
    page.wait_for_function(
        "Array.from(document.querySelectorAll('.orb')).some(orb => "
        "orb.getAnimations().some(animation => animation.effect.getKeyframes().length > 20))"
    )
    sampled_frames = page.locator(".orb").first.evaluate(
        "orb => Math.max(...orb.getAnimations().map(animation => animation.effect.getKeyframes().length))"
    )
    assert sampled_frames == 25
    expect(page.locator("#face-name")).to_have_text("Back")
    expect(page.locator(".layer-chip")).to_have_text(["4", "3", "2", "1"])
    expect(page.locator(".layer-chip").last).to_have_class(re.compile(r"\bactive\b"))

    mirrored_cell = page.locator(".cell-button").nth(edited_y * 4 + (3 - edited_x))
    assert int(mirrored_cell.get_attribute("data-index")) == edited_index
    expect(mirrored_cell.locator(".orb.active")).to_have_class(re.compile(r"\bcoral\b"))
    expect(page.locator(".game-card")).not_to_have_class(re.compile(r"\bturning\b"))

    expected_orders = {
        "Left": ["1", "2", "3", "4"],
        "Right": ["4", "3", "2", "1"],
        "Up": ["1", "2", "3", "4"],
        "Down": ["4", "3", "2", "1"],
    }
    for face, order in expected_orders.items():
        page.get_by_role("button", name=f"View {face} face").click()
        expect(page.locator(".layer-chip")).to_have_text(order)
        expect(page.locator(".game-card")).not_to_have_class(re.compile(r"\bturning\b"))
