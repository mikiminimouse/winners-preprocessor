#!/usr/bin/env python3
"""
Объединяет несколько JSON файлов с протоколами из MCP сервера в один, ограничивая итоговое количество.
"""
import sys
import json
from pathlib import Path
from collections import OrderedDict
from datetime import datetime


def combine_protocols(output_file: str, target_count: int, input_files: list[str]) -> None:
    combined_protocols: "OrderedDict[str, object]" = OrderedDict()
    sources = []
    total_urls = 0

    for file in input_files:
        path = Path(file)
        if not path.exists():
            print(f"⚠️  Файл не найден: {file}")
            continue

        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        protocols = data.get('protocols', {})
        sources.append({
            "file": file,
            "date": data.get('date', 'unknown'),
            "protocols_count": len(protocols)
        })

        for purchase_number, doc_info in protocols.items():
            if purchase_number not in combined_protocols:
                combined_protocols[purchase_number] = doc_info
                # Подсчитываем количество URLs
                if isinstance(doc_info, dict):
                    total_urls += 1
                elif isinstance(doc_info, list):
                    total_urls += len(doc_info)

                if len(combined_protocols) >= target_count:
                    break
        if len(combined_protocols) >= target_count:
            break

    result = {
        "combined_at": datetime.utcnow().isoformat() + "Z",
        "source_files": sources,
        "target_count": target_count,
        "protocols_count": len(combined_protocols),
        "total_urls": total_urls,
        "protocols": combined_protocols
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Итоговый файл: {output_file}")
    print(f"✓ Протоколов собрано: {len(combined_protocols)}")
    print(f"✓ Всего URLs: {total_urls}")


def main():
    if len(sys.argv) < 4:
        print("Использование: python3 combine_protocols_mcp.py <output_file> <target_count> <input_json1> [input_json2 ...]")
        sys.exit(1)

    output_file = sys.argv[1]
    target_count = int(sys.argv[2])
    input_files = sys.argv[3:]

    combine_protocols(output_file, target_count, input_files)


if __name__ == "__main__":
    main()
