"""
Substage - атомарные операции (convert, extract, normalize).
"""
import typer
from pathlib import Path
from typing import Optional
from datetime import datetime

from ..engine.converter import Converter
from ..engine.extractor import Extractor
from ..engine.normalizers import NameNormalizer, ExtensionNormalizer
from ..core.unit_processor import process_directory_units
from ..utils.paths import find_all_units

app = typer.Typer(name="substage", help="Атомарные операции")


@app.command("convert")
def substage_convert_run(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла (1, 2, 3)"),
    from_format: Optional[str] = typer.Option(None, "--from", help="Исходный формат"),
    to_format: Optional[str] = typer.Option(None, "--to", help="Целевой формат"),
    engine: str = typer.Option("libreoffice", "--engine", help="Движок конвертации"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Конвертация форматов (doc→docx и т.д.)."""
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"🔄 Конвертация: {input_dir} (цикл {cycle})")
    
    converter = Converter()
    
    def process_unit(unit_path: Path) -> dict:
        """Обработка одного UNIT конвертером."""
        result = converter.convert_unit(
            unit_path=unit_path,
            cycle=cycle,
            from_format=from_format,
            to_format=to_format,
            engine=engine,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        if verbose:
            typer.echo(f"  ✓ {unit_path.name}: {result.get('files_converted', 0)} файлов")
        return result

    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )

    typer.echo(f"\n✅ Обработано UNIT: {results['units_processed']}")
    if results['units_failed'] > 0:
        typer.echo(f"❌ Ошибок: {results['units_failed']}", err=True)


@app.command("extract")
def substage_extract_run(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла (1, 2, 3)"),
    max_depth: int = typer.Option(2, "--max-depth", help="Максимальная глубина"),
    keep_archive: bool = typer.Option(False, "--keep-archive", help="Сохранять архив"),
    flatten: bool = typer.Option(False, "--flatten", help="Размещать все в одной директории"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Разархивация архивов."""
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"📦 Разархивация: {input_dir} (цикл {cycle})")
    
    extractor = Extractor()
    
    def process_unit(unit_path: Path) -> dict:
        """Обработка одного UNIT экстрактором."""
        result = extractor.extract_unit(
            unit_path=unit_path,
            cycle=cycle,
            max_depth=max_depth,
            keep_archive=keep_archive,
            flatten=flatten,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        if verbose:
            typer.echo(f"  ✓ {unit_path.name}: {result.get('files_extracted', 0)} файлов")
        return result

    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )

    typer.echo(f"\n✅ Обработано UNIT: {results['units_processed']}")
    if results['units_failed'] > 0:
        typer.echo(f"❌ Ошибок: {results['units_failed']}", err=True)


@app.command("normalize")
def substage_normalize_name(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла (1, 2, 3)"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Нормализация имени файла (ТОЛЬКО имя)."""
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"📝 Нормализация имен: {input_dir} (цикл {cycle})")
    
    normalizer = NameNormalizer()
    
    def process_unit(unit_path: Path) -> dict:
        """Обработка одного UNIT нормализатором имен."""
        result = normalizer.normalize_names(
            unit_path=unit_path,
            cycle=cycle,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        if verbose:
            typer.echo(f"  ✓ {unit_path.name}: {result.get('files_normalized', 0)} файлов")
        return result

    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )

    typer.echo(f"\n✅ Обработано UNIT: {results['units_processed']}")
    if results['units_failed'] > 0:
        typer.echo(f"❌ Ошибок: {results['units_failed']}", err=True)


@app.command("normalize-extension")
def substage_normalize_extension(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла (1, 2, 3)"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Нормализация расширения (по сигнатурам)."""
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"🔧 Нормализация расширений: {input_dir} (цикл {cycle})")
    
    normalizer = ExtensionNormalizer()
    
    def process_unit(unit_path: Path) -> dict:
        """Обработка одного UNIT нормализатором расширений."""
        result = normalizer.normalize_extensions(
            unit_path=unit_path,
            cycle=cycle,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        if verbose:
            typer.echo(f"  ✓ {unit_path.name}: {result.get('files_normalized', 0)} файлов")
        return result

    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )

    typer.echo(f"\n✅ Обработано UNIT: {results['units_processed']}")
    if results['units_failed'] > 0:
        typer.echo(f"❌ Ошибок: {results['units_failed']}", err=True)


@app.command("normalize-full")
def substage_normalize_full(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла (1, 2, 3)"),
    protocol_date: Optional[str] = typer.Option(None, "--date", help="Дата протокола (YYYY-MM-DD)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим имитации"),
):
    """Полная нормализация (имя + расширение)."""
    if not input_dir.exists():
        typer.echo(f"❌ Директория не найдена: {input_dir}", err=True)
        raise typer.Exit(1)

    if not protocol_date:
        protocol_date = datetime.now().strftime("%Y-%m-%d")

    typer.echo(f"✨ Полная нормализация: {input_dir} (цикл {cycle})")
    
    name_normalizer = NameNormalizer()
    ext_normalizer = ExtensionNormalizer()
    
    def process_unit(unit_path: Path) -> dict:
        """Обработка одного UNIT полной нормализацией."""
        # Сначала нормализуем имена
        name_result = name_normalizer.normalize_names(
            unit_path=unit_path,
            cycle=cycle,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        # Затем нормализуем расширения (на обновленном пути)
        updated_path = Path(name_result.get("target_directory", unit_path))
        ext_result = ext_normalizer.normalize_extensions(
            unit_path=updated_path,
            cycle=cycle,
            protocol_date=protocol_date,
            dry_run=dry_run,
        )
        if verbose:
            typer.echo(f"  ✓ {unit_path.name}: {name_result.get('files_normalized', 0)} имен, {ext_result.get('files_normalized', 0)} расширений")
        return {
            "name_normalization": name_result,
            "extension_normalization": ext_result,
        }

    results = process_directory_units(
        source_dir=input_dir,
        processor_func=process_unit,
        dry_run=dry_run,
    )

    typer.echo(f"\n✅ Обработано UNIT: {results['units_processed']}")
    if results['units_failed'] > 0:
        typer.echo(f"❌ Ошибок: {results['units_failed']}", err=True)

