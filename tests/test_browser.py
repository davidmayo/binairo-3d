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
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    expect(page.locator(".cell-button")).to_have_count(16)
    expect(page.locator("#toast")).to_be_hidden()

    initial_board = page.locator(".orb").evaluate_all("orbs => orbs.map(orb => orb.className)")
    page.locator("#new-button").click()
    page.wait_for_function("!document.querySelector('#new-button').disabled")
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    expect(page.locator("#toast")).to_be_visible()
    expect(page.locator("#toast")).to_be_hidden(timeout=4000)
    repeated_board = page.locator(".orb").evaluate_all("orbs => orbs.map(orb => orb.className)")
    assert repeated_board == initial_board

    page.locator("#settings-button").click()
    expect(page.locator("#settings-panel")).to_be_visible()
    expect(page.locator("#settings-button")).to_have_attribute("aria-expanded", "true")
    expect(page.locator("#show-remaining-counts")).to_be_checked()
    page.locator("#show-remaining-counts").uncheck()
    expect(page.locator(".remaining-counts").first).to_be_hidden()
    page.locator("#show-remaining-counts").check()
    expect(page.locator(".remaining-counts").first).to_be_visible()
    expect(page.locator("#allow-background-clicks")).to_be_checked()
    panel_box = page.locator("#settings-panel").bounding_box()
    assert panel_box and panel_box["x"] == pytest.approx(0, abs=.5)
    colored_cell = page.locator(".orb.active.coral, .orb.active.blue").first
    colored_diameter_before = colored_cell.evaluate("orb => getComputedStyle(orb, '::after').width")
    background_empty = page.locator(".orb.empty:not(.active)").first
    expect(background_empty).to_have_css("background-color", "rgb(192, 192, 192)")
    expect(background_empty).to_have_css("opacity", "0.2")
    highlighted_empty = page.locator(".orb.active.empty").first
    expect(highlighted_empty).to_have_css("--empty-cell", "#c0c0c0")
    assert highlighted_empty.evaluate("orb => getComputedStyle(orb, '::after').backgroundColor") == "rgb(192, 192, 192)"
    assert highlighted_empty.evaluate("orb => getComputedStyle(orb, '::after').opacity") == "0.2"
    page.locator("#highlight-opacity").fill("30")
    page.locator("#highlight-radius").fill("25")
    page.locator("#highlight-border").fill("2")
    configured_orb = page.locator(".orb.active").first
    expect(configured_orb).to_have_css("background-color", "rgba(36, 39, 38, 0.3)")
    visual_scale = page.evaluate("boardVisualScale()")
    configured_border = configured_orb.evaluate("orb => parseFloat(getComputedStyle(orb).borderTopWidth)")
    assert configured_border == max(1, math.floor(2 * visual_scale))
    configured_orb_box = configured_orb.bounding_box()
    configured_cell_box = page.locator(".cell-button").first.bounding_box()
    assert configured_orb_box and configured_cell_box
    assert configured_orb_box["width"] / configured_cell_box["width"] == pytest.approx(.5, abs=.005)
    colored_diameter_after = colored_cell.evaluate("orb => getComputedStyle(orb, '::after').width")
    assert colored_diameter_after == colored_diameter_before
    page.locator("#background-opacity").fill("45")
    expect(background_empty).to_have_css("opacity", "0.45")
    assert highlighted_empty.evaluate("orb => getComputedStyle(orb, '::after').opacity") == "0.45"
    page.locator("#stack-angle").fill("45")
    page.locator("#stack-spacing").fill("30")
    stack_near_box = page.locator(".cell-button").first.locator(".orb.layer-0").bounding_box()
    stack_next_box = page.locator(".cell-button").first.locator(".orb.layer-1").bounding_box()
    assert stack_near_box and stack_next_box
    stack_dx = stack_next_box["x"] + stack_next_box["width"] / 2 - stack_near_box["x"] - stack_near_box["width"] / 2
    stack_dy = stack_next_box["y"] + stack_next_box["height"] / 2 - stack_near_box["y"] - stack_near_box["height"] / 2
    assert math.degrees(math.atan2(abs(stack_dy), abs(stack_dx))) == pytest.approx(45, abs=.5)
    assert math.hypot(stack_dx, stack_dy) == pytest.approx(30 * visual_scale, abs=.75)
    page.locator("#red-cell-color").fill("#aa1122")
    page.locator("#blue-cell-color").fill("#1166cc")
    page.locator("#empty-cell-color").fill("#556677")
    page.locator("#complete-color").fill("#44ee66")
    expect(page.locator(".orb.coral:not(.active)").first).to_have_css("background-color", "rgb(170, 17, 34)")
    expect(page.locator(".orb.blue:not(.active)").first).to_have_css("background-color", "rgb(17, 102, 204)")
    expect(page.locator(".orb.empty:not(.active)").first).to_have_css("background-color", "rgb(85, 102, 119)")
    assert highlighted_empty.evaluate("orb => getComputedStyle(orb, '::after').backgroundColor") == "rgb(85, 102, 119)"
    expect(page.locator("#red-cell-color-output")).to_have_text("#AA1122")
    expect(page.locator("#complete-color-output")).to_have_text("#44EE66")
    expect(page.locator(".remaining-check").first).to_have_css("color", "rgb(68, 238, 102)")
    page.locator("#highlight-opacity").fill("0")
    page.locator("#highlight-radius").fill("20.3")
    page.locator("#highlight-border").fill("5")
    page.locator("#background-opacity").fill("20")
    page.locator("#stack-angle").fill("65")
    page.locator("#stack-spacing").fill("24")
    page.locator("#red-cell-color").fill("#f2554a")
    page.locator("#blue-cell-color").fill("#28c7ce")
    page.locator("#empty-cell-color").fill("#c0c0c0")
    page.locator("#complete-color").fill("#65d97b")
    expect(page.locator("#cube-moves")).to_be_checked()
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    stationary_before = page.locator(".cell-button").first.locator(".orb.active").bounding_box()
    stationary_cell_before = page.locator(".cell-button").first.bounding_box()
    page.locator(".layer-chip").nth(1).click()
    stationary_after = page.locator(".cell-button").first.locator(".orb.active").bounding_box()
    stationary_cell_after = page.locator(".cell-button").first.bounding_box()
    assert stationary_before and stationary_after and stationary_cell_before and stationary_cell_after
    before_relative_x = stationary_before["x"] + stationary_before["width"] / 2 - stationary_cell_before["x"]
    before_relative_y = stationary_before["y"] + stationary_before["height"] / 2 - stationary_cell_before["y"]
    after_relative_x = stationary_after["x"] + stationary_after["width"] / 2 - stationary_cell_after["x"]
    after_relative_y = stationary_after["y"] + stationary_after["height"] / 2 - stationary_cell_after["y"]
    assert after_relative_x == pytest.approx(
        before_relative_x, abs=.5
    )
    assert after_relative_y == pytest.approx(
        before_relative_y, abs=.5
    )
    assert not page.locator(".orb").evaluate_all("orbs => orbs.some(orb => orb.getAnimations().length > 0)")
    page.locator("#cube-moves").uncheck()
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    page.locator("#settings-close").click()
    expect(page.locator("#settings-panel")).to_be_hidden()
    page.locator(".layer-chip").first.click()

    background_orb = page.locator(".orb:not(.active):not(.fixed)").first
    background_index = background_orb.get_attribute("data-index")
    background_classes = background_orb.get_attribute("class") or ""
    background_next = "coral" if "empty" in background_classes else "blue" if "coral" in background_classes else "empty"
    background_orb.click()
    expect(page.locator(f'.orb[data-index="{background_index}"]')).to_have_class(re.compile(rf"\b{background_next}\b"))

    page.locator("#settings-button").click()
    page.locator("#allow-background-clicks").uncheck()
    page.locator("#settings-close").click()
    disabled_background = page.locator(".orb:not(.active):not(.fixed)").first
    disabled_index = disabled_background.get_attribute("data-index")
    disabled_classes = disabled_background.get_attribute("class")
    disabled_background.click(force=True)
    expect(page.locator(f'.orb[data-index="{disabled_index}"]')).to_have_class(disabled_classes)
    context_menu_prevented = page.locator(".play-area").evaluate(
        "area => { const event = new MouseEvent('contextmenu', { bubbles: true, cancelable: true }); "
        "area.dispatchEvent(event); return event.defaultPrevented; }"
    )
    assert context_menu_prevented
    page.locator("#settings-button").click()
    page.locator("#allow-background-clicks").check()
    page.locator("#settings-close").click()

    expect(page.locator(".face-button")).to_have_count(6)
    expect(page.locator(".layer-chip")).to_have_text(["XY 1", "XY 2", "XY 3", "XY 4"])
    first_progress = page.locator(".layer-chip").first.evaluate(
        "chip => ({ progress: chip.style.getPropertyValue('--slice-progress'), border: getComputedStyle(chip).borderTopWidth, "
        "width: getComputedStyle(chip).width, radius: getComputedStyle(chip).borderRadius })"
    )
    assert first_progress["progress"].endswith("%")
    assert first_progress["border"] == "3px"
    assert first_progress["width"] == "72px"
    assert first_progress["radius"] == "999px"
    assert page.locator(".layer-chip").nth(1).evaluate("chip => getComputedStyle(chip).borderTopWidth") == "1px"
    expect(page.locator(".row-sum")).to_have_count(4)
    expect(page.locator(".column-sum")).to_have_count(4)
    expect(page.locator(".stack-sum")).to_have_count(16)
    expect(page.locator(".remaining-check")).not_to_have_count(0)
    assert page.locator(".remaining-check").first.evaluate(
        "mark => parseFloat(getComputedStyle(mark).fontSize)"
    ) == pytest.approx(22 * visual_scale, abs=.1)
    expect(page.locator(".remaining-check").first).to_have_css("font-weight", "900")
    assert page.locator(".row-sum").first.evaluate(
        "mark => parseFloat(getComputedStyle(mark).fontSize)"
    ) == pytest.approx(16 * visual_scale, abs=.1)
    expect(page.locator(".row-sum").first).to_have_css("font-weight", "600")
    assert page.locator(".stack-sum").first.evaluate(
        "mark => parseFloat(getComputedStyle(mark).fontSize)"
    ) == pytest.approx(15 * visual_scale, abs=.1)

    first_active_box = page.locator(".cell-button").first.locator(".orb.active").bounding_box()
    first_far_box = page.locator(".cell-button").first.locator(".orb.layer-3").bounding_box()
    first_stack_sum_box = page.locator(".stack-sum").first.bounding_box()
    assert first_active_box and first_far_box and first_stack_sum_box
    assert first_stack_sum_box["x"] + first_stack_sum_box["width"] < first_active_box["x"]
    active_center = (
        first_active_box["x"] + first_active_box["width"] / 2,
        first_active_box["y"] + first_active_box["height"] / 2,
    )
    stack_vector = (
        first_far_box["x"] + first_far_box["width"] / 2 - active_center[0],
        first_far_box["y"] + first_far_box["height"] / 2 - active_center[1],
    )
    label_vector = (
        first_stack_sum_box["x"] + first_stack_sum_box["width"] / 2 - active_center[0],
        first_stack_sum_box["y"] + first_stack_sum_box["height"] / 2 - active_center[1],
    )
    cosine = (stack_vector[0] * label_vector[0] + stack_vector[1] * label_vector[1]) / (
        math.hypot(*stack_vector) * math.hypot(*label_vector)
    )
    assert cosine == pytest.approx(0, abs=0.03)

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
    layer_1 = first_cell.locator(".orb.layer-0")
    layer_4 = first_cell.locator(".orb.layer-3")
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
        "background": "rgba(36, 39, 38, 0)",
        "borderColor": "rgb(36, 39, 38)",
        "borderWidth": "5px",
    }

    editable = page.locator(".cell-button:not(.fixed)").first
    editable_position = editable.evaluate("button => Array.from(document.querySelectorAll('.cell-button')).indexOf(button)")
    editable_row = editable_position // 4
    editable_column = editable_position % 4
    row_red_before = int(page.locator(".row-sum").nth(editable_row).locator(".remaining-red").text_content())
    column_red_before = int(page.locator(".column-sum").nth(editable_column).locator(".remaining-red").text_content())
    stack_red_before = int(editable.locator(".stack-sum .remaining-red").text_content())
    edited_index = int(editable.get_attribute("data-index"))
    edited_x = edited_index % 4
    edited_y = (edited_index % 16) // 4
    editable.locator(".orb.active").click()
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bcoral\b"))
    expect(page.locator(".row-sum").nth(editable_row).locator(".remaining-red")).to_have_text(str(row_red_before - 1))
    expect(page.locator(".column-sum").nth(editable_column).locator(".remaining-red")).to_have_text(str(column_red_before - 1))
    expect(page.locator(f'.cell-button[data-index="{edited_index}"] .stack-sum .remaining-red')).to_have_text(
        str(max(0, stack_red_before - 1))
    )
    editable.locator(".orb.active").click(button="right")
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bempty\b"))
    page.locator(f'.cell-button[data-index="{edited_index}"] .orb.active').click(button="right")
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bblue\b"))
    page.locator(f'.cell-button[data-index="{edited_index}"] .orb.active').click(button="right")
    expect(page.locator(f'.orb.active[data-index="{edited_index}"]')).to_have_class(re.compile(r"\bcoral\b"))

    page.get_by_role("button", name="View +Z Face").click()
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
    expect(page.locator("#face-name")).to_have_text("+Z Face")
    expect(page.locator("#slice-plane")).to_have_text("XY")
    expect(page.locator(".layer-chip")).to_have_text(["XY 4", "XY 3", "XY 2", "XY 1"])
    expect(page.locator(".layer-chip").last).to_have_class(re.compile(r"\bactive\b"))

    mirrored_cell = page.locator(".cell-button").nth(edited_y * 4 + (3 - edited_x))
    assert int(mirrored_cell.get_attribute("data-index")) == edited_index
    expect(mirrored_cell.locator(".orb.active")).to_have_class(re.compile(r"\bcoral\b"))
    expect(page.locator(".game-card")).not_to_have_class(re.compile(r"\bturning\b"))

    expected_orders = {
        "−X Face": ["YZ 1", "YZ 2", "YZ 3", "YZ 4"],
        "+X Face": ["YZ 4", "YZ 3", "YZ 2", "YZ 1"],
        "−Y Face": ["XZ 1", "XZ 2", "XZ 3", "XZ 4"],
        "+Y Face": ["XZ 4", "XZ 3", "XZ 2", "XZ 1"],
    }
    for face, order in expected_orders.items():
        page.get_by_role("button", name=f"View {face}").click()
        expect(page.locator(".layer-chip")).to_have_text(order)
        expect(page.locator(".game-card")).not_to_have_class(re.compile(r"\bturning\b"))

    page.evaluate("values = [...solution]; render()")
    expect(page.locator("#status-text")).to_have_text("Cube complete")
    page.wait_for_function("celebrationActive && isTurning")
    page.wait_for_function(
        "Array.from(document.querySelectorAll('.orb')).some(orb => "
        "orb.getAnimations().some(animation => animation.effect.getKeyframes().length > 20))"
    )
    win_duration = page.locator(".orb").evaluate_all(
        "orbs => Math.max(...orbs.flatMap(orb => orb.getAnimations().map(animation => animation.effect.getTiming().duration)))"
    )
    assert win_duration >= 1290
    page.evaluate("stopWinAnimation()")


