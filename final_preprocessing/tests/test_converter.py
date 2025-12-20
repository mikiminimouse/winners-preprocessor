"""
Unit тесты для Converter.
"""
import pytest
from pathlib import Path

from docprep.engine.converter import Converter


def test_converter_initialization():
    """Тест инициализации Converter."""
    converter = Converter()
    assert converter is not None
    assert converter.audit_logger is not None
    assert "doc" in converter.CONVERSION_MAP
    assert converter.CONVERSION_MAP["doc"] == "docx"


def test_converter_detects_convertible_files(sample_unit_dir):
    """Тест определения файлов для конвертации."""
    converter = Converter()
    
    # Создаем .doc файл для теста
    doc_file = sample_unit_dir / "test.doc"
    doc_file.write_bytes(b"\xd0\xcf\x11\xe0 fake doc content")
    
    # Проверяем, что файл определяется как конвертируемый
    from docprep.utils.file_ops import detect_file_type
    detection = detect_file_type(doc_file)
    
    assert detection["detected_type"] == "doc" or detection["requires_conversion"]


def test_converter_handles_no_convertible_files(sample_unit_dir):
    """Тест обработки UNIT без конвертируемых файлов."""
    converter = Converter()
    result = converter.convert_unit(
        unit_path=sample_unit_dir,
        cycle=1,
        protocol_date="2025-03-18",
        dry_run=True,
    )
    
    assert result is not None
    assert result["files_converted"] == 0
    assert "moved_to" in result


@pytest.mark.skip(reason="Requires LibreOffice installed")
def test_converter_converts_doc_to_docx(temp_dir):
    """Тест реальной конвертации doc -> docx (требует LibreOffice)."""
    # Создаем UNIT с .doc файлом
    unit_path = temp_dir / "UNIT_TEST"
    unit_path.mkdir()
    
    # Создаем простой .doc файл (в реальности нужен настоящий)
    doc_file = unit_path / "test.doc"
    doc_file.write_bytes(b"fake doc content")
    
    converter = Converter()
    result = converter.convert_unit(
        unit_path=unit_path,
        cycle=1,
        protocol_date="2025-03-18",
        dry_run=False,
    )
    
    # Проверяем результат
    assert result is not None
    # В реальном тесте проверяем наличие .docx файла

