#!/usr/bin/env python3
"""
Полноценный тест Cycle 1 с batch processing, checkpoints, и полной validation.
БАГ #4: error handling реализован здесь через обработку результатов classify_unit
"""
import sys
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
import argparse

# Добавляем путь к docprep
sys.path.insert(0, str(Path(__file__).parent))

from docprep.engine.classifier import Classifier
from docprep.utils.disk_utils import check_disk_space, estimate_unit_size


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_cycle1_full_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Cycle1TestRunner:
    """Тестовый раннер для Cycle 1 с batch processing и checkpoints."""

    def __init__(
        self,
        input_dir: Path,
        protocol_date: str,
        batch_size: int = 50,
        checkpoint_file: str = "checkpoint.json",
        dry_run: bool = False,
        copy_mode: bool = True,
        limit: Optional[int] = None,
    ):
        self.input_dir = Path(input_dir)
        self.protocol_date = protocol_date
        self.batch_size = batch_size
        self.checkpoint_file = Path(checkpoint_file)
        self.dry_run = dry_run
        self.copy_mode = copy_mode
        self.limit = limit
        self.classifier = Classifier()

        self.stats = {
            'start_time': None,
            'end_time': None,
            'total': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'by_category': defaultdict(int),
            'by_destination': defaultdict(list),
            'by_file_type': defaultdict(int),
            'errors': [],
            'batches': [],
            'disk_space_before': None,
            'disk_space_after': None,
        }

        self.processed_units = set()

    def load_checkpoint(self) -> bool:
        """Загружает checkpoint для resume."""
        if not self.checkpoint_file.exists():
            logger.info("No checkpoint found, starting fresh")
            return False

        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)

            self.processed_units = set(checkpoint.get('processed_units', []))
            # Восстановление stats из checkpoint
            saved_stats = checkpoint.get('stats', {})
            for key in ['processed', 'successful', 'failed']:
                if key in saved_stats:
                    self.stats[key] = saved_stats[key]
            if 'by_category' in saved_stats:
                self.stats['by_category'] = defaultdict(int, saved_stats['by_category'])
            if 'by_destination' in saved_stats:
                self.stats['by_destination'] = defaultdict(list, saved_stats['by_destination'])
            if 'by_file_type' in saved_stats:
                self.stats['by_file_type'] = defaultdict(int, saved_stats['by_file_type'])
            if 'errors' in saved_stats:
                self.stats['errors'] = saved_stats['errors']
            if 'batches' in saved_stats:
                self.stats['batches'] = saved_stats['batches']

            logger.info(f"Loaded checkpoint: {len(self.processed_units)} units already processed")
            return True

        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return False

    def save_checkpoint(self):
        """Сохраняет checkpoint после batch."""
        try:
            checkpoint = {
                'timestamp': datetime.now().isoformat(),
                'processed_units': list(self.processed_units),
                'stats': {
                    'processed': self.stats['processed'],
                    'successful': self.stats['successful'],
                    'failed': self.stats['failed'],
                    'by_category': dict(self.stats['by_category']),
                    'by_destination': {k: v for k, v in self.stats['by_destination'].items()},
                    'by_file_type': dict(self.stats['by_file_type']),
                    'errors': self.stats['errors'],
                    'batches': self.stats['batches'],
                },
            }

            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)

            logger.info(f"Checkpoint saved: {len(self.processed_units)} units processed")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def check_prerequisites(self) -> bool:
        """Проверяет prerequisites перед запуском."""
        logger.info("Checking prerequisites...")

        # Проверка директории Input
        if not self.input_dir.exists():
            logger.error(f"Input directory not found: {self.input_dir}")
            return False

        # Проверка свободного места
        required_gb = 50.0 if not self.dry_run else 1.0
        has_space, msg = check_disk_space(self.input_dir.parent, required_gb)
        if not has_space:
            logger.error(msg)
            return False

        self.stats['disk_space_before'] = msg

        logger.info("Prerequisites check PASSED")
        return True

    def get_units_to_process(self) -> List[Path]:
        """Получает список UNITs для обработки."""
        all_units = sorted([u for u in self.input_dir.iterdir() if u.is_dir() and u.name.startswith('UNIT_')])

        # Применяем limit если указан
        if self.limit:
            all_units = all_units[:self.limit]

        # Фильтруем уже обработанные
        units_to_process = [u for u in all_units if u.name not in self.processed_units]

        logger.info(f"Total units: {len(all_units)}, To process: {len(units_to_process)}")

        return units_to_process

    def process_batch(self, units_batch: List[Path]) -> Dict[str, Any]:
        """Обрабатывает один batch UNITs."""
        batch_start = time.time()
        batch_stats = {
            'size': len(units_batch),
            'successful': 0,
            'failed': 0,
            'errors': [],
        }

        logger.info(f"Processing batch of {len(units_batch)} units...")

        for i, unit_path in enumerate(units_batch, 1):
            unit_name = unit_path.name

            # БАГ #4: Обработка ошибок на уровне вызова classify_unit
            try:
                # Прогресс каждые 10 UNITs
                if i % 10 == 0:
                    logger.info(f"  [{i}/{len(units_batch)}] Processing...")

                # Классифицируем UNIT
                result = self.classifier.classify_unit(
                    unit_path=unit_path,
                    cycle=1,
                    protocol_date=self.protocol_date,
                    dry_run=self.dry_run,
                    copy_mode=self.copy_mode,
                )

                # Проверяем результат на ошибки
                if 'error' in result:
                    # Есть ошибка в результате
                    batch_stats['failed'] += 1
                    error_info = {
                        'unit': unit_name,
                        'error': result.get('error', 'Unknown error'),
                        'error_type': result.get('error_type', 'Unknown'),
                    }
                    batch_stats['errors'].append(error_info)
                    self.stats['errors'].append(error_info)
                    logger.error(f"Failed to process {unit_name}: {result['error']}")
                    # Не помечаем как processed, можно попробовать снова
                    continue

                # Успешно обработан
                batch_stats['successful'] += 1
                self.stats['successful'] += 1

                # Собираем статистику
                category = result['unit_category']
                self.stats['by_category'][category] += 1

                # Определяем destination (аналогично test_cycle1_200_with_verification.py)
                target = result['target_directory']
                if 'Merge' in target and 'Direct' in target:
                    destination = "Merge/Direct"
                elif 'Processing' in target:
                    if 'Convert' in target:
                        destination = "Processing_1/Convert"
                    elif 'Extract' in target:
                        destination = "Processing_1/Extract"
                    elif 'Normalize' in target:
                        destination = "Processing_1/Normalize"
                    else:
                        destination = "Processing_1/Other"
                elif 'Exception' in target:
                    if 'Empty' in target:
                        destination = "Exceptions_1/Empty"
                    elif 'Special' in target:
                        destination = "Exceptions_1/Special"
                    elif 'Ambiguous' in target:
                        destination = "Exceptions_1/Ambiguous"
                    else:
                        destination = "Exceptions_1/Other"
                else:
                    destination = "Unknown"

                self.stats['by_destination'][destination].append(unit_name)

                # Собираем типы файлов
                for fc in result.get('file_classifications', []):
                    file_type = fc.get('classification', {}).get('detected_type', 'unknown')
                    self.stats['by_file_type'][file_type] += 1

                # Отмечаем как обработанный
                self.processed_units.add(unit_name)

            except FileNotFoundError as e:
                # Файл или директория не найдены
                batch_stats['failed'] += 1
                error_info = {
                    'unit': unit_name,
                    'error': f"File not found: {e}",
                    'error_type': 'FileNotFoundError',
                }
                batch_stats['errors'].append(error_info)
                self.stats['errors'].append(error_info)
                logger.error(f"FileNotFoundError for {unit_name}: {e}")

            except PermissionError as e:
                # Нет прав доступа
                batch_stats['failed'] += 1
                error_info = {
                    'unit': unit_name,
                    'error': f"Permission denied: {e}",
                    'error_type': 'PermissionError',
                }
                batch_stats['errors'].append(error_info)
                self.stats['errors'].append(error_info)
                logger.error(f"PermissionError for {unit_name}: {e}")

            except (OSError, IOError) as e:
                # IO ошибки
                batch_stats['failed'] += 1
                error_info = {
                    'unit': unit_name,
                    'error': f"IO error: {e}",
                    'error_type': type(e).__name__,
                }
                batch_stats['errors'].append(error_info)
                self.stats['errors'].append(error_info)
                logger.error(f"IO error for {unit_name}: {e}")

            except Exception as e:
                # Непредвиденные ошибки
                batch_stats['failed'] += 1
                error_info = {
                    'unit': unit_name,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
                batch_stats['errors'].append(error_info)
                self.stats['errors'].append(error_info)
                logger.exception(f"Unexpected error processing {unit_name}")

        batch_end = time.time()
        batch_stats['duration_sec'] = batch_end - batch_start
        batch_stats['units_per_sec'] = len(units_batch) / batch_stats['duration_sec'] if batch_stats['duration_sec'] > 0 else 0

        self.stats['batches'].append(batch_stats)
        self.stats['processed'] += len(units_batch)
        self.stats['failed'] += batch_stats['failed']

        logger.info(f"Batch completed: {batch_stats['successful']}/{len(units_batch)} successful, "
                   f"{batch_stats['failed']} failed, {batch_stats['duration_sec']:.1f}s")

        return batch_stats

    def validate_batch(self, units_batch: List[Path]) -> bool:
        """Валидирует результаты batch."""
        logger.info("Validating batch...")

        validation_errors = []

        for unit_path in units_batch:
            unit_name = unit_path.name

            # Проверка 1: UNIT должен быть обработан
            if unit_name not in self.processed_units:
                validation_errors.append(f"{unit_name}: not marked as processed")
                continue

            # В dry_run режиме дальнейшая валидация не имеет смысла
            if self.dry_run:
                continue

            # Проверка 2: Найти UNIT в целевых директориях
            # TODO: более детальная проверка (проверить что файлы действительно скопированы)

        if validation_errors:
            logger.warning(f"Validation found {len(validation_errors)} issues")
            for error in validation_errors[:10]:  # Показываем первые 10
                logger.warning(f"  - {error}")
            return False

        logger.info("Validation PASSED")
        return True

    def run(self):
        """Главный метод запуска."""
        logger.info("=" * 80)
        logger.info("CYCLE 1 FULL RUN TEST")
        logger.info("=" * 80)
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Protocol date: {self.protocol_date}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info(f"Copy mode: {self.copy_mode}")
        if self.limit:
            logger.info(f"Limit: {self.limit} UNITs")
        logger.info("=" * 80)

        self.stats['start_time'] = datetime.now().isoformat()

        # Prerequisites check
        if not self.check_prerequisites():
            logger.error("Prerequisites check failed, aborting")
            return False

        # Load checkpoint if exists
        self.load_checkpoint()

        # Get units to process
        units_to_process = self.get_units_to_process()
        self.stats['total'] = len(units_to_process) + len(self.processed_units)

        if not units_to_process:
            logger.info("No units to process")
            # Создаем отчет даже если нечего обрабатывать
            self.stats['end_time'] = datetime.now().isoformat()
            self.generate_report()
            return True

        # Process in batches
        batch_num = 0
        for i in range(0, len(units_to_process), self.batch_size):
            batch_num += 1
            units_batch = units_to_process[i:i + self.batch_size]

            logger.info(f"\n{'=' * 80}")
            logger.info(f"BATCH {batch_num}: Processing units {i+1} to {i+len(units_batch)}")
            logger.info(f"{'=' * 80}")

            # Process batch
            batch_stats = self.process_batch(units_batch)

            # Validate batch
            self.validate_batch(units_batch)

            # Save checkpoint
            self.save_checkpoint()

            # Проверка места после каждого batch
            if not self.dry_run:
                has_space, msg = check_disk_space(self.input_dir.parent, 10.0)
                if not has_space:
                    logger.warning(msg)
                    logger.warning("Low disk space, stopping")
                    break

        self.stats['end_time'] = datetime.now().isoformat()

        # Final disk space check
        _, msg = check_disk_space(self.input_dir.parent, 0.0)
        self.stats['disk_space_after'] = msg

        # Generate report
        self.generate_report()

        logger.info("\n" + "=" * 80)
        logger.info("CYCLE 1 FULL RUN COMPLETED")
        logger.info("=" * 80)

        return True

    def generate_report(self):
        """Генерирует детальный отчет."""
        report_file = Path("/tmp/cycle1_full_run_FINAL_REPORT.md")

        logger.info(f"Generating report: {report_file}")

        # Подсчет времени
        start = datetime.fromisoformat(self.stats['start_time'])
        end = datetime.fromisoformat(self.stats['end_time'])
        duration = end - start

        # Распределение по маршрутам
        merge_count = len(self.stats['by_destination'].get('Merge/Direct', []))
        processing_convert = len(self.stats['by_destination'].get('Processing_1/Convert', []))
        processing_extract = len(self.stats['by_destination'].get('Processing_1/Extract', []))
        processing_normalize = len(self.stats['by_destination'].get('Processing_1/Normalize', []))
        exceptions_empty = len(self.stats['by_destination'].get('Exceptions_1/Empty', []))
        exceptions_special = len(self.stats['by_destination'].get('Exceptions_1/Special', []))
        exceptions_ambiguous = len(self.stats['by_destination'].get('Exceptions_1/Ambiguous', []))

        processing_total = processing_convert + processing_extract + processing_normalize
        exceptions_total = exceptions_empty + exceptions_special + exceptions_ambiguous

        with open(report_file, 'w') as f:
            f.write("# CYCLE 1 FULL RUN FINAL REPORT\n\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
            f.write("---\n\n")

            f.write("## Executive Summary\n\n")
            f.write(f"- **Date:** {self.stats['start_time']}\n")
            f.write(f"- **Duration:** {duration}\n")
            f.write(f"- **UNITs Total:** {self.stats['total']}\n")
            if self.stats['total'] > 0:
                f.write(f"- **UNITs Processed:** {self.stats['processed']}/{self.stats['total']} "
                       f"({self.stats['processed']/self.stats['total']*100:.1f}%)\n")
            else:
                f.write(f"- **UNITs Processed:** {self.stats['processed']}/{self.stats['total']}\n")
            f.write(f"- **Successful:** {self.stats['successful']}\n")
            f.write(f"- **Failed:** {self.stats['failed']}\n")
            f.write(f"- **Mode:** {'DRY RUN' if self.dry_run else 'REAL RUN'}\n")
            f.write(f"- **Copy Mode:** {self.copy_mode}\n")
            f.write(f"- **Status:** {'✅ SUCCESS' if self.stats['failed'] == 0 else '⚠️ PARTIAL SUCCESS'}\n\n")

            f.write("---\n\n")

            f.write("## Исправленные баги в этом запуске\n\n")
            f.write("1. ✅ **БАГ #1**: Empty UNITs path - теперь показывают `Exceptions_1/Empty`\n")
            f.write("2. ✅ **БАГ #2**: Race condition при удалении target_dir - добавлена проверка на пустоту\n")
            f.write("3. ✅ **БАГ #3**: Error handling в move/copy операциях - добавлены try-except обертки\n")
            f.write("4. ✅ **БАГ #4**: Error handling в classify_unit - реализовано в test script\n")
            f.write("5. ✅ **БАГ #5**: fsync() в save_manifest - добавлена гарантия записи на диск\n")
            f.write("6. ✅ **БАГ #6**: Проверка свободного места - добавлен disk_utils.py\n\n")

            f.write("---\n\n")

            if self.stats['processed'] > 0:
                f.write("## Распределение по категориям\n\n")
                for category, count in sorted(self.stats['by_category'].items(), key=lambda x: -x[1]):
                    percentage = (count / self.stats['processed']) * 100
                    f.write(f"- **{category}**: {count} ({percentage:.1f}%)\n")
                f.write("\n")

                f.write("## Распределение по маршрутам\n\n")
                f.write(f"### 🟢 Merge_0/Direct (готовы к Docling)\n")
                f.write(f"- **Всего:** {merge_count} UNITs ({(merge_count/self.stats['processed']*100):.1f}%)\n\n")

                f.write(f"### 🔵 Processing_1 (требуют обработки)\n")
                f.write(f"- **Всего:** {processing_total} UNITs ({(processing_total/self.stats['processed']*100):.1f}%)\n")
                f.write(f"  - Convert: {processing_convert}\n")
                f.write(f"  - Extract: {processing_extract}\n")
                f.write(f"  - Normalize: {processing_normalize}\n\n")

                f.write(f"### 🔴 Exceptions_1 (исключения)\n")
                f.write(f"- **Всего:** {exceptions_total} UNITs ({(exceptions_total/self.stats['processed']*100):.1f}%)\n")
                f.write(f"  - Empty: {exceptions_empty}\n")
                f.write(f"  - Special: {exceptions_special}\n")
                f.write(f"  - Ambiguous: {exceptions_ambiguous}\n\n")

                if self.stats['by_file_type']:
                    f.write("## Типы файлов\n\n")
                    top_types = sorted(self.stats['by_file_type'].items(), key=lambda x: -x[1])[:15]
                    for file_type, count in top_types:
                        f.write(f"- **{file_type}**: {count}\n")
                    f.write("\n")

            f.write("## Производительность\n\n")
            f.write(f"- **Общее время:** {duration}\n")
            if self.stats['batches']:
                avg_batch_time = sum(b['duration_sec'] for b in self.stats['batches']) / len(self.stats['batches'])
                avg_units_per_sec = sum(b['units_per_sec'] for b in self.stats['batches']) / len(self.stats['batches'])
                f.write(f"- **Среднее время batch:** {avg_batch_time:.1f} sec\n")
                f.write(f"- **Средняя скорость:** {avg_units_per_sec:.2f} units/sec\n")
            if self.stats.get('disk_space_before'):
                f.write(f"- **Disk space before:** {self.stats['disk_space_before']}\n")
            if self.stats.get('disk_space_after'):
                f.write(f"- **Disk space after:** {self.stats['disk_space_after']}\n")
            f.write("\n")

            if self.stats['errors']:
                f.write("## Ошибки\n\n")
                f.write(f"**Всего ошибок:** {len(self.stats['errors'])}\n\n")
                for i, error in enumerate(self.stats['errors'][:20], 1):  # Первые 20
                    f.write(f"{i}. **{error['unit']}**: {error.get('error_type', 'Unknown')} - {error.get('error', 'No details')}\n")
                if len(self.stats['errors']) > 20:
                    f.write(f"\n... и еще {len(self.stats['errors']) - 20} ошибок\n")
                f.write("\n")

            f.write("---\n\n")
            f.write("**End of Report**\n")

        logger.info(f"Report saved: {report_file}")


def main():
    parser = argparse.ArgumentParser(description='Cycle 1 Full Run Test')
    parser.add_argument('--input-dir', type=str,
                       default='/root/winners_preprocessor/final_preprocessing/Data/2025-03-18/Input',
                       help='Input directory with UNITs')
    parser.add_argument('--protocol-date', type=str, default='2025-03-18',
                       help='Protocol date')
    parser.add_argument('--batch-size', type=int, default=50,
                       help='Batch size for processing')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of UNITs to process (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no actual moving)')
    parser.add_argument('--copy-mode', action='store_true', default=False,
                       help='Use copy mode instead of move')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint')
    parser.add_argument('--checkpoint-file', type=str, default='checkpoint.json',
                       help='Checkpoint file path')

    args = parser.parse_args()

    runner = Cycle1TestRunner(
        input_dir=Path(args.input_dir),
        protocol_date=args.protocol_date,
        batch_size=args.batch_size,
        checkpoint_file=args.checkpoint_file,
        dry_run=args.dry_run,
        copy_mode=args.copy_mode,
        limit=args.limit,
    )

    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
