"""
Управление pipeline обработки файлов.

Оркестрирует процесс обработки нескольких файлов и управляет состоянием pipeline.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .processor import FileProcessor
from ...core.config import get_config
from ...core.exceptions import ProcessingError


class ProcessingPipeline:
    """
    Pipeline для обработки файлов.
    
    Управляет процессом обработки нескольких файлов, собирает метрики и обрабатывает ошибки.
    """
    
    def __init__(self):
        self.processor = FileProcessor()
        self.config = get_config().router
    
    def process_directory(
        self,
        directory: Path,
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает все файлы в директории.
        
        Args:
            directory: Директория для обработки
            recursive: Обрабатывать поддиректории рекурсивно
            pattern: Glob паттерн для фильтрации файлов (например, "*.pdf")
        
        Returns:
            Словарь с результатами:
            {
                "total_files": int,
                "processed": int,
                "failed": int,
                "results": list,
                "errors": list
            }
        """
        if not directory.exists():
            raise ProcessingError(
                f"Directory does not exist: {directory}",
                context={"directory": str(directory)}
            )
        
        # Находим файлы
        if pattern:
            if recursive:
                files = list(directory.rglob(pattern))
            else:
                files = list(directory.glob(pattern))
        else:
            if recursive:
                files = [f for f in directory.rglob("*") if f.is_file() and not f.name.startswith('.')]
            else:
                files = [f for f in directory.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        # Обрабатываем файлы
        return self.process_files(files)
    
    def process_files(self, file_paths: List[Path]) -> Dict[str, Any]:
        """
        Обрабатывает список файлов.
        
        Args:
            file_paths: Список путей к файлам
        
        Returns:
            Словарь с результатами обработки
        """
        total_files = len(file_paths)
        processed = 0
        failed = 0
        results = []
        errors = []
        
        for file_path in file_paths:
            try:
                result = self.processor.process_file(file_path)
                if result.get("status") == "processed":
                    processed += 1
                else:
                    failed += 1
                results.append(result)
            except ProcessingError as e:
                failed += 1
                error_result = {
                    "status": "error",
                    "message": str(e),
                    "unit_id": None,
                    "file": str(file_path),
                    "error_context": e.context
                }
                results.append(error_result)
                errors.append({
                    "file": str(file_path),
                    "error": str(e),
                    "context": e.context
                })
        
        return {
            "total_files": total_files,
            "processed": processed,
            "failed": failed,
            "success_rate": (processed / total_files * 100) if total_files > 0 else 0,
            "results": results,
            "errors": errors
        }
    
    def process_input_directory(self) -> Dict[str, Any]:
        """
        Обрабатывает все файлы из INPUT_DIR.
        
        Returns:
            Словарь с результатами обработки
        """
        input_dir = self.config.input_dir
        return self.process_directory(input_dir, recursive=False)

