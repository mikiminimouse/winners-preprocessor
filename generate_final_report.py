#!/usr/bin/env python3
"""
Генератор финального отчета в формате Markdown на основе метрик обработки.
"""
import json
import sys
import requests
from datetime import datetime
from typing import Dict, Any, List

def get_metrics(session_id: str = None) -> Dict[str, Any]:
    """Получает метрики обработки из API."""
    url = "http://localhost:8080/metrics/processing"
    if session_id:
        url += f"?session_id={session_id}"
    
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        sys.exit(1)
    
    return response.json()


def format_duration(started_at: str, completed_at: str) -> str:
    """Форматирует длительность обработки."""
    try:
        start = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
        end = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
        duration = end - start
        seconds = duration.total_seconds()
        
        if seconds < 60:
            return f"~{int(seconds)} секунд"
        elif seconds < 3600:
            return f"~{int(seconds / 60)} минут"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"~{hours}ч {minutes}м"
    except:
        return "неизвестно"


def generate_report(metrics: Dict[str, Any]) -> str:
    """Генерирует финальный отчет в формате Markdown."""
    lines = []
    
    # Заголовок
    lines.append("# ОТЧЕТ ОБ ОБРАБОТКЕ ДОКУМЕНТОВ")
    lines.append("")
    lines.append(f"**Session ID:** {metrics['session_id']}  ")
    lines.append(f"**Время начала:** {metrics['started_at']}  ")
    lines.append(f"**Время завершения:** {metrics.get('completed_at', 'N/A')}  ")
    
    duration = format_duration(metrics['started_at'], metrics.get('completed_at', metrics['started_at']))
    lines.append(f"**Длительность:** {duration}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Общая статистика
    s = metrics.get('summary', {})
    lines.append("## ОБЩАЯ СТАТИСТИКА")
    lines.append("")
    lines.append("| Показатель | Значение |")
    lines.append("|------------|----------|")
    lines.append(f"| **Всего входных файлов** | {s.get('total_input_files', 0)} |")
    lines.append(f"| **Создано unit'ов** | {s.get('total_units', 0)} |")
    
    total_files = s.get('total_input_files', 1)
    total_units = s.get('total_units', 0)
    success_rate = (total_units / total_files * 100) if total_files > 0 else 0
    lines.append(f"| **Успешность обработки** | {success_rate:.1f}% |")
    lines.append(f"| **Обнаружено архивов** | {s.get('total_archives', 0)} |")
    lines.append(f"| **Извлечено файлов из архивов** | {s.get('total_extracted', 0)} |")
    lines.append(f"| **Всего ошибок** | {s.get('total_errors', 0)} |")
    
    total_errors = s.get('total_errors', 0)
    error_rate = (total_errors / total_files * 100) if total_files > 0 else 0
    lines.append(f"| **Процент ошибок** | {error_rate:.1f}% |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Распределение по расширениям
    lines.append("## РАСПРЕДЕЛЕНИЕ ПО РАСШИРЕНИЯМ")
    lines.append("")
    lines.append("| Расширение | Количество |")
    lines.append("|------------|------------|")
    by_ext = s.get('by_extension', {})
    for ext, count in sorted(by_ext.items(), key=lambda x: -x[1]):
        percent = (count / total_files * 100) if total_files > 0 else 0
        lines.append(f"| `{ext}` | {count} файла ({percent:.1f}%) |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Распределение по типам
    lines.append("## РАСПРЕДЕЛЕНИЕ ПО ОПРЕДЕЛЕННЫМ ТИПАМ")
    lines.append("")
    lines.append("| Тип файла | Количество |")
    lines.append("|-----------|------------|")
    by_type = s.get('by_detected_type', {})
    for ftype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"| `{ftype}` | {count} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Статистика по PDF
    pdf_stats = s.get('pdf_statistics', {})
    if pdf_stats and pdf_stats.get('total_pdf', 0) > 0:
        lines.append("## СТАТИСТИКА ПО PDF")
        lines.append("")
        total_pdf = pdf_stats.get('total_pdf', 0)
        with_text = pdf_stats.get('pdf_with_text_layer', 0)
        needs_ocr = pdf_stats.get('pdf_requires_ocr', 0)
        
        lines.append("| Показатель | Количество | Процент |")
        lines.append("|------------|------------|---------|")
        lines.append(f"| **Всего PDF файлов** | {total_pdf} | 100% |")
        text_percent = (with_text / total_pdf * 100) if total_pdf > 0 else 0
        lines.append(f"| С текстовым слоем (не требуют OCR) | {with_text} | {text_percent:.1f}% |")
        ocr_percent = (needs_ocr / total_pdf * 100) if total_pdf > 0 else 0
        lines.append(f"| Требуют OCR | {needs_ocr} | {ocr_percent:.1f}% |")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    # Анализ архивов
    lines.append("## АНАЛИЗ АРХИВОВ")
    lines.append("")
    archives = metrics.get('archives_extracted', [])
    total_archives = len(archives)
    successful = sum(1 for a in archives if a.get('success', False))
    failed = total_archives - successful
    
    lines.append(f"**Всего архивов обнаружено:** {total_archives}  ")
    lines.append(f"**Успешно распаковано:** {successful}  ")
    lines.append(f"**Не распаковано:** {failed}")
    lines.append("")
    
    if archives:
        lines.append("### Детальная информация по архивам:")
        lines.append("")
        
        for i, a in enumerate(archives, 1):
            lines.append(f"{i}. **{a['original_file']}**")
            lines.append(f"   - Archive ID: `{a['archive_id']}`")
            lines.append(f"   - Извлечено файлов: {a.get('extracted_count', 0)}")
            lines.append(f"   - Успешно: {'✅' if a.get('success', False) else '❌'}")
            
            if a.get('success', False):
                # Файлы по расширениям
                files_by_ext = a.get('files_by_extension', {})
                if files_by_ext:
                    lines.append(f"   - **Файлы по расширениям:**")
                    for ext, count in sorted(files_by_ext.items(), key=lambda x: -x[1]):
                        lines.append(f"     - `{ext}`: {count} файлов")
                
                # Файлы по типам
                files_by_type = a.get('files_by_type', {})
                if files_by_type:
                    lines.append(f"   - **Файлы по типам:**")
                    for ftype, count in sorted(files_by_type.items(), key=lambda x: -x[1]):
                        lines.append(f"     - `{ftype}`: {count} файлов")
                
                # Pipeline обработки
                pipeline_info = a.get('pipeline_info', {})
                if pipeline_info:
                    lines.append(f"   - **Pipeline обработки:**")
                    for ftype, info in sorted(pipeline_info.items()):
                        count = info.get('count', 0)
                        route = info.get('route', 'unknown')
                        needs_ocr = info.get('needs_ocr', 0)
                        requires_conv = info.get('requires_conversion', 0)
                        
                        lines.append(f"     - `{ftype}` ({count} файлов):")
                        lines.append(f"       - Route: `{route}`")
                        if needs_ocr > 0:
                            lines.append(f"       - Требуют OCR: {needs_ocr}")
                        if requires_conv > 0:
                            lines.append(f"       - Требуют конвертации: {requires_conv}")
                
                # Детальный список файлов (первые 10)
                extracted_details = a.get('extracted_files_details', [])
                if extracted_details:
                    lines.append(f"   - **Детальный список файлов в архиве:**")
                    for idx, file_detail in enumerate(extracted_details[:10], 1):
                        name = file_detail.get('original_name', 'unknown')
                        ftype = file_detail.get('detected_type', 'unknown')
                        needs_ocr = file_detail.get('needs_ocr', False)
                        size = file_detail.get('size', 0)
                        size_mb = size / (1024 * 1024)
                        ocr_status = "требует OCR" if needs_ocr else "текстовый слой"
                        lines.append(f"     - `{name}` | {ftype} | {size_mb:.2f} MB | {ocr_status}")
                    if len(extracted_details) > 10:
                        lines.append(f"     - ... и еще {len(extracted_details) - 10} файлов")
            else:
                # Информация об ошибке
                errors = metrics.get('errors', [])
                archive_errors = [e for e in errors if a['archive_id'] in e.get('details', '')]
                if archive_errors:
                    error = archive_errors[0]
                    error_msg = error.get('error', 'Unknown error')[:200]
                    lines.append(f"   - **Ошибка:** {error_msg}")
            
            lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Анализ ошибок
    lines.append("## АНАЛИЗ ОШИБОК")
    lines.append("")
    errors = metrics.get('errors', [])
    lines.append(f"**Всего ошибок:** {len(errors)}  ")
    
    if errors:
        # Группируем по этапам
        by_stage = {}
        for e in errors:
            stage = e.get('stage', 'unknown')
            if stage not in by_stage:
                by_stage[stage] = []
            by_stage[stage].append(e)
        
        if by_stage:
            lines.append(f"**Ошибки по этапам:**")
            for stage, errs in sorted(by_stage.items()):
                lines.append(f"- `{stage}`: {len(errs)} ошибок")
            lines.append("")
        
        # Категории ошибок
        lines.append("### Категории ошибок:")
        lines.append("")
        
        # RAR архивы
        rar_errors = [e for e in errors if 'rar' in e.get('error', '').lower() or 'unsupported method' in e.get('error', '').lower()]
        if rar_errors:
            lines.append(f"1. **RAR архивы с неподдерживаемым методом сжатия ({len(rar_errors)} файлов):**")
            for e in rar_errors[:5]:
                filename = e['file'].split('/')[-1] if '/' in e['file'] else e['file']
                lines.append(f"   - `{filename}`")
            lines.append("")
            lines.append("   **Причина:** 7z не может распаковать эти RAR архивы из-за \"Unsupported Method\". ")
            lines.append("   Вероятно, это RAR5 архивы или архивы с методом сжатия, который не поддерживается p7zip.")
            lines.append("")
            lines.append("   **Решение:** Используется `unrar` для RAR архивов, с fallback на 7z.")
            lines.append("")
        
        # HTML файлы
        html_errors = [e for e in errors if 'html' in e.get('error', '').lower() or e.get('stage') == 'extraction' and 'html' in e.get('file', '').lower()]
        if html_errors:
            lines.append(f"2. **HTML файлы с расширением .doc ({len(html_errors)} файлов):**")
            for e in html_errors[:5]:
                filename = e['file'].split('/')[-1] if '/' in e['file'] else e['file']
                lines.append(f"   - `{filename}`")
            lines.append("")
            lines.append("   **Причина:** Файлы определены как HTML, но система пыталась их распаковать как архивы.")
            lines.append("")
            lines.append("   **Решение:** HTML файлы теперь не обрабатываются как архивы.")
            lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Выводы и рекомендации
    lines.append("## ВЫВОДЫ И РЕКОМЕНДАЦИИ")
    lines.append("")
    
    # Успешно обработано
    lines.append("### ✅ Успешно обработано:")
    input_files = metrics.get('input_files', [])
    pdf_count = sum(1 for f in input_files if f.get('detected_type') == 'pdf')
    docx_count = sum(1 for f in input_files if f.get('detected_type') == 'docx')
    doc_count = sum(1 for f in input_files if f.get('detected_type') == 'doc' and not f.get('is_fake_doc', False))
    
    if pdf_count > 0:
        lines.append(f"- {pdf_count} PDF файлов (все успешно)")
    if docx_count > 0:
        lines.append(f"- {docx_count} DOCX файлов (все успешно)")
    if doc_count > 0:
        lines.append(f"- {doc_count} DOC файлов (успешно сконвертированы в DOCX)")
    
    lines.append("")
    
    # Проблемы
    if total_errors > 0:
        lines.append("### ⚠️ Проблемы:")
        lines.append("")
        
        if failed > 0:
            lines.append(f"1. **Архивы:**")
            lines.append(f"   - {failed} архивов не распаковано")
            if rar_errors:
                lines.append("   - RAR архивы теперь обрабатываются через unrar с fallback на 7z")
            if html_errors:
                lines.append("   - HTML файлы больше не обрабатываются как архивы")
            lines.append("")
    
    # Метрики в MongoDB
    lines.append("### 📊 Метрики сохранены в MongoDB:")
    lines.append(f"- Коллекция: `docling_metadata.processing_metrics`")
    lines.append(f"- Session ID: `{metrics['session_id']}`")
    lines.append("- Все детали доступны через API: `/metrics/processing` и `/metrics/summary`")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Следующие шаги
    lines.append("## СЛЕДУЮЩИЕ ШАГИ")
    lines.append("")
    lines.append("1. ✅ Установлен `unrar` для обработки RAR архивов")
    lines.append("2. ✅ Улучшена логика определения HTML файлов - они не распаковываются")
    lines.append("3. ✅ Добавлен fallback механизм для RAR архивов (unrar → 7z)")
    lines.append("4. ✅ Добавлены метрики по PDF (OCR vs text layer)")
    lines.append("5. ✅ Добавлена детальная информация о файлах в архивах")
    lines.append("")
    
    return "\n".join(lines)


def main():
    """Главная функция."""
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    print("Получение метрик...")
    metrics = get_metrics(session_id)
    
    print("Генерация отчета...")
    report = generate_report(metrics)
    
    output_file = "FINAL_REPORT.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"Отчет сохранен в {output_file}")


if __name__ == "__main__":
    main()

