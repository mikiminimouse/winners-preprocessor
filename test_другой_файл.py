#!/usr/bin/env python3
"""
Быстрый тест на ДРУГОМ PDF файле
"""

import sys
from pathlib import Path

sys.path.insert(0, '/root/winners_preprocessor')

from granite_docling_extractor import GraniteDoclingExtractor

def main():
    print("="*70)
    print("ТЕСТ НА ДРУГОМ PDF ФАЙЛЕ")
    print("="*70)
    print()
    
    # Путь к тестовым файлам
    input_dir = Path("/root/winners_preprocessor/pilot_winers223/data/pending/direct/pdf")
    
    # Собираем все PDF файлы
    all_pdfs = []
    for unit_dir in input_dir.iterdir():
        if unit_dir.is_dir() and unit_dir.name.startswith("UNIT_"):
            files_dir = unit_dir / "files"
            if files_dir.exists():
                pdf_files = list(files_dir.glob("*.pdf"))
                all_pdfs.extend(pdf_files)
    
    if len(all_pdfs) < 2:
        print("Недостаточно файлов для теста")
        return
    
    # Выбираем ВТОРОЙ файл (первый был проблемный)
    test_file = all_pdfs[1]
    
    print(f"📁 Найдено всего PDF: {len(all_pdfs)}")
    print(f"🎯 Тестируем файл: {test_file.name}")
    print(f"   Размер: {test_file.stat().st_size // 1024} KB")
    print()
    
    # Создаем экстрактор
    extractor = GraniteDoclingExtractor(
        output_dir="/root/winners_preprocessor/output_test2_granite"
    )
    
    # Проверяем готовность сервера
    if not extractor.wait_for_server(max_wait=120):
        print("❌ Сервер недоступен")
        return
    
    # Обрабатываем только первые 2 страницы
    result = extractor.process_pdf(test_file, max_pages=2)
    extractor.save_result(result, test_file)
    
    # Показываем результаты
    print("\n" + "="*70)
    print("РЕЗУЛЬТАТЫ")
    print("="*70)
    
    if result["success"]:
        print(f"✅ Успех!")
        print(f"   Текста: {len(result['combined_text'])} символов")
        print(f"   Таблиц: {len(result['all_tables'])}")
        print(f"   Метаданных: {len(result['metadata'])} полей")
        
        # Показываем первые 500 символов текста
        if result['combined_text']:
            print(f"\nПервые 500 символов:")
            print("-" * 70)
            print(result['combined_text'][:500])
            print("-" * 70)
        
        # Показываем метаданные
        metadata = result['metadata']
        print(f"\nМетаданные (основные):")
        print(f"  • номер_процедуры: {metadata.get('номер_процедуры', 'N/A')}")
        print(f"  • победитель: {metadata.get('победитель', 'N/A')[:50] if metadata.get('победитель') else 'N/A'}...")
        print(f"  • ИНН: {metadata.get('ИНН', 'N/A')}")
        print(f"  • цена: {metadata.get('цена_победителя', 'N/A')} {metadata.get('валюта', '')}")
    else:
        print(f"❌ Ошибка: {result.get('error', 'Unknown')}")

if __name__ == "__main__":
    main()

