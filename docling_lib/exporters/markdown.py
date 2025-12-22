"""
Markdown экспорт DoclingDocument.
"""
import logging
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def export_to_markdown(
    document: Any,
    output_path: Path,
    include_metadata: bool = True,
    metadata: Optional[dict] = None,
) -> Path:
    """
    Экспортирует DoclingDocument в Markdown.

    Args:
        document: Document объект от Docling
        output_path: Путь для сохранения Markdown
        include_metadata: Включать ли метаданные в начало файла
        metadata: Дополнительные метаданные

    Returns:
        Путь к сохраненному файлу
    """
    try:
        markdown_lines = []

        # Метаданные в начале (опционально)
        if include_metadata:
            markdown_lines.append("---")
            markdown_lines.append(f"exported_at: {datetime.utcnow().isoformat()}Z")
            markdown_lines.append("export_format: markdown")
            if metadata:
                for key, value in metadata.items():
                    markdown_lines.append(f"{key}: {value}")
            markdown_lines.append("---")
            markdown_lines.append("")

        # Извлекаем текст из документа
        # Docling Document имеет структуру с текстом, таблицами и т.д.
        if hasattr(document, "text"):
            # Простой текст
            markdown_lines.append(document.text)
        elif hasattr(document, "document"):
            # Вложенная структура
            doc_content = document.document
            if hasattr(doc_content, "text"):
                markdown_lines.append(doc_content.text)
        elif hasattr(document, "pages"):
            # Документ со страницами
            for page in document.pages:
                if hasattr(page, "text"):
                    markdown_lines.append(page.text)
                    markdown_lines.append("")
        elif hasattr(document, "model_dump"):
            # Пытаемся извлечь текст из структуры
            doc_dict = document.model_dump()
            text_content = _extract_text_from_dict(doc_dict)
            if text_content:
                markdown_lines.append(text_content)

        # Таблицы (если есть)
        if hasattr(document, "tables"):
            markdown_lines.append("\n## Таблицы\n")
            for i, table in enumerate(document.tables, 1):
                markdown_lines.append(f"\n### Таблица {i}\n")
                table_md = _table_to_markdown(table)
                markdown_lines.append(table_md)
                markdown_lines.append("")

        # Создаем директорию если нужно
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Сохраняем Markdown
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(markdown_lines))

        logger.info(f"Exported document to Markdown: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"Failed to export to Markdown: {e}", exc_info=True)
        raise


def _extract_text_from_dict(doc_dict: dict) -> str:
    """Рекурсивно извлекает текст из словаря."""
    text_parts = []

    if isinstance(doc_dict, dict):
        for key, value in doc_dict.items():
            if key in ["text", "content", "body"]:
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, list):
                    text_parts.extend([str(v) for v in value if isinstance(v, str)])
            elif isinstance(value, (dict, list)):
                nested_text = _extract_text_from_dict(value)
                if nested_text:
                    text_parts.append(nested_text)
    elif isinstance(doc_dict, list):
        for item in doc_dict:
            nested_text = _extract_text_from_dict(item)
            if nested_text:
                text_parts.append(nested_text)

    return "\n".join(text_parts)


def _table_to_markdown(table: Any) -> str:
    """Конвертирует таблицу в Markdown формат."""
    try:
        if hasattr(table, "to_markdown"):
            return table.to_markdown()
        elif hasattr(table, "rows"):
            # Простая таблица с rows
            rows = table.rows
            if not rows:
                return ""

            md_lines = []
            # Заголовок (первая строка)
            if rows:
                header = "| " + " | ".join(str(cell) for cell in rows[0]) + " |"
                md_lines.append(header)
                md_lines.append("| " + " | ".join(["---"] * len(rows[0])) + " |")

                # Данные
                for row in rows[1:]:
                    md_lines.append("| " + " | ".join(str(cell) for cell in row) + " |")

            return "\n".join(md_lines)
        else:
            return str(table)
    except Exception as e:
        logger.warning(f"Failed to convert table to markdown: {e}")
        return str(table)

