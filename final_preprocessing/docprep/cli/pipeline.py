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
from ..core.config import get_cycle_paths, init_directory_structure

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

    # Инициализируем структуру директорий
    processing_dir = input_dir.parent / "Processing"
    init_directory_structure(processing_dir)

    classifier_engine = Classifier()
    converter_engine = Converter()
    extractor_engine = Extractor()
    merger_engine = Merger()

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

    merge_dirs = []
    for cycle_num in range(1, max_cycles + 1):
        cycle_paths = get_cycle_paths(cycle_num, processing_dir)
        merge_dirs.append(cycle_paths["merge"])

    result = merger_engine.collect_units(merge_dirs, output_dir)
    typer.echo(f"Обработано UNIT: {result['units_processed']}")

