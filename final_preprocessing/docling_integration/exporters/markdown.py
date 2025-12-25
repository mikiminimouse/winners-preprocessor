"""
Markdown экспорт DoclingDocument с сохранением структуры документа.

Использует встроенный метод export_to_markdown из DoclingDocument для сохранения layout.
"""
import logging
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime, timezone

# Импортируем DoclingDocument для конвертации словарей
try:
    from docling.datamodel.document import DoclingDocument
except ImportError:
    DoclingDocument = None

logger = logging.getLogger(__name__)


def export_to_markdown(
    document: Any,
    output_path: Path,
    include_metadata: bool = True,
    metadata: Optional[dict] = None,
) -> Path:
    """
    Экспортирует DoclingDocument в Markdown с сохранением структуры.

    Args:
        document: ConversionResult объект от Docling (имеет поле document с DoclingDocument) 
                  или словарь с данными документа
        output_path: Путь для сохранения Markdown
        include_metadata: Включать ли метаданные в начало файла
        metadata: Дополнительные метаданные

    Returns:
        Путь к сохраненному файлу
    """
    try:
        # Получаем DoclingDocument
        doc_obj = None
        
        # 1. Попытка извлечь из ConversionResult (object)
        if hasattr(document, "document"):
            doc_obj = document.document
        
        # 2. Попытка использования самого document, если это уже DoclingDocument
        elif hasattr(document, "export_to_markdown"):
             doc_obj = document

        # 3. Если это словарь (например, из JSON), нужно восстановить объект
        elif isinstance(document, dict):
            # Если словарь содержит ключ "document", берем его
            doc_data = document.get("document", document)
            
            if DoclingDocument:
                try:
                    doc_obj = DoclingDocument.model_validate(doc_data)
                except Exception as e:
                    logger.warning(f"Failed to validate DoclingDocument from dict: {e}")
                    # Fallback mechanism if validation fails (unlikely if data is correct)

        if not doc_obj:
            logger.warning("Could not resolve DoclingDocument object. Export may fail or be empty.")
            markdown_content = "<!-- Failed to resolve document structure -->"
        else:
            # Используем встроенный метод экспорта
            if hasattr(doc_obj, "export_to_markdown"):
                markdown_content = doc_obj.export_to_markdown()
            else:
                 logger.warning("DoclingDocument object does not have export_to_markdown method.")
                 markdown_content = "<!-- DoclingDocument.export_to_markdown not found -->"

        # Формируем итоговый контент
        final_lines = []
        
        # Метаданные в начале (опционально)
        if include_metadata:
            final_lines.append("---")
            final_lines.append(f"exported_at: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
            final_lines.append("export_format: markdown")
            if metadata:
                for key, value in metadata.items():
                    final_lines.append(f"{key}: {value}")
            final_lines.append("---")
            final_lines.append("")

        final_lines.append(markdown_content)

        # Создаем директорию если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем Markdown
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(final_lines))

        logger.info(f"Exported document to Markdown: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to export to Markdown: {e}", exc_info=True)
        raise
