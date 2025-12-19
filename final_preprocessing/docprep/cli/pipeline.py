"""
Pipeline - полный прогон preprocessing (3 цикла подряд).
"""
import typer
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

    Выполняет: classifier → pending → merge для каждого цикла.
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

    # Запускаем циклы
    for cycle_num in range(1, max_cycles + 1):
        if verbose:
            typer.echo(f"\n=== Цикл {cycle_num} ===")

        try:
            # Получаем пути для цикла
            cycle_paths = get_cycle_paths(cycle_num, processing_dir)

            # 1. Классификация
            if verbose:
                typer.echo(f"Классификация цикла {cycle_num}...")
            # TODO: Реализовать классификацию всех UNIT в input_dir

            # 2. Обработка Pending
            if verbose:
                typer.echo(f"Обработка Pending_{cycle_num}...")
            # TODO: Реализовать обработку всех Pending директорий

            # 3. Merge
            if verbose:
                typer.echo(f"Merge цикла {cycle_num}...")
            # TODO: Реализовать merge в Merge_N

        except Exception as e:
            if stop_on_exception:
                typer.echo(f"Ошибка в цикле {cycle_num}: {e}", err=True)
                raise
            else:
                typer.echo(f"Предупреждение в цикле {cycle_num}: {e}", err=True)

    # Финальный merge из всех Merge_N в Ready2Docling
    if verbose:
        typer.echo("\n=== Финальный merge в Ready2Docling ===")

    merge_dirs = []
    for cycle_num in range(1, max_cycles + 1):
        cycle_paths = get_cycle_paths(cycle_num, processing_dir)
        merge_dirs.append(cycle_paths["merge"])

    result = merger_engine.collect_units(merge_dirs, output_dir)
    typer.echo(f"Обработано UNIT: {result['units_processed']}")

