#!/usr/bin/env python3
"""Простое скачивание одного файла для теста."""
import json
import requests
from pathlib import Path

# Читаем JSON и берем первый URL
with open('test_protocols_mcp_combined_500.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

protocols = data.get('protocols', {})
first_key = list(protocols.keys())[0]
first_doc = protocols[first_key]

if isinstance(first_doc, dict):
    url = first_doc.get('url')
    filename = first_doc.get('fileName', 'test.pdf')
elif isinstance(first_doc, list):
    url = first_doc[0].get('url')
    filename = first_doc[0].get('fileName', 'test.pdf')

print(f'URL: {url}')
print(f'Filename: {filename}')
print()

# Простое скачивание
print('Пробую скачать...')
try:
    # Увеличиваем timeout и пробуем разные варианты
    for timeout in [30, 60, 120]:
        print(f'Попытка с timeout={timeout}...')
        try:
            response = requests.get(url, timeout=timeout, verify=True, allow_redirects=True)
            print(f'Status: {response.status_code}')
            print(f'Content-Type: {response.headers.get("Content-Type", "unknown")}')
            print(f'Size: {len(response.content)} bytes')
            
            if response.status_code == 200 and len(response.content) > 0:
                output_path = Path('input/test_single')
                output_path.mkdir(parents=True, exist_ok=True)
                safe_filename = filename.replace('/', '_').replace('\\', '_')
                file_path = output_path / safe_filename
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f'✓ Файл сохранен: {file_path}')
                print(f'✓ Размер файла: {file_path.stat().st_size} bytes')
                break
            else:
                print(f'✗ Ошибка: status={response.status_code}, size={len(response.content)}')
        except requests.exceptions.Timeout:
            print(f'✗ Timeout ({timeout}s)')
            continue
        except Exception as e:
            print(f'✗ Ошибка: {type(e).__name__}: {e}')
            continue
    else:
        print('✗ Все попытки не удались')
        
except Exception as e:
    print(f'✗ Критическая ошибка: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()

