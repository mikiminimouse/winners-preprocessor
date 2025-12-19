"""
Определение дубликатов файлов внутри unit'а (протокола).
Файлы с разными именами, но одинаковым содержимым (SHA256) считаются дубликатами.
"""
from typing import Dict, List, Optional
import uuid


def detect_duplicates_in_unit(files: List[Dict]) -> Dict[str, List[str]]:
    """
    Определяет дубликаты файлов внутри одного unit'а.
    
    Args:
        files: Список файлов unit'а, каждый должен содержать 'sha256' и 'file_id'
    
    Returns:
        Словарь {sha256: [file_ids]}, где для каждого SHA256 список file_id файлов-дубликатов.
        Первый файл в группе считается оригиналом, остальные - дубликатами.
    """
    duplicates_map: Dict[str, List[str]] = {}
    sha256_to_files: Dict[str, List[Dict]] = {}
    
    # Группируем файлы по SHA256
    for file_info in files:
        sha256 = file_info.get("sha256")
        if not sha256:
            continue
        
        file_id = file_info.get("file_id")
        if not file_id:
            # Генерируем file_id если его нет
            file_id = str(uuid.uuid4())
            file_info["file_id"] = file_id
        
        if sha256 not in sha256_to_files:
            sha256_to_files[sha256] = []
        
        sha256_to_files[sha256].append({
            "file_id": file_id,
            "file_info": file_info
        })
    
    # Находим группы с дубликатами (более одного файла с одинаковым SHA256)
    for sha256, file_list in sha256_to_files.items():
        if len(file_list) > 1:
            # Сортируем по file_id для детерминированности (первый - оригинал)
            file_list.sort(key=lambda x: x["file_id"])
            file_ids = [f["file_id"] for f in file_list]
            duplicates_map[sha256] = file_ids
    
    return duplicates_map


def mark_duplicates_in_metadata(files: List[Dict], duplicates_map: Dict[str, List[str]]) -> List[Dict]:
    """
    Помечает дубликаты в метаданных файлов.
    
    Args:
        files: Список файлов unit'а
        duplicates_map: Результат detect_duplicates_in_unit()
    
    Returns:
        Обновленный список файлов с полями is_duplicate, original_file_id, duplicate_group
    """
    # Создаем обратный индекс: file_id -> sha256
    file_id_to_sha256: Dict[str, str] = {}
    for file_info in files:
        file_id = file_info.get("file_id")
        sha256 = file_info.get("sha256")
        if file_id and sha256:
            file_id_to_sha256[file_id] = sha256
    
    # Помечаем дубликаты
    for file_info in files:
        file_id = file_info.get("file_id")
        if not file_id:
            continue
        
        sha256 = file_id_to_sha256.get(file_id)
        if not sha256 or sha256 not in duplicates_map:
            # Не дубликат
            file_info["is_duplicate"] = False
            file_info["original_file_id"] = None
            file_info["duplicate_group"] = []
            continue
        
        # Находим группу дубликатов
        duplicate_group = duplicates_map[sha256]
        
        # Первый файл в группе - оригинал
        if file_id == duplicate_group[0]:
            file_info["is_duplicate"] = False
            file_info["original_file_id"] = None
            file_info["duplicate_group"] = duplicate_group
        else:
            # Остальные - дубликаты
            file_info["is_duplicate"] = True
            file_info["original_file_id"] = duplicate_group[0]
            file_info["duplicate_group"] = duplicate_group
    
    return files

