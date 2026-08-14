import re

import pytest
from playwright.sync_api import Page, expect


def open_game(page: Page, live_server: str) -> None:
    page.emulate_media(reduced_motion="reduce")
    page.goto(live_server)
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    page.wait_for_function("!document.querySelector('#new-button').disabled")


def test_initial_board_contract_and_accessible_state(page: Page, live_server: str) -> None:
    open_game(page, live_server)

    expect(page.get_by_role("heading", name="3D Binairo", exact=True)).to_be_visible()
    expect(page.locator("#board")).to_have_attribute("role", "grid")
    expect(page.get_by_role("gridcell")).to_have_count(16)
    expect(page.locator(".cell-button")).to_have_count(16)
    expect(page.locator(".orb")).to_have_count(64)
    expect(page.locator(".orb.active")).to_have_count(16)
    assert page.locator(".cell-button").evaluate_all(
        "cells => cells.every(cell => cell.querySelectorAll('.orb').length === 4)"
    )

    face_buttons = page.locator(".face-button")
    expect(face_buttons).to_have_count(6)
    expect(face_buttons).to_have_text(["−Z Face", "+Z Face", "−X Face", "+X Face", "−Y Face", "+Y Face"])
    assert face_buttons.evaluate_all(
        "buttons => buttons.map(button => button.getAttribute('aria-pressed'))"
    ) == ["true", "false", "false", "false", "false", "false"]

    expect(page.locator(".layer-chip")).to_have_text(["XY 1", "XY 2", "XY 3", "XY 4"])
    expect(page.locator(".layer-chip.active")).to_have_count(1)
    expect(page.locator(".layer-chip.active")).to_have_text("XY 1")
    expect(page.locator(".cell-button.fixed").first).to_have_attribute("aria-disabled", "true")
    expect(page.locator(".cell-button:not(.fixed)").first).to_have_attribute("aria-disabled", "false")
    expect(page.locator(".cell-button").first).to_have_attribute(
        "aria-label", re.compile(r"row 1, column 1: (empty|coral|blue); stack needs \d+ red and \d+ blue")
    )

    filled, total = page.evaluate("[values.filter(value => value !== null).length, CELLS]")
    expect(page.locator("#progress-text")).to_have_text(f"{filled} / {total}")
    assert float(page.locator("#progress-bar").evaluate("bar => parseFloat(bar.style.width)")) == pytest.approx(
        filled / total * 100
    )
    expect(page.locator("#undo-button")).to_be_disabled()


def test_settings_defaults_and_count_controls_are_independent(page: Page, live_server: str) -> None:
    open_game(page, live_server)
    page.locator("#settings-button").click()

    defaults = {
        "#highlight-opacity": "0",
        "#highlight-radius": "20.3",
        "#highlight-border": "5",
        "#background-opacity": "20",
        "#stack-angle": "65",
        "#stack-spacing": "24",
        "#red-cell-color": "#f2554a",
        "#blue-cell-color": "#28c7ce",
        "#empty-cell-color": "#c0c0c0",
        "#complete-color": "#65d97b",
    }
    for selector, value in defaults.items():
        expect(page.locator(selector)).to_have_value(value)

    expect(page.locator("#cube-moves")).to_be_checked()
    expect(page.locator("#show-remaining-counts")).to_be_checked()
    expect(page.locator("#show-stack-counts")).not_to_be_checked()
    expect(page.locator("#allow-background-clicks")).to_be_checked()
    expect(page.locator(".row-sum").first).to_be_visible()
    expect(page.locator(".column-sum").first).to_be_visible()
    expect(page.locator(".stack-sum").first).to_be_hidden()

    page.locator("#show-remaining-counts").uncheck()
    expect(page.locator(".row-sum").first).to_be_hidden()
    expect(page.locator(".column-sum").first).to_be_hidden()
    expect(page.locator(".stack-sum").first).to_be_hidden()

    page.locator("#show-stack-counts").check()
    expect(page.locator(".row-sum").first).to_be_hidden()
    expect(page.locator(".column-sum").first).to_be_hidden()
    expect(page.locator(".stack-sum").first).to_be_visible()

    page.keyboard.press("Escape")
    expect(page.locator("#settings-panel")).to_be_hidden()
    expect(page.locator("#settings-button")).to_have_attribute("aria-expanded", "false")
    expect(page.locator("#settings-button")).to_be_focused()


def test_left_and_right_click_cycles_and_undo(page: Page, live_server: str) -> None:
    open_game(page, live_server)
    editable = page.locator(".cell-button:not(.fixed) .orb.active").first
    expect(editable).to_have_class(re.compile(r"\bempty\b"))
    starting_filled = page.evaluate("values.filter(value => value !== null).length")

    editable.click()
    expect(editable).to_have_class(re.compile(r"\bcoral\b"))
    expect(page.locator("#progress-text")).to_have_text(f"{starting_filled + 1} / 64")
    editable.click()
    expect(editable).to_have_class(re.compile(r"\bblue\b"))
    editable.click()
    expect(editable).to_have_class(re.compile(r"\bempty\b"))

    editable.click(button="right")
    expect(editable).to_have_class(re.compile(r"\bblue\b"))
    editable.click(button="right")
    expect(editable).to_have_class(re.compile(r"\bcoral\b"))
    editable.click(button="right")
    expect(editable).to_have_class(re.compile(r"\bempty\b"))

    page.evaluate("history = []; render()")
    editable = page.locator(".cell-button:not(.fixed) .orb.active").first
    editable.click()
    expect(page.locator("#undo-button")).to_be_enabled()
    page.locator("#undo-button").click()
    expect(editable).to_have_class(re.compile(r"\bempty\b"))
    expect(page.locator("#undo-button")).to_be_disabled()

    editable.click(button="right")
    expect(editable).to_have_class(re.compile(r"\bblue\b"))
    page.keyboard.press("Control+z")
    expect(editable).to_have_class(re.compile(r"\bempty\b"))
    expect(page.locator("#undo-button")).to_be_disabled()

    fixed = page.locator(".cell-button.fixed .orb.active").first
    fixed_classes = fixed.get_attribute("class")
    fixed.click(force=True)
    fixed.click(button="right", force=True)
    expect(fixed).to_have_class(fixed_classes)
    expect(page.locator("#undo-button")).to_be_disabled()


