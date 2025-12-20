"""
Файловые операции: определение типа файла, хеширование, санитизация имен.
"""
import hashlib
import magic
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import zipfile

# Ленивый импорт для избежания циклических зависимостей
# from ..core.decision_engine import resolve_type_decision

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


def _detect_by_signature(header: bytes, extension: str) -> Tuple[Optional[str], float]:
    """
    Определяет тип файла по magic bytes (signature).

    Args:
        header: Первые 16 байт файла
        extension: Расширение файла (для дополнительного контекста)

    Returns:
        Tuple[detected_type, confidence]:
        - detected_type: определенный тип файла или None
        - confidence: уровень уверенности (0.0-1.0)
    """
    MAGIC_SIGNATURES = {
        b"%PDF-": ("pdf", 1.0),
        b"PK\x03\x04": ("zip_or_office", 0.6),  # Может быть DOCX/XLSX/PPTX, нужен структурный парсинг
        b"\xFF\xD8\xFF": ("jpeg", 1.0),
        b"\x89PNG\r\n\x1a\n": ("png", 1.0),
        b"GIF87a": ("gif", 1.0),
        b"GIF89a": ("gif", 1.0),
        b"II*\x00": ("tiff", 1.0),
        b"MM\x00*": ("tiff", 1.0),
        b"\xD0\xCF\x11\xE0": ("ole2", 0.9),  # OLE2 (DOC/XLS/PPT)
        b"7z\xBC\xAF\x27\x1C": ("7z", 1.0),
        b"Rar!\x1a\x07": ("rar", 1.0),
        b"{\\rtf": ("rtf", 1.0),
    }

    for signature, (file_type, base_confidence) in MAGIC_SIGNATURES.items():
        if header.startswith(signature):
            # Для PK нужна дополнительная проверка (может быть Office)
            if signature == b"PK\x03\x04":
                # Низкая уверенность, нужен структурный парсинг
                return ("zip_or_office", 0.6)
            return (file_type, base_confidence)

    return (None, 0.0)


def _calculate_mime_confidence(mime_type: str) -> float:
    """
    Вычисляет confidence для MIME типа.

    Args:
        mime_type: MIME тип файла

    Returns:
        Уровень уверенности (0.0-1.0)
    """
    if mime_type == "application/octet-stream":
        return 0.0
    if mime_type.startswith("application/vnd."):
        return 0.9  # Высокая уверенность для специфичных типов Office
    if mime_type.startswith("application/"):
        return 0.7  # Средняя уверенность для общих типов
    if mime_type.startswith("image/") or mime_type.startswith("text/"):
        return 0.9  # Высокая уверенность для простых типов
    return 0.5  # Низкая уверенность по умолчанию


def collect_truth_sources(file_path: Path) -> Dict[str, Any]:
    """
    Собирает три источника истины явно и раздельно.

    Args:
        file_path: Путь к файлу

    Returns:
        Словарь с источниками истины:
        - mime_type: MIME тип файла
        - mime_confidence: уверенность MIME (0.0-1.0)
        - signature_type: тип по сигнатуре (magic bytes) или None
        - signature_confidence: уверенность сигнатуры (0.0-1.0)
        - extension: расширение файла
        - header: первые 16 байт файла
    """
    extension = file_path.suffix.lower()

    # MIME через python-magic
    try:
        mime = magic.Magic(mime=True)
        mime_type = mime.from_file(str(file_path))
        mime_confidence = _calculate_mime_confidence(mime_type)
    except Exception:
        mime_type = "application/octet-stream"
        mime_confidence = 0.0

    # Signature (magic bytes)
    try:
        with open(file_path, "rb") as f:
            header = f.read(16)
        signature_type, sig_confidence = _detect_by_signature(header, extension)
    except Exception:
        signature_type = None
        sig_confidence = 0.0
        header = b""

    return {
        "mime_type": mime_type,
        "mime_confidence": mime_confidence,
        "signature_type": signature_type,
        "signature_confidence": sig_confidence,
        "extension": extension,
        "header": header,
    }


