#!/usr/bin/env python3
"""
Скрипт для сбора метрик из output файлов и MongoDB.
"""
import json
import subprocess
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List

def get_mongo_via_docker():
    """Получает данные из MongoDB через docker exec."""
    try:
        result = subprocess.run(
            ["docker", "exec", "docling_mongodb", "mongosh",
             "-u", "admin", "-p", "password",
             "--authenticationDatabase", "admin",
             "--quiet",
             "--eval",
             "db = db.getSiblingDB('docling_metadata'); "
             "JSON.stringify({metrics: db.processing_metrics.find({}).toArray(), manifests: db.manifests.find({}).toArray()})"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
        return None
    except Exception as e:
        print(f"⚠️  Ошибка получения данных через docker: {e}")
        return None

def collect_metrics_from_output() -> List[Dict[str, Any]]:
    """Собирает метрики из output файлов."""
    metrics = []
    output_dir = Path("/root/winners_preprocessor/output")
    
    if not output_dir.exists():
        return metrics
    
    for unit_dir in output_dir.iterdir():
        if not unit_dir.is_dir():
            continue
        
        for json_file in unit_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    output_data = json.load(f)
                    metrics_data = output_data.get("metrics", {})
                    if metrics_data:
                        metric = {
                            "unit_id": output_data.get("unit_id", ""),
                            "file_name": output_data.get("file", ""),
                            "route": output_data.get("route", "unknown"),
                            "processing_method": output_data.get("processing_method", "unknown"),
                            "processing_times": metrics_data.get("processing_times", {}),
                            "file_stats": metrics_data.get("file_stats", {}),
                            "detected_type": output_data.get("detected_type", "unknown")
                        }
                        metrics.append(metric)
            except Exception as e:
                continue
    
    return metrics

def analyze_library_usage(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует использование библиотек."""
    library_usage = defaultdict(lambda: {
        "count": 0,
        "total_time": 0.0,
        "stages": [],
        "routes": defaultdict(int)
    })
    
    for metric in metrics:
        method = str(metric.get("processing_method", "unknown")).lower()
        route = str(metric.get("route", "unknown"))
        processing_times = metric.get("processing_times", {})
        total_time = processing_times.get("total", 0) or sum(processing_times.values()) if processing_times else 0
        
        # Определяем библиотеку
        library = None
        if "pdfplumber" in method or "plumber" in method:
            library = "pdfplumber"
        elif "python-docx" in method or ("docx" in method and "fallback" in method):
            library = "python-docx"
        elif "beautifulsoup" in method or "soup" in method or route == "html_text":
            library = "beautifulsoup"
        elif "pytesseract" in method or "tesseract" in method:
            library = "pytesseract"
        elif "pdf2image" in method:
            library = "pdf2image"
        elif "docling" in method and "core" in method:
            library = "docling-core"
        else:
            # Определяем по route
            if route in ["pdf_text", "pdf_scan"]:
                library = "pdfplumber"
            elif route == "docx":
                library = "python-docx"
            elif route == "html_text":
                library = "beautifulsoup"
            else:
                library = "fallback/unknown"
        
        library_usage[library]["count"] += 1
        library_usage[library]["total_time"] += total_time
        library_usage[library]["routes"][route] += 1
        library_usage[library]["stages"].append({
            "route": route,
            "method": metric.get("processing_method", "unknown"),
            "times": processing_times
        })
    
    return dict(library_usage)

def analyze_extensions(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует статистику по расширениям."""
    extensions_stats = defaultdict(lambda: {
        "count": 0,
        "routes": defaultdict(int),
        "times": {
            "total": [],
            "text_extraction": [],
            "ocr": [],
            "layout_analysis": [],
            "table_extraction": []
        },
        "library_methods": defaultdict(int)
    })
    
    for metric in metrics:
        file_name = metric.get("file_name", "")
        ext = Path(file_name).suffix.lower() if file_name else "unknown"
        route = metric.get("route", "unknown")
        method = metric.get("processing_method", "unknown")
        processing_times = metric.get("processing_times", {})
        
        extensions_stats[ext]["count"] += 1
        extensions_stats[ext]["routes"][route] += 1
        extensions_stats[ext]["library_methods"][method] += 1
        
        if "total" in processing_times:
            extensions_stats[ext]["times"]["total"].append(processing_times["total"])
        if "text_extraction" in processing_times:
            extensions_stats[ext]["times"]["text_extraction"].append(processing_times["text_extraction"])
        if "ocr" in processing_times:
            extensions_stats[ext]["times"]["ocr"].append(processing_times["ocr"])
        if "layout_analysis" in processing_times:
            extensions_stats[ext]["times"]["layout_analysis"].append(processing_times["layout_analysis"])
        if "table_extraction" in processing_times:
            extensions_stats[ext]["times"]["table_extraction"].append(processing_times["table_extraction"])
    
    # Вычисляем средние
    for ext, stats in extensions_stats.items():
        for time_type, times in stats["times"].items():
            if times:
                stats["times"][time_type] = {
                    "min": min(times),
                    "max": max(times),
                    "avg": sum(times) / len(times),
                    "total": sum(times),
                    "count": len(times)
                }
            else:
                stats["times"][time_type] = {"min": 0, "max": 0, "avg": 0, "total": 0, "count": 0}
    
    return dict(extensions_stats)

def analyze_stages(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Анализирует времена по этапам."""
    stages_timing = defaultdict(lambda: {
        "count": 0,
        "total_time": 0.0,
        "min": float("inf"),
        "max": 0.0,
        "avg": 0.0
    })
    
    for metric in metrics:
        processing_times = metric.get("processing_times", {})
        for stage, stage_time in processing_times.items():
            if stage_time and stage_time > 0:
                stages_timing[stage]["count"] += 1
                stages_timing[stage]["total_time"] += stage_time
                stages_timing[stage]["min"] = min(stages_timing[stage]["min"], stage_time)
                stages_timing[stage]["max"] = max(stages_timing[stage]["max"], stage_time)
    
    # Вычисляем средние
    for stage, stats in stages_timing.items():
        if stats["count"] > 0:
            stats["avg"] = stats["total_time"] / stats["count"]
        if stats["min"] == float("inf"):
            stats["min"] = 0.0
    
    return dict(stages_timing)

def generate_report(metrics: List[Dict[str, Any]], library_usage: Dict[str, Any], 
                   extensions_stats: Dict[str, Any], stages_timing: Dict[str, Any]) -> str:
    """Генерирует отчет."""
    from datetime import datetime
    
    lines = []
    lines.append("# ПОЛНЫЙ ОТЧЕТ ОБ ОБРАБОТКЕ PIPELINE")
    lines.append("")
    lines.append(f"**Время генерации отчета:** {datetime.utcnow().isoformat()}")
    lines.append(f"**Всего метрик собрано:** {len(metrics)}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Общая статистика
    lines.append("## ОБЩАЯ СТАТИСТИКА")
    lines.append("")
    total_files = len(metrics)
    total_time = sum(sum(m.get("processing_times", {}).values()) for m in metrics)
    avg_time = total_time / total_files if total_files > 0 else 0
    
    lines.append(f"- **Всего обработано файлов:** {total_files}")
    lines.append(f"- **Общее время обработки:** {total_time:.2f}s")
    lines.append(f"- **Среднее время на файл:** {avg_time:.3f}s")
    lines.append("")
    
    # Группировка по routes
    routes_stats = defaultdict(lambda: {"count": 0, "total_time": 0.0})
    for metric in metrics:
        route = str(metric.get("route", "unknown"))
        times = metric.get("processing_times", {})
        file_time = sum(times.values()) if times else 0
        routes_stats[route]["count"] += 1
        routes_stats[route]["total_time"] += file_time
    
    lines.append("### Статистика по Routes:")
    lines.append("")
    lines.append("| Route | Количество | Общее время | Среднее время |")
    lines.append("|-------|------------|-------------|---------------|")
    for route, stats in sorted(routes_stats.items()):
        avg = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
        lines.append(f"| `{route}` | {stats['count']} | {stats['total_time']:.2f}s | {avg:.3f}s |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Статистика по расширениям
    lines.append("## СТАТИСТИКА ПО РАСШИРЕНИЯМ ФАЙЛОВ")
    lines.append("")
    lines.append("| Расширение | Количество | Routes | Среднее время | Библиотеки |")
    lines.append("|------------|------------|--------|---------------|------------|")
    
    for ext, stats in sorted(extensions_stats.items()):
        count = stats["count"]
        routes = ", ".join([f"{r}({c})" for r, c in list(stats["routes"].items())[:3]])
        # Вычисляем среднее время из всех времен total
        total_times = stats["times"]["total"]["total"]
        avg_time = stats["times"]["total"]["avg"] if stats["times"]["total"]["count"] > 0 else 0
        libraries = ", ".join(list(stats["library_methods"].keys())[:2])
        lines.append(f"| `{ext}` | {count} | {routes[:40]} | {avg_time:.3f}s | {libraries[:30]} |")
    
    lines.append("")
    lines.append("### Детальная статистика по расширениям:")
    lines.append("")
    
    for ext, stats in sorted(extensions_stats.items())[:10]:
        lines.append(f"#### {ext}")
        lines.append(f"- **Количество файлов:** {stats['count']}")
        lines.append(f"- **Routes:** {dict(stats['routes'])}")
        lines.append(f"- **Библиотеки:** {dict(stats['library_methods'])}")
        lines.append("")
        lines.append("Времена обработки:")
        for time_type, time_stats in stats["times"].items():
            if time_stats.get("count", 0) > 0:
                lines.append(f"  - **{time_type}**: avg={time_stats['avg']:.3f}s, min={time_stats['min']:.3f}s, max={time_stats['max']:.3f}s (count: {time_stats['count']})")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    
    # Статистика по этапам
    lines.append("## СТАТИСТИКА ПО ЭТАПАМ ОБРАБОТКИ")
    lines.append("")
    lines.append("| Этап | Количество | Общее время | Среднее | Мин | Макс |")
    lines.append("|------|------------|-------------|---------|-----|------|")
    
    for stage, stats in sorted(stages_timing.items()):
        lines.append(f"| `{stage}` | {stats['count']} | {stats['total_time']:.2f}s | {stats['avg']:.3f}s | {stats['min']:.3f}s | {stats['max']:.3f}s |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Статистика по библиотекам
    lines.append("## СТАТИСТИКА ПО ИСПОЛЬЗУЕМЫМ БИБЛИОТЕКАМ/LLM")
    lines.append("")
    lines.append("| Библиотека | Использований | Общее время | Среднее время | Routes |")
    lines.append("|------------|---------------|-------------|---------------|--------|")
    
    for lib, stats in sorted(library_usage.items()):
        count = stats["count"]
        total_time = stats["total_time"]
        avg_time = total_time / count if count > 0 else 0
        routes = ", ".join(sorted([str(r) for r in stats["routes"].keys()])[:3])
        lines.append(f"| **{lib}** | {count} | {total_time:.2f}s | {avg_time:.3f}s | {routes} |")
    
    lines.append("")
    lines.append("### Детальная информация по библиотекам:")
    lines.append("")
    
    for lib, stats in sorted(library_usage.items()):
        lines.append(f"#### {lib}")
        lines.append(f"- **Количество использований:** {stats['count']}")
        lines.append(f"- **Общее время:** {stats['total_time']:.2f}s")
        lines.append(f"- **Среднее время:** {stats['total_time'] / max(stats['count'], 1):.3f}s")
        lines.append(f"- **Routes:** {dict(stats['routes'])}")
        lines.append("")
        lines.append("Использование по этапам (примеры):")
        for stage_info in stats["stages"][:10]:
            route = stage_info.get("route", "unknown")
            method = stage_info.get("method", "unknown")
            times = stage_info.get("times", {})
            lines.append(f"  - **Route:** {route}, **Method:** {method}")
            for time_stage, time_val in times.items():
                if time_val and time_val > 0:
                    lines.append(f"    - {time_stage}: {time_val:.3f}s")
        lines.append("")
    
    lines.append("---")
    lines.append("")
    lines.append(f"**Отчет сгенерирован:** {datetime.utcnow().isoformat()}")
    
    return "\n".join(lines)

def main():
    print("Сбор метрик из output файлов...")
    
    # Собираем метрики из output
    metrics = collect_metrics_from_output()
    print(f"✅ Собрано метрик из output: {len(metrics)}")
    
    # Анализируем использование библиотек
    library_usage = analyze_library_usage(metrics)
    print(f"✅ Найдено библиотек: {len(library_usage)}")
    
    # Анализируем расширения
    extensions_stats = analyze_extensions(metrics)
    print(f"✅ Найдено расширений: {len(extensions_stats)}")
    
    # Анализируем этапы
    stages_timing = analyze_stages(metrics)
    print(f"✅ Найдено этапов: {len(stages_timing)}")
    
    # Генерируем отчет
    report = generate_report(metrics, library_usage, extensions_stats, stages_timing)
    
    # Сохраняем отчет
    with open("FULL_PIPELINE_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    print("✅ Отчет сохранен в FULL_PIPELINE_REPORT.md")
    
    # Сохраняем метрики
    all_metrics = {
        "metrics": metrics,
        "library_usage": library_usage,
        "extensions_stats": extensions_stats,
        "stages_timing": stages_timing
    }
    
    with open("pipeline_metrics.json", "w", encoding="utf-8") as f:
        json.dump(all_metrics, f, indent=2, ensure_ascii=False, default=str)
    
    print("✅ Метрики сохранены в pipeline_metrics.json")

if __name__ == "__main__":
    main()

