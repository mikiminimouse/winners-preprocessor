#!/usr/bin/env python3
"""
Тест OCR pipeline для версии 2.0.13
Проверяет работоспособность всех компонентов
"""
import os
import sys
import requests
import time
from pathlib import Path
from typing import Dict, Any

# URL сервиса из Cloud.ru
API_URL = os.getenv(
    "PADDLEOCR_API_URL",
    "https://af7d4d53-b94a-423b-b7b5-815c886945f4.modelrun.inference.cloud.ru"
)

# API Key
API_KEY = os.getenv(
    "PADDLEOCR_API_KEY",
    "ZDRhOWQ3OTAtZjU4MC00MzA2LThhNTgtMDU1NGFlMjE4OWRl.85a830f9340966e0ad1fd1642884c7c8"
)

# Тестовые изображения
TEST_IMAGES = [
    "test_images/page_0001 (3).png",
    "test_images/page_0002 (1).png",
]

HEADERS = {
    "x-api-key": API_KEY
}

def print_section(title: str):
    """Печать заголовка секции"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_health() -> bool:
    """Тест health endpoint"""
    print_section("1. Health Check")
    try:
        response = requests.get(f"{API_URL}/health", headers=HEADERS, timeout=30)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Service Status: {data.get('status')}")
            print(f"✅ PaddleOCR: {data.get('paddleocr')}")
            print(f"✅ S3 Storage: {data.get('s3_storage')}")
            print(f"✅ Output Dir: {data.get('output_dir')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_ocr_image(image_path: str, return_content: bool = False) -> Dict[str, Any]:
    """Тест OCR обработки изображения"""
    print_section(f"2. OCR Processing: {Path(image_path).name}")
    
    if not Path(image_path).exists():
        print(f"❌ Image not found: {image_path}")
        return {"success": False, "error": "Image not found"}
    
    file_size = Path(image_path).stat().st_size
    print(f"📄 File: {image_path}")
    print(f"📊 Size: {file_size:,} bytes")
    
    try:
        start_time = time.perf_counter()
        
        with open(image_path, 'rb') as f:
            files = {'file': (Path(image_path).name, f, 'image/png')}
            data = {'return_content': return_content}
            
            print(f"⏳ Sending request to {API_URL}/ocr...")
            response = requests.post(
                f"{API_URL}/ocr",
                headers=HEADERS,
                files=files,
                data=data,
                timeout=600  # 10 минут для обработки
            )
        
        elapsed = time.perf_counter() - start_time
        
        print(f"⏱️  Response time: {elapsed:.2f}s")
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status: {result.get('status')}")
            print(f"✅ Input Type: {result.get('input_type')}")
            print(f"⏱️  Elapsed: {result.get('elapsed_sec', 0):.2f}s")
            
            # Локальные файлы
            local_files = result.get('local_files', {})
            if local_files:
                print(f"📁 Local MD: {local_files.get('markdown', 'N/A')}")
                print(f"📁 Local JSON: {local_files.get('json', 'N/A')}")
            
            # S3 файлы
            s3_files = result.get('s3_files', {})
            if s3_files:
                print(f"☁️  S3 Status: {s3_files.get('status', 'N/A')}")
                if s3_files.get('status') == 'uploaded':
                    print(f"☁️  S3 MD URL: {s3_files.get('markdown', 'N/A')}")
                    print(f"☁️  S3 JSON URL: {s3_files.get('json', 'N/A')}")
            
            # Контент (если запрошен)
            if return_content:
                md_text = result.get('markdown_text', '')
                json_data = result.get('json_data', {})
                
                if md_text:
                    print(f"\n📝 Markdown preview (first 500 chars):")
                    print("-" * 80)
                    print(md_text[:500])
                    print("-" * 80)
                
                if json_data:
                    print(f"\n📋 JSON keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
            
            return {
                "success": True,
                "result": result,
                "elapsed": elapsed
            }
        else:
            print(f"❌ OCR processing failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "response": response.text[:500]
            }
            
    except requests.Timeout:
        print(f"❌ Request timeout (>600s)")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}

def test_files_endpoint() -> bool:
    """Тест endpoints для работы с файлами"""
    print_section("3. Files Endpoints")
    
    try:
        # Список файлов
        response = requests.get(
            f"{API_URL}/files?limit=5",
            headers=HEADERS,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"✅ Found {count} files")
            
            files = data.get('files', [])[:3]
            for f in files:
                print(f"  📄 {f.get('filename')} ({f.get('size_bytes', 0):,} bytes)")
            
            return True
        else:
            print(f"❌ Failed to list files: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("\n" + "=" * 80)
    print("  OCR Pipeline Test - Version 2.0.13")
    print("=" * 80)
    print(f"API URL: {API_URL}")
    print(f"Test Images: {len(TEST_IMAGES)}")
    
    results = {
        "health": False,
        "ocr_tests": [],
        "files": False
    }
    
    # 1. Health check
    results["health"] = test_health()
    
    if not results["health"]:
        print("\n❌ Health check failed. Aborting tests.")
        return
    
    # Небольшая задержка перед OCR тестами
    print("\n⏳ Waiting 5 seconds before OCR tests...")
    time.sleep(5)
    
    # 2. OCR тесты
    for img_path in TEST_IMAGES:
        if Path(img_path).exists():
            result = test_ocr_image(img_path, return_content=False)
            results["ocr_tests"].append({
                "image": img_path,
                "result": result
            })
            
            # Пауза между тестами
            if len(TEST_IMAGES) > 1:
                print("\n⏳ Waiting 3 seconds before next test...")
                time.sleep(3)
        else:
            print(f"⚠️  Skipping {img_path} - file not found")
    
    # 3. Files endpoint
    results["files"] = test_files_endpoint()
    
    # Итоговый отчет
    print_section("Test Summary")
    
    print(f"Health Check: {'✅ PASS' if results['health'] else '❌ FAIL'}")
    print(f"Files Endpoint: {'✅ PASS' if results['files'] else '❌ FAIL'}")
    
    print(f"\nOCR Tests: {len(results['ocr_tests'])}")
    for i, test in enumerate(results['ocr_tests'], 1):
        status = "✅ PASS" if test['result'].get('success') else "❌ FAIL"
        image = Path(test['image']).name
        elapsed = test['result'].get('elapsed', 0)
        print(f"  {i}. {image}: {status} ({elapsed:.2f}s)")
    
    # Общий статус
    all_ocr_passed = all(t['result'].get('success') for t in results['ocr_tests'])
    overall = results['health'] and results['files'] and all_ocr_passed
    
    print("\n" + "=" * 80)
    print(f"  Overall Status: {'✅ ALL TESTS PASSED' if overall else '❌ SOME TESTS FAILED'}")
    print("=" * 80)
    
    return overall

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


















