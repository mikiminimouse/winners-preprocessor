"""
Cycle - управление отдельным циклом (1, 2, 3).
"""
import typer
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..engine.classifier import Classifier
from ..engine.converter import Converter
from ..engine.extractor import Extractor
from ..engine.normalizers import NameNormalizer, ExtensionNormalizer
from ..core.config import get_cycle_paths, get_processing_paths, PROCESSING_DIR, MERGE_DIR
from ..core.unit_processor import process_directory_units
from ..utils.paths import find_all_units

app = typer.Typer(name="cycle", help="Управление отдельным циклом")


@app.command("run")
def cycle_run(
    cycle_num: int = typer.Argument(..., help="Номер цикла (1, 2, 3)"),
    input_dir: Optional[Path] = typer.Option(None, "--input", help="Входная директория"),
    pending_dir: Optional[Path] = typer.Option(None, "--pending", help="Pending директория"),
    merge_dir: Optional[Path] = typer.Option(None, "--merge", help="Merge директория"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим проверки"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Запускает полный цикл обработки: classify → pending → merge."""
    if cycle_num < 1 or cycle_num > 3:
        typer.echo("❌ Цикл должен быть 1, 2 или 3", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"🔄 Запуск цикла {cycle_num}")
    
    # Определяем пути
    processing_base = PROCESSING_DIR / protocol_date
    merge_base = MERGE_DIR / protocol_date
    
    cycle_paths = get_cycle_paths(cycle_num, processing_base, merge_base, None)
    
    if not input_dir:
        input_dir = processing_base / "Input" if cycle_num == 1 else cycle_paths["processing"]
    
    if not pending_dir:
        pending_dir = cycle_paths["processing"]
    
    if not merge_dir:
        merge_dir = cycle_paths["merge"]

    # 1. Классификация
    typer.echo(f"\n📋 Шаг 1: Классификация")
    from ..cli.stage import stage_classifier
    try:
        stage_classifier(
            cycle=cycle_num,
            input_dir=input_dir,
            protocol_date=protocol_date,
            verbose=verbose,
            dry_run=dry_run,
        )
    except Exception as e:
        typer.echo(f"❌ Ошибка классификации: {e}", err=True)
        if dry_run:
            raise

    # 2. Обработка Processing
    typer.echo(f"\n⚙️  Шаг 2: Обработка Processing_{cycle_num}")
    from ..cli.substage import (
        substage_convert_run,
        substage_extract_run,
        substage_normalize_full,
    )
    
    processing_paths = get_processing_paths(cycle_num, processing_base)
    
    # Обработка Convert
    convert_dir = processing_paths["Convert"]
    if convert_dir.exists() and find_all_units(convert_dir):
        typer.echo(f"  🔄 Конвертация: {convert_dir}")
        try:
            substage_convert_run(
                input_dir=convert_dir,
                cycle=cycle_num,
                protocol_date=protocol_date,
                verbose=verbose,
                dry_run=dry_run,
            )
        except Exception as e:
            typer.echo(f"  ⚠️  Ошибка конвертации: {e}", err=True)
    
    # Обработка Extract
    extract_dir = processing_paths["Extract"]
    if extract_dir.exists() and find_all_units(extract_dir):
        typer.echo(f"  📦 Разархивация: {extract_dir}")
        try:
            substage_extract_run(
                input_dir=extract_dir,
                cycle=cycle_num,
                protocol_date=protocol_date,
                verbose=verbose,
                dry_run=dry_run,
            )
        except Exception as e:
            typer.echo(f"  ⚠️  Ошибка разархивации: {e}", err=True)
    
    # Обработка Normalize
    normalize_dir = processing_paths["Normalize"]
    if normalize_dir.exists() and find_all_units(normalize_dir):
        typer.echo(f"  ✨ Нормализация: {normalize_dir}")
        try:
            substage_normalize_full(
                input_dir=normalize_dir,
                cycle=cycle_num,
                protocol_date=protocol_date,
                verbose=verbose,
                dry_run=dry_run,
            )
        except Exception as e:
            typer.echo(f"  ⚠️  Ошибка нормализации: {e}", err=True)

    # 3. Merge
    typer.echo(f"\n🔀 Шаг 3: Merge в {merge_dir}")
    from ..cli.stage import stage_merge
    try:
        stage_merge(
            cycle=cycle_num,
            source_dir=pending_dir,
            target_dir=merge_dir,
            protocol_date=protocol_date,
            verbose=verbose,
            dry_run=dry_run,
        )
    except Exception as e:
        typer.echo(f"❌ Ошибка merge: {e}", err=True)
        if dry_run:
            raise

    typer.echo(f"\n✅ Цикл {cycle_num} завершен")


@app.command("classify")
def cycle_classify(
    cycle_num: int = typer.Argument(..., help="Номер цикла (1, 2, 3)"),
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим проверки"),
):
    """Выполняет только классификацию цикла."""
    if cycle_num < 1 or cycle_num > 3:
        typer.echo("❌ Цикл должен быть 1, 2 или 3", err=True)
        raise typer.Exit(1)

    from ..cli.stage import stage_classifier
    stage_classifier(
        cycle=cycle_num,
        input_dir=input_dir,
        protocol_date=protocol_date,
        verbose=verbose,
        dry_run=dry_run,
    )


@app.command("process")
def cycle_process(
    cycle_num: int = typer.Argument(..., help="Номер цикла (1, 2, 3)"),
    pending_dir: Path = typer.Option(..., "--pending", help="Processing директория"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим проверки"),
):
    """Выполняет только обработку Processing директории."""
    if cycle_num < 1 or cycle_num > 3:
        typer.echo("❌ Цикл должен быть 1, 2 или 3", err=True)
        raise typer.Exit(1)

    from ..cli.stage import stage_pending
    stage_pending(
        cycle=cycle_num,
        pending_dir=pending_dir,
        protocol_date=protocol_date,
        verbose=verbose,
        dry_run=dry_run,
    )

