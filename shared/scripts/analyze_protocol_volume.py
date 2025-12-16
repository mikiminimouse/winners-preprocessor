#!/usr/bin/env python3
"""
Анализ объёма протоколов за последние 3 месяца напрямую из MongoDB.

Цели:
- Посчитать, сколько "юнитов" (протоколов) в день/неделю приходит в коллекцию
  `protocols223.purchaseProtocol` — в том же смысле, как их возвращает MCP
  (`purchaseNoticeNumber` → один или несколько URL'ов).
- Посчитать, сколько документов (URL'ов) в день.
- Собрать примеры, где на один протокол приходится несколько URL, и понять причину.

Важно:
- Подключение берётся из `.env`:
  - mongoServer
  - readAllUser
  - readAllPassword
  - sslCertPath
- РФ VPN для MongoDB НЕ нужен (нужен только для скачивания файлов с zakupki.gov.ru).
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Tuple

from dotenv import dotenv_values
from pymongo import MongoClient


@dataclass
class DayStats:
    date: date
    protocols: int = 0          # количество протоколов (юнитов)
    urls: int = 0               # количество URL'ов (документов) по этим протоколам


@dataclass
class MultiUrlSample:
    date: date
    purchase_notice_number: str
    url_count: int
    filenames: List[str]


def get_mongo_client() -> MongoClient:
    """Создаёт Mongo-клиент на основе .env без использования глобального состояния."""
    cfg = dotenv_values(".env")

    mongo_hosts = cfg.get("mongoServer")
    username = cfg.get("readAllUser")
    password = cfg.get("readAllPassword")
    ssl_cert = cfg.get("sslCertPath")

    if not all([mongo_hosts, username, password, ssl_cert]):
        print("✗ Не все обязательные Mongo-параметры найдены в .env:", file=sys.stderr)
        print(f"  mongoServer:  {'OK' if mongo_hosts else 'MISSING'}", file=sys.stderr)
        print(f"  readAllUser:  {'OK' if username else 'MISSING'}", file=sys.stderr)
        print(f"  readAllPassword: {'OK' if password else 'MISSING'}", file=sys.stderr)
        print(f"  sslCertPath:  {'OK' if ssl_cert else 'MISSING'}", file=sys.stderr)
        sys.exit(1)

    url_mongo = f"mongodb://{username}:{password}@{mongo_hosts}/?authSource=protocols223"

    print("Подключение к MongoDB:")
    print(f"  URL: mongodb://{username}:***@{mongo_hosts}/?authSource=protocols223")
    print(f"  CA:  {ssl_cert}")

    client = MongoClient(
        url_mongo,
        tls=True,
        authMechanism="SCRAM-SHA-1",
        tlsAllowInvalidHostnames=True,
        tlsCAFile=ssl_cert,
        serverSelectionTimeoutMS=20_000,
        connectTimeoutMS=20_000,
        socketTimeoutMS=20_000,
    )

    # Бросит исключение, если что-то не так
    ping_result = client.admin.command("ping")
    print("✓ ping:", ping_result)

    return client


def iter_recent_protocols(
    collection,
    days_back: int = 90,
) -> Tuple[Dict[date, DayStats], List[MultiUrlSample]]:
    """
    Итерирует протоколы за последние days_back дней, группируя по датам loadDate.

    Возвращает:
    - day_stats: date → DayStats
    - multi_samples: примеры протоколов с несколькими URL'ами
    """
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days_back)

    print()
    print(f"Анализируем период: {start_dt.date()} .. {end_dt.date()} (последние {days_back} дней)")

    query = {
        "loadDate": {
            "$gte": datetime(start_dt.year, start_dt.month, start_dt.day, 0, 0, 0),
            "$lte": datetime(end_dt.year, end_dt.month, end_dt.day, 23, 59, 59),
        }
    }

    projection = {
        "purchaseInfo.purchaseNoticeNumber": 1,
        "attachments": 1,
        "loadDate": 1,
    }

    day_stats: Dict[date, DayStats] = {}
    multi_samples: List[MultiUrlSample] = []

    total_docs = 0
    total_protocols = 0
    total_urls = 0
    multi_url_protocols = 0

    cursor = collection.find(
        query,
        projection,
        no_cursor_timeout=True,
        batch_size=1000,
    )

    try:
        for doc in cursor:
            total_docs += 1

            ld = doc.get("loadDate")
            if not isinstance(ld, datetime):
                continue
            day = ld.date()

            purchase_info = doc.get("purchaseInfo") or {}
            pn = purchase_info.get("purchaseNoticeNumber")
            if not pn:
                continue

            attachments = doc.get("attachments")
            urls: List[Dict[str, Any]] = []

            # Основной ожидаемый формат: attachments: {document: {...} or [..]}
            if isinstance(attachments, dict):
                docs_field = attachments.get("document", [])
                if isinstance(docs_field, dict):
                    docs_field = [docs_field]
                if isinstance(docs_field, list):
                    for item in docs_field:
                        if isinstance(item, dict) and item.get("url"):
                            urls.append(
                                {
                                    "url": item.get("url"),
                                    "fileName": item.get("fileName", ""),
                                }
                            )
            # На всякий случай — если attachments уже список документов
            elif isinstance(attachments, list):
                for item in attachments:
                    if isinstance(item, dict) and item.get("url"):
                        urls.append(
                            {
                                "url": item.get("url"),
                                "fileName": item.get("fileName", ""),
                            }
                        )

            url_count = len(urls)

            # Обновляем дневную статистику
            if day not in day_stats:
                day_stats[day] = DayStats(date=day)

            day_stats[day].protocols += 1
            day_stats[day].urls += url_count

            total_protocols += 1
            total_urls += url_count

            # Примеры протоколов с несколькими URL
            if url_count > 1:
                multi_url_protocols += 1
                if len(multi_samples) < 50:
                    multi_samples.append(
                        MultiUrlSample(
                            date=day,
                            purchase_notice_number=str(pn),
                            url_count=url_count,
                            filenames=[u.get("fileName", "") for u in urls],
                        )
                    )

            if total_docs % 10_000 == 0:
                print(
                    f"  Обработано документов: {total_docs:,} | "
                    f"протоколов: {total_protocols:,} | URL: {total_urls:,}",
                    flush=True,
                )

    finally:
        cursor.close()

    print()
    print(f"ИТОГО за период:")
    print(f"  документов (Mongo-доков): {total_docs:,}")
    print(f"  протоколов (юнитов, purchaseNoticeNumber): {total_protocols:,}")
    print(f"  документов/URL для скачивания: {total_urls:,}")
    if total_protocols:
        print(f"  среднее URL на протокол: {total_urls / total_protocols:.3f}")
        print(
            f"  протоколов с несколькими URL: {multi_url_protocols:,} "
            f"({multi_url_protocols / total_protocols * 100:.2f}% )"
        )

    return day_stats, multi_samples


def summarize_by_week(day_stats: Dict[date, DayStats]) -> Dict[Tuple[int, int], Dict[str, Any]]:
    """Агрегирует дневную статистику по ISO-неделям (год, неделя)."""
    week_stats: Dict[Tuple[int, int], Dict[str, Any]] = defaultdict(
        lambda: {
            "protocols": 0,
            "urls": 0,
            "days": 0,
        }
    )

    for d, stats in day_stats.items():
        iso_year, iso_week, _ = d.isocalendar()
        key = (iso_year, iso_week)
        week_stats[key]["protocols"] += stats.protocols
        week_stats[key]["urls"] += stats.urls
        week_stats[key]["days"] += 1

    return week_stats


def print_summary(day_stats: Dict[date, DayStats], multi_samples: List[MultiUrlSample]) -> None:
    """Печатает человекочитаемое резюме по дням и неделям."""
    if not day_stats:
        print("✗ Нет данных за указанный период")
        return

    days_sorted = sorted(day_stats.keys())
    total_days = len(days_sorted)

    total_protocols = sum(day_stats[d].protocols for d in days_sorted)
    total_urls = sum(day_stats[d].urls for d in days_sorted)

    avg_protocols_per_day = total_protocols / total_days
    avg_urls_per_day = total_urls / total_days

    print()
    print("=== СУТОЧНАЯ СТАТИСТИКА (агрегировано) ===")
    print(f"Дней в выборке: {total_days}")
    print(f"Всего протоколов: {total_protocols:,}")
    print(f"Всего документов/URL: {total_urls:,}")
    print(f"Среднее протоколов в день: {avg_protocols_per_day:.1f}")
    print(f"Среднее документов/URL в день: {avg_urls_per_day:.1f}")

    week_stats = summarize_by_week(day_stats)
    print()
    print("=== НЕДЕЛЬНАЯ СТАТИСТИКА ===")
    for (iso_year, iso_week), w in sorted(week_stats.items()):
        days = w["days"]
        if not days:
            continue
        avg_p = w["protocols"] / days
        avg_u = w["urls"] / days
        print(
            f"  ISO {iso_year}-W{iso_week:02d}: "
            f"дней={days}, протоколов={w['protocols']:,}, URL={w['urls']:,}, "
            f"~прот/день={avg_p:.1f}, ~URL/день={avg_u:.1f}"
        )

    print()
    print("=== ПРИМЕРЫ ПРОТОКОЛОВ С НЕСКОЛЬКИМИ URL ===")
    if not multi_samples:
        print("  Нет протоколов с несколькими URL в выборке.")
    else:
        for s in multi_samples[:20]:
            print(
                f"  {s.date} PN={s.purchase_notice_number} "
                f"URL={s.url_count} | files={', '.join(s.filenames[:3])}"
            )
        if len(multi_samples) > 20:
            print(f"  ... ещё {len(multi_samples) - 20} протоколов с несколькими URL")


def main() -> None:
    print("=" * 80)
    print("АНАЛИЗ ОБЪЁМА ПРОТОКОЛОВ ЗА ПОСЛЕДНИЕ 3 МЕСЯЦА (MONGO DIRECT)")
    print("=" * 80)

    client = get_mongo_client()
    try:
        db = client["protocols223"]
        collection = db["purchaseProtocol"]

        day_stats, multi_samples = iter_recent_protocols(collection, days_back=90)
        print_summary(day_stats, multi_samples)

        # Дополнительно можно сохранить "сырые" метрики в JSON, если понадобится.
        out_json = Path("protocol_volume_stats_last90d.json")
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "days": [
                {
                    "date": d.isoformat(),
                    "protocols": day_stats[d].protocols,
                    "urls": day_stats[d].urls,
                }
                for d in sorted(day_stats.keys())
            ],
            "multi_url_samples": [
                {
                    "date": s.date.isoformat(),
                    "purchaseNoticeNumber": s.purchase_notice_number,
                    "url_count": s.url_count,
                    "filenames": s.filenames,
                }
                for s in multi_samples
            ],
        }
        out_json.write_text(
            __import__("json").dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print()
        print(f"JSON со статистикой сохранён в: {out_json}")
    finally:
        client.close()


if __name__ == "__main__":
    main()