def detect_file_type(file_path: Path) -> Dict[str, Any]:
    """
    Определяет тип файла используя эталонный pipeline с Decision Engine:
    1. Сбор источников истины (MIME, Signature, Extension)
    2. Decision Engine (разрешение конфликтов)
    3. Структурный парсинг (для полиглотных форматов)
    4. Возврат результата с полями Decision Engine

    Args:
        file_path: Путь к файлу

    Returns:
        Словарь с информацией о файле:
        - detected_type: тип файла (из Decision Engine)
        - mime_type: MIME тип
        - classification: "direct" | "normalize" | "ambiguous" (из Decision Engine)
        - scenario: идентификатор сценария Decision Engine
        - confidence: уровень уверенности
        - correct_extension: правильное расширение (если classification="normalize")
        - original_extension: исходное расширение
        - extension_matches_content: соответствует ли расширение содержимому
        - needs_ocr: требуется ли OCR
        - requires_conversion: требуется ли конвертация
        - is_archive: является ли архивом
        - is_fake_doc: архив с расширением .doc
        - is_signature_file: файл подписи
        - is_unsupported: неподдерживаемый формат
        - has_complex_extension: сложное расширение
        - sha256: SHA256 хеш
        - detection_details: детали детекции
    """
    result: Dict[str, Any] = {
        "detected_type": "unknown",
        "mime_type": "application/octet-stream",
        "needs_ocr": False,
        "requires_conversion": False,
        "is_archive": False,
        "is_fake_doc": False,
        "is_signature_file": False,
        "is_unsupported": False,
        "has_complex_extension": False,
        "extension_matches_content": True,
        "sha256": None,
        "detection_details": {},
        "original_extension": "",
        # Новые поля из Decision Engine
        "classification": "unknown",
        "scenario": None,
        "confidence": 0.0,
        "correct_extension": None,
    }

    if not file_path.exists():
        return result

    extension = file_path.suffix.lower()
    result["original_extension"] = extension
    full_name = file_path.name.lower()

    # ========================================================================
    # ШАГ 1: Быстрые проверки (подписи, неподдерживаемые, сложные расширения)
    # ========================================================================
    
    # Подписи
    signature_extensions = {".sig", ".p7s", ".pem", ".cer", ".crt"}
    if extension in signature_extensions:
        result["detected_type"] = "signature"
        result["is_signature_file"] = True
        result["extension_matches_content"] = True
        result["classification"] = "special"
        return result

    # Неподдерживаемые форматы
    unsupported_extensions = {".exe", ".dll", ".db", ".tmp", ".log", ".ini", ".sys", ".bat", ".sh"}
    if extension in unsupported_extensions:
        result["detected_type"] = "unsupported"
        result["is_unsupported"] = True
        result["extension_matches_content"] = True
        result["classification"] = "special"
        return result

    # Сложные расширения
    complex_extensions = [".tar.gz", ".tar.bz2", ".tar.xz", ".docm", ".xlsm", ".pptm"]
    for complex_ext in complex_extensions:
        if full_name.endswith(complex_ext):
            result["has_complex_extension"] = True
            result["is_unsupported"] = True
            result["classification"] = "special"
            return result

    # ========================================================================
    # ШАГ 2: Сбор источников истины
    # ========================================================================
    
    sources = collect_truth_sources(file_path)
    result["mime_type"] = sources["mime_type"]
    header = sources["header"]

    # ========================================================================
    # ШАГ 3: Decision Engine (разрешение конфликтов)
    # ========================================================================
    
    # Ленивый импорт для избежания циклических зависимостей
    from ..core.decision_engine import resolve_type_decision
    decision = resolve_type_decision(sources, file_path)
    
    # Добавляем поля из Decision Engine
    result["classification"] = decision["classification"]
    result["scenario"] = decision["scenario"]
    result["confidence"] = decision["confidence"]
    result["extension_matches_content"] = decision["sources_agreement"]
    result["correct_extension"] = decision.get("correct_extension")
    result["detection_details"]["decision_engine"] = {
        "scenario": decision["scenario"],
        "confidence": decision["confidence"],
        "conflict_reason": decision.get("conflict_reason"),
    }

    # ========================================================================
    # ШАГ 4: Структурный парсинг (если нужно)
    # ========================================================================

    true_type = decision.get("true_type")
    needs_parsing = decision.get("needs_structural_parsing", False)

    if needs_parsing or true_type in ["zip_or_office", "ole2"]:
    # Проверка ZIP/Office документов (все начинаются с PK\x03\x04)
        if sources["mime_type"].startswith("application/zip") or header.startswith(b"PK\x03\x04"):
            zip_result = _detect_zip_or_office(file_path, sources["mime_type"], extension, header)
            result.update(zip_result)
            # Обновляем true_type из структурного парсинга
            if zip_result.get("detected_type") != "unknown":
                true_type = zip_result.get("detected_type")
                result["detected_type"] = true_type
        # Проверка fake_doc после определения типа
        if result.get("is_archive") and extension in [".doc", ".docx", ".xls", ".xlsx"]:
            result["is_fake_doc"] = True
            result["detection_details"]["fake_doc_reason"] = f"{result.get('detected_type', 'archive')} with document extension"
    # Проверка Excel с OLE2
        elif header.startswith(b"\xd0\xcf\x11\xe0"):
            excel_result = _detect_excel_with_ole2(file_path, sources["mime_type"], extension, header)
            result.update(excel_result)
            if excel_result.get("detected_type") != "unknown":
                true_type = excel_result.get("detected_type")
                result["detected_type"] = true_type
    # Проверка OLE2 (старые Office форматы)
    elif header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        result["detected_type"] = "doc"
        result["requires_conversion"] = True
        result["detection_details"]["ole2_signature"] = True
        result["detection_details"]["real_doc"] = True
        true_type = "doc"
    else:
        # Используем true_type из Decision Engine
        if true_type:
            result["detected_type"] = true_type

    # ========================================================================
    # ШАГ 5: Дополнительные проверки для специфичных форматов
    # ========================================================================
    
    detected_type = result.get("detected_type", "unknown")
    mime_type = sources["mime_type"]

    # Проверка PDF с детальным анализом текстового слоя
    if detected_type == "pdf" or mime_type.startswith("application/pdf") or header.startswith(b"%PDF"):
        if detected_type != "pdf":
            detected_type = "pdf"
            result["detected_type"] = "pdf"
        pdf_result = _detect_pdf_with_text_layer(file_path, mime_type)
        result.update(pdf_result)

    # Проверка Office Open XML через MIME (если еще не определено)
    if detected_type == "unknown" and mime_type.startswith("application/vnd.openxmlformats"):
        if "wordprocessingml" in mime_type:
            detected_type = "docx"
        elif "spreadsheetml" in mime_type:
            detected_type = "xlsx"
        elif "presentationml" in mime_type:
            detected_type = "pptx"
        result["detected_type"] = detected_type

    # Проверка старых Office форматов через MIME (если еще не определено)
    if detected_type == "unknown":
        if mime_type.startswith("application/msword"):
            detected_type = "doc"
        result["detected_type"] = "doc"
        result["requires_conversion"] = True
    elif mime_type.startswith("application/vnd.ms-powerpoint"):
        detected_type = "ppt"
        result["detected_type"] = "ppt"
        result["requires_conversion"] = True

    # Проверка изображений
    if mime_type.startswith("image/"):
        detected_type = mime_type.split("/")[1]
        result["detected_type"] = detected_type
        result["needs_ocr"] = True

    # Проверка текстовых файлов
    if mime_type.startswith("text/"):
        if extension in [".html", ".htm"]:
            detected_type = "html"
        elif extension == ".xml":
            detected_type = "xml"
        else:
            detected_type = "txt"
        result["detected_type"] = detected_type

    # Проверка RTF
    if mime_type in ["application/rtf", "text/rtf"] or header.startswith(b"{\\rtf"):
        result["detected_type"] = "rtf"
        result["requires_conversion"] = True
        result["detection_details"]["rtf_detected"] = True

    # Проверка RAR архивов
    if header.startswith(b"Rar!\x1a\x07") or mime_type.startswith("application/x-rar"):
        result["is_archive"] = True
        result["detected_type"] = "rar_archive"
        result["detection_details"]["archive_type"] = "RAR"
        if extension in [".doc", ".docx"]:
            result["is_fake_doc"] = True
            result["detection_details"]["fake_doc_reason"] = "RAR archive with document extension"

    # Проверка 7z архивов
    if header.startswith(b"7z\xbc\xaf\x27\x1c") or mime_type.startswith("application/x-7z"):
        result.update(_detect_7z_archive(file_path, extension))

    # Обновляем correct_extension для normalize на основе финального detected_type
    if result["classification"] == "normalize" and not result.get("correct_extension"):
        from ..core.decision_engine import TypeDecisionEngine
        engine = TypeDecisionEngine()
        correct_ext = engine._type_to_extension(result.get("detected_type", "unknown"))
        if correct_ext:
            result["correct_extension"] = correct_ext

    # ========================================================================
    # ШАГ 6: Вычисление SHA256
    # ========================================================================
    
    try:
        result["sha256"] = calculate_sha256(file_path)
    except Exception as e:
        result["detection_details"]["sha256_error"] = str(e)

    return result


