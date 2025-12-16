#!/usr/bin/env python3
"""
Локальное тестирование OCR pipeline
Запускает Docker контейнер локально и тестирует pipeline
"""
import subprocess
import requests
import time
import sys
from pathlib import Path

LOCAL_URL = "http://localhost:8081"
TEST_IMAGE = "test_images/page_0001 (3).png"
IMAGE_NAME = "docling-granite-258m.cr.cloud.ru/docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.13"

def check_container_running():
    """Проверяет, запущен ли контейнер"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"ancestor={IMAGE_NAME}", "--format", "{{.ID}}"],
            capture_output=True,
            text=True
        )
        container_id = result.stdout.strip()
        if container_id:
            print(f"✅ Контейнер запущен: {container_id}")
            return True
        else:
            print("⚠️  Контейнер не запущен")
            return False
    except Exception as e:
        print(f"❌ Ошибка проверки контейнера: {e}")
        return False

def start_container():
    """Запускает контейнер"""
    print(f"🚀 Запуск контейнера {IMAGE_NAME}...")
    try:
        # Пробуем сначала без GPU (для базовой проверки)
        # OCR может не работать без GPU, но сервер должен запуститься
        cmd = [
            "docker", "run", "-d",
            "--name", "paddleocr-test",
            "-p", "8081:8081",
            IMAGE_NAME
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            container_id = result.stdout.strip()
            print(f"✅ Контейнер запущен: {container_id}")
            print("⏳ Ожидание инициализации (30 секунд)...")
            time.sleep(30)
            return True
        else:
            print(f"❌ Ошибка запуска: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_health():
    """Тест health endpoint"""
    print("\n📡 Проверка health endpoint...")
    try:
        response = requests.get(f"{LOCAL_URL}/health", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health: {data.get('status')}")
            print(f"✅ PaddleOCR: {data.get('paddleocr')}")
            print(f"✅ S3: {data.get('s3_storage')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def test_ocr(image_path):
    """Тест OCR обработки"""
    print(f"\n🔍 Тест OCR для {Path(image_path).name}...")
    
    if not Path(image_path).exists():
        print(f"❌ Файл не найден: {image_path}")
        return False
    
    try:
        with open(image_path, 'rb') as f:
            files = {'file': (Path(image_path).name, f, 'image/png')}
            data = {'return_content': 'false'}
            
            print("⏳ Отправка запроса...")
            start_time = time.perf_counter()
            response = requests.post(
                f"{LOCAL_URL}/ocr",
                files=files,
                data=data,
                timeout=300
            )
            elapsed = time.perf_counter() - start_time
        
        print(f"⏱️  Время обработки: {elapsed:.2f}s")
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Статус: {result.get('status')}")
            print(f"✅ Elapsed: {result.get('elapsed_sec', 0):.2f}s")
            
            local_files = result.get('local_files', {})
            if local_files:
                md_file = local_files.get('markdown', '')
                json_file = local_files.get('json', '')
                print(f"📁 MD: {Path(md_file).name if md_file else 'N/A'}")
                print(f"📁 JSON: {Path(json_file).name if json_file else 'N/A'}")
            
            return True
        else:
            print(f"❌ Ошибка: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def stop_container():
    """Останавливает контейнер"""
    print("\n🛑 Остановка контейнера...")
    try:
        subprocess.run(
            ["docker", "stop", "paddleocr-test"],
            capture_output=True
        )
        subprocess.run(
            ["docker", "rm", "paddleocr-test"],
            capture_output=True
        )
        print("✅ Контейнер остановлен")
    except Exception as e:
        print(f"⚠️  Ошибка остановки: {e}")

def main():
    """Главная функция"""
    print("=" * 80)
    print("  Локальное тестирование OCR Pipeline")
    print("=" * 80)
    
    # Проверка образа
    print(f"\n📦 Проверка образа {IMAGE_NAME}...")
    try:
        result = subprocess.run(
            ["docker", "images", IMAGE_NAME, "--format", "{{.ID}}"],
            capture_output=True,
            text=True
        )
        if not result.stdout.strip():
            print(f"❌ Образ {IMAGE_NAME} не найден")
            print("   Сначала соберите образ или скачайте из registry")
            return False
        print("✅ Образ найден")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    
    # Проверка/запуск контейнера
    if not check_container_running():
        if not start_container():
            return False
    
    # Тесты
    success = True
    
    if not test_health():
        success = False
    else:
        if not test_ocr(TEST_IMAGE):
            success = False
    
    # Остановка контейнера (опционально)
    stop_after = input("\n❓ Остановить контейнер? (y/n): ").lower().strip()
    if stop_after == 'y':
        stop_container()
    
    print("\n" + "=" * 80)
    print(f"  Результат: {'✅ УСПЕХ' if success else '❌ ОШИБКА'}")
    print("=" * 80)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        stop_container()
        sys.exit(1)