def test_layer_keyboard_navigation_and_opposite_face_order(page: Page, live_server: str) -> None:
    open_game(page, live_server)

    page.locator("#prev-layer").click()
    expect(page.locator("#layer-number")).to_have_text("4")
    expect(page.locator(".layer-chip.active")).to_have_text("XY 4")
    page.locator("#next-layer").click()
    expect(page.locator("#layer-number")).to_have_text("1")
    page.keyboard.press("ArrowRight")
    expect(page.locator("#layer-number")).to_have_text("2")
    page.keyboard.press("ArrowLeft")
    expect(page.locator("#layer-number")).to_have_text("1")

    page.get_by_role("button", name="View +Z Face").click()
    expect(page.locator("#face-name")).to_have_text("+Z Face")
    expect(page.locator(".layer-chip")).to_have_text(["XY 4", "XY 3", "XY 2", "XY 1"])
    expect(page.locator(".layer-chip.active")).to_have_text("XY 1")
    assert page.locator(".face-button").evaluate_all(
        "buttons => buttons.map(button => button.getAttribute('aria-pressed'))"
    ) == ["false", "true", "false", "false", "false", "false"]

    page.get_by_role("button", name="View −X Face").click()
    expect(page.locator("#slice-plane")).to_have_text("YZ")
    expect(page.locator(".layer-chip")).to_have_text(["YZ 1", "YZ 2", "YZ 3", "YZ 4"])
    page.get_by_role("button", name="View +X Face").click()
    expect(page.locator(".layer-chip")).to_have_text(["YZ 4", "YZ 3", "YZ 2", "YZ 1"])
    page.get_by_role("button", name="View −Y Face").click()
    expect(page.locator(".layer-chip")).to_have_text(["XZ 1", "XZ 2", "XZ 3", "XZ 4"])
    page.get_by_role("button", name="View +Y Face").click()
    expect(page.locator(".layer-chip")).to_have_text(["XZ 4", "XZ 3", "XZ 2", "XZ 1"])
    expect(page.locator(".game-card")).not_to_have_attribute("aria-busy", "true")


def test_conflicts_and_completion_state(page: Page, live_server: str) -> None:
    open_game(page, live_server)
    page.evaluate(
        "puzzle = Array(CELLS).fill(null); values = Array(CELLS).fill(null); "
        "values[0] = false; values[1] = false; values[2] = false; history = []; render()"
    )

    expect(page.locator(".cell-button.invalid")).to_have_count(3)
    expect(page.locator("#status-text")).to_have_text("3 conflicting circles")
    expect(page.locator(".row-sum").first.locator(".remaining-red")).to_have_text("0")
    expect(page.locator(".row-sum").first.locator(".remaining-blue")).to_have_text("2")

    page.evaluate("values[2] = true; render()")
    expect(page.locator(".cell-button.invalid")).to_have_count(0)
    expect(page.locator("#status-text")).to_have_text("Cube in progress")

    page.evaluate("values = [...solution]; render()")
    expect(page.locator("#status-text")).to_have_text("Cube complete")
    expect(page.locator("#progress-text")).to_have_text("64 / 64")
    expect(page.locator(".layer-chip.complete")).to_have_count(4)
    expect(page.locator(".row-sum .remaining-check")).to_have_count(4)
    expect(page.locator(".column-sum .remaining-check")).to_have_count(4)
    expect(page.locator("#toast")).to_contain_text("Cube solved! Every slice is valid.")


@pytest.mark.parametrize("size", [4, 6, 8, 10])
def test_every_supported_size_builds_a_valid_playable_cube(page: Page, live_server: str, size: int) -> None:
    open_game(page, live_server)
    if size != 4:
        page.locator("#size-select").select_option(str(size))
        page.wait_for_function("!document.querySelector('#new-button').disabled", timeout=15_000)
        page.wait_for_function("!document.querySelector('main').dataset.fitting", timeout=15_000)

    expect(page.locator(".cell-button")).to_have_count(size**2)
    expect(page.locator(".orb")).to_have_count(size**3)
    expect(page.locator(".orb.active")).to_have_count(size**2)
    expect(page.locator(".layer-chip")).to_have_count(size)
    expect(page.locator(".row-sum")).to_have_count(size)
    expect(page.locator(".column-sum")).to_have_count(size)
    expect(page.locator("#layer-count")).to_have_text(str(size))
    expect(page.locator("#progress-text")).to_contain_text(f"/ {size**3}")
    assert page.evaluate("document.documentElement.dataset.size") == str(size)
    assert page.evaluate("allPlanesValid(solution, true)") is True
    assert page.evaluate("puzzle.some(value => value === null)") is True
    assert page.evaluate(
        "puzzle.every((value, index) => value === null || value === solution[index])"
    ) is True
    assert page.evaluate("solution.filter(Boolean).length") == size**3 // 2
    assert page.locator(".cell-button:not(.fixed)").count() > 0

    progress = page.locator(".layer-chip").first.evaluate(
        "chip => parseFloat(chip.style.getPropertyValue('--slice-progress'))"
    )
    assert 0 < progress < 100
