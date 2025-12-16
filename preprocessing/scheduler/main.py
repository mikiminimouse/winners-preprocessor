"""
Scheduler для периодического запуска обработки документов.
Использует APScheduler для cron-like планирования.
"""
import os
import sys
import requests
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Настройка логирования
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

ROUTER_API = os.environ.get("ROUTER_API", "http://router:8080/process_now")
SCHEDULE_CRON = os.environ.get("SCHEDULE_CRON", "*/15 * * * *")  # По умолчанию каждые 15 минут

scheduler = BlockingScheduler()


def trigger_processing():
    """Вызывает endpoint router для обработки всех файлов."""
    try:
        logger.info(f"Triggering processing via {ROUTER_API}")
        response = requests.post(ROUTER_API, timeout=300)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Processing triggered successfully: {result.get('processed_count', 0)} files")
        else:
            logger.error(f"Error triggering processing: {response.status_code} - {response.text}")
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


# Парсим cron строку и добавляем задачу
try:
    # Формат: "минуты часы день месяц день_недели"
    # Примеры: "*/15 * * * *" (каждые 15 минут), "0 */1 * * *" (каждый час)
    parts = SCHEDULE_CRON.split()
    
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
        
        trigger = CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )
        
        scheduler.add_job(
            trigger_processing,
            trigger=trigger,
            id="process_documents",
            name="Process documents from input directory"
        )
        
        logger.info(f"Scheduler configured with cron: {SCHEDULE_CRON}")
        logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    else:
        # Если формат неверный, используем интервал (каждые 15 минут)
        logger.warning(f"Invalid cron format: {SCHEDULE_CRON}. Using default interval (15 minutes)")
        scheduler.add_job(
            trigger_processing,
            'interval',
            minutes=15,
            id="process_documents",
            name="Process documents from input directory"
        )

except Exception as e:
    logger.error(f"Error configuring scheduler: {e}")
    logger.info("Using default interval (15 minutes)")
    scheduler.add_job(
        trigger_processing,
        'interval',
        minutes=15,
        id="process_documents",
        name="Process documents from input directory"
    )


if __name__ == "__main__":
    try:
        # Запускаем сразу при старте (опционально)
        logger.info("Running initial processing...")
        trigger_processing()
        
        # Запускаем планировщик
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
        scheduler.shutdown()



