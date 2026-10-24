"""The root requirements.txt (used by Vercel) must pin exactly what the backend pins."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _pins(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text().splitlines() if line.strip() and not line.startswith("#")}


def test_vercel_requirements_match_backend() -> None:
    assert _pins(ROOT / "requirements.txt") == _pins(ROOT / "backend" / "requirements.txt")
