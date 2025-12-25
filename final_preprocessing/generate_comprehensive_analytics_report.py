#!/usr/bin/env python3
"""
Генерация комплексного отчета с детальной аналитикой по обработке UNIT.
"""
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def collect_comprehensive_stats(base_dir: str):
    """Собирает комплексную статистику по всем фазам обработки."""
    base_path = Path(base_dir)
    
    stats = {
        "input": {
            "total": 0,
            "empty": 0,
            "by_extension": Counter(),
            "by_extension_units": Counter(),
        },
        "ready": {
            "total": 0,
            "by_extension": Counter(),
            "by_route": Counter(),
            "by_cycle": Counter(),
            "pdf_distribution": {"scan": 0, "text": 0, "mixed": 0, "unknown": 0},
        },
        "exceptions": {
            "total": 0,
            "by_category": Counter(),
            "by_cycle": defaultdict(Counter),
        },
        "processing": {
            "by_cycle": defaultdict(lambda: {"convert": 0, "extract": 0, "normalize": 0}),
        },
        "merge": {
            "by_cycle": defaultdict(lambda: {"converted": 0, "extracted": 0, "normalized": 0, "direct": 0}),
        },
        "operations": {
            "by_cycle": defaultdict(lambda: defaultdict(Counter)),
        },
    }
    
    # Input Analysis
    input_dir = base_path / "Input"
    if input_dir.exists():
        for unit_dir in input_dir.glob("UNIT_*"):
            if unit_dir.is_dir():
                stats["input"]["total"] += 1
                files = list(unit_dir.glob("*"))
                files = [f for f in files if f.is_file() and f.name not in ["manifest.json", "audit.log.jsonl"]]
                
                if not files:
                    stats["input"]["empty"] += 1
                else:
                    extensions = set()
                    for f in files:
                        ext = f.suffix.lower().lstrip(".")
                        if ext:
                            extensions.add(ext)
                            stats["input"]["by_extension"][ext] += 1
                    if extensions:
                        first_ext = list(extensions)[0]
                        stats["input"]["by_extension_units"][first_ext] += 1
    
    # Ready2Docling Analysis
    ready_dir = base_path / "Ready2Docling"
    if ready_dir.exists():
        for unit_dir in ready_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                stats["ready"]["total"] += 1
                manifest_path = unit_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            m = json.load(f)
                            proc = m.get("processing", {})
                            route = proc.get("route", "unknown")
                            cycle = proc.get("current_cycle", 1)
                            
                            stats["ready"]["by_route"][route] += 1
                            stats["ready"]["by_cycle"][cycle] += 1
                            
                            # Формат
                            files = m.get("files", [])
                            if files:
                                main_file = files[0]
                                ext = Path(main_file.get("current_name", "")).suffix.lower().lstrip(".")
                                if not ext:
                                    ext = "no_ext"
                                stats["ready"]["by_extension"][ext] += 1
                                
                                # PDF distribution
                                if ext == "pdf" or "pdf" in route:
                                    if "scan" in route:
                                        stats["ready"]["pdf_distribution"]["scan"] += 1
                                    elif "text" in route:
                                        stats["ready"]["pdf_distribution"]["text"] += 1
                                    elif "mixed" in route:
                                        stats["ready"]["pdf_distribution"]["mixed"] += 1
                                    else:
                                        stats["ready"]["pdf_distribution"]["unknown"] += 1
                    except:
                        pass
    
    # Exceptions Analysis
    exceptions_dir = base_path / "Exceptions"
    if exceptions_dir.exists():
        for unit_dir in exceptions_dir.rglob("UNIT_*"):
            if unit_dir.is_dir():
                stats["exceptions"]["total"] += 1
                rel_path = unit_dir.relative_to(exceptions_dir)
                parts = rel_path.parts
                
                category = "Unknown"
                cycle = 1
                
                if len(parts) >= 2:
                    if parts[0].startswith("Exceptions_"):
                        cycle = int(parts[0].split("_")[1])
                        category = parts[1]
                    else:
                        category = parts[0]
                
                stats["exceptions"]["by_category"][category] += 1
                stats["exceptions"]["by_cycle"][cycle][category] += 1
    
    # Processing & Merge Analysis (from manifests)
    for dir_path in [ready_dir, exceptions_dir]:
        if not dir_path.exists():
            continue
        for unit_dir in dir_path.rglob("UNIT_*"):
            if unit_dir.is_dir():
                manifest_path = unit_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            m = json.load(f)
                            proc = m.get("processing", {})
                            cycle = proc.get("current_cycle", 1)
                            route = proc.get("route", "")
                            
                            # Operations
                            ops = proc.get("operations", [])
                            root_ops = m.get("applied_operations", [])
                            all_ops = ops + root_ops
                            
                            for op in all_ops:
                                op_type = op.get("type", "unknown")
                                status = op.get("status", "success")
                                op_cycle = op.get("cycle", cycle)
                                stats["operations"]["by_cycle"][op_cycle][op_type][status] += 1
                            
                            # Processing/Merge routes
                            if "convert" in route.lower():
                                if "converted" in route.lower():
                                    stats["merge"]["by_cycle"][cycle]["converted"] += 1
                                else:
                                    stats["processing"]["by_cycle"][cycle]["convert"] += 1
                            elif "extract" in route.lower():
                                if "extracted" in route.lower():
                                    stats["merge"]["by_cycle"][cycle]["extracted"] += 1
                                else:
                                    stats["processing"]["by_cycle"][cycle]["extract"] += 1
                            elif "normalize" in route.lower():
                                if "normalized" in route.lower():
                                    stats["merge"]["by_cycle"][cycle]["normalized"] += 1
                                else:
                                    stats["processing"]["by_cycle"][cycle]["normalize"] += 1
                            elif "direct" in route.lower():
                                stats["merge"]["by_cycle"][cycle]["direct"] += 1
                    except:
                        pass
    
    return stats

