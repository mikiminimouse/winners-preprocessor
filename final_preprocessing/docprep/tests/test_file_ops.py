"""
Unit тесты для file_ops утилит.
"""
import pytest
from pathlib import Path
import zipfile

from docprep.utils.file_ops import (
    detect_file_type,
    calculate_sha256,
    sanitize_filename,
    get_file_size,
)


def test_detect_file_type_pdf(temp_dir):
    """Тест детекции PDF файла."""
    pdf_file = temp_dir / "test.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake pdf content")
    
    result = detect_file_type(pdf_file)
    
    assert result["detected_type"] == "pdf"
    assert result["mime_type"].startswith("application/pdf")
    assert "sha256" in result


def test_detect_file_type_zip(temp_dir):
    """Тест детекции ZIP архива."""
    zip_file = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_file, "w") as zf:
        zf.writestr("file.txt", "content")
    
    result = detect_file_type(zip_file)
    
    assert result["is_archive"] is True
    assert result["detected_type"] == "zip_archive"


def test_detect_file_type_fake_doc(temp_dir):
    """Тест детекции fake_doc (ZIP с расширением .doc)."""
    fake_doc = temp_dir / "fake.doc"
    with zipfile.ZipFile(fake_doc, "w") as zf:
        zf.writestr("file.txt", "content")
    
    result = detect_file_type(fake_doc)
    
    # Должен определить как архив, а не doc
    assert result.get("is_fake_doc", False) or result["is_archive"] is True


def test_detect_file_type_docx(temp_dir):
    """Тест детекции DOCX файла."""
    docx_file = temp_dir / "test.docx"
    # Создаем минимальный DOCX (ZIP с [Content_Types].xml)
    with zipfile.ZipFile(docx_file, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types></Types>')
        zf.writestr("word/document.xml", "<document></document>")
    
    result = detect_file_type(docx_file)
    
    # Должен определить как docx, а не zip
    assert result["detected_type"] == "docx" or result["is_archive"] is False


def test_calculate_sha256(temp_dir):
    """Тест вычисления SHA256."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    
    sha256 = calculate_sha256(test_file)
    
    assert sha256 is not None
    assert len(sha256) == 64  # SHA256 hex длина
    assert isinstance(sha256, str)


def test_sanitize_filename():
    """Тест санитизации имени файла."""
    dangerous = "../file.txt"
    safe = sanitize_filename(dangerous)
    
    assert "../" not in safe
    assert ".." not in safe or safe.count("..") == 0


def test_get_file_size(temp_dir):
    """Тест получения размера файла."""
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")
    
    size = get_file_size(test_file)
    
    assert size > 0
    assert isinstance(size, int)

