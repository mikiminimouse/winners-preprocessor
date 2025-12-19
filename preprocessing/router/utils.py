"""
Утилиты для router микросервиса.
"""
import hashlib
from pathlib import Path


def calculate_sha256(file_path: Path) -> str:
    """Вычисляет SHA256 хеш файла."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def sanitize_filename(filename: str) -> str:
    """Очищает имя файла от опасных символов."""
    # Удаляем пути и опасные символы
    filename = filename.replace("../", "").replace("..\\", "")
    filename = Path(filename).name
    
    # Заменяем опасные символы
    dangerous = ['<', '>', ':', '"', '|', '?', '*', '\x00']
    for char in dangerous:
        filename = filename.replace(char, '_')
    
    # Ограничиваем длину
    if len(filename) > 200:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:200-len(ext)] + ext
    
    return filename