def _detect_zip_or_office(
    file_path: Path, mime_type: str, extension: str, header: bytes
) -> Dict[str, Any]:
    """
    Различает ZIP архив от Office документов (DOCX/XLSX/PPTX).

    Все они начинаются с PK\x03\x04, нужно проверить структуру.
    """
    result: Dict[str, Any] = {
        "is_archive": False,
        "detected_type": "unknown",
        "detection_details": {},
    }

    try:
        with zipfile.ZipFile(file_path, "r") as zf:
            namelist = zf.namelist()

            # Office Open XML документы содержат [Content_Types].xml
            if "[Content_Types].xml" in namelist:
                # Определяем тип по содержимому папок
                if any("word/" in name for name in namelist):
                    result["detected_type"] = "docx"
                elif any("xl/" in name for name in namelist):
                    result["detected_type"] = "xlsx"
                elif any("ppt/" in name for name in namelist):
                    result["detected_type"] = "pptx"
                else:
                    # Fallback на расширение
                    if extension == ".docx":
                        result["detected_type"] = "docx"
                    elif extension == ".xlsx":
                        result["detected_type"] = "xlsx"
                    elif extension == ".pptx":
                        result["detected_type"] = "pptx"
                result["detection_details"]["office_document"] = True
            else:
                # Это реальный ZIP архив - проверяем целостность через testzip()
                corrupted_file = zf.testzip()
                if corrupted_file is None:
                    result["is_archive"] = True
                    result["detected_type"] = "zip_archive"
                    result["detection_details"]["archive_validation_passed"] = True
                else:
                    result["detection_details"]["zip_validation_error"] = f"Corrupted file: {corrupted_file}"
                    result["detected_type"] = "unknown"
    except zipfile.BadZipFile:
        result["detection_details"]["zip_validation_error"] = "Not a valid ZIP archive"
    except Exception as e:
        result["detection_details"]["zip_validation_error"] = str(e)

    return result