def generate_report(stats: dict, base_dir: str) -> str:
    """Генерирует детальный отчет с таблицами."""
    report = []
    report.append("# 📊 КОМПЛЕКСНЫЙ ОТЧЕТ ОБ ОБРАБОТКЕ UNIT")
    report.append("")
    report.append(f"**Дата обработки:** {Path(base_dir).name}")
    report.append(f"**Дата генерации отчета:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    report.append("---")
    report.append("")
    
    # 1. ОБЩАЯ СТАТИСТИКА
    report.append("## 1. ОБЩАЯ СТАТИСТИКА")
    report.append("")
    
    input_total = stats["input"]["total"]
    input_with_files = input_total - stats["input"]["empty"]
    ready_total = stats["ready"]["total"]
    exceptions_total = stats["exceptions"]["total"]
    total_output = ready_total + exceptions_total
    
    report.append("| Метрика | Значение | Процент от Input |")
    report.append("|---------|----------|------------------|")
    report.append(f"| **Всего UNIT в Input** | {input_total} | 100.0% |")
    report.append(f"| **Пустых UNIT** | {stats['input']['empty']} | {stats['input']['empty']/input_total*100:.1f}% |")
    report.append(f"| **UNIT с файлами** | {input_with_files} | {input_with_files/input_total*100:.1f}% |")
    report.append(f"| **Обработано успешно** | {ready_total} | {ready_total/input_total*100:.1f}% |")
    report.append(f"| **В Exceptions** | {exceptions_total} | {exceptions_total/input_total*100:.1f}% |")
    report.append(f"| **Успешность обработки** | {ready_total/input_with_files*100:.1f}% | {ready_total/input_total*100:.1f}% |")
    report.append("")
    
    # 2. ВХОДНЫЕ ДАННЫЕ (Input)
    report.append("## 2. ВХОДНЫЕ ДАННЫЕ (Input)")
    report.append("")
    report.append("### Распределение по расширениям (файлы):")
    report.append("")
    report.append("| Расширение | Количество файлов | Процент |")
    report.append("|------------|-------------------|---------|")
    
    total_files = sum(stats["input"]["by_extension"].values())
    for ext, count in sorted(stats["input"]["by_extension"].items(), key=lambda x: x[1], reverse=True):
        pct = count / total_files * 100 if total_files > 0 else 0
        report.append(f"| .{ext} | {count} | {pct:.1f}% |")
    
    report.append("")
    report.append("### Распределение по расширениям (UNIT):")
    report.append("")
    report.append("| Расширение | Количество UNIT | Процент от UNIT с файлами |")
    report.append("|------------|-----------------|---------------------------|")
    
    for ext, count in sorted(stats["input"]["by_extension_units"].items(), key=lambda x: x[1], reverse=True):
        pct = count / input_with_files * 100 if input_with_files > 0 else 0
        report.append(f"| .{ext} | {count} | {pct:.1f}% |")
    
    report.append("")
    report.append("---")
    report.append("")
    
    # 3. ГОТОВНОСТЬ К DOCLING (Ready2Docling)
    report.append("## 3. ГОТОВНОСТЬ К DOCLING (Ready2Docling)")
    report.append("")
    report.append(f"- **Всего UNIT:** {ready_total}")
    report.append(f"- **Процент от Input:** {ready_total/input_total*100:.1f}%")
    report.append(f"- **Процент от UNIT с файлами:** {ready_total/input_with_files*100:.1f}%")
    report.append("")
    
    # Распределение по маршрутам
    report.append("### Распределение по маршрутам:")
    report.append("")
    report.append("| Маршрут | Количество UNIT | Процент от Ready2Docling |")
    report.append("|---------|-----------------|--------------------------|")
    
    for route, count in sorted(stats["ready"]["by_route"].items(), key=lambda x: x[1], reverse=True):
        pct = count / ready_total * 100 if ready_total > 0 else 0
        report.append(f"| {route} | {count} | {pct:.1f}% |")
    
    report.append("")
    
    # Распределение по расширениям
    report.append("### Распределение по расширениям:")
    report.append("")
    report.append("| Расширение | Количество UNIT | Процент от Ready2Docling |")
    report.append("|------------|-----------------|--------------------------|")
    
    for ext, count in sorted(stats["ready"]["by_extension"].items(), key=lambda x: x[1], reverse=True):
        pct = count / ready_total * 100 if ready_total > 0 else 0
        report.append(f"| .{ext} | {count} | {pct:.1f}% |")
    
    report.append("")
    
    # PDF Distribution
    pdf_total = sum(stats["ready"]["pdf_distribution"].values())
    if pdf_total > 0:
        report.append("### Распределение PDF:")
        report.append("")
        report.append("| Тип PDF | Количество UNIT | Процент от всех PDF |")
        report.append("|---------|-----------------|---------------------|")
        
        for pdf_type, count in stats["ready"]["pdf_distribution"].items():
            if count > 0:
                pct = count / pdf_total * 100
                report.append(f"| {pdf_type} | {count} | {pct:.1f}% |")
        
        report.append("")
    
    # Распределение по циклам
    report.append("### Распределение по циклам обработки:")
    report.append("")
    report.append("| Цикл | Количество UNIT | Процент от Ready2Docling |")
    report.append("|------|-----------------|--------------------------|")
    
    for cycle in sorted(stats["ready"]["by_cycle"].keys()):
        count = stats["ready"]["by_cycle"][cycle]
        pct = count / ready_total * 100 if ready_total > 0 else 0
        report.append(f"| {cycle} | {count} | {pct:.1f}% |")
    
    report.append("")
    report.append("---")
    report.append("")
    
    # 4. ИСКЛЮЧЕНИЯ (Exceptions)
    report.append("## 4. ИСКЛЮЧЕНИЯ (Exceptions)")
    report.append("")
    report.append(f"- **Всего UNIT:** {exceptions_total}")
    report.append(f"- **Процент от Input:** {exceptions_total/input_total*100:.1f}%")
    report.append("")
    
    report.append("### Распределение по категориям:")
    report.append("")
    report.append("| Категория | Количество UNIT | Процент от Exceptions |")
    report.append("|-----------|-----------------|----------------------|")
    
    for cat, count in sorted(stats["exceptions"]["by_category"].items(), key=lambda x: x[1], reverse=True):
        pct = count / exceptions_total * 100 if exceptions_total > 0 else 0
        report.append(f"| {cat} | {count} | {pct:.1f}% |")
    
    report.append("")
    
    # По циклам
    if stats["exceptions"]["by_cycle"]:
        report.append("### Распределение по циклам:")
        report.append("")
        for cycle in sorted(stats["exceptions"]["by_cycle"].keys()):
            cycle_exc = stats["exceptions"]["by_cycle"][cycle]
            total_cycle_exc = sum(cycle_exc.values())
            report.append(f"#### Цикл {cycle}: {total_cycle_exc} UNIT")
            report.append("")
            report.append("| Категория | Количество | Процент |")
            report.append("|-----------|------------|---------|")
            for cat, count in sorted(cycle_exc.items(), key=lambda x: x[1], reverse=True):
                pct = count / total_cycle_exc * 100 if total_cycle_exc > 0 else 0
                report.append(f"| {cat} | {count} | {pct:.1f}% |")
            report.append("")
    
    report.append("---")
    report.append("")
    
    # 5. FLOW АНАЛИТИКА
    report.append("## 5. FLOW АНАЛИТИКА (Процентное распределение)")
    report.append("")
    report.append("### Распределение UNIT по фазам обработки:")
    report.append("")
    report.append("| Фаза | Количество UNIT | Процент от Input (всего) | Процент от Input (без пустых) |")
    report.append("|------|-----------------|---------------------------|-------------------------------|")
    
    report.append(f"| Input (всего) | {input_total} | 100.0% | - |")
    report.append(f"| Input (с файлами) | {input_with_files} | {input_with_files/input_total*100:.1f}% | 100.0% |")
    
    # Direct units (cycle 1, direct route)
    direct_count = stats["merge"]["by_cycle"].get(1, {}).get("direct", 0)
    if direct_count > 0:
        report.append(f"| Merge_0/Direct | {direct_count} | {direct_count/input_total*100:.1f}% | {direct_count/input_with_files*100:.1f}% |")
    
    # По циклам
    for cycle in sorted(set(list(stats["processing"]["by_cycle"].keys()) + list(stats["merge"]["by_cycle"].keys()))):
        proc_cycle = stats["processing"]["by_cycle"].get(cycle, {})
        merge_cycle = stats["merge"]["by_cycle"].get(cycle, {})
        
        total_proc = sum(proc_cycle.values())
        total_merge = sum([v for k, v in merge_cycle.items() if k != "direct"])
        
        if total_proc > 0:
            report.append(f"| Processing_{cycle} | {total_proc} | {total_proc/input_total*100:.1f}% | {total_proc/input_with_files*100:.1f}% |")
        if total_merge > 0:
            report.append(f"| Merge_{cycle} | {total_merge} | {total_merge/input_total*100:.1f}% | {total_merge/input_with_files*100:.1f}% |")
        
        cycle_exc = sum(stats["exceptions"]["by_cycle"].get(cycle, {}).values())
        if cycle_exc > 0:
            report.append(f"| Exceptions_{cycle} | {cycle_exc} | {cycle_exc/input_total*100:.1f}% | {cycle_exc/input_with_files*100:.1f}% |")
    
    report.append(f"| Ready2Docling | {ready_total} | {ready_total/input_total*100:.1f}% | {ready_total/input_with_files*100:.1f}% |")
    report.append(f"| Exceptions (всего) | {exceptions_total} | {exceptions_total/input_total*100:.1f}% | {exceptions_total/input_with_files*100:.1f}% |")
    
    report.append("")
    report.append("---")
    report.append("")
    
    # 6. ОПЕРАЦИИ
    if stats["operations"]["by_cycle"]:
        report.append("## 6. ОПЕРАЦИИ ПО ЦИКЛАМ")
        report.append("")
        for cycle in sorted(stats["operations"]["by_cycle"].keys()):
            ops_cycle = stats["operations"]["by_cycle"][cycle]
            report.append(f"### Цикл {cycle}")
            report.append("")
            report.append("| Операция | Успешно | Ошибки | Пропущено | Всего | Успешность % |")
            report.append("|----------|---------|--------|-----------|-------|--------------|")
            
            for op_type, statuses in sorted(ops_cycle.items()):
                success = statuses.get("success", 0) + statuses.get("completed", 0)
                failed = statuses.get("failed", 0) + statuses.get("error", 0)
                skipped = statuses.get("skipped", 0)
                total = success + failed + skipped
                success_pct = (success / (success + failed) * 100) if (success + failed) > 0 else 0
                
                report.append(f"| {op_type} | {success} | {failed} | {skipped} | {total} | {success_pct:.1f}% |")
            
            report.append("")
    
    report.append("---")
    report.append("")
    
    # 7. ИТОГОВАЯ СВОДКА
    report.append("## 7. ИТОГОВАЯ СВОДКА")
    report.append("")
    report.append("### Ключевые показатели:")
    report.append("")
    report.append(f"- ✅ **Обработано успешно:** {ready_total} UNIT ({ready_total/input_with_files*100:.1f}% от UNIT с файлами)")
    report.append(f"- ⚠️ **В Exceptions:** {exceptions_total} UNIT ({exceptions_total/input_total*100:.1f}% от всех UNIT)")
    report.append(f"- 📊 **Подотчетность данных:** {total_output} UNIT ({total_output/input_total*100:.1f}% от Input)")
    report.append(f"- 🔍 **Дельта:** {input_total - total_output} UNIT")
    report.append("")
    
    if input_total == total_output:
        report.append("✅ **Целостность данных:** PASS (все UNIT учтены)")
    else:
        report.append(f"⚠️ **Целостность данных:** FAIL (дельта: {input_total - total_output} UNIT)")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append(f"*Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report.append("*Система: DocPrep v1.0*")
    report.append("*Статус: ✅ Готово к передаче в Docling pipeline*")
    
    return "\n".join(report)

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 generate_comprehensive_analytics_report.py <date>")
        print("Пример: python3 generate_comprehensive_analytics_report.py Data/2025-11-29")
        sys.exit(1)
    
    base_dir = sys.argv[1]
    if not Path(base_dir).exists():
        print(f"❌ Директория не найдена: {base_dir}")
        sys.exit(1)
    
    print(f"📊 Сбор комплексной статистики для {base_dir}...")
    stats = collect_comprehensive_stats(base_dir)
    
    print("📝 Генерация отчета...")
    report = generate_report(stats, base_dir)
    
    output_file = Path(base_dir) / "COMPREHENSIVE_ANALYTICS_REPORT.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    print(f"✅ Отчет сохранен: {output_file}")
    
    # Также сохраняем статистику в JSON
    json_file = Path(base_dir) / "COMPREHENSIVE_ANALYTICS_STATS.json"
    # Конвертируем Counter и defaultdict в обычные dict
    def convert_to_serializable(obj):
        if isinstance(obj, Counter):
            return dict(obj)
        elif isinstance(obj, defaultdict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: convert_to_serializable(v) for k, v in obj.items()}
        else:
            return obj
    
    json_stats = convert_to_serializable(stats)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_stats, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Статистика сохранена: {json_file}")

if __name__ == "__main__":
    main()
