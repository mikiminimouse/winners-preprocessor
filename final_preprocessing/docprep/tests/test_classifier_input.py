#!/usr/bin/env python3
"""
Тесты для Classifier с учетом Input директории и copy_mode.
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
def sample_unit_dir_in_input(temp_dir):
    """Создает пример UNIT директории в Input с одним PDF файлом."""
    # Создаем структуру с датой
    data_dir = temp_dir / "Data"
    input_with_date = data_dir / "2025-03-18" / "Input"
    input_with_date.mkdir(parents=True)
    
    # Создаем тестовый UNIT в Input директории
    unit_id = "UNIT_000123"
    unit_path = input_with_date / unit_id
    unit_path.mkdir()
    
    # Создаем один тестовый PDF файл
    (unit_path / "test.pdf").write_bytes(b"%PDF-1.4\nstream\nBT\n/F1 12 Tf\n(Test PDF content) Tj\nET\nendstream\n%%EOF")
    
    return unit_path


def test_classify_unit_in_input_creates_manifest(sample_unit_dir_in_input):
    """Тест создания manifest при классификации UNIT из Input директории."""
    # Удаляем существующий manifest если есть
    manifest_path = sample_unit_dir_in_input / "manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    
    classifier = Classifier()
    result = classifier.classify_unit(sample_unit_dir_in_input, cycle=1)
    
    # Проверяем, что manifest создан в исходной директории (при copy_mode)
    assert manifest_path.exists()
    
    # Проверяем, что UNIT скопирован (исходная директория существует)
    assert sample_unit_dir_in_input.exists()
    
    # Проверяем категорию
    assert result["category"] == "direct"


def test_classify_unit_in_input_updates_state(sample_unit_dir_in_input):
    """Тест обновления state machine при классификации UNIT из Input директории."""
    classifier = Classifier()
    result = classifier.classify_unit(sample_unit_dir_in_input, cycle=1)
    
    # Проверяем, что state обновлен в исходной директории (при copy_mode)
    manifest = load_manifest(sample_unit_dir_in_input)
    
    assert manifest is not None
    assert "state_machine" in manifest
    assert manifest["state_machine"]["current_state"] == UnitState.MERGED_DIRECT.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