def _detect_pdf_with_text_layer(file_path: Path, mime_type: str) -> Dict[str, Any]:
    """
    Детальная проверка PDF: анализ текстового слоя на нескольких страницах.
    """
    result: Dict[str, Any] = {
        "detected_type": "pdf",
        "mime_type": mime_type,
        "needs_ocr": True,
        "detection_details": {},
    }

    if not PYPDF_AVAILABLE:
        result["detection_details"]["pypdf_unavailable"] = True
        return result

    try:
        reader = PdfReader(str(file_path))
        total_pages = len(reader.pages)

        if total_pages == 0:
            result["detection_details"]["pdf_text_check"] = {"error": "No pages in PDF"}
            return result

        # Проверяем минимум 3 страницы, максимум 10 или 10% от общего количества
        pages_to_check = min(
            max(3, int(total_pages * 0.1)),
            10,
            total_pages
        )

        has_text = False
        text_length = 0
        pages_with_text = 0

        for i, page in enumerate(reader.pages[:pages_to_check]):
            try:
                text = page.extract_text()
                if text:
                    text_length += len(text.strip())
                    if len(text.strip()) > 10:
                        pages_with_text += 1
                        has_text = True
            except Exception as e:
                result["detection_details"]["pdf_page_error"] = str(e)

        # Если на 30%+ проверенных страниц есть текст - считаем что есть text layer
        if pages_to_check > 0:
            has_text = (pages_with_text / pages_to_check) >= 0.3

        result["needs_ocr"] = not has_text
        result["detection_details"]["pdf_text_check"] = {
            "has_text": has_text,
            "text_length": text_length,
            "total_pages": total_pages,
            "pages_checked": pages_to_check,
            "pages_with_text": pages_with_text,
        }
    except Exception as e:
        result["needs_ocr"] = True
        result["detection_details"]["pdf_text_check"] = {
            "error": str(e),
            "assumed_scan": True,
        }

    return result


