# Binairo³

A playable 4×4×4 Binairo puzzle. Each of the cube's twelve axis-aligned 2D slices must independently satisfy the classic Binairo rules.

## Run locally

```powershell
uv run uvicorn main:app --reload
```

Then visit <http://127.0.0.1:8000>.

## Tests

Install the Firefox browser binary once:

```powershell
uv run playwright install firefox
```

Then run the complete Python, JavaScript-logic, and Firefox browser suite:

```powershell
uv run pytest
```
