#!/usr/bin/env python3
"""
Скрипт для автоматического пуша Docker образа в Cloud.ru Artifact Registry
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def load_env_vars():
    """Загрузка переменных окружения из .env файла"""
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("✅ Переменные окружения загружены из .env")
    else:
        print("⚠️  Файл .env не найден")

def check_credentials():
    """Проверка наличия учетных данных"""
    key_id = os.environ.get('CLOUD_RU_IAM_KEY_ID')
    secret = os.environ.get('CLOUD_RU_IAM_SECRET')
    
    if not key_id or not secret:
        print("❌ Не найдены учетные данные Cloud.ru IAM")
        print("   Пожалуйста, заполните переменные в файле .env:")
        print("   CLOUD_RU_IAM_KEY_ID=ваш_key_id")
        print("   CLOUD_RU_IAM_SECRET=ваш_secret_key")
        return False
    
    if key_id == '' or secret == '':
        print("❌ Учетные данные Cloud.ru IAM пусты")
        print("   Пожалуйста, заполните переменные в файле .env")
        return False
    
    print("✅ Учетные данные Cloud.ru IAM найдены")
    return True

def docker_login():
    """Авторизация в Docker registry"""
    registry = "docling-granite-258m.cr.cloud.ru"
    key_id = os.environ.get('CLOUD_RU_IAM_KEY_ID')
    secret = os.environ.get('CLOUD_RU_IAM_SECRET')
    
    print(f"🔐 Авторизация в {registry}...")
    
    try:
        # Выполняем docker login
        result = subprocess.run([
            "docker", "login", registry,
            "-u", key_id,
            "--password-stdin"
        ], input=secret.encode(), capture_output=True, check=True)
        
        print("✅ Авторизация успешна")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка авторизации: {e.stderr.decode()}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при авторизации: {e}")
        return False

def tag_image():
    """Присвоение тега образу"""
    source_image = "docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.14"
    target_image = "docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.14"
    latest_image = "docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest"
    
    print("🏷️  Присвоение тегов образу...")
    
    try:
        # Проверяем наличие исходного образа
        result = subprocess.run(["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"], 
                              capture_output=True, text=True, check=True)
        images = result.stdout.strip().split('\n')
        
        if source_image not in images:
            print(f"⚠️  Образ {source_image} не найден локально")
            print("   Убедитесь, что образ собран командой:")
            print("   docker build -t docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.14 -f ocr_vl/service/Dockerfile .")
            return False
        
        # Присваиваем теги
        subprocess.run(["docker", "tag", source_image, target_image], check=True)
        subprocess.run(["docker", "tag", source_image, latest_image], check=True)
        
        print("✅ Теги присвоены успешно")
        print(f"   📦 {target_image}")
        print(f"   📦 {latest_image}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при присвоении тегов: {e}")
        return False
    except Exception as e:
        print(f"❌ Ошибка при присвоении тегов: {e}")
        return False

def push_image():
    """Пуш образа в registry"""
    images = [
        "docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.14",
        "docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest"
    ]
    
    registry = "docling-granite-258m.cr.cloud.ru"
    print(f"📤 Пуш образов в {registry}...")
    
    for image in images:
        print(f"   📦 Пуш {image}...")
        try:
            # Выполняем пуш образа
            process = subprocess.Popen([
                "docker", "push", image
            ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Выводим прогресс
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(f"      {output.strip()}")
            
            rc = process.poll()
            if rc == 0:
                print(f"   ✅ {image} загружен успешно")
            else:
                print(f"   ❌ Ошибка при пуше {image}")
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка при пуше {image}: {e}")
            return False
    
    return True

def main():
    """Основная функция"""
    print("🚀 АВТОМАТИЧЕСКИЙ ПУШ DOCKER ОБРАЗА В CLOUD.RU ARTIFACT REGISTRY")
    print("=" * 70)
    print()
    
    # Загружаем переменные окружения
    load_env_vars()
    
    # Проверяем учетные данные
    if not check_credentials():
        sys.exit(1)
    
    # Авторизуемся в registry
    if not docker_login():
        sys.exit(1)
    
    # Присваиваем теги
    if not tag_image():
        sys.exit(1)
    
    # Пушим образ
    print()
    if push_image():
        print()
        print("🎉 ПУШ ЗАВЕРШЕН УСПЕШНО!")
        print()
        print("📊 Результаты:")
        print("   ✅ Образ docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.14")
        print("   ✅ Образ docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:latest")
        print()
        print("📋 Следующие шаги:")
        print("   1. Перейдите в консоль Cloud.ru ML Inference")
        print("   2. Создайте новый сервис")
        print("   3. Укажите образ: docling-granite-258m.cr.cloud.ru/paddleocr-vl-service:2.0.14")
        print("   4. Откройте порты: 8081 (API) и 7860 (Web UI)")
        print("   5. Настройте переменные окружения при необходимости")
        print()
        print("✅ ГОТОВО К ДЕПЛОЮ!")
    else:
        print()
        print("❌ ОШИБКА ПРИ ПУШЕ ОБРАЗА")
        sys.exit(1)

if __name__ == "__main__":
    main()
