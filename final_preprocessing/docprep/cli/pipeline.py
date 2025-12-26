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

app = typer.Typer(help="Полный прогон preprocessing")


@app.command("run")
def run(
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
            msg = f"Ошибка в цикле {cycle_num}: {e}"
            if stop_on_exception:
                typer.echo(f"❌ {msg}", err=True)
                raise
            else:
                typer.echo(f"⚠️  {msg} - пропуск цикла", err=True)
                continue

    # Финальный merge из всех Merge_N в Ready2Docling
    typer.echo(f"\n{'='*60}")
    typer.echo("🏁 ФИНАЛЬНЫЙ MERGE в Ready2Docling")
    typer.echo(f"{'='*60}")

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
        if cycle_paths["merge"].exists():
             merge_dirs.append(cycle_paths["merge"])

    typer.echo(f"🔍 Источники для Merge: {[d.name for d in merge_dirs]}")
    
    # Получаем er_merge_base для обработки ошибок финального merge
    er_merge_base = data_paths.get("er_merge")
    
    try:
        result = merger_engine.collect_units(merge_dirs, output_dir, cycle=None, er_merge_base=er_merge_base)
        typer.echo(f"✅ Успешно обработано: {result['units_processed']} UNITs")
        
        if result.get("errors"):
            typer.echo(f"⚠️  Ошибок: {len(result['errors'])}", err=True)
            if verbose:
                for error in result["errors"][:10]:
                    typer.echo(f"  ❌ {error.get('unit_id', 'unknown')}: {error.get('error')}", err=True)
        
        # Валидация результата
        ready_units = list(output_dir.rglob("UNIT_*")) if output_dir.exists() else []
        typer.echo(f"📁 UNITs в Ready2Docling: {len(ready_units)}")

        # Очистка только при успешном завершении и если не dry_run
        if not dry_run and result['units_processed'] > 0:
            _cleanup_intermediate_dirs(merge_dirs, data_paths, max_cycles, typer)

    except Exception as e:
        typer.echo(f"❌ Критическая ошибка при финальном merge: {e}", err=True)
        raise


def _cleanup_intermediate_dirs(merge_dirs, data_paths, max_cycles, typer_instance):
    """Очищает промежуточные директории после успешной обработки."""
    import shutil
    
    typer_instance.echo("🧹 Очистка временных директорий...")
    
    # Очистка Merge директорий
    for merge_dir in merge_dirs:
        if merge_dir.exists():
            try:
                for item in merge_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            except Exception as e:
                 typer_instance.echo(f"  ⚠️  Не удалось очистить {merge_dir}: {e}", err=True)

    # Очистка Processing директорий
    processing_base = data_paths["processing"]
    for cycle_num in range(1, max_cycles + 1):
        cycle_processing_dir = processing_base / f"Processing_{cycle_num}"
        if cycle_processing_dir.exists():
            try:
                shutil.rmtree(cycle_processing_dir)
                cycle_processing_dir.mkdir() # Пересоздаем пустую
            except Exception as e:
                typer_instance.echo(f"  ⚠️  Не удалось очистить {cycle_processing_dir}: {e}", err=True)
                
    typer_instance.echo("✅ Очистка завершена")


if __name__ == "__main__":
    app()


