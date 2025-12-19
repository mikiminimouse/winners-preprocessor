#!/usr/bin/env python3
"""
Анализ работы Docling pipeline для OCR, извлечения текста, разметки и таблиц.
Проверяет почему данные не извлекаются из PDF и JPEG файлов.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

def analyze_output_file(json_path: Path) -> Dict[str, Any]:
    """Анализирует output JSON файл."""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        analysis = {
            "file": json_path.name,
            "route": data.get("route", "unknown"),
            "method": data.get("processing_method", "unknown"),
            "text_length": len(data.get("text", "")),
            "text_extracted": len(data.get("text", "")) > 0,
            "tables_count": len(data.get("tables", [])) if isinstance(data.get("tables"), list) else 0,
            "layout_detected": bool(data.get("layout")),
            "has_ocr": "ocr" in data.get("processing_method", "").lower(),
            "metrics": data.get("metrics", {}),
            "issues": []
        }
        
        # Проверка проблем
        if analysis["route"] == "pdf_scan" and not analysis["text_extracted"]:
            analysis["issues"].append("PDF требует OCR, но текст не извлечен")
        
        if analysis["route"] == "pdf_scan" and not analysis["has_ocr"]:
            analysis["issues"].append("PDF требует OCR, но OCR не использован")
        
        if analysis["method"] == "pdfplumber_fallback" and analysis["route"] == "pdf_scan":
            analysis["issues"].append("Используется fallback вместо Docling OCR")
        
        if analysis["tables_count"] == 0 and analysis["route"] in ["pdf_text", "pdf_scan"]:
            analysis["issues"].append("Таблицы не найдены (возможно, есть в документе)")
        
        return analysis
    except Exception as e:
        return {
            "file": json_path.name,
            "error": str(e),
            "issues": [f"Ошибка чтения файла: {e}"]
        }

def main():
    print("=" * 70)
    print("АНАЛИЗ РАБОТЫ DOCLING PIPELINE")
    print("=" * 70)
    print()
    
    # Находим все output JSON файлы
    output_dirs = list(Path("output").glob("UNIT_*"))
    
    print(f"Найдено обработанных файлов: {len(output_dirs)}")
    print()
    
    analyses = []
    
    # Анализируем каждый файл
    for output_dir in output_dirs:
        json_files = list(output_dir.glob("*.json"))
        if json_files:
            analysis = analyze_output_file(json_files[0])
            analyses.append(analysis)
    
    # Группируем по route
    by_route = {}
    for analysis in analyses:
        route = analysis.get("route", "unknown")
        if route not in by_route:
            by_route[route] = []
        by_route[route].append(analysis)
    
    print("СТАТИСТИКА ПО ROUTE:")
    print("-" * 70)
    
    for route, files in sorted(by_route.items(), key=lambda x: str(x[0] or "")):
        route_str = str(route or "unknown")
        total = len(files)
        with_text = sum(1 for f in files if f.get("text_extracted", False))
        with_tables = sum(1 for f in files if f.get("tables_count", 0) > 0)
        with_layout = sum(1 for f in files if f.get("layout_detected", False))
        with_ocr = sum(1 for f in files if f.get("has_ocr", False))
        with_issues = sum(1 for f in files if f.get("issues"))
        
        print(f"{route_str:15} Всего: {total:3} | Текст: {with_text:3} | Таблицы: {with_tables:3} | "
              f"Разметка: {with_layout:3} | OCR: {with_ocr:3} | Проблемы: {with_issues:3}")
    
    print()
    print("=" * 70)
    print("ПРОБЛЕМЫ И РЕКОМЕНДАЦИИ")
    print("=" * 70)
    print()
    
    # Анализ проблем
    pdf_scan_issues = [a for a in analyses if a.get("route") == "pdf_scan" and a.get("issues")]
    pdf_text_issues = [a for a in analyses if a.get("route") == "pdf_text" and a.get("issues")]
    
    if pdf_scan_issues:
        print(f"⚠️  PDF_SCAN файлы с проблемами: {len(pdf_scan_issues)}")
        for analysis in pdf_scan_issues[:5]:
            print(f"  - {analysis['file']}: {', '.join(analysis['issues'])}")
            print(f"    Method: {analysis.get('method')}, Text: {analysis.get('text_length')} символов")
        print()
    
    if pdf_text_issues:
        print(f"⚠️  PDF_TEXT файлы с проблемами: {len(pdf_text_issues)}")
        for analysis in pdf_text_issues[:3]:
            print(f"  - {analysis['file']}: {', '.join(analysis['issues'])}")
        print()
    
    # Проверка Docling
    print("ПРОВЕРКА DOCLING:")
    print("-" * 70)
    
    try:
        from docling.document_converter import DocumentConverter
        print("✓ Docling установлен")
    except ImportError:
        print("✗ Docling НЕ установлен - используется fallback!")
        print("  Рекомендация: установить docling-core")
        print("    pip install docling-core")
    
    # Проверка методов обработки
    methods_used = {}
    for analysis in analyses:
        method = analysis.get("method", "unknown")
        methods_used[method] = methods_used.get(method, 0) + 1
    
    print()
    print("ИСПОЛЬЗУЕМЫЕ МЕТОДЫ:")
    for method, count in sorted(methods_used.items(), key=lambda x: -x[1]):
        print(f"  {method:30} : {count:3} файлов")
    
    print()
    print("=" * 70)
    print("ВЫВОДЫ")
    print("=" * 70)
    print()
    
    # Основные выводы
    docling_used = sum(1 for a in analyses if "docling" in a.get("method", "").lower())
    fallback_used = sum(1 for a in analyses if "fallback" in a.get("method", "").lower())
    
    print(f"1. Docling используется: {docling_used}/{len(analyses)} файлов")
    print(f"2. Fallback используется: {fallback_used}/{len(analyses)} файлов")
    print()
    
    if fallback_used > docling_used:
        print("⚠️  ПРОБЛЕМА: Fallback используется чаще, чем Docling!")
        print("   Это означает, что Docling не установлен или не работает.")
        print()
    
    pdf_scan_no_text = sum(1 for a in analyses 
                          if a.get("route") == "pdf_scan" and not a.get("text_extracted"))
    
    if pdf_scan_no_text > 0:
        print(f"⚠️  ПРОБЛЕМА: {pdf_scan_no_text} PDF_SCAN файлов без извлеченного текста!")
        print("   OCR не работает для сканированных PDF.")
        print()
    
    # Сохраняем отчет
    report = {
        "total_files": len(analyses),
        "by_route": {route: len(files) for route, files in by_route.items()},
        "methods_used": methods_used,
        "issues": {
            "pdf_scan_no_text": pdf_scan_no_text,
            "fallback_used": fallback_used,
            "docling_used": docling_used
        },
        "analyses": analyses
    }
    
    report_file = "docling_analysis_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"Отчет сохранен: {report_file}")
    print("=" * 70)

if __name__ == "__main__":
    main()

