"""
Pipeline - полный прогон preprocessing (3 цикла подряд).
"""
import typer
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..engine.classifier import Classifier
from ..engine.converter import Converter
from ..engine.extractor import Extractor
from ..engine.merger import Merger
from ..core.config import get_cycle_paths, init_directory_structure, get_data_paths

app = typer.Typer(name="pipeline", help="Полный прогон preprocessing")


@app.command("run")
def pipeline_run(
    input_dir: Path = typer.Argument(..., help="Входная директория (Input)"),
    output_dir: Path = typer.Argument(..., help="Выходная директория (Ready2Docling)"),
    max_cycles: int = typer.Option(3, "--max-cycles", help="Максимальное количество циклов"),
    stop_on_exception: bool = typer.Option(
        False, "--stop-on-exception", help="Останавливаться при ошибке"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим проверки"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """
    Запускает полный цикл preprocessing (3 цикла подряд).

    Выполняет: classifier → processing → merge для каждого цикла.
    """
    if verbose:
        typer.echo(f"Запуск полного pipeline: {input_dir} -> {output_dir}")

    if dry_run:
        typer.echo("🔍 РЕЖИМ DRY RUN - изменения не будут применены")

    # Определяем дату протокола из input_dir или используем текущую
    protocol_date = datetime.now().strftime("%Y-%m-%d")
    if "/" in str(input_dir) or "\\" in str(input_dir):
        # Пытаемся извлечь дату из пути
        parts = Path(input_dir).parts
        for part in parts:
            if part and len(part) == 10 and part[4] == "-" and part[7] == "-":
                protocol_date = part
                break

    typer.echo(f"📅 Дата протокола: {protocol_date}")

    # Инициализируем структуру директорий с правильной датой
    init_directory_structure(date=protocol_date)

    classifier_engine = Classifier()
    converter_engine = Converter()
    extractor_engine = Extractor()
    merger_engine = Merger()

    # Запускаем циклы
    for cycle_num in range(1, max_cycles + 1):
        typer.echo(f"\n{'='*60}")
        typer.echo(f"🔄 ЦИКЛ {cycle_num} из {max_cycles}")
        typer.echo(f"{'='*60}")

        try:
            # Используем cycle_run для полного цикла
            from ..cli.cycle import cycle_run
            
            cycle_input_dir = input_dir if cycle_num == 1 else None
            
            cycle_run(
                cycle_num=cycle_num,
                input_dir=cycle_input_dir,
                protocol_date=protocol_date,
                dry_run=dry_run,
                verbose=verbose,
            )

        except Exception as e:
            if stop_on_exception:
                typer.echo(f"❌ Ошибка в цикле {cycle_num}: {e}", err=True)
                raise
            else:
                typer.echo(f"⚠️  Предупреждение в цикле {cycle_num}: {e}", err=True)
                continue

    # Финальный merge из всех Merge_N в Ready2Docling
    if verbose:
        typer.echo("\n=== Финальный merge в Ready2Docling ===")

    # Получаем правильные пути для merge директорий
    data_paths = get_data_paths(protocol_date)
    merge_dirs = []
    
    # Добавляем Merge_0/Direct для direct файлов из цикла 1
    merge_0_direct = data_paths["merge"] / "Merge_0" / "Direct"
    if merge_0_direct.exists():
        merge_dirs.append(data_paths["merge"] / "Merge_0")
    
    # Добавляем все Merge_N (1, 2, 3)
    for cycle_num in range(1, max_cycles + 1):
        cycle_paths = get_cycle_paths(
            cycle_num,
            data_paths["processing"],
            data_paths["merge"],
            data_paths["exceptions"]
        )
        merge_dirs.append(cycle_paths["merge"])

    typer.echo(f"🔍 Merge dirs: {[str(d) for d in merge_dirs]}")
    result = merger_engine.collect_units(merge_dirs, output_dir)
    typer.echo(f"✅ Обработано UNIT: {result['units_processed']}")
    if result.get("errors"):
        typer.echo(f"⚠️  Ошибок: {len(result['errors'])}", err=True)
        if verbose:
            for error in result["errors"][:10]:  # Показываем первые 10 ошибок
                typer.echo(f"  ❌ {error.get('unit_id', 'unknown')}: {error.get('error', 'unknown error')}", err=True)

    # Очищаем Merge директории после успешного финального merge
    if result['units_processed'] > 0:
        typer.echo("🧹 Очистка Merge директорий...")
        for merge_dir in merge_dirs:
            if merge_dir.exists():
                import shutil
                try:
                    # Очищаем содержимое директории, но оставляем саму директорию
                    for item in merge_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    typer.echo(f"  ✅ Очищено: {merge_dir}")
                except Exception as e:
                    typer.echo(f"  ⚠️  Ошибка очистки {merge_dir}: {e}", err=True)

        # Очищаем Processing директории
        typer.echo("🧹 Очистка Processing директорий...")
        processing_base = data_paths["processing"]
        for cycle_num in range(1, max_cycles + 1):
            cycle_processing_dir = processing_base / f"Processing_{cycle_num}"
            if cycle_processing_dir.exists():
                try:
                    for item in cycle_processing_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        elif item.is_dir():
                            shutil.rmtree(item)
                    typer.echo(f"  ✅ Очищено: {cycle_processing_dir}")
                except Exception as e:
                    typer.echo(f"  ⚠️  Ошибка очистки {cycle_processing_dir}: {e}", err=True)

