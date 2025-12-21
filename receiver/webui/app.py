"""
Основное приложение Gradio WebUI для управления и мониторинга компонентов receiver.
"""

import os
import sys
import gradio as gr
import logging
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json
import base64
from io import BytesIO
from PIL import Image

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настройка логирования ПЕРЕД импортами
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем конфигурацию из .env ПЕРЕД импортом компонентов
from receiver.core.config import load_env_file
env_file = project_root / ".env"
if env_file.exists():
    load_env_file(env_file)
    logger.info(f"✅ Загружена конфигурация из {env_file}")
else:
    logger.warning(f"⚠️ Файл .env не найден: {env_file}")

# Импортируем наши компоненты
from receiver.core.config import get_config
from receiver.sync_db.enhanced_service import EnhancedSyncService
from receiver.sync_db.health_checks import run_comprehensive_health_check
from receiver.sync_db.analytics import SyncAnalytics
from receiver.downloader.enhanced_service import EnhancedProtocolDownloader
from receiver.vpn_utils import check_zakupki_access, check_vpn_connectivity, ensure_vpn_connected, get_vpn_status
from receiver.webui.charts import (
    create_sync_trend_chart, create_performance_chart, create_error_distribution_chart,
    create_sync_progress_chart, create_download_progress_chart
)
from receiver.webui.health_panel import (
    check_vpn_health, check_remote_mongo_health, check_local_mongo_health,
    check_environment_health, check_ssl_health, check_zakupki_health,
    check_all_health_components, run_individual_check, get_comprehensive_health_log,
    get_status_color, get_status_icon
)

# Получаем конфигурацию
config = get_config()

# Глобальные переменные для сервисов
sync_service = None
downloader_service = None
analytics_service = None

