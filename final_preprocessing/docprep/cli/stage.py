"""
Stage - этап внутри цикла (classifier, pending, merge).
"""
import typer
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..engine.classifier import Classifier
from ..engine.merger import Merger
from ..core.unit_processor import process_directory_units
from ..core.config import get_processing_paths, get_cycle_paths, PROCESSING_DIR, MERGE_DIR
from ..utils.paths import find_all_units

app = typer.Typer(name="stage", help="Этап внутри цикла")


@app.command("classifier")
def stage_classifier(
    cycle: int = typer.Option(..., "--cycle", help="Номер цикла (1, 2, 3)"),
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Прогнать classifier по всей директории."""
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"🔍 Classifier цикла {cycle}: {input_dir}")
    
    classifier = Classifier()
    
    def process_unit(unit_path: Path) -> dict:
        """Обработка одного UNIT классификатором."""
        # copy_mode автоматически определяется в classify_unit для Input директории
        # (units из Input всегда копируются, а не перемещаются)
        result = classifier.classify_unit(unit_path, cycle, protocol_date, None, dry_run, copy_mode=False)
        if verbose:
            typer.echo(f"  ✓ {unit_path.name}: {result.get('category', 'unknown')}")
        return result

    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )

    typer.echo(f"\n✅ Обработано UNIT: {results['units_processed']}")
    if results['units_failed'] > 0:
        typer.echo(f"❌ Ошибок: {results['units_failed']}", err=True)
        if verbose:
            for error in results['errors']:
                typer.echo(f"  - {error['unit_id']}: {error['error']}", err=True)


@app.command("pending")
def stage_pending(
    cycle: int = typer.Option(..., "--cycle", help="Номер цикла (1, 2, 3)"),
    pending_dir: Path = typer.Option(..., "--pending", help="Processing директория"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """
    Обработать все Processing_N.
    
    Обрабатывает все UNIT в поддиректориях Convert, Extract, Normalize.
    Примечание: Direct файлы не проходят через Processing, они идут напрямую в Merge_0/Direct/ после классификации.
    """
    if not pending_dir.exists():
        typer.echo(f"❌ Директория не найдена: {pending_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"⚙️  Обработка Processing_{cycle}: {pending_dir}")
    
    # Находим все UNIT в поддиректориях
    units = find_all_units(pending_dir)
    
    if not units:
        typer.echo("ℹ️  UNIT не найдены")
        return

    typer.echo(f"📦 Найдено UNIT: {len(units)}")
    
    # Определяем поддиректории Processing
    processing_paths = get_processing_paths(cycle, pending_dir.parent if pending_dir.name.startswith("Processing_") else pending_dir)
    
    # Обработка Convert
    convert_dir = processing_paths["Convert"]
    if convert_dir.exists():
        convert_units = find_all_units(convert_dir)
        if convert_units:
            typer.echo(f"\n  🔄 Конвертация ({len(convert_units)} UNIT)")
            from ..cli.substage import substage_convert_run
            try:
                substage_convert_run(
                    input_dir=convert_dir,
                    cycle=cycle,
                    protocol_date=protocol_date,
                    verbose=verbose,
                    dry_run=dry_run,
                )
            except Exception as e:
                typer.echo(f"  ⚠️  Ошибка конвертации: {e}", err=True)
    
    # Обработка Extract
    extract_dir = processing_paths["Extract"]
    if extract_dir.exists():
        extract_units = find_all_units(extract_dir)
        if extract_units:
            typer.echo(f"\n  📦 Разархивация ({len(extract_units)} UNIT)")
            from ..cli.substage import substage_extract_run
            try:
                substage_extract_run(
                    input_dir=extract_dir,
                    cycle=cycle,
                    protocol_date=protocol_date,
                    verbose=verbose,
                    dry_run=dry_run,
                )
            except Exception as e:
                typer.echo(f"  ⚠️  Ошибка разархивации: {e}", err=True)
    
    # Обработка Normalize
    normalize_dir = processing_paths["Normalize"]
    if normalize_dir.exists():
        normalize_units = find_all_units(normalize_dir)
        if normalize_units:
            typer.echo(f"\n  ✨ Нормализация ({len(normalize_units)} UNIT)")
            from ..cli.substage import substage_normalize_full
            try:
                substage_normalize_full(
                    input_dir=normalize_dir,
                    cycle=cycle,
                    protocol_date=protocol_date,
                    verbose=verbose,
                    dry_run=dry_run,
                )
            except Exception as e:
                typer.echo(f"  ⚠️  Ошибка нормализации: {e}", err=True)
    
    typer.echo(f"\n✅ Обработка Processing_{cycle} завершена")


@app.command("merge")
def stage_merge(
    cycle: int = typer.Option(..., "--cycle", help="Номер цикла (1, 2, 3)"),
    source_dir: Path = typer.Option(..., "--source", help="Исходная директория"),
    target_dir: Optional[Path] = typer.Option(None, "--target", help="Целевая директория (Ready2Docling)"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Перенести готовые юниты в Merge_N."""
    if not source_dir.exists():
        typer.echo(f"❌ Директория не найдена: {source_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    # Определяем целевую директорию Merge
    merge_base = MERGE_DIR / protocol_date if protocol_date else MERGE_DIR
    cycle_paths = get_cycle_paths(cycle, None, merge_base, None)
    
    # Определяем категорию Merge на основе исходной директории
    # Merge_0: Direct файлы (уже там после классификации, merge не нужен)
    # Merge_1, Merge_2, Merge_3: Converted, Extracted, Normalized (из Processing_N после обработки)
    
    # Определяем категорию по пути
    merge_category = None
    source_str = str(source_dir)
    if "Convert" in source_str:
        merge_category = "Converted"
    elif "Extract" in source_str:
        merge_category = "Extracted"
    elif "Normalize" in source_str:
        merge_category = "Normalized"
    else:
        # Если не удалось определить, пытаемся из manifest
        merge_category = "Converted"  # Fallback
    
    if not target_dir:
        if merge_category:
            target_dir = cycle_paths["merge"] / merge_category
        else:
            typer.echo(f"❌ Не удалось определить категорию для {source_dir}", err=True)
            raise typer.Exit(1)

    typer.echo(f"🔀 Merge цикла {cycle}: {source_dir} -> {target_dir} (категория: {merge_category})")
    
    # Находим все UNIT в source_dir
    units = find_all_units(source_dir)
    
    if not units:
        typer.echo("ℹ️  UNIT не найдены")
        return

    typer.echo(f"📦 Найдено UNIT: {len(units)}")
    
    # Перемещаем UNIT в Merge_N
    from ..core.unit_processor import move_unit_to_target
    from ..core.state_machine import UnitState
    from ..core.manifest import load_manifest
    
    if not target_dir.exists():
        target_dir.mkdir(parents=True, exist_ok=True)
    
    moved_count = 0
    errors = []
    
    for unit_path in units:
        try:
            # Определяем расширение для сортировки
            from ..core.unit_processor import determine_unit_extension
            extension = determine_unit_extension(unit_path)
            
            # Пытаемся определить категорию из manifest для точности
            actual_category = merge_category
            try:
                manifest = load_manifest(unit_path)
                operations = manifest.get("processing", {}).get("operations", [])
                # Ищем последнюю операцию
                for op in reversed(operations):
                    op_type = op.get("type")
                    if op_type == "convert":
                        actual_category = "Converted"
                        break
                    elif op_type == "extract":
                        actual_category = "Extracted"
                        break
                    elif op_type == "normalize":
                        actual_category = "Normalized"
                        break
            except Exception:
                pass
            
            # Обновляем target_dir если категория изменилась
            if actual_category != merge_category:
                target_dir_for_unit = cycle_paths["merge"] / actual_category
            else:
                target_dir_for_unit = target_dir
            
            # Перемещаем UNIT в Merge_N с учетом расширения
            target_unit_path = move_unit_to_target(
                unit_dir=unit_path,
                target_base_dir=target_dir_for_unit,
                extension=extension,
                dry_run=dry_run,
            )
            
            # Обновляем состояние UNIT
            # Все обработанные файлы идут в MERGED_PROCESSED
            # (Direct файлы уже в Merge_0/Direct/ после классификации)
            merge_state = UnitState.MERGED_PROCESSED
            
            if not dry_run:
                from ..core.unit_processor import update_unit_state
                update_unit_state(
                    unit_path=target_unit_path,
                    new_state=merge_state,
                    cycle=cycle,
                    operation={
                        "type": "merge",
                        "category": actual_category,
                        "cycle": cycle,
                    },
                )
            
            moved_count += 1
            if verbose:
                typer.echo(f"  ✓ {unit_path.name} -> {target_unit_path}")
        except Exception as e:
            errors.append({"unit_id": unit_path.name, "error": str(e)})
            typer.echo(f"  ❌ {unit_path.name}: {e}", err=True)
    
    typer.echo(f"\n✅ Перемещено UNIT: {moved_count}")
    if errors:
        typer.echo(f"❌ Ошибок: {len(errors)}", err=True)
        if verbose:
            for error in errors:
                typer.echo(f"  - {error['unit_id']}: {error['error']}", err=True)

