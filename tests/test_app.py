from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_homepage_loads_game() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "BINAIRO" in response.text
    assert 'id="board"' in response.text


def test_static_assets_are_served() -> None:
    assert client.get("/static/styles.css").status_code == 200
    script = client.get("/static/app.js")
    assert script.status_code == 200
    assert "generateSolution" in script.text
