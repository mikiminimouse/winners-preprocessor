"""
Работа с архивами для router микросервиса.
Поддержка ZIP, RAR, 7z архивов с безопасностью (защита от zip bomb).
"""
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

from .config import MAX_UNPACK_SIZE_MB, MAX_FILES_IN_ARCHIVE
from .file_detection import detect_file_type
from .utils import sanitize_filename

# Импортируем add_error_metric - она может быть в metrics.py если файл существует
try:
    from .metrics import add_error_metric
except ImportError:
    def add_error_metric(*args, **kwargs):
        pass  # Заглушка если metrics недоступен


def safe_extract_archive(archive_path: Path, extract_to: Path, archive_id: str) -> Tuple[List[Dict], bool]:
    """
    Безопасно распаковывает архив с проверками на zip bomb и ограничениями.
    Возвращает список файлов и успешность операции.
    """
    extracted_files = []
    max_size = MAX_UNPACK_SIZE_MB * 1024 * 1024
    total_size = 0
    file_count = 0
    archive_size = archive_path.stat().st_size
    extraction_details = {
        "archive_path": str(archive_path),
        "archive_size": archive_size,
        "archive_type": None,
        "extraction_started": datetime.utcnow().isoformat(),
        "extraction_errors": []
    }
    
    try:
        # Определяем тип архива
        file_type = detect_file_type(archive_path)
        extraction_details["archive_type"] = file_type.get("detected_type", "unknown")
        extraction_details["detected_mime"] = file_type.get("mime_type", "")
        extraction_details["is_fake_doc"] = file_type.get("is_fake_doc", False)
        
        print(f"[EXTRACT_ARCHIVE] Starting extraction: {archive_path.name}, "
              f"type={extraction_details['archive_type']}, size={archive_size}, "
              f"is_fake_doc={extraction_details['is_fake_doc']}")
        
        # Проверка на HTML файлы - не должны распаковываться как архивы
        if file_type.get("detected_type") == "html":
            error_msg = f"File {archive_path.name} is an HTML file, not an archive. Cannot extract."
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "reason": "html_not_archive",
                "detected_type": file_type.get("detected_type"),
                "mime_type": file_type.get("mime_type")
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            return extracted_files, False
        
        # Проверка на реальный DOC файл
        if archive_path.suffix.lower() == ".doc" and not file_type.get("is_archive") and not file_type.get("is_fake_doc"):
            error_msg = f"File {archive_path.name} is a real DOC file (OLE2 format), not an archive. Cannot extract."
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "reason": "real_doc_not_archive",
                "detected_type": file_type.get("detected_type"),
                "has_ole2_signature": file_type.get("detection_details", {}).get("ole2_signature", False)
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            return extracted_files, False
        
        # Обработка ZIP архивов
        if file_type["detected_type"] == "zip_archive" or archive_path.suffix.lower() == ".zip":
            extracted_files, success = _extract_zip(archive_path, extract_to, extraction_details, max_size)
            if success:
                extraction_details["extraction_completed"] = datetime.utcnow().isoformat()
                extraction_details["success"] = True
                return extracted_files, True
            else:
                return extracted_files, False
        
        # Обработка RAR архивов
        elif file_type["detected_type"] == "rar_archive" or archive_path.suffix.lower() == ".rar":
            extracted_files, success = _extract_rar(archive_path, extract_to, extraction_details, max_size)
            if success:
                extraction_details["extraction_completed"] = datetime.utcnow().isoformat()
                extraction_details["success"] = True
                return extracted_files, True
            else:
                return extracted_files, False
        
        # Обработка 7z архивов
        elif archive_path.suffix.lower() == ".7z":
            extracted_files, success = _extract_7z(archive_path, extract_to, extraction_details, max_size)
            if success:
                extraction_details["extraction_completed"] = datetime.utcnow().isoformat()
                extraction_details["success"] = True
                return extracted_files, True
            else:
                return extracted_files, False
        
        else:
            error_msg = f"Unknown archive type or file is not an archive. Detected type: {file_type.get('detected_type')}"
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "detected_type": file_type.get("detected_type"),
                "is_archive": file_type.get("is_archive", False)
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            return extracted_files, False
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        error_msg = f"Error extracting archive {archive_path.name}: {str(e)}"
        extraction_details["extraction_errors"].append({
            "error": error_msg,
            "exception_type": type(e).__name__,
            "traceback": error_details
        })
        extraction_details["extraction_completed"] = datetime.utcnow().isoformat()
        extraction_details["success"] = False
        print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
        print(f"[EXTRACT_ARCHIVE] Traceback: {error_details}")
        add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
        return extracted_files, False


