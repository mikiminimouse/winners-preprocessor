"""
Определение типа файла через magic bytes и mimetype.
"""
from pathlib import Path
from typing import Dict, Any
import magic
import zipfile
from pypdf import PdfReader

# Опциональные библиотеки для проверки архивов
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
    from .metrics import add_error_metric
    from .utils import calculate_sha256
except ImportError:
    # Fallback для случаев циклических импортов
    def add_error_metric(*args, **kwargs):
        pass
    def calculate_sha256(file_path: Path) -> str:
        """Вычисляет SHA256 хеш файла."""
        import hashlib
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def detect_file_type(file_path: Path) -> Dict[str, Any]:
    """
    Определяет тип файла используя magic bytes и mimetype.
    Возвращает: detected_type, mime_type, needs_ocr, requires_conversion, is_archive,
    extension_matches_content, sha256
    """
    result = {
        "detected_type": "unknown",
        "mime_type": "application/octet-stream",
        "needs_ocr": False,
        "requires_conversion": False,
        "is_archive": False,
        "is_fake_doc": False,
        "is_signature_file": False,
        "is_unsupported": False,
        "has_complex_extension": False,
        "is_processable": True,
        "extension": file_path.suffix.lower(),
        "extension_matches_content": False,
        "magic_bytes": None,
        "sha256": None,
        "detection_details": {}
    }
    
    # Проверка на .sig и другие файлы подписей
    signature_extensions = [".sig", ".p7s", ".pem", ".cer", ".crt"]
    if result["extension"] in signature_extensions:
        result["detected_type"] = "signature"
        result["extension_matches_content"] = True
        result["is_signature_file"] = True
        result["is_processable"] = False
        result["detection_details"]["is_signature_file"] = True
        result["detection_details"]["signature_reason"] = f"File has {result['extension']} extension (digital signature)"
        return result
    
    # Проверка на неподдерживаемые форматы
    unsupported_extensions = [".exe", ".dll", ".db", ".tmp", ".log", ".ini", ".sys", ".bat", ".sh"]
    if result["extension"] in unsupported_extensions:
        result["detected_type"] = "unsupported"
        result["extension_matches_content"] = True
        result["is_unsupported"] = True
        result["is_processable"] = False
        result["detection_details"]["is_unsupported"] = True
        result["detection_details"]["unsupported_reason"] = f"File type {result['extension']} is not supported"
        return result
    
    # Проверка на сложные расширения
    full_name = file_path.name.lower()
    complex_extensions = [".tar.gz", ".tar.bz2", ".tar.xz", ".docm", ".xlsm", ".pptm", ".dotx", ".xltx", ".potx"]
    for complex_ext in complex_extensions:
        if full_name.endswith(complex_ext):
            result["detected_type"] = "complex_extension"
            result["extension_matches_content"] = True
            result["has_complex_extension"] = True
            result["is_processable"] = False
            result["detection_details"]["has_complex_extension"] = True
            result["detection_details"]["complex_extension"] = complex_ext
            return result
    
    # Вычисляем SHA256 для определения дубликатов
    try:
        result["sha256"] = calculate_sha256(file_path)
    except Exception as e:
        result["detection_details"]["sha256_error"] = str(e)
    
    try:
        # Используем python-magic для определения MIME типа
        mime = magic.from_file(str(file_path), mime=True)
        result["mime_type"] = mime
        result["detection_details"]["mime_detected"] = mime
        
        # Приоритетная проверка для .xls файлов - если расширение .xls и MIME указывает на Excel
        if result["extension"] == ".xls" and (mime == "application/vnd.ms-excel" or mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"):
            result["detected_type"] = "excel"
            result["needs_ocr"] = False
            result["detection_details"]["excel_type"] = "xls"
            result["detection_details"]["excel_priority"] = "extension_and_mime_match"
        
        # Читаем первые байты для дополнительной проверки
        with open(file_path, "rb") as f:
            header = f.read(16)
        
        # Сохраняем magic bytes для логирования
        result["magic_bytes"] = header.hex()[:32]  # Первые 16 байт в hex
        result["detection_details"]["header_hex"] = header.hex()[:32]
        
        # Проверка на архивы (даже если расширение .doc)
        if header.startswith(b"Rar!\x1a\x07") or header.startswith(b"Rar!\x1a\x07\x00"):
            result["is_archive"] = True
            result["detected_type"] = "rar_archive"
            result["detection_details"]["archive_type"] = "RAR"
            if result["extension"] == ".doc":
                result["is_fake_doc"] = True
                result["detection_details"]["fake_doc_reason"] = "RAR archive with .doc extension"
        elif header.startswith(b"PK\x03\x04") or header.startswith(b"PK\x05\x06"):
            # ZIP, DOCX (DOCX это ZIP) или XLSX (XLSX это тоже ZIP)
            result["detection_details"]["zip_signature"] = True
            
            # Проверяем Excel файлы (xlsx, xls) - они тоже начинаются с PK
            if mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                # XLSX файл
                result["detected_type"] = "excel"
                result["needs_ocr"] = False
                result["detection_details"]["excel_type"] = "xlsx"
            elif mime == "application/vnd.ms-excel":
                # Старый формат XLS (может быть OLE2 или бинарный)
                if header.startswith(b"\xd0\xcf\x11\xe0"):
                    result["detected_type"] = "excel"
                    result["needs_ocr"] = False
                    result["detection_details"]["excel_type"] = "xls"
                else:
                    result["detected_type"] = "excel"
                    result["needs_ocr"] = False
                    result["detection_details"]["excel_type"] = "xls_binary"
            elif mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                result["detected_type"] = "docx"
                result["needs_ocr"] = False
                result["detection_details"]["docx_detected"] = True
            elif mime == "application/zip":
                # Проверяем ZIP архив через попытку открытия
                archive_valid = False
                try:
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        # testzip() возвращает None если архив валиден, иначе имя поврежденного файла
                        if zf.testzip() is None:
                            archive_valid = True
                except Exception as e:
                    result["detection_details"]["zip_validation_error"] = str(e)
                
                if archive_valid:
                    result["is_archive"] = True
                    result["detected_type"] = "zip_archive"
                    result["detection_details"]["archive_type"] = "ZIP"
                    result["detection_details"]["archive_validation_passed"] = True
                    if result["extension"] == ".doc":
                        result["is_fake_doc"] = True
                        result["detection_details"]["fake_doc_reason"] = "ZIP archive with .doc extension"
                else:
                    result["is_archive"] = False
                    result["detected_type"] = "unknown"
                    result["detection_details"]["archive_validation_passed"] = False
            else:
                # Если MIME не определен, но есть PK signature - проверяем расширение
                if result["extension"] in [".xlsx", ".xls"]:
                    result["detected_type"] = "excel"
                    result["needs_ocr"] = False
                    result["detection_details"]["excel_type"] = "detected_by_extension"
                elif result["extension"] == ".docx":
                    result["detected_type"] = "docx"
                    result["needs_ocr"] = False
                    result["detection_details"]["docx_detected"] = True
                else:
                    # По умолчанию считаем ZIP архивом, но проверяем через открытие
                    archive_valid = False
                    try:
                        with zipfile.ZipFile(file_path, 'r') as zf:
                            if zf.testzip() is None:
                                archive_valid = True
                    except Exception as e:
                        result["detection_details"]["zip_validation_error"] = str(e)
                    
                    if archive_valid:
                        result["is_archive"] = True
                        result["detected_type"] = "zip_archive"
                        result["detection_details"]["archive_type"] = "ZIP"
                        result["detection_details"]["archive_validation_passed"] = True
                        if result["extension"] == ".doc":
                            result["is_fake_doc"] = True
                            result["detection_details"]["fake_doc_reason"] = "ZIP archive with .doc extension"
                    else:
                        result["is_archive"] = False
                        result["detected_type"] = "unknown"
                        result["detection_details"]["archive_validation_passed"] = False
        elif header.startswith(b"%PDF"):
            result["detected_type"] = "pdf"
            result["detection_details"]["pdf_signature"] = True
            # Проверяем наличие текстового слоя (улучшенная проверка)
            try:
                reader = PdfReader(str(file_path))
                total_pages = len(reader.pages)
                
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
                    text = page.extract_text()
                    if text:
                        text_length += len(text.strip())
                        if len(text.strip()) > 10:
                            pages_with_text += 1
                            has_text = True
                
                # Если на 30%+ проверенных страниц есть текст - считаем что есть text layer
                if pages_to_check > 0:
                    has_text = (pages_with_text / pages_to_check) >= 0.3
                
                result["needs_ocr"] = not has_text
                result["detection_details"]["pdf_text_check"] = {
                    "has_text": has_text,
                    "text_length": text_length,
                    "total_pages": total_pages,
                    "pages_checked": pages_to_check,
                    "pages_with_text": pages_with_text
                }
            except Exception as e:
                result["needs_ocr"] = True  # Если ошибка чтения - считаем сканом
                result["detection_details"]["pdf_text_check"] = {
                    "error": str(e),
                    "assumed_scan": True
                }
        elif header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            # OLE2 формат - реальный DOC
            result["detected_type"] = "doc"
            result["requires_conversion"] = True
            result["needs_ocr"] = False
            result["detection_details"]["ole2_signature"] = True
            result["detection_details"]["real_doc"] = True
        elif mime.startswith("image/"):
            result["detected_type"] = "image"
            result["needs_ocr"] = True
            result["detection_details"]["image_type"] = mime
        elif header.startswith(b"7z\xbc\xaf\x27\x1c") or mime == "application/x-7z-compressed":
            # 7z архив - проверяем через попытку открытия
            archive_valid = False
            if PY7ZR_AVAILABLE:
                try:
                    with py7zr.SevenZipFile(file_path, mode='r') as z7:
                        # Проверяем список файлов в архиве
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
                if result["extension"] == ".doc":
                    result["is_fake_doc"] = True
                    result["detection_details"]["fake_doc_reason"] = "7z archive with .doc extension"
            else:
                result["is_archive"] = False
                result["detected_type"] = "unknown"
                result["detection_details"]["archive_validation_passed"] = False
                result["detection_details"]["archive_validation_error"] = "7z file failed validation"
        elif mime == "application/rtf" or mime == "text/rtf" or header.startswith(b"{\\rtf"):
            # RTF файл
            result["detected_type"] = "rtf"
            result["needs_ocr"] = False
            result["detection_details"]["rtf_detected"] = True
        # Excel файлы обрабатываются выше в блоке PK signature
        # Этот блок оставлен для случаев, когда MIME определен, но PK signature не обнаружен
        elif (mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or \
              mime == "application/vnd.ms-excel") and not header.startswith(b"PK\x03\x04"):
            # Excel файлы (xlsx, xls) - старый формат XLS без PK signature
            result["detected_type"] = "excel"
            result["needs_ocr"] = False
            result["detection_details"]["excel_type"] = mime
        elif header.startswith(b"<?xml") or (mime == "application/xml" or mime == "text/xml"):
            # XML файл (может быть WordML)
            # Читаем больше байт для проверки XML
            with open(file_path, "rb") as f:
                first_2048 = f.read(2048).decode('utf-8', errors='ignore')
                # Проверяем на WordML (w:wordDocument) или другие XML форматы
                xml_indicators = [
                    '<?xml',
                    '<w:wordDocument',
                    '<wordDocument',
                    'xmlns:w=',
                    'xmlns:o=',
                    '<office:document'
                ]
                is_xml = any(indicator in first_2048 for indicator in xml_indicators)
                
                if is_xml:
                    # Определяем тип XML
                    if 'wordDocument' in first_2048 or 'xmlns:w=' in first_2048:
                        result["detected_type"] = "xml"
                        result["detection_details"]["xml_type"] = "WordML"
                    else:
                        result["detected_type"] = "xml"
                        result["detection_details"]["xml_type"] = "generic"
                    
                    if result["extension"] == ".doc":
                        result["is_fake_doc"] = True
                        result["detection_details"]["fake_doc_reason"] = f"XML ({result['detection_details'].get('xml_type', 'generic')}) file with .doc extension"
                    result["needs_ocr"] = False
                    result["detection_details"]["xml_indicators_found"] = [
                        ind for ind in xml_indicators if ind in first_2048
                    ]
        elif mime == "text/html" or header.startswith(b"<!DOCTYPE") or header.startswith(b"<html") or \
             header.startswith(b"<HTML") or (len(header) > 4 and header[:4].startswith(b"<") and not header.startswith(b"<?xml")):
            # HTML файл (проверяем более тщательно, но не XML)
            # Читаем больше байт для проверки HTML
            with open(file_path, "rb") as f:
                first_1024 = f.read(1024).decode('utf-8', errors='ignore').lower()
                # Проверяем на различные HTML теги
                html_indicators = [
                    '<html', '<!doctype', '<body', '<head', '<section', 
                    '<div', '<table', '<p', '<h1', '<h2', '<h3', '<title',
                    '<meta', '<script', '<style', '<link'
                ]
                is_html = any(indicator in first_1024 for indicator in html_indicators)
                
                if is_html:
                    result["detected_type"] = "html"
                    # Различаем реальные HTML и фейковые .doc с HTML
                    if result["extension"] in [".html", ".htm"]:
                        # Реальный HTML файл
                        result["is_fake_doc"] = False
                    elif result["extension"] == ".doc":
                        # Фейковый .doc с HTML содержимым
                        result["is_fake_doc"] = True
                        result["detection_details"]["fake_doc_reason"] = "HTML file with .doc extension"
                    result["needs_ocr"] = False
                    result["detection_details"]["html_indicators_found"] = [
                        ind for ind in html_indicators if ind in first_1024
                    ]
                else:
                    # Если не HTML, но расширение .doc и не OLE2 - возможно поврежденный файл
                    if result["extension"] == ".doc" and not header.startswith(b"\xd0\xcf\x11\xe0"):
                        result["is_fake_doc"] = True
                        result["detection_details"]["fake_doc_reason"] = "Unknown format with .doc extension"
            result["detection_details"]["html_detected"] = True
        elif mime == "application/msword":
            result["detected_type"] = "doc"
            result["requires_conversion"] = True
            result["needs_ocr"] = False
            result["detection_details"]["msword_mime"] = True
            # Проверяем, не является ли это архивом с неправильным MIME
            if not header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
                result["detection_details"]["suspicious"] = "MIME says msword but no OLE2 signature"
        
        # Определяем соответствие расширения реальному содержимому
        extension = result["extension"]
        detected_type = result["detected_type"]
        
        # Маппинг расширений на ожидаемые типы
        extension_to_type = {
            ".pdf": "pdf",
            ".doc": "doc",
            ".docx": "docx",
            ".zip": "zip_archive",
            ".rar": "rar_archive",
            ".7z": "7z_archive",
            ".html": "html",
            ".htm": "html",
            ".jpg": "image",
            ".jpeg": "image",
            ".png": "image",
            ".gif": "image",
            ".bmp": "image",
            ".xlsx": "excel",
            ".xls": "excel",
            ".rtf": "rtf",
            ".xml": "xml"
        }
        
        expected_type = extension_to_type.get(extension)
        if expected_type:
            # Нормализуем detected_type для сравнения
            normalized_detected = detected_type.replace("_archive", "")
            normalized_expected = expected_type.replace("_archive", "")
            
            # Специальная обработка для архивов
            if extension in [".zip", ".rar", ".7z"]:
                result["extension_matches_content"] = result["is_archive"]
            # Специальная обработка для DOCX (это ZIP)
            elif extension == ".docx" and detected_type == "docx":
                result["extension_matches_content"] = True
            # Специальная обработка для Excel (xlsx, xls)
            elif extension in [".xlsx", ".xls"] and detected_type == "excel":
                result["extension_matches_content"] = True
            # Специальная обработка для RTF
            elif extension == ".rtf" and detected_type == "rtf":
                result["extension_matches_content"] = True
            # Для остальных типов
            elif normalized_detected == normalized_expected or detected_type == expected_type:
                result["extension_matches_content"] = True
            else:
                result["extension_matches_content"] = False
        else:
            # Если расширение неизвестно, считаем что не соответствует
            result["extension_matches_content"] = False
        
        # Добавляем информацию о несоответствии в detection_details
        if not result["extension_matches_content"]:
            result["detection_details"]["extension_mismatch"] = {
                "extension": extension,
                "expected_type": expected_type,
                "detected_type": detected_type
            }
        
        # Логируем результат определения типа
        print(f"[DETECT_TYPE] {file_path.name}: extension={result['extension']}, "
              f"mime={result['mime_type']}, detected={result['detected_type']}, "
              f"is_archive={result['is_archive']}, is_fake_doc={result['is_fake_doc']}, "
              f"extension_matches={result['extension_matches_content']}, "
              f"magic_bytes={result.get('magic_bytes', 'N/A')[:16]}...")
        
    except Exception as e:
        print(f"Error detecting file type for {file_path}: {e}")
        import traceback
        error_details = traceback.format_exc()
        result["detected_type"] = "unknown"
        result["detection_details"]["error"] = str(e)
        result["detection_details"]["error_traceback"] = error_details
        add_error_metric(str(file_path), "detect_type", str(e), error_details)
    
    return result

