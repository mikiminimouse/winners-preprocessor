#!/usr/bin/env python3
"""
Тестовый скрипт: попробовать скачать несколько документов по URL с zakupki.gov.ru.

Берём первые N протоколов из test_protocols_mcp_combined_500.json
и пробуем скачать максимум один файл из каждого, логируя статусы и ошибки.
"""
import json
from pathlib import Path
from typing import Any, Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


MAX_PROTOCOLS = 20  # сколько протоколов смотреть максимум
MAX_SUCCESS_FILES = 5  # сколько удачных скачиваний достаточно

# Простейший UA от десктопного браузера, чтобы минимизировать блокировки по user-agent
BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def make_session() -> requests.Seшlfdfssion:
    """
    Создаёт requests.Session с ретраями и приличным User-Agent.
    Работает поверх уже настроенного РФ VPN и системного роутинга.
    """
    sess = requests.Session()

    # Ретраи на сетевые глюки/5xx, но не превращаем это в бесконечный цикл
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1.0,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)

    sess.headers.update(
        {
            "User-Agent": BROWSER_UA,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        }
    )
    return sess


def try_download(
    url: str,
    filename: str,
    idx: int,
    session: requests.Session | None = None,
) -> Dict[str, Any]:
    """Пробует скачать один URL, возвращает подробный результат.

    ВАЖНО: этот код не настраивает VPN, он просто использует системный роутинг.
    РФ VPN должен быть уже поднят на хосте (openvpn + split-tunnel).
    """
    print(f"\n[{idx}] URL: {url}")
    print(f"[{idx}] Имя файла: {filename}")

    result: Dict[str, Any] = {
        "url": url,
        "filename": filename,
        "status_code": None,
        "size": 0,
        "ok": False,
        "error": None,
        "saved_path": None,
        "strategy": None,
    }

    sess = session or make_session()

    # 1) попытка обычным GET c редиректами
    headers = {
        # Иногда zakupki чувствительны к Referer/Host, но начнём с простого.
        "Referer": "https://zakupki.gov.ru/",
    }

    try:
        resp = sess.get(
            url,
            timeout=60,
            allow_redirects=True,
            verify=True,  # при проблемах с сертификатом можно временно поставить False
            headers=headers,
        )
        result["strategy"] = "session+ua+referer"
        result["status_code"] = resp.status_code
        result["size"] = len(resp.content)

        print(f"[{idx}] HTTP status: {resp.status_code}")
        print(f"[{idx}] Content-Type: {resp.headers.get('Content-Type', 'unknown')}")
        print(f"[{idx}] Content-Length header: {resp.headers.get('Content-Length', 'unknown')}")
        print(f"[{idx}] Фактический размер контента: {len(resp.content)} байт")

        if resp.status_code == 200 and len(resp.content) > 0:
            out_dir = Path("input/vpn_test")
            out_dir.mkdir(parents=True, exist_ok=True)

            safe_name = filename.replace("/", "_").replace("\\", "_")
            out_path = out_dir / safe_name

            with out_path.open("wb") as f:
                f.write(resp.content)

            result["ok"] = True
            result["saved_path"] = str(out_path.resolve())
            print(f"[{idx}] ✓ Файл сохранён: {out_path.resolve()}")
            print(f"[{idx}] ✓ Размер файла на диске: {out_path.stat().st_size} байт")
        else:
            print(f"[{idx}] ✗ Неуспешный HTTP или пустой ответ, файл НЕ сохраняю.")
    except requests.exceptions.Timeout:
        result["error"] = "timeout"
        print(f"[{idx}] ✗ Timeout при обращении к URL (60 секунд)")
    except requests.exceptions.ConnectionError as e:
        result["error"] = f"connection_error: {e}"
        print(f"[{idx}] ✗ Ошибка соединения: {e}")
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"
        print(f"[{idx}] ✗ Неожиданная ошибка: {type(e).__name__}: {e}")

    return result


def main() -> None:
    json_path = Path("test_protocols_mcp_combined_500.json")
    if not json_path.exists():
        print(f"✗ Файл с протоколами не найден: {json_path}")
        return

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    protocols = data.get("protocols", {})
    if not protocols:
        print("✗ В JSON нет поля 'protocols' или оно пустое")
        return

    keys = list(protocols.keys())
    print(f"Всего протоколов в файле: {len(keys)}")

    tested = 0
    success_count = 0
    fail_count = 0

    for idx, purchase_number in enumerate(keys[:MAX_PROTOCOLS], start=1):
        if success_count >= MAX_SUCCESS_FILES:
            break

        doc_info = protocols[purchase_number]

        # Один протокол может иметь словарь или список документов
        docs = [doc_info] if isinstance(doc_info, dict) else list(doc_info)
        if not docs:
            continue

        # Берём первый документ с валидным URL
        chosen_doc = None
        for d in docs:
            if isinstance(d, Dict) and d.get("url"):
                chosen_doc = d
                break

        if not chosen_doc:
            print(f"\n[{idx}] Протокол {purchase_number}: нет документов с URL, пропускаю")
            continue

        url = chosen_doc.get("url")
        filename = chosen_doc.get("fileName", f"{purchase_number}.bin")

        print(f"\n=== Протокол {purchase_number} (#{idx}) ===")
        res = try_download(url, filename, idx)

        tested += 1
        if res["ok"]:
            success_count += 1
        else:
            fail_count += 1

    print("\n===== ИТОГ =====")
    print(f"Протестировано протоколов (до {MAX_PROTOCOLS}): {tested}")
    print(f"Успешно скачано файлов: {success_count}")
    print(f"Ошибок/неуспешных попыток: {fail_count}")


if __name__ == "__main__":
    main()