def initialize_services():
    """Инициализирует сервисы для работы с компонентами."""
    global sync_service, downloader_service, analytics_service
    
    try:
        sync_service = EnhancedSyncService()
        downloader_service = EnhancedProtocolDownloader()
        analytics_service = SyncAnalytics()
        logger.info("Services initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        return False

def get_health_status():
    """Получает статус здоровья системы."""
    try:
        results = run_comprehensive_health_check()
        
        # Форматируем результаты для отображения
        status_lines = []
        healthy_count = 0
        total_count = 0
        
        # results может быть словарем или списком
        if isinstance(results, dict):
            results_list = list(results.values())
        elif isinstance(results, list):
            results_list = results
        else:
            return "❌ Error", f"❌ Unexpected results type: {type(results)}"
        
        for result in results_list:
            # Проверяем, что result имеет атрибут status
            if hasattr(result, 'status') and hasattr(result, 'name') and hasattr(result, 'message'):
                total_count += 1
                status_icon = "✅" if result.status == "healthy" else "⚠️" if result.status == "degraded" else "❌"
                status_lines.append(f"{status_icon} {result.name}: {result.message}")
                if result.status == "healthy":
                    healthy_count += 1
            else:
                # Если это не объект HealthCheckResult, попробуем обработать как строку
                status_lines.append(f"⚠️ Unknown result: {str(result)}")
        
        if total_count == 0:
            return "⚠️ No health checks available", "No health check results found"
        
        overall_status = f"✅ {healthy_count}/{total_count} checks passed" if healthy_count == total_count else f"⚠️ {healthy_count}/{total_count} checks passed"
        
        return overall_status, "\n".join(status_lines)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in get_health_status: {error_details}")
        return "❌ Error", f"❌ Failed to check health: {e}\n\nDetails: {error_details}"

def get_sync_statistics():
    """Получает статистику синхронизации."""
    try:
        if analytics_service is None:
            return "❌ Analytics service not available", ""
        
        # Получаем последние данные синхронизации
        recent_data = analytics_service.get_historical_sync_data(days=7)
        
        if not recent_data:
            return "ℹ️ No recent sync data", ""
        
        # Форматируем данные для отображения
        stats_lines = []
        total_scanned = 0
        total_inserted = 0
        total_errors = 0
        
        for record in recent_data:
            stats_lines.append(f"📅 {record.date}:")
            stats_lines.append(f"   🔍 Scanned: {record.scanned_documents}")
            stats_lines.append(f"   💾 Inserted: {record.inserted_documents}")
            stats_lines.append(f"   ⚠️  Errors: {record.processing_errors}")
            stats_lines.append("")
            
            total_scanned += record.scanned_documents
            total_inserted += record.inserted_documents
            total_errors += record.processing_errors
        
        summary = f"📊 Last 7 days: {total_scanned} scanned, {total_inserted} inserted, {total_errors} errors"
        
        return summary, "\n".join(stats_lines)
    except Exception as e:
        return "❌ Error", f"❌ Failed to get sync statistics: {e}"

def get_download_statistics():
    """Получает статистику загрузки."""
    try:
        # Здесь должна быть логика получения статистики загрузки
        # Пока возвращаем заглушку
        return "ℹ️ Download statistics not implemented", ""
    except Exception as e:
        return "❌ Error", f"❌ Failed to get download statistics: {e}"

def sync_protocols_handler(date_str: str, limit: int = 0):
    """Обработчик синхронизации протоколов с детальными метриками."""
    try:
        if sync_service is None:
            return "❌ Sync service not available", "", "", ""
        
        # Парсим дату
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Выполняем синхронизацию
        result = sync_service.sync_protocols_for_date(target_date, limit if limit > 0 else None)
        
        # Форматируем детальные метрики
        metrics_text = f"""📊 Детальные метрики синхронизации:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Дата: {date_str}
⏱️  Время выполнения: {result.duration:.2f} секунд
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 Основные показатели:
  • Отсканировано записей: {result.scanned}
  • Вставлено новых: {result.inserted}
  • Пропущено (уже существует): {result.skipped_existing}
  • Ошибок: {result.errors_count}
  
📊 Статистика:
  • Успешность: {((result.inserted + result.skipped_existing) / result.scanned * 100) if result.scanned > 0 else 0:.1f}%
  • Скорость обработки: {result.scanned / result.duration if result.duration > 0 else 0:.2f} записей/сек
"""
        
        # Формируем информацию об ошибках
        errors_text = ""
        if result.errors and len(result.errors) > 0:
            errors_text = f"\n⚠️  Ошибки ({len(result.errors)}):\n"
            for i, error in enumerate(result.errors[:10], 1):  # Показываем первые 10
                errors_text += f"  {i}. {error}\n"
            if len(result.errors) > 10:
                errors_text += f"  ... и еще {len(result.errors) - 10} ошибок\n"
        
        # Создаем график прогресса
        chart_data = {
            "scanned": result.scanned,
            "inserted": result.inserted,
            "skipped": result.skipped_existing,
            "errors": result.errors_count
        }
        
        # Создаем график
        chart_image_base64 = create_sync_progress_chart(chart_data, date_str)
        
        # Конвертируем base64 в PIL Image
        chart_image = None
        if chart_image_base64 and chart_image_base64.startswith("data:image"):
            try:
                # Извлекаем base64 данные
                img_data = chart_image_base64.split(",")[1]
                img_bytes = base64.b64decode(img_data)
                chart_image = Image.open(BytesIO(img_bytes))
            except Exception as e:
                logger.error(f"Error converting chart image: {e}")
        
        # Общий статус
        if result.success:
            status_text = f"✅ Синхронизация завершена успешно"
        else:
            status_text = f"❌ Синхронизация завершена с ошибками: {result.message}"
        
        return status_text, metrics_text, errors_text, chart_image
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error: {e}", "", f"Детали ошибки:\n{error_details}", ""

def download_protocols_handler(date_str: str = "", limit: int = 0):
    """Обработчик загрузки протоколов с детальными метриками."""
    try:
        if downloader_service is None:
            return "❌ Downloader service not available", "", "", ""
        
        # Если указана дата, фильтруем по дате
        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass
        
        # Выполняем загрузку
        result = downloader_service.process_pending_protocols(
            limit=limit if limit > 0 else None,
            target_date=target_date
        )
        
        # Форматируем детальные метрики
        metrics_text = f"""📊 Детальные метрики загрузки:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏱️  Время выполнения: {result.duration:.2f} секунд
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 Основные показатели:
  • Обработано протоколов: {result.processed}
  • Успешно загружено: {result.downloaded}
  • Неудачных загрузок: {result.failed}
  
📊 Статистика:
  • Успешность: {(result.downloaded / result.processed * 100) if result.processed > 0 else 0:.1f}%
  • Скорость загрузки: {result.downloaded / result.duration if result.duration > 0 else 0:.2f} файлов/сек
"""
        
        # Добавляем статистику из result.statistics если есть
        if result.statistics:
            stats = result.statistics
            if "total_size" in stats:
                total_size_mb = stats["total_size"] / (1024 * 1024)
                metrics_text += f"  • Общий размер: {total_size_mb:.2f} MB\n"
            if "avg_file_size" in stats:
                avg_size_kb = stats["avg_file_size"] / 1024
                metrics_text += f"  • Средний размер файла: {avg_size_kb:.2f} KB\n"
        
        # Формируем информацию об ошибках
        errors_text = ""
        if result.errors and len(result.errors) > 0:
            errors_text = f"\n⚠️  Ошибки ({len(result.errors)}):\n"
            for i, error in enumerate(result.errors[:10], 1):  # Показываем первые 10
                errors_text += f"  {i}. {error}\n"
            if len(result.errors) > 10:
                errors_text += f"  ... и еще {len(result.errors) - 10} ошибок\n"
        
        # Создаем график прогресса
        chart_data = {
            "processed": result.processed,
            "downloaded": result.downloaded,
            "failed": result.failed
        }
        
        # Создаем график
        chart_image_base64 = create_download_progress_chart(chart_data)
        
        # Конвертируем base64 в PIL Image
        chart_image = None
        if chart_image_base64 and chart_image_base64.startswith("data:image"):
            try:
                # Извлекаем base64 данные
                img_data = chart_image_base64.split(",")[1]
                img_bytes = base64.b64decode(img_data)
                chart_image = Image.open(BytesIO(img_bytes))
            except Exception as e:
                logger.error(f"Error converting chart image: {e}")
        
        # Общий статус
        if result.status == "success":
            status_text = f"✅ Загрузка завершена успешно"
        else:
            status_text = f"❌ Загрузка завершена с ошибками: {result.message}"
        
        return status_text, metrics_text, errors_text, chart_image
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error: {e}", "", f"Детали ошибки:\n{error_details}", ""

def create_status_box_html(status: str, message: str, color: str, check_type: str, prefix: str = "") -> str:
    """Создает HTML плашки статуса.
    
    Args:
        status: Текст статуса
        message: Сообщение
        color: Цвет фона
        check_type: Тип проверки (vpn, remote_mongo, local_mongo, environment, ssl, zakupki)
        prefix: Префикс (не используется, оставлен для совместимости)
    """
    html = f"""<div style='padding: 15px; border-radius: 8px; background-color: {color}; color: white; font-weight: bold; min-height: 120px; display: flex; flex-direction: column;'>
        <div style='flex: 1;'>
            {status}<br/>
            <small style='font-weight: normal;'>{message}</small>
        </div>
    </div>"""
    return html

# Создаем Gradio интерфейс
with gr.Blocks(title="Preprocessing WebUI", css="""
    .hidden-refresh-btn {
        display: none !important;
    }
    /* Стили только для плашек статусов на Health Check */
    .html-container > div > div {
        min-height: 120px !important;
        display: flex !important;
        flex-direction: column !important;
    }
""") as demo:
    gr.Markdown("# 🔄 Preprocessing WebUI")
    gr.Markdown("Интерфейс для управления и мониторинга компонентов препроцессинга")
    
    with gr.Tab("📊 Dashboard"):
        with gr.Row():
            with gr.Column():
                health_status = gr.Textbox(label="🏥 System Health Summary", interactive=False)
                health_details = gr.Textbox(label="📋 Health Details", lines=10, interactive=False)
                refresh_health = gr.Button("🔄 Refresh All Health Checks", variant="primary")
            
            with gr.Column():
                sync_summary = gr.Textbox(label="📥 Sync Statistics", interactive=False)
                sync_details = gr.Textbox(label="📋 Sync Details", lines=10, interactive=False)
                refresh_sync = gr.Button("🔄 Refresh Sync Stats")
        
        with gr.Row():
            download_summary = gr.Textbox(label="💾 Download Statistics", interactive=False)
            refresh_download = gr.Button("🔄 Refresh Download Stats")
        
        refresh_health.click(
            fn=get_health_status,
            outputs=[health_status, health_details]
        )
    
    with gr.Tab("🔄 Sync Control"):
        gr.Markdown("## Управление синхронизацией протоколов")
        gr.Markdown("Ручной запуск синхронизации с просмотром метрик, аналитики и статистики")
        
        with gr.Row():
            sync_date = gr.Textbox(
                label="📅 Дата (YYYY-MM-DD)",
                value="2025-03-20",
                placeholder="2025-03-20",
                info="Дата для синхронизации протоколов"
            )
            sync_limit = gr.Number(
                label="🔢 Лимит записей (0 = без лимита)",
                value=0,
                precision=0,
                minimum=0,
                info="Максимальное количество записей для синхронизации. 0 = все записи за указанную дату"
            )
        
        sync_button = gr.Button("🚀 Запустить синхронизацию", variant="primary", size="lg")
        
        with gr.Row():
            sync_status = gr.Textbox(label="📊 Статус синхронизации", interactive=False, lines=2)
            sync_metrics = gr.Textbox(label="📈 Детальные метрики", interactive=False, lines=15)
        
        with gr.Row():
            sync_errors = gr.Textbox(label="⚠️ Ошибки и предупреждения", interactive=False, lines=10)
            sync_chart = gr.Image(label="📊 График результатов", type="pil", height=400)
        
        # Кнопка для просмотра статистики
        view_stats_btn = gr.Button("📊 Просмотр статистики синхронизации", variant="secondary")
        sync_stats_display = gr.Textbox(label="📈 Историческая статистика", interactive=False, lines=10)
    
    with gr.Tab("💾 Download Control"):
        gr.Markdown("## Управление загрузкой протоколов")
        gr.Markdown("Ручной запуск загрузки с просмотром метрик, аналитики и статистики")
        
        with gr.Row():
            download_date = gr.Textbox(
                label="📅 Дата (YYYY-MM-DD, опционально)",
                value="",
                placeholder="2025-03-20 или оставьте пустым для всех",
                info="Дата для загрузки протоколов. Оставьте пустым для загрузки всех ожидающих"
            )
            download_limit = gr.Number(
                label="🔢 Лимит протоколов (0 = без лимита)",
                value=0,
                precision=0,
                minimum=0,
                info="Максимальное количество протоколов для загрузки. 0 = все доступные"
            )
        
        download_button = gr.Button("📥 Запустить загрузку", variant="primary", size="lg")
        
        with gr.Row():
            download_status = gr.Textbox(label="📊 Статус загрузки", interactive=False, lines=2)
            download_metrics = gr.Textbox(label="📈 Детальные метрики", interactive=False, lines=15)
        
        with gr.Row():
            download_errors = gr.Textbox(label="⚠️ Ошибки и предупреждения", interactive=False, lines=10)
            download_chart = gr.Image(label="📊 График результатов", type="pil", height=400)
        
        # Кнопка для просмотра статистики
        view_download_stats_btn = gr.Button("📊 Просмотр статистики загрузки", variant="secondary")
        download_stats_display = gr.Textbox(label="📈 Историческая статистика", interactive=False, lines=10)
    
    with gr.Tab("🏥 Health Check"):
        gr.Markdown("## Комплексная проверка здоровья системы")
        
        # Плашки статусов - первая строка (3 плашки)
        with gr.Row():
            health_vpn_status = gr.HTML(label="VPN Health", value=create_status_box_html("🔄 Проверка...", "Нажмите кнопку проверки для обновления", "#6b7280", "vpn", "health_"))
            health_remote_mongo_status = gr.HTML(label="Remote MongoDB Health", value=create_status_box_html("🔄 Проверка...", "Нажмите кнопку проверки для обновления", "#6b7280", "remote_mongo", "health_"))
            health_local_mongo_status = gr.HTML(label="Local MongoDB Health", value=create_status_box_html("🔄 Проверка...", "Нажмите кнопку проверки для обновления", "#6b7280", "local_mongo", "health_"))
        
        # Плашки статусов - вторая строка (3 плашки)
        with gr.Row():
            health_env_status = gr.HTML(label="Environment Variables Health", value=create_status_box_html("🔄 Проверка...", "Нажмите кнопку проверки для обновления", "#6b7280", "environment", "health_"))
            health_ssl_status = gr.HTML(label="SSL Certificate Health", value=create_status_box_html("🔄 Проверка...", "Нажмите кнопку проверки для обновления", "#6b7280", "ssl", "health_"))
            health_zakupki_status = gr.HTML(label="Zakupki.gov.ru Health", value=create_status_box_html("🔄 Проверка...", "Нажмите кнопку проверки для обновления", "#6b7280", "zakupki", "health_"))
        
        # Меню для индивидуальных проверок
        gr.Markdown("### Индивидуальные проверки компонентов")
        with gr.Row():
            check_vpn_btn = gr.Button("🔒 Проверить VPN", variant="secondary")
            check_remote_mongo_btn = gr.Button("🌐 Проверить Remote MongoDB", variant="secondary")
            check_local_mongo_btn = gr.Button("🗄️ Проверить Local MongoDB", variant="secondary")
        
        with gr.Row():
            check_env_btn = gr.Button("⚙️ Проверить Environment Variables", variant="secondary")
            check_ssl_btn = gr.Button("🔐 Проверить SSL Certificate", variant="secondary")
            check_zakupki_btn = gr.Button("🌐 Проверить zakupki.gov.ru", variant="secondary")
            check_all_btn = gr.Button("🔄 Проверить все компоненты", variant="primary")
        
        # Окно для вывода логов
        health_log_output = gr.Textbox(
            label="📋 Health Check Logs (в реальном времени)",
            lines=20,
            interactive=False,
            value="Логи проверок будут отображаться здесь...\n"
        )
        
        # Функции для обновления плашек и логов при единичной проверке
        def check_vpn_and_update():
            """Проверяет VPN и обновляет плашку и лог."""
            log_output = run_individual_check("vpn")
            status_html = update_single_health_status_box("vpn")
            return status_html, log_output
        
        def check_remote_mongo_and_update():
            """Проверяет Remote MongoDB и обновляет плашку и лог."""
            log_output = run_individual_check("remote_mongodb")
            status_html = update_single_health_status_box("remote_mongo")
            return status_html, log_output
        
        def check_local_mongo_and_update():
            """Проверяет Local MongoDB и обновляет плашку и лог."""
            log_output = run_individual_check("local_mongodb")
            status_html = update_single_health_status_box("local_mongo")
            return status_html, log_output
        
        def check_env_and_update():
            """Проверяет Environment Variables и обновляет плашку и лог."""
            log_output = run_individual_check("environment")
            status_html = update_single_health_status_box("environment")
            return status_html, log_output
        
        def check_ssl_and_update():
            """Проверяет SSL Certificate и обновляет плашку и лог."""
            log_output = run_individual_check("ssl_certificate")
            status_html = update_single_health_status_box("ssl")
            return status_html, log_output
        
        def check_zakupki_and_update():
            """Проверяет zakupki.gov.ru и обновляет плашку и лог."""
            log_output = run_individual_check("zakupki")
            status_html = update_single_health_status_box("zakupki")
            return status_html, log_output
        
        # Обработчики для индивидуальных проверок
        check_vpn_btn.click(
            fn=check_vpn_and_update,
            outputs=[health_vpn_status, health_log_output]
        )
        
        check_remote_mongo_btn.click(
            fn=check_remote_mongo_and_update,
            outputs=[health_remote_mongo_status, health_log_output]
        )
        
        check_local_mongo_btn.click(
            fn=check_local_mongo_and_update,
            outputs=[health_local_mongo_status, health_log_output]
        )
        
        check_env_btn.click(
            fn=check_env_and_update,
            outputs=[health_env_status, health_log_output]
        )
        
        check_ssl_btn.click(
            fn=check_ssl_and_update,
            outputs=[health_ssl_status, health_log_output]
        )
        
        check_zakupki_btn.click(
            fn=check_zakupki_and_update,
            outputs=[health_zakupki_status, health_log_output]
        )
        
        def update_health_status_boxes_for_health_check():
            """Обновляет плашки статусов компонентов для Health Check."""
            vpn_status, vpn_msg, vpn_color = check_vpn_health()
            remote_status, remote_msg, remote_color = check_remote_mongo_health()
            local_status, local_msg, local_color = check_local_mongo_health()
            env_status, env_msg, env_color = check_environment_health()
            ssl_status, ssl_msg, ssl_color = check_ssl_health()
            zakupki_status, zakupki_msg, zakupki_color = check_zakupki_health()
            
            vpn_html = create_status_box_html(vpn_status, vpn_msg, vpn_color, "vpn", "health_")
            remote_html = create_status_box_html(remote_status, remote_msg, remote_color, "remote_mongo", "health_")
            local_html = create_status_box_html(local_status, local_msg, local_color, "local_mongo", "health_")
            env_html = create_status_box_html(env_status, env_msg, env_color, "environment", "health_")
            ssl_html = create_status_box_html(ssl_status, ssl_msg, ssl_color, "ssl", "health_")
            zakupki_html = create_status_box_html(zakupki_status, zakupki_msg, zakupki_color, "zakupki", "health_")
            
            return vpn_html, remote_html, local_html, env_html, ssl_html, zakupki_html
        
        def check_all_and_update():
            """Проверяет все компоненты и обновляет плашки."""
            # Обновляем плашки
            vpn_html, remote_html, local_html, env_html, ssl_html, zakupki_html = update_health_status_boxes_for_health_check()
            
            # Получаем полный лог
            log_output = get_comprehensive_health_log()
            
            return vpn_html, remote_html, local_html, env_html, ssl_html, zakupki_html, log_output
        
        def update_single_health_status_box(check_type: str):
            """Обновляет одну плашку статуса на Health Check."""
            if check_type == "vpn":
                status, msg, color = check_vpn_health()
            elif check_type == "remote_mongo":
                status, msg, color = check_remote_mongo_health()
            elif check_type == "local_mongo":
                status, msg, color = check_local_mongo_health()
            elif check_type == "environment":
                status, msg, color = check_environment_health()
            elif check_type == "ssl":
                status, msg, color = check_ssl_health()
            elif check_type == "zakupki":
                status, msg, color = check_zakupki_health()
            else:
                return create_status_box_html("❌ Unknown", "Unknown check type", "#f0f0f0", check_type, "health_")
            
            return create_status_box_html(status, msg, color, check_type, "health_")
        
        check_all_btn.click(
            fn=check_all_and_update,
            outputs=[health_vpn_status, health_remote_mongo_status, health_local_mongo_status, health_env_status, health_ssl_status, health_zakupki_status, health_log_output]
        )
    
    with gr.Tab("⚙️ Configuration"):
        gr.Markdown("## Настройки конфигурации из .env файла")
        
        # MongoDB Configuration
        with gr.Accordion("🗄️ MongoDB Configuration", open=True):
            with gr.Row():
                mongo_metadata_server = gr.Textbox(label="MONGO_METADATA_SERVER", value=os.environ.get("MONGO_METADATA_SERVER", os.environ.get("LOCAL_MONGO_SERVER", "localhost:27017")))
                mongo_metadata_user = gr.Textbox(label="MONGO_METADATA_USER", value=os.environ.get("MONGO_METADATA_USER", "admin"))
            with gr.Row():
                mongo_metadata_password = gr.Textbox(label="MONGO_METADATA_PASSWORD", type="password", value=os.environ.get("MONGO_METADATA_PASSWORD", ""))
                mongo_metadata_db = gr.Textbox(label="MONGO_METADATA_DB", value=os.environ.get("MONGO_METADATA_DB", "docling_metadata"))
            with gr.Row():
                local_mongo_server = gr.Textbox(label="LOCAL_MONGO_SERVER", value=os.environ.get("LOCAL_MONGO_SERVER", os.environ.get("MONGO_METADATA_SERVER", "localhost:27017")), info="Адрес локального MongoDB сервера")
        
        # Remote MongoDB Configuration
        with gr.Accordion("🌐 Remote MongoDB (for sync) - Requires VPN", open=False):
            with gr.Row():
                mongo_server = gr.Textbox(label="MONGO_SERVER", value=os.environ.get("MONGO_SERVER", "192.168.0.46:8635"))
                mongo_user = gr.Textbox(label="MONGO_USER", value=os.environ.get("MONGO_USER", "readProtocols223"))
            with gr.Row():
                mongo_password = gr.Textbox(label="MONGO_PASSWORD", type="password", value=os.environ.get("MONGO_PASSWORD", ""))
                mongo_ssl_cert = gr.Textbox(label="MONGO_SSL_CERT", value=os.environ.get("MONGO_SSL_CERT", "/root/winners_preprocessor/certs/sber2.crt"))
            with gr.Row():
                remote_mongo_use_vpn = gr.Radio(
                    choices=[("Да", "true"), ("Нет", "false")],
                    label="Использовать VPN для Remote MongoDB",
                    value=os.environ.get("REMOTE_MONGO_USE_VPN", "true").lower(),
                    info="Обязательно включите VPN для подключения к удаленной MongoDB"
                )
        
        # Processing Configuration
        with gr.Accordion("⚙️ Processing Configuration", open=False):
            with gr.Row():
                input_dir = gr.Textbox(label="INPUT_DIR", value=os.environ.get("INPUT_DIR", "/root/winners_preprocessor/final_preprocessing/Data"))
                output_dir = gr.Textbox(label="OUTPUT_DIR", value=os.environ.get("OUTPUT_DIR", "/root/winners_preprocessor/final_preprocessing/Data"))
            with gr.Row():
                max_urls = gr.Number(label="MAX_URLS_PER_PROTOCOL", value=int(os.environ.get("MAX_URLS_PER_PROTOCOL", "15")), precision=0)
                download_timeout = gr.Number(label="DOWNLOAD_HTTP_TIMEOUT", value=int(os.environ.get("DOWNLOAD_HTTP_TIMEOUT", "120")), precision=0)
            with gr.Row():
                download_concurrency = gr.Number(label="DOWNLOAD_CONCURRENCY", value=int(os.environ.get("DOWNLOAD_CONCURRENCY", "20")), precision=0)
                protocols_concurrency = gr.Number(label="PROTOCOLS_CONCURRENCY", value=int(os.environ.get("PROTOCOLS_CONCURRENCY", "20")), precision=0)
        
        # Scheduler Configuration
        with gr.Accordion("⏰ Scheduler Configuration", open=False):
            scheduler_enabled = gr.Checkbox(
                label="Включить Scheduler",
                value=os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true",
                info="Включить автоматическое выполнение задач по расписанию"
            )
            
            gr.Markdown("### Настройки синхронизации протоколов")
            sync_schedule_type = gr.Radio(
                choices=[
                    ("Ежедневно", "daily"),
                    ("Еженедельно", "weekly"),
                    ("Ежемесячно", "monthly"),
                    ("Кастомный период", "custom")
                ],
                label="Частота синхронизации",
                value="daily",
                info="Выберите частоту выполнения синхронизации"
            )
            
            with gr.Row(visible=False) as sync_daily_settings:
                sync_daily_time = gr.Textbox(
                    label="Время выполнения (HH:MM)",
                    value="02:00",
                    placeholder="02:00",
                    info="Время суток для ежедневной синхронизации"
                )
            
            with gr.Row(visible=False) as sync_weekly_settings:
                sync_weekly_day = gr.Dropdown(
                    choices=[("Понедельник", "0"), ("Вторник", "1"), ("Среда", "2"), ("Четверг", "3"), ("Пятница", "4"), ("Суббота", "5"), ("Воскресенье", "6")],
                    label="День недели",
                    value="0",
                    info="День недели для еженедельной синхронизации"
                )
                sync_weekly_time = gr.Textbox(
                    label="Время выполнения (HH:MM)",
                    value="02:00",
                    placeholder="02:00"
                )
            
            with gr.Row(visible=False) as sync_monthly_settings:
                sync_monthly_day = gr.Number(
                    label="День месяца (1-31)",
                    value=1,
                    precision=0,
                    minimum=1,
                    maximum=31,
                    info="День месяца для ежемесячной синхронизации"
                )
                sync_monthly_time = gr.Textbox(
                    label="Время выполнения (HH:MM)",
                    value="02:00",
                    placeholder="02:00"
                )
            
            with gr.Row(visible=False) as sync_custom_settings:
                sync_custom_period = gr.Dropdown(
                    choices=[("Дни", "days"), ("Недели", "weeks"), ("Месяцы", "months")],
                    label="Единица периода",
                    value="days"
                )
                sync_custom_count = gr.Number(
                    label="Количество",
                    value=1,
                    precision=0,
                    minimum=1,
                    info="Количество единиц периода"
                )
                sync_custom_time = gr.Textbox(
                    label="Время выполнения (HH:MM)",
                    value="02:00",
                    placeholder="02:00"
                )
            
            sync_schedule_cron_display = gr.Textbox(
                label="Сгенерированное CRON выражение (только чтение)",
                value=os.environ.get("SYNC_SCHEDULE_CRON", "0 2 * * *"),
                interactive=False,
                info="Автоматически генерируется на основе выбранных настроек"
            )
            
            gr.Markdown("### Настройки обработки документов")
            process_schedule_type = gr.Radio(
                choices=[
                    ("Каждые N минут", "interval"),
                    ("По расписанию (CRON)", "cron")
                ],
                label="Тип расписания обработки",
                value="interval",
                info="Выберите тип расписания для обработки документов"
            )
            
            with gr.Row(visible=True) as process_interval_settings:
                process_interval_minutes = gr.Number(
                    label="Интервал (минуты)",
                    value=15,
                    precision=0,
                    minimum=1,
                    info="Интервал между запусками обработки в минутах"
                )
            
            with gr.Row(visible=False) as process_cron_settings:
                schedule_cron = gr.Textbox(
                    label="SCHEDULE_CRON",
                    value=os.environ.get("SCHEDULE_CRON", "*/15 * * * *"),
                    placeholder="*/15 * * * *",
                    info="CRON выражение для расписания обработки"
                )
            
            def update_sync_schedule_visibility(schedule_type):
                """Обновляет видимость настроек синхронизации."""
                return (
                    gr.update(visible=(schedule_type == "daily")),
                    gr.update(visible=(schedule_type == "weekly")),
                    gr.update(visible=(schedule_type == "monthly")),
                    gr.update(visible=(schedule_type == "custom"))
                )
            
            def update_process_schedule_visibility(schedule_type):
                """Обновляет видимость настроек обработки."""
                return (
                    gr.update(visible=(schedule_type == "interval")),
                    gr.update(visible=(schedule_type == "cron"))
                )
            
            def generate_sync_cron(schedule_type, daily_time, weekly_day, weekly_time, monthly_day, monthly_time, custom_period, custom_count, custom_time):
                """Генерирует CRON выражение на основе настроек."""
                try:
                    if schedule_type == "daily":
                        hour, minute = daily_time.split(":")
                        return f"{minute} {hour} * * *"
                    elif schedule_type == "weekly":
                        hour, minute = weekly_time.split(":")
                        return f"{minute} {hour} * * {weekly_day}"
                    elif schedule_type == "monthly":
                        hour, minute = monthly_time.split(":")
                        return f"{minute} {hour} {int(monthly_day)} * *"
                    elif schedule_type == "custom":
                        hour, minute = custom_time.split(":")
                        if custom_period == "days":
                            return f"{minute} {hour} */{int(custom_count)} * *"
                        elif custom_period == "weeks":
                            return f"{minute} {hour} * */{int(custom_count)} *"
                        else:  # months
                            return f"{minute} {hour} 1 */{int(custom_count)} *"
                    return "0 2 * * *"
                except Exception as e:
                    logger.error(f"Error generating cron: {e}")
                    return "0 2 * * *"
            
            sync_schedule_type.change(
                fn=update_sync_schedule_visibility,
                inputs=sync_schedule_type,
                outputs=[sync_daily_settings, sync_weekly_settings, sync_monthly_settings, sync_custom_settings]
            )
            
            sync_schedule_type.change(
                fn=generate_sync_cron,
                inputs=[sync_schedule_type, sync_daily_time, sync_weekly_day, sync_weekly_time, sync_monthly_day, sync_monthly_time, sync_custom_period, sync_custom_count, sync_custom_time],
                outputs=sync_schedule_cron_display
            )
            
            # Обновление CRON при изменении параметров
            for input_component in [sync_daily_time, sync_weekly_day, sync_weekly_time, sync_monthly_day, sync_monthly_time, sync_custom_period, sync_custom_count, sync_custom_time]:
                input_component.change(
                    fn=generate_sync_cron,
                    inputs=[sync_schedule_type, sync_daily_time, sync_weekly_day, sync_weekly_time, sync_monthly_day, sync_monthly_time, sync_custom_period, sync_custom_count, sync_custom_time],
                    outputs=sync_schedule_cron_display
                )
            
            process_schedule_type.change(
                fn=update_process_schedule_visibility,
                inputs=process_schedule_type,
                outputs=[process_interval_settings, process_cron_settings]
            )
        
        # VPN Configuration
        with gr.Accordion("🔒 VPN Configuration", open=False):
            gr.Markdown("### Настройки VPN для работы с удаленными ресурсами")
            with gr.Row():
                vpn_enabled_remote_mongo = gr.Radio(
                    choices=[("Включен", "true"), ("Выключен", "false")],
                    label="VPN включен (для Remote MongoDB)",
                    value=os.environ.get("VPN_ENABLED_REMOTE_MONGO", os.environ.get("VPN_ENABLED", "false")).lower(),
                    info="Включено ли использование VPN в данный момент для тестов и работы с Remote MongoDB"
                )
                vpn_enabled_zakupki = gr.Radio(
                    choices=[("Включен", "true"), ("Выключен", "false")],
                    label="VPN включен (для zakupki.gov.ru)",
                    value=os.environ.get("VPN_ENABLED_ZAKUPKI", os.environ.get("VPN_ENABLED", "false")).lower(),
                    info="Включено ли использование VPN в данный момент для тестов и работы с zakupki.gov.ru"
                )
            with gr.Row():
                zakupki_url = gr.Textbox(
                    label="ZAKUPKI_URL",
                    value=os.environ.get("ZAKUPKI_URL", "https://zakupki.gov.ru"),
                    info="URL для проверки доступа к zakupki.gov.ru"
                )
            with gr.Row():
                with gr.Column(scale=2):
                    vpn_config_file = gr.Textbox(
                        label="VPN_CONFIG_FILE",
                        value=os.environ.get("VPN_CONFIG_FILE", "/root/winners_preprocessor/vitaly_bychkov.ovpn"),
                        info="Путь к файлу конфигурации OpenVPN (.ovpn)"
                    )
                with gr.Column(scale=2):
                    vpn_config_file_upload = gr.File(
                        label="📁 Загрузить файл конфигурации VPN (.ovpn)",
                        file_types=[".ovpn"],
                        type="filepath"
                    )
                with gr.Column(scale=1):
                    gr.Markdown("💡 Выберите файл конфигурации OpenVPN (.ovpn) для загрузки на сервер")
            
            def handle_vpn_file_upload(uploaded_file):
                """Обрабатывает загруженный файл VPN конфигурации."""
                if uploaded_file is None:
                    return gr.update(), "⚠️ Файл не выбран"
                
                try:
                    # Определяем целевой путь для сохранения файла
                    target_dir = Path("/root/winners_preprocessor")
                    target_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Получаем имя файла
                    source_path = Path(uploaded_file)
                    target_path = target_dir / source_path.name
                    
                    # Копируем файл в целевую директорию
                    shutil.copy2(source_path, target_path)
                    
                    # Устанавливаем правильные права доступа
                    os.chmod(target_path, 0o644)
                    
                    # Обновляем переменную окружения
                    os.environ["VPN_CONFIG_FILE"] = str(target_path)
                    
                    return gr.update(value=str(target_path)), f"✅ Файл успешно загружен: {target_path}"
                except Exception as e:
                    logger.error(f"Error uploading VPN config file: {e}")
                    return gr.update(), f"❌ Ошибка загрузки файла: {e}"
            
            vpn_file_upload_status = gr.Textbox(
                label="Статус загрузки файла",
                interactive=False,
                lines=2,
                value=""
            )
            
            vpn_config_file_upload.upload(
                fn=handle_vpn_file_upload,
                inputs=[vpn_config_file_upload],
                outputs=[vpn_config_file, vpn_file_upload_status]
            )
        
        config_status = gr.Textbox(label="🔧 Configuration Status", interactive=False, lines=3)
        with gr.Row():
            save_config_btn = gr.Button("💾 Save Configuration to .env", variant="primary")
            reload_config_btn = gr.Button("🔄 Reload from .env")
            restart_webui_btn = gr.Button("🔄 Перезапустить WebUI", variant="secondary")
        
        def save_configuration(
            mongo_meta_server, mongo_meta_user, mongo_meta_pass, mongo_meta_db, local_mongo_srv,
            mongo_srv, mongo_usr, mongo_pass, mongo_ssl, remote_mongo_vpn,
            input_d, output_d, max_u, dl_timeout, dl_conc, prot_conc,
            sched_enabled, sync_sched_type, sync_daily_t, sync_weekly_d, sync_weekly_t,
            sync_monthly_d, sync_monthly_t, sync_custom_p, sync_custom_c, sync_custom_t,
            sync_cron_display, proc_sched_type, proc_interval_m, proc_cron,
            vpn_en_remote, vpn_en_zakupki, zak_url, vpn_config_file_path
        ):
            """Сохраняет конфигурацию в .env файл."""
            try:
                env_file = Path(__file__).parent.parent / ".env"
                
                # Формируем содержимое .env файла
                env_content = f"""# MongoDB Configuration
MONGO_METADATA_SERVER={mongo_meta_server}
LOCAL_MONGO_SERVER={local_mongo_srv}
MONGO_METADATA_USER={mongo_meta_user}
MONGO_METADATA_PASSWORD={mongo_meta_pass}
MONGO_METADATA_DB={mongo_meta_db}

# Remote MongoDB (for sync) - Requires VPN
MONGO_SERVER={mongo_srv}
MONGO_USER={mongo_usr}
MONGO_PASSWORD={mongo_pass}
MONGO_SSL_CERT={mongo_ssl}
REMOTE_MONGO_USE_VPN={remote_mongo_vpn}

# Processing Configuration
INPUT_DIR={input_d}
OUTPUT_DIR={output_d}
MAX_URLS_PER_PROTOCOL={int(max_u)}
DOWNLOAD_HTTP_TIMEOUT={int(dl_timeout)}
DOWNLOAD_CONCURRENCY={int(dl_conc)}
PROTOCOLS_CONCURRENCY={int(prot_conc)}

# Scheduler Configuration
SCHEDULER_ENABLED={str(sched_enabled).lower()}
SCHEDULE_CRON="{proc_cron if proc_sched_type == 'cron' else f'*/{int(proc_interval_m)} * * * *'}"
SYNC_SCHEDULE_CRON="{sync_cron_display}"

# VPN Configuration
VPN_ENABLED={vpn_en_remote if vpn_en_remote == vpn_en_zakupki else "true"}
VPN_ENABLED_REMOTE_MONGO={vpn_en_remote}
VPN_ENABLED_ZAKUPKI={vpn_en_zakupki}
VPN_REQUIRED=true
VPN_CONFIG_FILE={vpn_config_file_path}
ZAKUPKI_URL={zak_url}
"""
                
                # Сохраняем файл
                with open(env_file, 'w', encoding='utf-8') as f:
                    f.write(env_content)
                
                # Обновляем переменные окружения
                os.environ["MONGO_METADATA_SERVER"] = mongo_meta_server
                os.environ["LOCAL_MONGO_SERVER"] = local_mongo_srv
                os.environ["MONGO_METADATA_USER"] = mongo_meta_user
                os.environ["MONGO_METADATA_PASSWORD"] = mongo_meta_pass
                os.environ["MONGO_METADATA_DB"] = mongo_meta_db
                os.environ["MONGO_SERVER"] = mongo_srv
                os.environ["MONGO_USER"] = mongo_usr
                os.environ["MONGO_PASSWORD"] = mongo_pass
                os.environ["MONGO_SSL_CERT"] = mongo_ssl
                os.environ["REMOTE_MONGO_USE_VPN"] = remote_mongo_vpn
                os.environ["INPUT_DIR"] = input_d
                os.environ["OUTPUT_DIR"] = output_d
                os.environ["MAX_URLS_PER_PROTOCOL"] = str(int(max_u))
                os.environ["DOWNLOAD_HTTP_TIMEOUT"] = str(int(dl_timeout))
                os.environ["DOWNLOAD_CONCURRENCY"] = str(int(dl_conc))
                os.environ["PROTOCOLS_CONCURRENCY"] = str(int(prot_conc))
                os.environ["SCHEDULER_ENABLED"] = str(sched_enabled).lower()
                final_schedule_cron = proc_cron if proc_sched_type == 'cron' else f"*/{int(proc_interval_m)} * * * *"
                os.environ["SCHEDULE_CRON"] = final_schedule_cron
                os.environ["SYNC_SCHEDULE_CRON"] = sync_cron_display
                # Используем значение для Remote MongoDB как основное VPN_ENABLED
                # Если они различаются, используем "true" (более безопасный вариант)
                vpn_enabled_value = vpn_en_remote if vpn_en_remote == vpn_en_zakupki else "true"
                os.environ["VPN_ENABLED"] = vpn_enabled_value
                os.environ["VPN_ENABLED_REMOTE_MONGO"] = vpn_en_remote
                os.environ["VPN_ENABLED_ZAKUPKI"] = vpn_en_zakupki
                os.environ["VPN_REQUIRED"] = "true"
                os.environ["VPN_CONFIG_FILE"] = vpn_config_file_path
                os.environ["ZAKUPKI_URL"] = zak_url
                
                return f"✅ Конфигурация успешно сохранена в {env_file}\n\n⚠️ Внимание: Для применения изменений нажмите кнопку '🔄 Перезапустить WebUI' ниже."
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Error saving configuration: {error_details}")
                return f"❌ Ошибка сохранения конфигурации: {e}\n\n{error_details}"
        
        def reload_configuration():
            """Перезагружает конфигурацию из .env файла."""
            try:
                from receiver.core.config import load_env_file
                env_file = Path(__file__).parent.parent / ".env"
                load_env_file(env_file)
                return f"✅ Конфигурация перезагружена из {env_file}\n\nОбновите страницу для отображения новых значений."
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Error reloading configuration: {error_details}")
                return f"❌ Ошибка перезагрузки конфигурации: {e}\n\n{error_details}"
        
        save_config_btn.click(
            fn=save_configuration,
            inputs=[
                mongo_metadata_server, mongo_metadata_user, mongo_metadata_password, mongo_metadata_db, local_mongo_server,
                mongo_server, mongo_user, mongo_password, mongo_ssl_cert, remote_mongo_use_vpn,
                input_dir, output_dir, max_urls, download_timeout, download_concurrency, protocols_concurrency,
                scheduler_enabled, sync_schedule_type, sync_daily_time, sync_weekly_day, sync_weekly_time,
                sync_monthly_day, sync_monthly_time, sync_custom_period, sync_custom_count, sync_custom_time,
                sync_schedule_cron_display, process_schedule_type, process_interval_minutes, schedule_cron,
                vpn_enabled_remote_mongo, vpn_enabled_zakupki, zakupki_url, vpn_config_file
            ],
            outputs=config_status
        )
        
        reload_config_btn.click(fn=reload_configuration, outputs=config_status)
        
        def restart_webui():
            """Перезапускает WebUI сервер для применения изменений."""
            try:
                import subprocess
                import sys
                # Ищем скрипт перезапуска в нескольких местах
                project_root = Path(__file__).parent.parent.parent
                possible_paths = [
                    project_root / "restart_webui.sh",
                    Path(__file__).parent.parent / "restart_webui.sh",
                    Path("/root/winners_preprocessor/restart_webui.sh")
                ]
                
                script_path = None
                for path in possible_paths:
                    if path.exists():
                        script_path = path
                        break
                
                if script_path:
                    # Запускаем скрипт перезапуска в фоне
                    subprocess.Popen(["/bin/bash", str(script_path)], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL,
                                   cwd=str(project_root))
                    return "✅ Команда перезапуска отправлена. WebUI будет перезапущен через несколько секунд.\n\nОбновите страницу через 10-15 секунд."
                else:
                    # Если скрипта нет, выполняем перезапуск напрямую
                    import os
                    current_pid = os.getpid()
                    # Запускаем команду перезапуска в фоне
                    restart_cmd = f"cd {project_root} && pkill -f 'receiver.*webui' && sleep 2 && nohup python3 -m receiver.webui.app > /tmp/webui.log 2>&1 &"
                    subprocess.Popen(["/bin/bash", "-c", restart_cmd],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    return "✅ Команда перезапуска отправлена. WebUI будет перезапущен через несколько секунд.\n\nОбновите страницу через 10-15 секунд."
            except Exception as e:
                import traceback
                error_details = traceback.format_exc()
                logger.error(f"Error restarting WebUI: {error_details}")
                return f"❌ Ошибка при перезапуске: {e}\n\nПожалуйста, перезапустите WebUI вручную:\n\n```bash\npkill -f receiver.webui.app\ncd /root/winners_preprocessor\nnohup python3 -m receiver.webui.app > /tmp/webui.log 2>&1 &\n```"
        
        restart_webui_btn.click(fn=restart_webui, outputs=config_status)
    
    # Обработчики событий
    # refresh_health уже обработан выше
    refresh_sync.click(fn=get_sync_statistics, outputs=[sync_summary, sync_details])
    refresh_download.click(fn=get_download_statistics, outputs=[download_summary])
    def view_sync_statistics():
        """Просмотр статистики синхронизации."""
        try:
            if analytics_service is None:
                return "❌ Analytics service not available"
            
            # Получаем статистику за последние 7 дней
            recent_data = analytics_service.get_historical_sync_data(days=7)
            
            if not recent_data:
                return "ℹ️ Нет данных о синхронизации за последние 7 дней"
            
            stats_lines = []
            stats_lines.append("📊 Статистика синхронизации за последние 7 дней:\n")
            stats_lines.append("=" * 60)
            
            total_scanned = 0
            total_inserted = 0
            total_errors = 0
            
            for record in recent_data:
                stats_lines.append(f"\n📅 {record.date}:")
                stats_lines.append(f"  • Отсканировано: {record.scanned_documents}")
                stats_lines.append(f"  • Вставлено: {record.inserted_documents}")
                stats_lines.append(f"  • Ошибок: {record.processing_errors}")
                
                total_scanned += record.scanned_documents
                total_inserted += record.inserted_documents
                total_errors += record.processing_errors
            
            stats_lines.append("\n" + "=" * 60)
            stats_lines.append(f"\n📈 Итого за 7 дней:")
            stats_lines.append(f"  • Всего отсканировано: {total_scanned}")
            stats_lines.append(f"  • Всего вставлено: {total_inserted}")
            stats_lines.append(f"  • Всего ошибок: {total_errors}")
            stats_lines.append(f"  • Средняя успешность: {(total_inserted / total_scanned * 100) if total_scanned > 0 else 0:.1f}%")
            
            return "\n".join(stats_lines)
        except Exception as e:
            return f"❌ Ошибка получения статистики: {e}"
    
    def view_download_statistics():
        """Просмотр статистики загрузки."""
        try:
            # Здесь должна быть логика получения статистики загрузки
            # Пока возвращаем заглушку
            return "ℹ️ Статистика загрузки будет реализована в следующей версии"
        except Exception as e:
            return f"❌ Ошибка получения статистики: {e}"
    
    sync_button.click(
        fn=sync_protocols_handler,
        inputs=[sync_date, sync_limit],
        outputs=[sync_status, sync_metrics, sync_errors, sync_chart]
    )
    
    download_button.click(
        fn=download_protocols_handler,
        inputs=[download_date, download_limit],
        outputs=[download_status, download_metrics, download_errors, download_chart]
    )
    
    view_stats_btn.click(fn=view_sync_statistics, outputs=sync_stats_display)
    view_download_stats_btn.click(fn=view_download_statistics, outputs=download_stats_display)
    
    # Инициализация сервисов при запуске
    demo.load(fn=lambda: "✅ Services initialized" if initialize_services() else "❌ Failed to initialize services", outputs=config_status)

if __name__ == "__main__":
    # Запуск приложения
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
