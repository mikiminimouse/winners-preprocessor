
import pytest
from pathlib import Path
from unittest.mock import MagicMock

@pytest.fixture
def unit_path(tmp_path):
    """Creates a mock unit directory."""
    d = tmp_path / "UNIT_test_123"
    d.mkdir()
    (d / "manifest.json").write_text('{"id": "UNIT_test_123", "files": [], "contract": {"routing": {"docling_route": "pdf_text"}}}')
    return d

@pytest.fixture
def unit_data(unit_path):
    """Returns mock unit data."""
    return {
        "unit_id": "UNIT_test_123",
        "route": "pdf_text",
        "files": [],
        "contract": {
            "routing": {
                "docling_route": "pdf_text"
            }
        },
        "path": unit_path
    }

@pytest.fixture
def route():
    return "pdf_text"

@pytest.fixture
def contract():
    return {}
