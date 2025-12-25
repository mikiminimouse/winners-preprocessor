#!/usr/bin/env python3
"""
Скрипт для очистки данных и запуска обработки архива Vitaly.rar
"""
import os
import shutil
import subprocess
import requests
import time
from pathlib import Path

# Конфигурация
INPUT_DIR = Path("/root/winners_preprocessor/input")
OUTPUT_DIR = Path("/root/winners_preprocessor/output")
EXTRACTED_DIR = Path("/root/winners_preprocessor/extracted")
NORMALIZED_DIR = Path("/root/winners_preprocessor/normalized")
ARCHIVE_DIR = Path("/root/winners_preprocessor/archive")
TEMP_DIR = Path("/root/winners_preprocessor/temp")
VITALY_RAR = Path("/root/winners_preprocessor/Vitaly.rar")

# MongoDB конфигурация
MONGO_SERVER = os.environ.get("MONGO_SERVER", "localhost:27017")
MONGO_METADATA_USER = os.environ.get("MONGO_METADATA_USER", "docling_user")
MONGO_METADATA_PASSWORD = os.environ.get("MONGO_METADATA_PASSWORD", "password")
MONGO_METADATA_DB = os.environ.get("MONGO_METADATA_DB", "docling_metadata")
MONGO_METRICS_COLLECTION = os.environ.get("MONGO_METRICS_COLLECTION", "processing_metrics")
MONGO_MANIFESTS_COLLECTION = os.environ.get("MONGO_METADATA_COLLECTION", "manifests")

ROUTER_API = "http://localhost:8080"


