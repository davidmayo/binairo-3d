import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_homepage_loads_game() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "3D Binairo" in response.text
    assert "<h1>3D Binairo</h1>" in response.text
    assert "beautifully done" not in client.get("/static/app.js").text
    assert 'id="board"' in response.text
    assert 'id="settings-panel"' in response.text
    assert 'id="red-cell-color"' in response.text
    assert 'id="blue-cell-color"' in response.text
    assert 'id="empty-cell-color"' in response.text
    assert 'id="show-remaining-counts"' in response.text
    assert 'id="show-stack-counts"' in response.text
    assert 'id="complete-color"' in response.text
    assert 'id="allow-background-clicks"' in response.text
    assert 'id="size-select"' in response.text
    assert "4×4×4" in response.text
    assert "6×6×6" in response.text
    assert "8×8×8" in response.text
    assert "10×10×10" in response.text
    assert 'id="axis-x"' not in response.text
    assert 'id="axis-y"' not in response.text
    assert "Think outside" not in response.text
    assert "<style>" in response.text
    assert ".orb.layer-0" in response.text
    assert ".orb.layer-3" in response.text
    assert response.headers["cache-control"] == "no-store"


def test_static_assets_are_served() -> None:
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert "generateSolution" in script.text

    html = client.get("/static/index.html")
    assert html.status_code == 200
    assert html.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("path", ["/missing", "/static/missing.js", "/static/../main.py"])
def test_unknown_and_out_of_scope_paths_return_404(path: str) -> None:
    assert client.get(path).status_code == 404


def test_ui_route_is_not_published_as_an_api() -> None:
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert schema.json()["paths"] == {}
