"""
Файловые операции: определение типа файла, хеширование, санитизация имен.
"""
import hashlib
import magic
from pathlib import Path
from typing import Dict, Any, Optional
import zipfile

try:
    import rarfile

    RARFILE_AVAILABLE = True
except ImportError:
    RARFILE_AVAILABLE = False

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def calculate_sha256(file_path: Path) -> str:
    """
    Вычисляет SHA256 хеш файла.

    Args:
        file_path: Путь к файлу

    Returns:
        SHA256 хеш в виде hex строки
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от опасных символов.

    Args:
        filename: Исходное имя файла

    Returns:
        Очищенное имя файла
    """
    # Удаляем path traversal символы
    filename = filename.replace("../", "").replace("..\\", "")
    # Удаляем другие опасные символы
    dangerous = ["<", ">", ":", '"', "|", "?", "*", "\x00"]
    for char in dangerous:
        filename = filename.replace(char, "_")
    return filename


def get_file_size(file_path: Path) -> int:
    """
    Возвращает размер файла в байтах.

    Args:
        file_path: Путь к файлу

    Returns:
        Размер файла в байтах
    """
    return file_path.stat().st_size if file_path.exists() else 0


def detect_file_type(file_path: Path) -> Dict[str, Any]:
    """
    Определяет тип файла используя magic bytes и mimetype.

    Args:
        file_path: Путь к файлу

    Returns:
        Словарь с информацией о файле:
        - detected_type: тип файла
        - mime_type: MIME тип
        - needs_ocr: требуется ли OCR
        - requires_conversion: требуется ли конвертация
        - is_archive: является ли архивом
        - extension_matches_content: соответствует ли расширение содержимому
        - sha256: SHA256 хеш
    """
    result: Dict[str, Any] = {
        "detected_type": "unknown",
        "mime_type": "application/octet-stream",
        "needs_ocr": False,
        "requires_conversion": False,
        "is_archive": False,
        "extension_matches_content": False,
        "sha256": None,
    }

    if not file_path.exists():
        return result

    extension = file_path.suffix.lower()

    try:
        # Используем python-magic для определения типа
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))

        # Определяем тип на основе MIME
        if mime_type.startswith("application/pdf"):
            result["detected_type"] = "pdf"
            result["mime_type"] = mime_type
            # Проверяем, есть ли текстовый слой
            if PYPDF_AVAILABLE:
                try:
                    reader = PdfReader(file_path)
                    if len(reader.pages) > 0:
                        # Простая проверка наличия текста
                        text = reader.pages[0].extract_text()
                        result["needs_ocr"] = len(text.strip()) < 50
                except Exception:
                    result["needs_ocr"] = True
        elif mime_type.startswith("application/vnd.openxmlformats"):
            if "wordprocessingml" in mime_type:
                result["detected_type"] = "docx"
            elif "spreadsheetml" in mime_type:
                result["detected_type"] = "xlsx"
            elif "presentationml" in mime_type:
                result["detected_type"] = "pptx"
        elif mime_type.startswith("application/msword"):
            result["detected_type"] = "doc"
            result["requires_conversion"] = True
        elif mime_type.startswith("application/vnd.ms-excel"):
            result["detected_type"] = "xls"
            result["requires_conversion"] = True
        elif mime_type.startswith("application/vnd.ms-powerpoint"):
            result["detected_type"] = "ppt"
            result["requires_conversion"] = True
        elif mime_type.startswith("application/zip"):
            # Проверяем, является ли ZIP архивом
            try:
                with zipfile.ZipFile(file_path, "r") as zf:
                    result["is_archive"] = True
                    result["detected_type"] = "zip_archive"
            except zipfile.BadZipFile:
                # Может быть Office документ
                pass
        elif mime_type.startswith("application/x-rar"):
            result["is_archive"] = True
            result["detected_type"] = "rar_archive"
        elif mime_type.startswith("application/x-7z"):
            result["is_archive"] = True
            result["detected_type"] = "7z_archive"
        elif mime_type.startswith("image/"):
            result["detected_type"] = mime_type.split("/")[1]
            result["needs_ocr"] = True
        elif mime_type.startswith("text/"):
            if extension == ".html" or extension == ".htm":
                result["detected_type"] = "html"
            elif extension == ".xml":
                result["detected_type"] = "xml"
            else:
                result["detected_type"] = "txt"

        # Проверяем соответствие расширения содержимому
        expected_extensions = {
            "pdf": ".pdf",
            "docx": ".docx",
            "doc": ".doc",
            "xlsx": ".xlsx",
            "xls": ".xls",
            "pptx": ".pptx",
            "ppt": ".ppt",
            "zip_archive": ".zip",
            "rar_archive": ".rar",
            "7z_archive": ".7z",
        }
        expected_ext = expected_extensions.get(result["detected_type"])
        result["extension_matches_content"] = (
            expected_ext is None or extension == expected_ext
        )

        # Вычисляем SHA256
        result["sha256"] = calculate_sha256(file_path)

    except Exception as e:
        # В случае ошибки оставляем значения по умолчанию
        result["detection_error"] = str(e)

    return result

