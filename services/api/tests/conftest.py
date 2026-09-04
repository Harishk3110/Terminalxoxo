from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///./knk_terminal_test_v3.db")


def pytest_configure(config):
    config.addinivalue_line("markers", "anyio: run async tests with anyio")


@pytest.fixture
def anyio_backend():
    return "asyncio"
