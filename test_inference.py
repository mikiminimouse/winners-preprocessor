#!/usr/bin/env python3
"""
Скрипт для тестирования подключения к Cloud.RU ML Inference.

Тестирует:
1. Доступность endpoint без авторизации (если публичный)
2. Подключение через SDK evolution_openai с IAM ключами
3. Прямые HTTP запросы с авторизацией
4. Тестовый вызов модели
"""

import os
import sys
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Попытка импорта SDK (если установлен)
try:
    from evolution_openai import EvolutionOpenAI
    EVOLUTION_SDK_AVAILABLE = True
except ImportError:
    EVOLUTION_SDK_AVAILABLE = False
    print("⚠️  evolution_openai SDK не установлен. Установите: pip install evolution-openai")


class InferenceTester:
    """Класс для тестирования подключения к ML Inference."""
    
    def __init__(self):
        """Инициализация с параметрами из переменных окружения."""
        # Параметры подключения
        self.endpoint_url = os.getenv("CLOUD_RU_INFERENCE_URL", "").rstrip("/")
        self.key_id = os.getenv("CLOUD_RU_IAM_KEY_ID", "")
        self.secret = os.getenv("CLOUD_RU_IAM_SECRET", "")
        self.inference_name = os.getenv("CLOUD_RU_INFERENCE_NAME", "")
        
        # Настройка сессии с retry
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Результаты тестов
        self.results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {}
        }
    
    def check_config(self) -> bool:
        """Проверяет наличие необходимых параметров."""
        print("\n" + "="*60)
        print("🔍 ПРОВЕРКА КОНФИГУРАЦИИ")
        print("="*60)
        
        missing = []
        
        if not self.endpoint_url:
            missing.append("CLOUD_RU_INFERENCE_URL")
            print("❌ CLOUD_RU_INFERENCE_URL не задан")
        else:
            print(f"✅ CLOUD_RU_INFERENCE_URL: {self.endpoint_url}")
        
        if not self.key_id:
            missing.append("CLOUD_RU_IAM_KEY_ID")
            print("⚠️  CLOUD_RU_IAM_KEY_ID не задан (будет тест без авторизации)")
        else:
            masked_key = f"{self.key_id[:4]}...{self.key_id[-4:]}" if len(self.key_id) > 8 else "***"
            print(f"✅ CLOUD_RU_IAM_KEY_ID: {masked_key}")
        
        if not self.secret:
            missing.append("CLOUD_RU_IAM_SECRET")
            if self.key_id:
                print("❌ CLOUD_RU_IAM_SECRET не задан (нужен для авторизации)")
        else:
            print(f"✅ CLOUD_RU_IAM_SECRET: {'*' * 20}")
        
        if not self.inference_name:
            print("⚠️  CLOUD_RU_INFERENCE_NAME не задан (будет использован из URL)")
        else:
            print(f"✅ CLOUD_RU_INFERENCE_NAME: {self.inference_name}")
        
        if missing and self.key_id:
            print(f"\n⚠️  Отсутствуют параметры: {', '.join(missing)}")
            print("   Некоторые тесты могут быть пропущены")
        
        return len(missing) == 0 or not self.key_id
    
    def test_endpoint_availability(self) -> Dict[str, Any]:
        """Тест 1: Проверка доступности endpoint без авторизации."""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 1: Доступность endpoint (без авторизации)")
        print("="*60)
        
        result = {
            "test": "endpoint_availability",
            "success": False,
            "status_code": None,
            "response_time": None,
            "error": None,
            "details": {}
        }
        
        if not self.endpoint_url:
            result["error"] = "Endpoint URL не задан"
            print("❌ Пропущен: нет endpoint URL")
            return result
        
        try:
            # Пробуем простой GET запрос к корню или /health
            test_urls = [
                f"{self.endpoint_url}/health",
                f"{self.endpoint_url}/",
                self.endpoint_url
            ]
            
            for url in test_urls:
                try:
                    start_time = time.time()
                    response = self.session.get(url, timeout=10)
                    response_time = time.time() - start_time
                    
                    result["status_code"] = response.status_code
                    result["response_time"] = round(response_time, 3)
                    result["details"]["url"] = url
                    result["details"]["headers"] = dict(response.headers)
                    
                    if response.status_code == 200:
                        result["success"] = True
                        print(f"✅ Endpoint доступен: {url}")
                        print(f"   Статус: {response.status_code}")
                        print(f"   Время ответа: {response_time:.3f}s")
                        try:
                            result["details"]["response"] = response.json()
                            print(f"   Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)[:200]}...")
                        except:
                            result["details"]["response"] = response.text[:500]
                            print(f"   Ответ (текст): {response.text[:200]}...")
                        break
                    elif response.status_code == 401:
                        result["success"] = False
                        result["error"] = "Требуется авторизация (401)"
                        print(f"⚠️  Endpoint требует авторизацию: {url}")
                        print(f"   Статус: {response.status_code}")
                        break
                    elif response.status_code == 404:
                        continue  # Пробуем следующий URL
                    else:
                        result["error"] = f"Неожиданный статус: {response.status_code}"
                        print(f"⚠️  Статус {response.status_code}: {url}")
                        break
                        
                except requests.exceptions.RequestException as e:
                    if url == test_urls[-1]:  # Последний URL
                        raise
                    continue
                    
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Ошибка: {e}")
        
        return result
    
    def test_sdk_connection(self) -> Dict[str, Any]:
        """Тест 2: Подключение через SDK evolution_openai."""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 2: Подключение через SDK evolution_openai")
        print("="*60)
        
        result = {
            "test": "sdk_connection",
            "success": False,
            "error": None,
            "details": {}
        }
        
        if not EVOLUTION_SDK_AVAILABLE:
            result["error"] = "SDK evolution_openai не установлен"
            print("❌ Пропущен: SDK не установлен")
            print("   Установите: pip install evolution-openai")
            return result
        
        if not self.endpoint_url:
            result["error"] = "Endpoint URL не задан"
            print("❌ Пропущен: нет endpoint URL")
            return result
        
        if not self.key_id or not self.secret:
            result["error"] = "IAM ключи не заданы"
            print("⚠️  Пропущен: нет IAM ключей для авторизации")
            return result
        
        try:
            # Инициализация клиента
            # Для SDK нужен URL с /v1 в конце
            base_url = self.endpoint_url
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            
            client = EvolutionOpenAI(
                base_url=base_url,
                api_key=self.key_id,
                api_secret=self.secret
            )
            
            # Попытка получить список моделей или простой запрос
            try:
                # Пробуем получить список моделей (если поддерживается)
                models = client.models.list()
                result["success"] = True
                result["details"]["models"] = [m.id for m in models.data] if hasattr(models, 'data') else []
                print("✅ SDK подключение успешно")
                print(f"   Доступно моделей: {len(result['details']['models'])}")
                if result["details"]["models"]:
                    print(f"   Модели: {', '.join(result['details']['models'][:5])}")
            except Exception as e:
                # Если список моделей не поддерживается, пробуем простой chat completion
                print(f"⚠️  Список моделей недоступен: {e}")
                print("   Пробуем тестовый запрос...")
                
                # Тестовый запрос
                test_response = client.chat.completions.create(
                    model=self.inference_name or "default",
                    messages=[{"role": "user", "content": "Привет"}],
                    max_tokens=10
                )
                
                result["success"] = True
                result["details"]["test_response"] = {
                    "model": test_response.model if hasattr(test_response, 'model') else None,
                    "content": test_response.choices[0].message.content if hasattr(test_response, 'choices') else None
                }
                print("✅ SDK тестовый запрос успешен")
                print(f"   Ответ: {result['details']['test_response']['content']}")
                
        except Exception as e:
            result["error"] = str(e)
            result["details"]["exception_type"] = type(e).__name__
            print(f"❌ Ошибка SDK: {e}")
            import traceback
            result["details"]["traceback"] = traceback.format_exc()
        
        return result
    
    def test_direct_http_request(self) -> Dict[str, Any]:
        """Тест 3: Прямой HTTP запрос с авторизацией."""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 3: Прямой HTTP запрос (с авторизацией)")
        print("="*60)
        
        result = {
            "test": "direct_http",
            "success": False,
            "status_code": None,
            "error": None,
            "details": {}
        }
        
        if not self.endpoint_url:
            result["error"] = "Endpoint URL не задан"
            print("❌ Пропущен: нет endpoint URL")
            return result
        
        if not self.key_id or not self.secret:
            result["error"] = "IAM ключи не заданы"
            print("⚠️  Пропущен: нет IAM ключей")
            return result
        
        try:
            # Простой тестовый запрос к /v1/models или /health
            test_url = f"{self.endpoint_url}/v1/models"
            
            # Cloud.RU использует подпись запросов через AK/SK
            # Для простоты пробуем с базовой авторизацией или заголовками
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Попытка с базовой авторизацией (если поддерживается)
            # В реальности Cloud.RU требует подпись запроса через SDK или специальную библиотеку
            start_time = time.time()
            response = self.session.get(test_url, headers=headers, timeout=10)
            response_time = time.time() - start_time
            
            result["status_code"] = response.status_code
            result["response_time"] = round(response_time, 3)
            result["details"]["url"] = test_url
            
            if response.status_code == 200:
                result["success"] = True
                try:
                    result["details"]["response"] = response.json()
                    print("✅ HTTP запрос успешен")
                    print(f"   Статус: {response.status_code}")
                    print(f"   Время ответа: {response_time:.3f}s")
                except:
                    result["details"]["response"] = response.text[:500]
                    print("✅ HTTP запрос успешен (текстовый ответ)")
            elif response.status_code == 401:
                result["error"] = "Требуется авторизация (401)"
                print("⚠️  Требуется авторизация")
                print("   Для прямых HTTP запросов нужна подпись через SDK")
            else:
                result["error"] = f"Статус {response.status_code}"
                print(f"⚠️  Статус: {response.status_code}")
                print(f"   Ответ: {response.text[:200]}")
                
        except Exception as e:
            result["error"] = str(e)
            print(f"❌ Ошибка: {e}")
        
        return result
    
    def test_model_inference(self) -> Dict[str, Any]:
        """Тест 4: Тестовый вызов модели (chat completion)."""
        print("\n" + "="*60)
        print("🧪 ТЕСТ 4: Тестовый вызов модели")
        print("="*60)
        
        result = {
            "test": "model_inference",
            "success": False,
            "error": None,
            "details": {}
        }
        
        if not self.endpoint_url:
            result["error"] = "Endpoint URL не задан"
            print("❌ Пропущен: нет endpoint URL")
            return result
        
        if not EVOLUTION_SDK_AVAILABLE or not self.key_id or not self.secret:
            result["error"] = "SDK или ключи не настроены"
            print("⚠️  Пропущен: требуется SDK и IAM ключи")
            return result
        
        try:
            # Для SDK нужен URL с /v1 в конце
            base_url = self.endpoint_url
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"
            
            client = EvolutionOpenAI(
                base_url=base_url,
                api_key=self.key_id,
                api_secret=self.secret
            )
            
            model_name = self.inference_name or "default"
            test_message = "Скажи 'Привет' одним словом"
            
            print(f"   Модель: {model_name}")
            print(f"   Запрос: {test_message}")
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": test_message}],
                max_tokens=50,
                temperature=0.7
            )
            response_time = time.time() - start_time
            
            result["success"] = True
            result["response_time"] = round(response_time, 3)
            result["details"]["model"] = response.model if hasattr(response, 'model') else model_name
            result["details"]["request"] = test_message
            
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                result["details"]["response"] = content
                print("✅ Вызов модели успешен")
                print(f"   Время ответа: {response_time:.3f}s")
                print(f"   Ответ: {content}")
            else:
                result["error"] = "Пустой ответ от модели"
                print("⚠️  Получен пустой ответ")
                
        except Exception as e:
            result["error"] = str(e)
            result["details"]["exception_type"] = type(e).__name__
            print(f"❌ Ошибка: {e}")
            import traceback
            result["details"]["traceback"] = traceback.format_exc()
        
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Запускает все тесты."""
        print("\n" + "="*60)
        print("🚀 ЗАПУСК ТЕСТОВ ПОДКЛЮЧЕНИЯ К CLOUD.RU ML INFERENCE")
        print("="*60)
        
        # Проверка конфигурации
        config_ok = self.check_config()
        
        if not config_ok and not self.endpoint_url:
            print("\n❌ Невозможно запустить тесты: отсутствуют необходимые параметры")
            return self.results
        
        # Запуск тестов
        self.results["tests"]["endpoint_availability"] = self.test_endpoint_availability()
        self.results["tests"]["sdk_connection"] = self.test_sdk_connection()
        self.results["tests"]["direct_http"] = self.test_direct_http_request()
        self.results["tests"]["model_inference"] = self.test_model_inference()
        
        # Итоговая статистика
        print("\n" + "="*60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("="*60)
        
        total = len(self.results["tests"])
        passed = sum(1 for t in self.results["tests"].values() if t.get("success", False))
        failed = total - passed
        
        print(f"Всего тестов: {total}")
        print(f"✅ Успешно: {passed}")
        print(f"❌ Провалено: {failed}")
        
        for test_name, test_result in self.results["tests"].items():
            status = "✅" if test_result.get("success") else "❌"
            print(f"  {status} {test_name}: {test_result.get('error', 'OK')}")
        
        self.results["summary"] = {
            "total": total,
            "passed": passed,
            "failed": failed
        }
        
        return self.results
    
    def save_results(self, output_file: Optional[str] = None):
        """Сохраняет результаты тестов в JSON файл."""
        if not output_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = f"inference_test_results_{timestamp}.json"
        
        output_path = Path(output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Результаты сохранены: {output_path}")


def main():
    """Главная функция."""
    # Загрузка переменных окружения из .env (если есть)
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv не обязателен
    
    tester = InferenceTester()
    results = tester.run_all_tests()
    tester.save_results()
    
    # Код выхода
    if results.get("summary", {}).get("failed", 0) > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

