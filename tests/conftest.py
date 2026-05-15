import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def load_fixture():
    def _load(name: str):
        with open(FIXTURES_DIR / name) as f:
            return json.load(f)
    return _load
