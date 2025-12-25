#!/usr/bin/env python3
"""
Альтернативный вариант скачивания с различными стратегиями:
1. Увеличенные таймауты
2. Прокси (если доступен)
3. Разные User-Agent
4. Последовательное скачивание вместо параллельного
"""
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, Tuple
import sys

def download_with_strategy(url: str, dest_path: Path, strategy: str = "default") -> Tuple[bool, str]:
    """Скачивает файл с различными стратегиями."""
    
    strategies = {
        "default": {
            "timeout": 30,
            "headers": {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            }
        },
        "long_timeout": {
            "timeout": 60,
            "headers": {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
            }
        },
        "with_referer": {
            "timeout": 30,
            "headers": {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'Referer': 'https://zakupki.gov.ru/',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
        },
        "minimal": {
            "timeout": 60,
            "headers": {
                'User-Agent': 'curl/7.68.0',
            }
        }
    }
    
    config = strategies.get(strategy, strategies["default"])
    
    try:
        print(f"  Стратегия: {strategy}, URL: {url[:60]}...")
        
        response = requests.get(
            url,
            timeout=config["timeout"],
            headers=config["headers"],
            stream=True,
            allow_redirects=True
        )
        
        response.raise_for_status()
        
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = dest_path.stat().st_size
        print(f"  ✓ Скачано: {dest_path.name} ({file_size:,} bytes)")
        return True, dest_path.name
        
    except requests.exceptions.Timeout:
        return False, f"Timeout ({config['timeout']}s)"
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)[:60]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:60]}"


def test_download_sequential(json_file: str, output_dir: str, limit: int = 10):
    """Последовательное скачивание с разными стратегиями."""
    
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    protocols = data.get('protocols', {})
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    downloaded = []
    failed = []
    
    strategies = ["default", "long_timeout", "with_referer", "minimal"]
    
    count = 0
    for purchase_number, doc_info in protocols.items():
        if count >= limit:
            break
            
        docs = [doc_info] if isinstance(doc_info, dict) else doc_info
        
        for doc in docs:
            if count >= limit:
                break
                
            url = doc.get("url")
            filename = doc.get("fileName", f"{purchase_number}.pdf")
            
            if not url:
                continue
            
            # Санитизируем имя файла
            safe_filename = filename.replace('..', '').replace('/', '_').replace('\\', '_')
            dest_path = output_path / safe_filename
            
            print(f"\n[{count + 1}/{limit}] {purchase_number}")
            
            # Пробуем разные стратегии
            success = False
            for strategy in strategies:
                success, result = download_with_strategy(url, dest_path, strategy)
                if success:
                    downloaded.append({
                        "purchase_number": purchase_number,
                        "url": url,
                        "filename": filename,
                        "strategy": strategy
                    })
                    break
                else:
                    print(f"    ✗ {strategy}: {result}")
                    time.sleep(1)  # Небольшая задержка между попытками
            
            if not success:
                failed.append({
                    "purchase_number": purchase_number,
                    "url": url,
                    "filename": filename
                })
            
            count += 1
            time.sleep(0.5)  # Задержка между файлами
    
    print(f"\n{'='*60}")
    print(f"Результаты:")
    print(f"  ✓ Скачано: {len(downloaded)}")
    print(f"  ✗ Ошибок: {len(failed)}")
    print(f"{'='*60}")
    
    return {
        "downloaded": downloaded,
        "failed": failed
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 test_download_alternative.py <json_file> [output_dir] [limit]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "input/test_alternative"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    print("=" * 60)
    print("Альтернативное скачивание (последовательное, разные стратегии)")
    print("=" * 60)
    
    test_download_sequential(json_file, output_dir, limit)

