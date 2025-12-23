"""
JSON экспорт DoclingDocument.
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def export_to_json(
    document: Any,
    output_path: Path,
    include_metadata: bool = True,
    metadata: Optional[dict] = None,
) -> Path:
    """
    Экспортирует DoclingDocument в JSON файл.

    Args:
        document: Document объект от Docling
        output_path: Путь для сохранения JSON
        include_metadata: Включать ли дополнительные метаданные
        metadata: Дополнительные метаданные для включения

    Returns:
        Путь к сохраненному файлу
    """
    try:
        # Сериализуем документ в JSON
        # Docling Document имеет метод model_dump() или dict()
        if hasattr(document, "model_dump"):
            doc_dict = document.model_dump()
        elif hasattr(document, "dict"):
            doc_dict = document.dict()
        elif hasattr(document, "__dict__"):
            doc_dict = document.__dict__
        else:
            # Fallback: пытаемся сериализовать как есть
            doc_dict = {"document": str(document)}

        # Добавляем метаданные если нужно
        if include_metadata:
            export_metadata = {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "export_format": "json",
            }
            if metadata:
                export_metadata.update(metadata)

            doc_dict["_export_metadata"] = export_metadata

        # Создаем директорию если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем JSON
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Exported document to JSON: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to export to JSON: {e}", exc_info=True)
        raise