def clear_mongodb():
    """Очищает MongoDB от метрик и других данных."""
    print("=" * 80)
    print("ОЧИСТКА MONGODB")
    print("=" * 80)
    
    try:
        # Используем mongosh через docker exec или напрямую
        # Пробуем через docker exec сначала
        try:
            cmd = [
                "docker", "exec", "docling_mongodb", "mongosh",
                "--quiet",
                "--eval",
                f"db = db.getSiblingDB('{MONGO_METADATA_DB}'); "
                f"metrics_count = db.{MONGO_METRICS_COLLECTION}.countDocuments({{}}); "
                f"manifests_count = db.{MONGO_MANIFESTS_COLLECTION}.countDocuments({{}}); "
                f"db.{MONGO_METRICS_COLLECTION}.deleteMany({{}}); "
                f"db.{MONGO_MANIFESTS_COLLECTION}.deleteMany({{}}); "
                f"print('Удалено метрик: ' + metrics_count + ', манифестов: ' + manifests_count);"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✓ MongoDB очищена через docker exec")
                if result.stdout.strip():
                    print(f"  {result.stdout.strip()}")
                return
        except Exception as docker_error:
            print(f"  Docker exec не сработал: {docker_error}")
        
        # Пробуем напрямую через mongosh
        try:
            # Формируем connection string
            if ":" in MONGO_SERVER:
                host, port = MONGO_SERVER.split(":")
            else:
                host, port = MONGO_SERVER, "27017"
            
            cmd = [
                "mongosh",
                f"mongodb://{MONGO_METADATA_USER}:{MONGO_METADATA_PASSWORD}@{host}:{port}/{MONGO_METADATA_DB}?authSource=admin",
                "--quiet",
                "--eval",
                f"db.{MONGO_METRICS_COLLECTION}.deleteMany({{}}); "
                f"db.{MONGO_MANIFESTS_COLLECTION}.deleteMany({{}}); "
                f"print('Коллекции очищены');"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✓ MongoDB очищена через mongosh")
                if result.stdout.strip():
                    print(f"  {result.stdout.strip()}")
                return
        except Exception as mongosh_error:
            print(f"  mongosh не сработал: {mongosh_error}")
        
        # Если ничего не сработало, просто выводим предупреждение
        print("⚠ Не удалось очистить MongoDB автоматически")
        print("  Вы можете очистить вручную:")
        print(f"  docker exec docling_mongodb mongosh --eval \"db = db.getSiblingDB('{MONGO_METADATA_DB}'); db.{MONGO_METRICS_COLLECTION}.deleteMany({{}}); db.{MONGO_MANIFESTS_COLLECTION}.deleteMany({{}});\"")
        
    except Exception as e:
        print(f"⚠ Ошибка при очистке MongoDB: {e}")
        print("  Продолжаем выполнение...")


def clear_directories():
    """Очищает все рабочие директории."""
    print("\n" + "=" * 80)
    print("ОЧИСТКА ДИРЕКТОРИЙ")
    print("=" * 80)
    
    directories = [INPUT_DIR, OUTPUT_DIR, EXTRACTED_DIR, NORMALIZED_DIR, ARCHIVE_DIR, TEMP_DIR]
    
    for directory in directories:
        if directory.exists():
            # Удаляем все содержимое
            for item in directory.iterdir():
                if item.is_file():
                    item.unlink()
                    print(f"  Удален файл: {item.name}")
                elif item.is_dir():
                    shutil.rmtree(item)
                    print(f"  Удалена директория: {item.name}")
            print(f"✓ Очищена директория: {directory}")
        else:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✓ Создана директория: {directory}")


def extract_vitaly_rar():
    """Извлекает файлы из Vitaly.rar в input директорию."""
    print("\n" + "=" * 80)
    print("ИЗВЛЕЧЕНИЕ ФАЙЛОВ ИЗ Vitaly.rar")
    print("=" * 80)
    
    if not VITALY_RAR.exists():
        raise FileNotFoundError(f"Файл {VITALY_RAR} не найден!")
    
    print(f"Архив найден: {VITALY_RAR}")
    print(f"Размер архива: {VITALY_RAR.stat().st_size / (1024*1024):.2f} MB")
    
    # Пробуем unrar сначала
    try:
        cmd = ["unrar", "x", "-y", str(VITALY_RAR), str(INPUT_DIR)]
        print(f"\nЗапуск команды: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print("✓ Успешно извлечено через unrar")
            print(result.stdout[:500])  # Первые 500 символов вывода
        else:
            # Пробуем 7z как fallback
            print(f"unrar вернул код {result.returncode}, пробуем 7z...")
            cmd = ["7z", "x", str(VITALY_RAR), f"-o{INPUT_DIR}", "-y"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✓ Успешно извлечено через 7z")
            else:
                raise subprocess.CalledProcessError(result.returncode, cmd, result.stderr)
    
    except FileNotFoundError:
        raise FileNotFoundError("Не найдены утилиты unrar или 7z. Установите их.")
    
    # Подсчитываем извлеченные файлы
    extracted_files = list(INPUT_DIR.iterdir())
    file_count = len([f for f in extracted_files if f.is_file()])
    
    print(f"\n✓ Извлечено файлов: {file_count}")
    print(f"✓ Файлы извлечены в: {INPUT_DIR}")
    
    # Показываем первые 10 файлов
    print("\nПервые 10 извлеченных файлов:")
    for i, file_path in enumerate(sorted(extracted_files)[:10], 1):
        if file_path.is_file():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  {i:2}. {file_path.name[:60]:60} ({size_mb:.2f} MB)")
    
    if file_count > 10:
        print(f"  ... и еще {file_count - 10} файлов")
    
    return file_count


def wait_for_router():
    """Ожидает готовности router API."""
    print("\n" + "=" * 80)
    print("ПРОВЕРКА ГОТОВНОСТИ ROUTER API")
    print("=" * 80)
    
    max_attempts = 30
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(f"{ROUTER_API}/health", timeout=5)
            if response.status_code == 200:
                print("✓ Router API готов")
                return True
        except Exception as e:
            pass
        
        print(f"  Попытка {attempt}/{max_attempts}...")
        time.sleep(2)
    
    raise Exception("Router API не отвечает после 30 попыток")


def process_files():
    """Запускает обработку файлов через router API."""
    print("\n" + "=" * 80)
    print("ЗАПУСК ОБРАБОТКИ ФАЙЛОВ")
    print("=" * 80)
    
    try:
        response = requests.post(f"{ROUTER_API}/process_now", timeout=600)
        response.raise_for_status()
        
        result = response.json()
        session_id = result.get("session_id")
        
        print(f"✓ Обработка запущена")
        print(f"  Session ID: {session_id}")
        print(f"  Обработано файлов: {result.get('processed_count', 0)}")
        
        return session_id
    
    except Exception as e:
        raise Exception(f"Ошибка при запуске обработки: {e}")


def wait_for_processing(session_id: str, timeout: int = 300):
    """Ожидает завершения обработки."""
    print("\n" + "=" * 80)
    print("ОЖИДАНИЕ ЗАВЕРШЕНИЯ ОБРАБОТКИ")
    print("=" * 80)
    
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{ROUTER_API}/metrics/processing?session_id={session_id}", timeout=10)
            if response.status_code == 200:
                metrics = response.json()
                completed_at = metrics.get("completed_at")
                
                if completed_at:
                    print("✓ Обработка завершена")
                    return metrics
                
                # Показываем прогресс
                summary = metrics.get("summary", {})
                total_files = summary.get("total_input_files", 0)
                total_units = summary.get("total_units", 0)
                total_errors = summary.get("total_errors", 0)
                
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] Файлов: {total_files}, Unit'ов: {total_units}, Ошибок: {total_errors}")
        
        except Exception as e:
            pass
        
        time.sleep(5)
    
    raise Exception(f"Таймаут ожидания обработки ({timeout} секунд)")


def generate_report(session_id: str):
    """Генерирует финальный отчет."""
    print("\n" + "=" * 80)
    print("ГЕНЕРАЦИЯ ОТЧЕТА")
    print("=" * 80)
    
    # Генерируем отчет через скрипт
    try:
        result = subprocess.run(
            ["python3", "generate_final_report.py", session_id],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("✓ Отчет сгенерирован: FINAL_REPORT.md")
            print(result.stdout)
        else:
            print(f"⚠ Ошибка при генерации отчета: {result.stderr}")
    
    except Exception as e:
        print(f"⚠ Ошибка при генерации отчета: {e}")
    
    # Также выводим через analyze_metrics
    try:
        result = subprocess.run(
            ["python3", "analyze_metrics.py"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("\n" + "=" * 80)
            print("ДЕТАЛЬНЫЙ ОТЧЕТ")
            print("=" * 80)
            print(result.stdout)
        else:
            print(f"⚠ Ошибка при выводе метрик: {result.stderr}")
    
    except Exception as e:
        print(f"⚠ Ошибка при выводе метрик: {e}")


def main():
    """Главная функция."""
    print("=" * 80)
    print("СКРИПТ ОЧИСТКИ И ОБРАБОТКИ")
    print("=" * 80)
    print()
    
    try:
        # Шаг 1: Очистка MongoDB
        clear_mongodb()
        
        # Шаг 2: Очистка директорий
        clear_directories()
        
        # Шаг 3: Извлечение архива
        file_count = extract_vitaly_rar()
        
        # Шаг 4: Ожидание готовности router
        wait_for_router()
        
        # Шаг 5: Запуск обработки
        session_id = process_files()
        
        # Шаг 6: Ожидание завершения
        metrics = wait_for_processing(session_id)
        
        # Шаг 7: Генерация отчета
        generate_report(session_id)
        
        print("\n" + "=" * 80)
        print("ОБРАБОТКА ЗАВЕРШЕНА")
        print("=" * 80)
        print(f"Session ID: {session_id}")
        print(f"Файлов на входе: {file_count}")
        print(f"Отчет сохранен в: FINAL_REPORT.md")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