def test_size_selector_builds_six_cube(page: Page, live_server: str) -> None:
    page.goto(live_server)
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    expect(page.locator("#size-select")).to_have_value("4")
    four_board_box = page.locator(".board").bounding_box()
    four_cell_box = page.locator(".cell-button").first.bounding_box()
    page.locator("#size-select").select_option("6")
    page.wait_for_function("!document.querySelector('#new-button').disabled")
    page.wait_for_function("!document.querySelector('main').dataset.fitting")

    expect(page.locator(".cell-button")).to_have_count(36)
    expect(page.locator(".orb")).to_have_count(216)
    expect(page.locator(".layer-chip")).to_have_text(
        ["XY 1", "XY 2", "XY 3", "XY 4", "XY 5", "XY 6"]
    )
    expect(page.locator("#layer-count")).to_have_text("6")
    expect(page.locator("#progress-text")).to_contain_text("/ 216")
    expect(page.locator("#half-count")).to_have_text("three")
    assert page.evaluate("allPlanesValid(solution, true)") is True
    six_board_box = page.locator(".board").bounding_box()
    six_cell_box = page.locator(".cell-button").first.bounding_box()
    assert four_board_box and four_cell_box and six_board_box and six_cell_box
    expected_cell_ratio = .6 * six_board_box["width"] / four_board_box["width"]
    assert six_cell_box["width"] / four_cell_box["width"] == pytest.approx(expected_cell_ratio, abs=.01)
    viewport_fit = page.evaluate("""() => {
      const region = document.querySelector('#game-board-region').getBoundingClientRect();
      const sidebar = document.querySelector('main').dataset.layout === 'sidebar';
      return {
        horizontalGap: Math.abs(region.width - (innerWidth - 32 - (sidebar ? 356 : 0))),
        verticalGap: Math.abs(region.height - (innerHeight - 16)),
      };
    }""")
    assert min(viewport_fit["horizontalGap"], viewport_fit["verticalGap"]) <= 2
    page.evaluate("""() => {
      const rules = document.querySelector('details');
      rules.open = true;
      rules.style.minHeight = '1200px';
    }""")
    board_top_before_scroll = page.locator("#game-board-region").bounding_box()["y"]
    sidebar_top_before_scroll = page.locator(".top").bounding_box()["y"]
    page.evaluate("scrollTo(0, 300)")
    page.wait_for_timeout(100)
    board_top_after_scroll = page.locator("#game-board-region").bounding_box()["y"]
    sidebar_top_after_scroll = page.locator(".top").bounding_box()["y"]
    assert board_top_after_scroll == pytest.approx(board_top_before_scroll, abs=.5)
    assert sidebar_top_after_scroll < sidebar_top_before_scroll - 250
    page.evaluate("""() => {
      scrollTo(0, 0);
      const rules = document.querySelector('details');
      rules.open = false;
      rules.style.minHeight = '';
    }""")
    bounds = page.evaluate("""() => {
      const region = document.querySelector('#game-board-region').getBoundingClientRect();
      const bottomOrbs = Array.from(document.querySelectorAll('.cell-button'))
        .slice(30)
        .flatMap(cell => Array.from(cell.querySelectorAll('.orb')))
        .map(orb => orb.getBoundingClientRect());
      const columnCounts = Array.from(document.querySelectorAll('.column-sum'))
        .map(count => count.getBoundingClientRect());
      const visibleGameMarks = Array.from(document.querySelectorAll('.orb, .row-sum, .column-sum, .stack-sum'))
        .filter(mark => !mark.hidden)
        .map(mark => mark.getBoundingClientRect());
      return {
        regionRight: region.right,
        marksRight: Math.max(...visibleGameMarks.map(mark => mark.right)),
        bottomOrbsBottom: Math.max(...bottomOrbs.map(orb => orb.bottom)),
        columnCountsTop: Math.min(...columnCounts.map(count => count.top)),
      };
    }""")
    assert bounds["marksRight"] <= bounds["regionRight"] - 8
    assert bounds["columnCountsTop"] >= bounds["bottomOrbsBottom"] + 12

    page.evaluate("cubeMovesInput.checked = true; updateVisualSettings()")
    expect(page.locator(".game-card")).to_have_class(re.compile(r"\bcube-moves\b"))
    page.wait_for_timeout(250)
    top_clearance = page.evaluate("""() => {
      const playArea = document.querySelector('.play-area').getBoundingClientRect();
      const board = document.querySelector('.board').getBoundingClientRect();
      const orbs = Array.from(document.querySelectorAll('.orb')).map(orb => orb.getBoundingClientRect());
      const highlights = Array.from(document.querySelectorAll('.orb.active')).map(orb => {
        const bounds = orb.getBoundingClientRect();
        return [bounds.x + bounds.width / 2 - board.x, bounds.y + bounds.height / 2 - board.y];
      });
      return { playTop: playArea.top, orbTop: Math.min(...orbs.map(orb => orb.top)), highlights };
    }""")
    assert top_clearance["orbTop"] >= top_clearance["playTop"]

    page.locator(".layer-chip").last.click()
    page.wait_for_timeout(250)
    bottom_clearance = page.evaluate("""() => {
      const playArea = document.querySelector('.play-area').getBoundingClientRect();
      const board = document.querySelector('.board').getBoundingClientRect();
      const orbs = Array.from(document.querySelectorAll('.orb')).map(orb => orb.getBoundingClientRect());
      const highlights = Array.from(document.querySelectorAll('.orb.active')).map(orb => {
        const bounds = orb.getBoundingClientRect();
        return [bounds.x + bounds.width / 2 - board.x, bounds.y + bounds.height / 2 - board.y];
      });
      return { playBottom: playArea.bottom, orbBottom: Math.max(...orbs.map(orb => orb.bottom)), highlights };
    }""")
    assert bottom_clearance["orbBottom"] <= bottom_clearance["playBottom"]
    for before, after in zip(top_clearance["highlights"], bottom_clearance["highlights"], strict=True):
        assert after == pytest.approx(before, abs=.5)

    original_region_width = page.locator("#game-board-region").bounding_box()["width"]
    page.set_viewport_size({"width": 2560, "height": 1440})
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    doubled_region_width = page.locator("#game-board-region").bounding_box()["width"]
    assert doubled_region_width >= original_region_width * 1.9
    doubled_fit = page.evaluate("""() => {
      const region = document.querySelector('#game-board-region').getBoundingClientRect();
      const sidebar = document.querySelector('main').dataset.layout === 'sidebar';
      return {
        horizontalGap: Math.abs(region.width - (innerWidth - 32 - (sidebar ? 356 : 0))),
        verticalGap: Math.abs(region.height - (innerHeight - 16)),
      };
    }""")
    assert min(doubled_fit["horizontalGap"], doubled_fit["verticalGap"]) <= 2

    page.set_viewport_size({"width": 1280, "height": 720})
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    for size, half_word in [(8, "four"), (10, "five")]:
        page.locator("#size-select").select_option(str(size))
        page.wait_for_function("!document.querySelector('#new-button').disabled")
        page.wait_for_function("!document.querySelector('main').dataset.fitting")
        expect(page.locator(".cell-button")).to_have_count(size**2)
        expect(page.locator(".orb")).to_have_count(size**3)
        expect(page.locator(".layer-chip")).to_have_count(size)
        expect(page.locator("#layer-count")).to_have_text(str(size))
        expect(page.locator("#half-count")).to_have_text(half_word)
        assert page.evaluate("allPlanesValid(solution, true)") is True
        assert page.locator(".orb").evaluate_all(
            "orbs => orbs.every(orb => { const bounds = orb.getBoundingClientRect(); "
            "const region = document.querySelector('#game-board-region').getBoundingClientRect(); "
            "return bounds.left >= region.left && bounds.right <= region.right; })"
        )

    page.locator("#size-select").select_option("4")
    page.wait_for_function("!document.querySelector('#new-button').disabled")
    page.wait_for_function("!document.querySelector('main').dataset.fitting")
    expect(page.locator(".cell-button")).to_have_count(16)
    expect(page.locator(".layer-chip")).to_have_count(4)
