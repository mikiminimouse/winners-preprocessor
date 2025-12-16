#!/usr/bin/env python3
import json
import sys
import requests

# Получаем метрики
response = requests.get("http://localhost:8080/metrics/processing")
if response.status_code != 200:
    print(f"Error: {response.status_code}")
    sys.exit(1)

d = response.json()

print("=" * 80)
print("ОТЧЕТ ОБ ОБРАБОТКЕ ДОКУМЕНТОВ")
print("=" * 80)
print(f"\nSession ID: {d['session_id']}")
print(f"Время начала: {d['started_at']}")
print(f"Время завершения: {d['completed_at']}")

print("\n" + "=" * 80)
print("СВОДКА")
print("=" * 80)
s = d['summary']
print(f"Всего входных файлов: {s['total_input_files']}")
print(f"Всего архивов обнаружено: {s['total_archives']}")
print(f"Всего извлечено файлов из архивов: {s['total_extracted']}")
print(f"Всего создано unit'ов: {s['total_units']}")
print(f"Всего ошибок: {s['total_errors']}")

print("\n" + "=" * 80)
print("РАСПРЕДЕЛЕНИЕ ПО РАСШИРЕНИЯМ")
print("=" * 80)
for ext, count in sorted(s['by_extension'].items()):
    print(f"  {ext:15} : {count:3} файлов")

print("\n" + "=" * 80)
print("РАСПРЕДЕЛЕНИЕ ПО ОПРЕДЕЛЕННЫМ ТИПАМ")
print("=" * 80)
for ftype, count in sorted(s['by_detected_type'].items()):
    print(f"  {ftype:20} : {count:3} файлов")

print("\n" + "=" * 80)
print("СТАТИСТИКА ПО PDF")
print("=" * 80)
pdf_stats = s.get('pdf_statistics', {})
if pdf_stats:
    print(f"Всего PDF файлов: {pdf_stats.get('total_pdf', 0)}")
    print(f"  - С текстовым слоем (не требуют OCR): {pdf_stats.get('pdf_with_text_layer', 0)}")
    print(f"  - Требуют OCR: {pdf_stats.get('pdf_requires_ocr', 0)}")
    if pdf_stats.get('total_pdf', 0) > 0:
        ocr_percent = (pdf_stats.get('pdf_requires_ocr', 0) / pdf_stats.get('total_pdf', 1)) * 100
        text_percent = (pdf_stats.get('pdf_with_text_layer', 0) / pdf_stats.get('total_pdf', 1)) * 100
        print(f"  - Процент требующих OCR: {ocr_percent:.1f}%")
        print(f"  - Процент с текстовым слоем: {text_percent:.1f}%")
else:
    print("Статистика по PDF недоступна")

print("\n" + "=" * 80)
print("АНАЛИЗ АРХИВОВ")
print("=" * 80)
archives = d.get('archives_extracted', [])
print(f"Всего архивов обработано: {len(archives)}")
for i, a in enumerate(archives, 1):
    print(f"\n{i}. Файл: {a['original_file']}")
    print(f"   Archive ID: {a['archive_id']}")
    print(f"   Извлечено файлов: {a['extracted_count']}")
    print(f"   Успешно: {a['success']}")
    if not a['success']:
        print(f"   ⚠️  Архив не распакован")
    else:
        # Детальная информация о файлах в архиве
        files_by_ext = a.get('files_by_extension', {})
        files_by_type = a.get('files_by_type', {})
        pipeline_info = a.get('pipeline_info', {})
        
        if files_by_ext:
            print(f"\n   📁 Файлы по расширениям:")
            for ext, count in sorted(files_by_ext.items()):
                print(f"      {ext:15} : {count:3} файлов")
        
        if files_by_type:
            print(f"\n   📋 Файлы по типам:")
            for ftype, count in sorted(files_by_type.items()):
                print(f"      {ftype:20} : {count:3} файлов")
        
        if pipeline_info:
            print(f"\n   🔄 Pipeline обработки:")
            for ftype, info in sorted(pipeline_info.items()):
                route = info.get('route', 'unknown')
                needs_ocr = info.get('needs_ocr', 0)
                requires_conv = info.get('requires_conversion', 0)
                count = info.get('count', 0)
                print(f"      {ftype:20} ({count} файлов):")
                print(f"         Route: {route}")
                if needs_ocr > 0:
                    print(f"         Требуют OCR: {needs_ocr}")
                if requires_conv > 0:
                    print(f"         Требуют конвертации: {requires_conv}")
        
        # Детальный список файлов
        extracted_details = a.get('extracted_files_details', [])
        if extracted_details:
            print(f"\n   📄 Детальный список файлов в архиве:")
            for idx, file_detail in enumerate(extracted_details[:20], 1):  # Показываем первые 20
                name = file_detail.get('original_name', 'unknown')
                ftype = file_detail.get('detected_type', 'unknown')
                needs_ocr = file_detail.get('needs_ocr', False)
                size = file_detail.get('size', 0)
                size_mb = size / (1024 * 1024)
                ocr_status = "требует OCR" if needs_ocr else "текстовый слой"
                print(f"      {idx:2}. {name[:50]:50} | {ftype:15} | {size_mb:6.2f} MB | {ocr_status}")
            if len(extracted_details) > 20:
                print(f"      ... и еще {len(extracted_details) - 20} файлов")

