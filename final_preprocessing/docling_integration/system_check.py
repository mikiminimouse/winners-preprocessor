"""
Проверка готовности системы для запуска Docling pipeline.
Валидирует зависимости, версии, доступность сервисов.
"""
import sys
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def check_python_version(min_version: tuple = (3, 9)) -> Dict[str, Any]:
    """Проверяет версию Python."""
    current = sys.version_info[:2]
    is_ok = current >= min_version

    return {
        "check": "python_version",
        "status": "ok" if is_ok else "error",
        "message": f"Python {current[0]}.{current[1]} ({'OK' if is_ok else f'Required: {min_version[0]}.{min_version[1]}+'})",
        "details": {
            "current": f"{current[0]}.{current[1]}",
            "required": f"{min_version[0]}.{min_version[1]}+",
        }
    }


def check_docling_installed() -> Dict[str, Any]:
    """Проверяет установлен ли Docling."""
    try:
        from ._docling_import import is_docling_available

        if not is_docling_available():
            return {
                "check": "docling_installed",
                "status": "error",
                "message": "Docling not available",
                "fix": "pip install docling>=2.0.0",
            }

        # Пытаемся получить версию
        try:
            from importlib.metadata import version
            docling_version = version('docling')
        except Exception:
            docling_version = "unknown"

        return {
            "check": "docling_installed",
            "status": "ok",
            "message": f"Docling {docling_version} installed",
            "details": {"version": docling_version}
        }

    except ImportError as e:
        return {
            "check": "docling_installed",
            "status": "error",
            "message": f"Docling import failed: {e}",
            "fix": "pip install docling>=2.0.0",
        }


def check_pymongo_installed() -> Dict[str, Any]:
    """Проверяет установлен ли PyMongo."""
    try:
        import pymongo
        from importlib.metadata import version
        pymongo_version = version('pymongo')

        return {
            "check": "pymongo_installed",
            "status": "ok",
            "message": f"PyMongo {pymongo_version} installed",
            "details": {"version": pymongo_version}
        }
    except ImportError:
        return {
            "check": "pymongo_installed",
            "status": "warning",
            "message": "PyMongo not installed (MongoDB export disabled)",
            "fix": "pip install pymongo>=4.0.0",
        }


def check_mongodb_connection() -> Dict[str, Any]:
    """Проверяет подключение к MongoDB."""
    try:
        # Пытаемся подключиться к MongoDB
        import pymongo
        import os

        # Получаем настройки из env vars (как в mongodb.py)
        mongo_server = os.environ.get("LOCAL_MONGO_SERVER") or os.environ.get("MONGO_METADATA_SERVER", "localhost:27018")
        mongo_user = os.environ.get("MONGO_METADATA_USER", "admin")
        mongo_password = os.environ.get("MONGO_METADATA_PASSWORD", "password")

        # Пытаемся подключиться
        try:
            client = pymongo.MongoClient(
                f"mongodb://{mongo_user}:{mongo_password}@{mongo_server}/",
                serverSelectionTimeoutMS=2000  # 2 секунды таймаут
            )
            # Проверяем подключение
            client.admin.command('ping')
            client.close()

            return {
                "check": "mongodb_connection",
                "status": "ok",
                "message": f"MongoDB connection successful ({mongo_server})",
                "details": {"server": mongo_server}
            }
        except Exception as e:
            return {
                "check": "mongodb_connection",
                "status": "warning",
                "message": f"MongoDB not available: {str(e)[:50]}",
                "fix": "Start MongoDB or set env vars: LOCAL_MONGO_SERVER, MONGO_METADATA_USER, MONGO_METADATA_PASSWORD",
            }

    except ImportError:
        return {
            "check": "mongodb_connection",
            "status": "warning",
            "message": "PyMongo not installed (skip MongoDB check)",
            "fix": "pip install pymongo>=4.0.0",
        }


def check_ready2docling_structure(data_dir: Path) -> Dict[str, Any]:
    """Проверяет структуру Ready2Docling."""
    ready2docling = data_dir / "Ready2Docling"

    if not ready2docling.exists():
        return {
            "check": "ready2docling_structure",
            "status": "error",
            "message": f"Ready2Docling directory not found: {ready2docling}",
            "fix": "Run docprep pipeline first",
        }

    # Проверяем наличие UNIT
    unit_dirs = list(ready2docling.rglob("UNIT_*"))
    unit_count = len([d for d in unit_dirs if d.is_dir()])

    if unit_count == 0:
        return {
            "check": "ready2docling_structure",
            "status": "warning",
            "message": "No UNIT directories found",
            "details": {"unit_count": 0}
        }

    # Проверяем наличие contract файлов
    units_with_contract = sum(1 for d in unit_dirs if (d / "docprep.contract.json").exists())

    return {
        "check": "ready2docling_structure",
        "status": "ok",
        "message": f"Found {unit_count} units, {units_with_contract} with contracts",
        "details": {
            "unit_count": unit_count,
            "units_with_contract": units_with_contract,
            "units_without_contract": unit_count - units_with_contract,
        }
    }


def run_system_check(data_dir: Optional[Path] = None, verbose: bool = True) -> Dict[str, Any]:
    """
    Выполняет полную проверку готовности системы.

    Args:
        data_dir: Путь к Data директории (опционально)
        verbose: Выводить результаты в лог

    Returns:
        Словарь с результатами всех проверок
    """
    checks = []

    # Обязательные проверки
    checks.append(check_python_version())
    checks.append(check_docling_installed())
    checks.append(check_pymongo_installed())
    checks.append(check_mongodb_connection())

    # Проверка данных (если указана директория)
    if data_dir:
        checks.append(check_ready2docling_structure(data_dir))

    # Подсчет результатов
    status_counts = {
        "ok": sum(1 for c in checks if c["status"] == "ok"),
        "warning": sum(1 for c in checks if c["status"] == "warning"),
        "error": sum(1 for c in checks if c["status"] == "error"),
    }

    overall_status = "ok"
    if status_counts["error"] > 0:
        overall_status = "error"
    elif status_counts["warning"] > 0:
        overall_status = "warning"

    result = {
        "overall_status": overall_status,
        "checks": checks,
        "summary": status_counts,
    }

    # Вывод в лог
    if verbose:
        logger.info("=" * 60)
        logger.info("System Readiness Check")
        logger.info("=" * 60)

        for check in checks:
            status_icon = {"ok": "✅", "warning": "⚠️", "error": "❌"}[check["status"]]
            logger.info(f"{status_icon} {check['message']}")

            if check["status"] != "ok" and "fix" in check:
                logger.info(f"   💡 Fix: {check['fix']}")

        logger.info("=" * 60)
        logger.info(f"Summary: {status_counts['ok']} OK, {status_counts['warning']} warnings, {status_counts['error']} errors")
        logger.info("=" * 60)

        if overall_status == "error":
            logger.error("❌ System not ready. Please fix errors above.")
        elif overall_status == "warning":
            logger.warning("⚠️ System ready with warnings. Some features may be disabled.")
        else:
            logger.info("✅ System ready!")

    return result


def is_system_ready(data_dir: Optional[Path] = None) -> bool:
    """
    Быстрая проверка готовности системы.

    Returns:
        True если система готова (нет критических ошибок)
    """
    result = run_system_check(data_dir, verbose=False)
    return result["overall_status"] != "error"
