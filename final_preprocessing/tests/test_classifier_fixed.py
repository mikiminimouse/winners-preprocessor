#!/usr/bin/env python3
"""
Исправленные тесты для Classifier с учетом copy_mode.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
import json
from datetime import datetime

from docprep.engine.classifier import Classifier
from docprep.core.state_machine import UnitState
from docprep.core.manifest import create_manifest_v2, load_manifest


@pytest.fixture
def temp_dir():
    """Создает временную директорию для тестов."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_unit_dir_single_pdf(temp_dir):
    """Создает пример UNIT директории с одним PDF файлом."""
    unit_id = "UNIT_000123"
    unit_path = temp_dir / unit_id
    unit_path.mkdir(parents=True)
    
    # Создаем один тестовый PDF файл
    (unit_path / "test.pdf").write_bytes(b"%PDF-1.4\nstream\nBT\n/F1 12 Tf\n(Test PDF content) Tj\nET\nendstream\n%%EOF")
    
    # Создаем manifest
    manifest = create_manifest_v2(
        unit_id=unit_id,
        protocol_id="000123",
        protocol_date=datetime.now().strftime("%Y-%m-%d"),
        files=[
            {
                "original_name": "test.pdf",
                "current_name": "test.pdf",
                "mime_type": "application/pdf",
                "detected_type": "pdf",
                "needs_ocr": False,
                "sha256": "test_hash_pdf",
                "size": 100,
                "transformations": [],
            },
        ],
        current_cycle=1,
        state_trace=[UnitState.RAW.value],
    )
    
    manifest_path = unit_path / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    return unit_path


def test_classify_unit_creates_manifest_single_pdf(sample_unit_dir_single_pdf):
    """Тест создания manifest при классификации с одним PDF файлом."""
    # Удаляем существующий manifest
    manifest_path = sample_unit_dir_single_pdf / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    
    classifier = Classifier()
    result = classifier.classify_unit(sample_unit_dir_single_pdf, cycle=1)
    
    # Проверяем, что manifest создан
    assert manifest_path.exists()
    
    # Проверяем, что UNIT перемещен
    assert "target_directory" in result
    # При copy_mode исходная директория должна существовать
    assert sample_unit_dir_single_pdf.exists()


def test_classify_unit_updates_state_single_pdf(sample_unit_dir_single_pdf):
    """Тест обновления state machine при классификации с одним PDF файлом."""
    classifier = Classifier()
    result = classifier.classify_unit(sample_unit_dir_single_pdf, cycle=1)
    
    # Проверяем, что state обновлен
    from docprep.core.manifest import load_manifest
    # При copy_mode манифест остается в исходной директории
    manifest = load_manifest(sample_unit_dir_single_pdf)
    
    assert manifest is not None
    assert "state_machine" in manifest
    assert manifest["state_machine"]["current_state"] == UnitState.MERGED_DIRECT.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