def _extract_zip(archive_path: Path, extract_to: Path, extraction_details: Dict, max_size: int) -> Tuple[List[Dict], bool]:
    """Распаковывает ZIP архив."""
    extracted_files = []
    total_size = 0
    file_count = 0
    
    extraction_details["extraction_method"] = "zipfile"
    
    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            total_members = len(zip_ref.namelist())
            extraction_details["total_members"] = total_members
            print(f"[EXTRACT_ARCHIVE] ZIP archive contains {total_members} members")
            
            for member in zip_ref.namelist():
                if file_count >= MAX_FILES_IN_ARCHIVE:
                    error_msg = f"Too many files in archive (>{MAX_FILES_IN_ARCHIVE})"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "file_count": file_count,
                        "limit": MAX_FILES_IN_ARCHIVE
                    })
                    raise ValueError(error_msg)
                
                safe_name = sanitize_filename(member)
                if not safe_name or safe_name.endswith('/'):
                    continue
                
                info = zip_ref.getinfo(member)
                if info.file_size > max_size:
                    extraction_details["extraction_errors"].append({
                        "warning": f"File {member} skipped: too large ({info.file_size} > {max_size})"
                    })
                    continue
                
                total_size += info.file_size
                if total_size > max_size:
                    error_msg = f"Archive too large (>{MAX_UNPACK_SIZE_MB}MB)"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "total_size": total_size,
                        "limit": max_size
                    })
                    raise ValueError(error_msg)
                
                dest_path = extract_to / safe_name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                with zip_ref.open(member) as source, open(dest_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                
                file_count += 1
                extracted_files.append({
                    "original_name": member,
                    "safe_name": safe_name,
                    "path": str(dest_path),
                    "size": info.file_size
                })
            
            extraction_details["extracted_count"] = file_count
            extraction_details["total_extracted_size"] = total_size
            print(f"[EXTRACT_ARCHIVE] Successfully extracted {file_count} files from ZIP archive")
            return extracted_files, True
    
    except zipfile.BadZipFile as e:
        error_msg = f"Invalid ZIP file: {str(e)}"
        extraction_details["extraction_errors"].append({
            "error": error_msg,
            "error_type": "BadZipFile"
        })
        print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
        add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
        return extracted_files, False


def _extract_rar(archive_path: Path, extract_to: Path, extraction_details: Dict, max_size: int) -> Tuple[List[Dict], bool]:
    """Распаковывает RAR архив через unrar или 7z."""
    extracted_files = []
    total_size = 0
    file_count = 0
    
    extraction_details["extraction_method"] = "unrar"
    
    try:
        cmd = ["unrar", "x", "-y", str(archive_path), str(extract_to)]
        print(f"[EXTRACT_ARCHIVE] Running unrar command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        extraction_details["unrar_returncode"] = result.returncode
        extraction_details["unrar_stdout"] = result.stdout[:1000]
        extraction_details["unrar_stderr"] = result.stderr[:1000]
        
        if result.returncode != 0:
            print(f"[EXTRACT_ARCHIVE] unrar failed (code {result.returncode}), trying 7z as fallback...")
            extraction_details["extraction_method"] = "7z_fallback"
            cmd = ["7z", "x", str(archive_path), f"-o{extract_to}", "-y"]
            print(f"[EXTRACT_ARCHIVE] Running 7z command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            extraction_details["7z_returncode"] = result.returncode
            extraction_details["7z_stdout"] = result.stdout[:1000]
            extraction_details["7z_stderr"] = result.stderr[:1000]
            
            if result.returncode != 0:
                error_msg = f"Both unrar and 7z failed. unrar: {extraction_details.get('unrar_stderr', '')[:200]}, 7z: {result.stderr[:200]}"
                extraction_details["extraction_errors"].append({
                    "error": error_msg,
                    "unrar_returncode": extraction_details.get("unrar_returncode"),
                    "7z_returncode": result.returncode,
                    "stderr": result.stderr[:500]
                })
                print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
                add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
        
        # Собираем список извлеченных файлов
        for file_path in extract_to.rglob("*"):
            if file_path.is_file():
                file_count += 1
                if file_count > MAX_FILES_IN_ARCHIVE:
                    error_msg = f"Too many files in archive (>{MAX_FILES_IN_ARCHIVE})"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "file_count": file_count
                    })
                    raise ValueError(error_msg)
                
                stat = file_path.stat()
                total_size += stat.st_size
                if total_size > max_size:
                    error_msg = f"Archive too large (>{MAX_UNPACK_SIZE_MB}MB)"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "total_size": total_size
                    })
                    raise ValueError(error_msg)
                
                extracted_files.append({
                    "original_name": file_path.name,
                    "safe_name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size
                })
        
        extraction_details["extracted_count"] = file_count
        extraction_details["total_extracted_size"] = total_size
        print(f"[EXTRACT_ARCHIVE] Successfully extracted {file_count} files from RAR archive")
        return extracted_files, True
    
    except FileNotFoundError as e:
        error_msg = f"Archive extraction utility not found: {str(e)}. Install unrar and/or p7zip-full."
        extraction_details["extraction_errors"].append({
            "error": error_msg,
            "error_type": "FileNotFoundError",
            "exception": str(e)
        })
        print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
        add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
        return extracted_files, False