def _detect_excel_with_ole2(
    file_path: Path, mime_type: str, extension: str, header: bytes
) -> Dict[str, Any]:
    """
    Детекция Excel файлов с проверкой OLE2 сигнатуры.
    """
    result: Dict[str, Any] = {
        "detected_type": "unknown",
        "requires_conversion": False,
        "detection_details": {},
    }

    # Проверка OLE2 signature для старых xls
    if header.startswith(b"\xd0\xcf\x11\xe0"):
        result["detected_type"] = "xls"
        result["requires_conversion"] = True
        result["detection_details"]["excel_type"] = "xls"
        result["detection_details"]["ole2_signature"] = True
    elif mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        result["detected_type"] = "xlsx"
        result["detection_details"]["excel_type"] = "xlsx"
    elif mime_type == "application/vnd.ms-excel":
        # Fallback на MIME для xls
        result["detected_type"] = "xls"
        result["requires_conversion"] = True
        result["detection_details"]["excel_type"] = "xls"

    return result


def _detect_7z_archive(file_path: Path, extension: str) -> Dict[str, Any]:
    """
    Детекция 7z архивов с валидацией.
    """
    result: Dict[str, Any] = {
        "is_archive": False,
        "detected_type": "unknown",
        "detection_details": {},
    }

    archive_valid = False
    if PY7ZR_AVAILABLE:
        try:
            with py7zr.SevenZipFile(file_path, mode='r') as z7:
                z7.getnames()
                archive_valid = True
        except Exception as e:
            result["detection_details"]["7z_validation_error"] = str(e)
    else:
        # Если py7zr недоступен, считаем валидным по magic bytes
        archive_valid = True

    if archive_valid:
        result["is_archive"] = True
        result["detected_type"] = "7z_archive"
        result["detection_details"]["archive_type"] = "7z"
        result["detection_details"]["archive_validation_passed"] = True
        if extension in [".doc", ".docx"]:
            result["is_fake_doc"] = True
            result["detection_details"]["fake_doc_reason"] = "7z archive with document extension"
    else:
        result["detection_details"]["archive_validation_failed"] = True

    return result

