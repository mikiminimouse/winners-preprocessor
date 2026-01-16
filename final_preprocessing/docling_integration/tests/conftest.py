import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock

@pytest.fixture
def unit_path(tmp_path):
    """Creates a mock unit directory with proper contract structure."""
    d = tmp_path / "UNIT_test_123"
    d.mkdir()

    # Create a test file
    test_file = d / "test_document.pdf"
    test_file.write_bytes(b"%PDF-1.4 test content")

    # Create docprep.contract.json (required by bridge_docprep)
    contract = {
        "schema_version": "1.0",
        "unit_id": "UNIT_test_123",
        "routing": {
            "docling_route": "pdf_text"
        },
        "files": [
            {
                "name": "test_document.pdf",
                "current_state": "MERGED_DIRECT"
            }
        ],
        "cost_estimation": {
            "time_seconds": 10,
            "cost_usd": 0.001
        }
    }
    (d / "docprep.contract.json").write_text(json.dumps(contract, indent=2))

    # Create manifest.json with state_machine (required by DoclingAdapter.validate_readiness)
    manifest = {
        "schema_version": "2.0",
        "unit_id": "UNIT_test_123",
        "state_machine": {
            "current_state": "MERGED_DIRECT",
            "state_trace": ["RAW", "CLASSIFIED", "MERGED_DIRECT"]
        },
        "files": [
            {
                "original_name": "test_document.pdf",
                "current_name": "test_document.pdf",
                "current_state": "MERGED_DIRECT"
            }
        ]
    }
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return d

@pytest.fixture
def unit_data(unit_path):
    """Returns mock unit data with Path objects for files."""
    return {
        "unit_id": "UNIT_test_123",
        "route": "pdf_text",
        "files": [
            unit_path / "test_document.pdf"  # Path object expected by get_main_file
        ],
        "unit_path": unit_path,
        "contract": {
            "routing": {
                "docling_route": "pdf_text"
            },
            "source": {
                "original_filename": "test_document.pdf"
            }
        },
        "path": unit_path
    }

@pytest.fixture
def route():
    return "pdf_text"

@pytest.fixture
def contract():
    return {
        "routing": {
            "docling_route": "pdf_text"
        }
    }
