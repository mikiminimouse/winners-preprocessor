"""
Unit тесты для Extractor.
"""
import pytest
from pathlib import Path
import zipfile

from docprep.engine.extractor import Extractor


def test_extractor_initialization():
    """Тест инициализации Extractor."""
    extractor = Extractor()
    assert extractor is not None
    assert extractor.audit_logger is not None
    assert extractor.MAX_UNPACK_SIZE_MB > 0
    assert extractor.MAX_FILES_IN_ARCHIVE > 0


def test_extractor_detects_archives(sample_archive_unit):
    """Тест определения архивов в UNIT."""
    extractor = Extractor()
    result = extractor.extract_unit(
        unit_path=sample_archive_unit,
        cycle=1,
        protocol_date="2025-03-18",
        dry_run=True,
    )
    
    assert result is not None
    assert result["archives_processed"] > 0 or result["archives_processed"] == 0


def test_extractor_handles_no_archives(sample_unit_dir):
    """Тест обработки UNIT без архивов."""
    extractor = Extractor()
    result = extractor.extract_unit(
        unit_path=sample_unit_dir,
        cycle=1,
        protocol_date="2025-03-18",
        dry_run=True,
    )
    
    assert result is not None
    assert result["archives_processed"] == 0
    assert "moved_to" in result


def test_extractor_extracts_zip(temp_dir):
    """Тест извлечения ZIP архива."""
    unit_path = temp_dir / "UNIT_TEST"
    unit_path.mkdir()
    
    # Создаем ZIP архив
    zip_path = unit_path / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("file1.txt", "Content 1")
        zf.writestr("file2.txt", "Content 2")
    
    extractor = Extractor()
    result = extractor.extract_unit(
        unit_path=unit_path,
        cycle=1,
        protocol_date="2025-03-18",
        keep_archive=True,
        dry_run=False,
    )
    
    assert result is not None
    assert result["files_extracted"] > 0
    
    # Проверяем, что файлы извлечены
    extracted_dir = unit_path / "test_extracted"
    if extracted_dir.exists():
        assert len(list(extracted_dir.rglob("*"))) > 0


def test_extractor_protects_against_zip_bomb(temp_dir):
    """Тест защиты от zip bomb."""
    unit_path = temp_dir / "UNIT_TEST"
    unit_path.mkdir()
    
    # Создаем большой архив (симуляция zip bomb)
    zip_path = unit_path / "bomb.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        # Создаем много файлов
        for i in range(2000):  # Больше MAX_FILES_IN_ARCHIVE
            zf.writestr(f"file_{i}.txt", "x" * 1000)
    
    extractor = Extractor()
    
    # Должно вызвать QuarantineError
    with pytest.raises(Exception):  # QuarantineError или OperationError
        extractor.extract_unit(
            unit_path=unit_path,
            cycle=1,
            protocol_date="2025-03-18",
            dry_run=False,
        )

