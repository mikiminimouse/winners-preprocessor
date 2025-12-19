#!/usr/bin/env python3
"""
Тест Docling VLM Pipeline (локальное использование Granite-Docling)
На основе документации: https://huggingface.co/ibm-granite/granite-docling-258M
"""
import sys
from pathlib import Path

print("="*70)
print("ТЕСТ DOCLING VLM PIPELINE (Granite-Docling)")
print("="*70)
print()

# Проверка установки Docling
try:
    from docling.datamodel import vlm_model_specs
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.vlm_pipeline import VlmPipeline
    print("✅ Docling импортирован успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта Docling: {e}")
    print("\n📦 Установите Docling:")
    print("   pip install docling docling-ibm-models")
    sys.exit(1)

# Выбираем тестовый файл
test_pdf = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf/UNIT_0052e4b00a764956/files/Протокол - световое оборудование.pdf")

if not test_pdf.exists():
    print(f"❌ Файл не найден: {test_pdf}")
    sys.exit(1)

print(f"📄 Тестовый файл: {test_pdf.name}")
print(f"   Размер: {test_pdf.stat().st_size // 1024} KB")
print()

# ВАРИАНТ 1: Использование значений по умолчанию
print("="*70)
print("ВАРИАНТ 1: Default Granite-Docling (transformers)")
print("="*70)
print()

try:
    print("🔧 Создание конвертера...")
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=VlmPipeline,
            ),
        }
    )
    print("✅ Конвертер создан")
    
    print(f"🚀 Конвертация файла: {test_pdf.name}")
    print("   ⏳ Это может занять 1-2 минуты...")
    
    result = converter.convert(source=str(test_pdf))
    doc = result.document
    
    print("✅ Конвертация завершена")
    print(f"   Страниц: {len(doc.pages)}")
    
    # Экспорт в Markdown
    markdown = doc.export_to_markdown()
    
    print(f"📝 Markdown сгенерирован: {len(markdown)} символов")
    
    # Сохранение результата
    output_dir = Path("/root/winners_preprocessor/output_docling_vlm_test")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"{test_pdf.stem}_default.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {test_pdf.name}\n\n")
        f.write(f"**Метод:** Default Granite-Docling (transformers)\n")
        f.write(f"**Страниц:** {len(doc.pages)}\n")
        f.write(f"**Размер Markdown:** {len(markdown)} символов\n\n")
        f.write("---\n\n")
        f.write(markdown)
    
    print(f"💾 Результат сохранен: {output_file}")
    
    # Показываем превью
    print("\n📋 ПРЕВЬЮ (первые 500 символов):")
    print("-" * 70)
    print(markdown[:500])
    print("-" * 70)
    
    # Проверяем на повторяющийся контент
    if "Внимательно изучение" in markdown:
        print("\n⚠️  ВНИМАНИЕ: Обнаружена проблемная фраза!")
    else:
        print("\n✅ Текст выглядит нормально (нет зацикливания)")
    
    print("\n✅ ВАРИАНТ 1 ЗАВЕРШЕН УСПЕШНО")
    
except Exception as e:
    print(f"\n❌ ОШИБКА при обработке: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("ТЕСТ ЗАВЕРШЕН")
print("="*70)