print("\n" + "=" * 80)
print("АНАЛИЗ ОШИБОК")
print("=" * 80)
errors = d.get('errors', [])
print(f"Всего ошибок: {len(errors)}")

# Группируем по этапам
by_stage = {}
for e in errors:
    stage = e['stage']
    if stage not in by_stage:
        by_stage[stage] = []
    by_stage[stage].append(e)

print("\nОшибки по этапам:")
for stage, errs in sorted(by_stage.items()):
    print(f"  {stage}: {len(errs)} ошибок")

print("\nДетали ошибок (первые 15):")
for i, e in enumerate(errors[:15], 1):
    filename = e['file'].split('/')[-1] if '/' in e['file'] else e['file']
    print(f"\n{i}. Файл: {filename}")
    print(f"   Этап: {e['stage']}")
    error_msg = e['error'][:200] + "..." if len(e['error']) > 200 else e['error']
    print(f"   Ошибка: {error_msg}")

print("\n" + "=" * 80)
print("АНАЛИЗ ПРОБЛЕМНЫХ .DOC ФАЙЛОВ")
print("=" * 80)
doc_errors = [e for e in errors if '.doc' in e['file'] and e['stage'] == 'extraction']
print(f"Найдено {len(doc_errors)} ошибок распаковки .doc файлов:\n")
for i, e in enumerate(doc_errors, 1):
    filename = e['file'].split('/')[-1] if '/' in e['file'] else e['file']
    print(f"{i}. {filename}")
    error_msg = e['error'][:300] + "..." if len(e['error']) > 300 else e['error']
    print(f"   Причина: {error_msg}")
    if 'details' in e and e['details']:
        try:
            details = json.loads(e['details']) if isinstance(e['details'], str) else e['details']
            if 'extraction_errors' in details:
                for err_detail in details['extraction_errors']:
                    if 'reason' in err_detail:
                        print(f"   Детали: {err_detail['reason']}")
        except:
            pass
    print()

print("=" * 80)
print("КОНВЕРТАЦИИ")
print("=" * 80)
conversions = d.get('conversions', [])
print(f"Всего конвертаций: {len(conversions)}")
for i, c in enumerate(conversions, 1):
    print(f"{i}. {c['original']} -> {c['converted_to']} (успешно: {c['success']})")

print("\n" + "=" * 80)
print("ВЫВОДЫ")
print("=" * 80)
print(f"✓ Обработано файлов: {s['total_input_files']}")
print(f"✓ Создано unit'ов: {s['total_units']}")
print(f"✓ Успешность: {s['total_units'] / s['total_input_files'] * 100:.1f}%")
print(f"⚠ Ошибок: {s['total_errors']}")
print(f"⚠ Процент ошибок: {s['total_errors'] / s['total_input_files'] * 100:.1f}%")
if s['total_archives'] > 0:
    print(f"📦 Архивов обнаружено: {s['total_archives']}")
    print(f"📦 Файлов извлечено: {s['total_extracted']}")