def _extract_7z(archive_path: Path, extract_to: Path, extraction_details: Dict, max_size: int) -> Tuple[List[Dict], bool]:
    """Распаковывает 7z архив через 7z."""
    extracted_files = []
    total_size = 0
    file_count = 0
    
    extraction_details["extraction_method"] = "7z"
    
    try:
        cmd = ["7z", "x", str(archive_path), f"-o{extract_to}", "-y"]
        print(f"[EXTRACT_ARCHIVE] Running 7z command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        extraction_details["7z_returncode"] = result.returncode
        extraction_details["7z_stdout"] = result.stdout[:1000]
        extraction_details["7z_stderr"] = result.stderr[:1000]
        
        if result.returncode != 0:
            error_msg = f"7z extraction failed with return code {result.returncode}: {result.stderr[:200]}"
            extraction_details["extraction_errors"].append({
                "error": error_msg,
                "returncode": result.returncode,
                "stderr": result.stderr[:500]
            })
            print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
            add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
        
        # Собираем список извлеченных файлов
        for file_path in extract_to.rglob("*"):
            if file_path.is_file():
                file_count += 1
                if file_count > MAX_FILES_IN_ARCHIVE:
                    error_msg = f"Too many files in archive (>{MAX_FILES_IN_ARCHIVE})"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "file_count": file_count
                    })
                    raise ValueError(error_msg)
                
                stat = file_path.stat()
                total_size += stat.st_size
                if total_size > max_size:
                    error_msg = f"Archive too large (>{MAX_UNPACK_SIZE_MB}MB)"
                    extraction_details["extraction_errors"].append({
                        "error": error_msg,
                        "total_size": total_size
                    })
                    raise ValueError(error_msg)
                
                extracted_files.append({
                    "original_name": file_path.name,
                    "safe_name": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size
                })
        
        extraction_details["extracted_count"] = file_count
        extraction_details["total_extracted_size"] = total_size
        print(f"[EXTRACT_ARCHIVE] Successfully extracted {file_count} files from 7z archive")
        return extracted_files, True
    
    except FileNotFoundError as e:
        error_msg = f"Archive extraction utility not found: {str(e)}. Install unrar and/or p7zip-full."
        extraction_details["extraction_errors"].append({
            "error": error_msg,
            "error_type": "FileNotFoundError",
            "exception": str(e)
        })
        print(f"[EXTRACT_ARCHIVE] ERROR: {error_msg}")
        add_error_metric(str(archive_path), "extraction", error_msg, json.dumps(extraction_details))
        return extracted_files, False

