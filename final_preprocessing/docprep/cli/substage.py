"""
Substage - атомарные операции (convert, extract, normalize).
"""
import typer
from pathlib import Path
from typing import Optional

from ..engine.converter import Converter
from ..engine.extractor import Extractor
from ..engine.normalizers import NameNormalizer, ExtensionNormalizer

app = typer.Typer(name="substage", help="Атомарные операции")


@app.command("convert")
def substage_convert_run(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    from_format: Optional[str] = typer.Option(None, "--from", help="Исходный формат"),
    to_format: Optional[str] = typer.Option(None, "--to", help="Целевой формат"),
    engine: str = typer.Option("libreoffice", "--engine", help="Движок конвертации"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Конвертация форматов (doc→docx и т.д.)."""
    typer.echo(f"Конвертация: {input_dir}")
    converter = Converter()
    # TODO: Обработать все UNIT в директории


@app.command("extract")
def substage_extract_run(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    max_depth: int = typer.Option(2, "--max-depth", help="Максимальная глубина"),
    keep_archive: bool = typer.Option(False, "--keep-archive", help="Сохранять архив"),
    flatten: bool = typer.Option(False, "--flatten", help="Размещать все в одной директории"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Разархивация архивов."""
    typer.echo(f"Разархивация: {input_dir}")
    extractor = Extractor()
    # TODO: Обработать все UNIT в директории


@app.command("normalize")
def substage_normalize_name(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Нормализация имени файла (ТОЛЬКО имя)."""
    typer.echo(f"Нормализация имен: {input_dir}")
    normalizer = NameNormalizer()
    # TODO: Обработать все UNIT в директории


@app.command("normalize-extension")
def substage_normalize_extension(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Нормализация расширения (по сигнатурам)."""
    typer.echo(f"Нормализация расширений: {input_dir}")
    normalizer = ExtensionNormalizer()
    # TODO: Обработать все UNIT в директории


@app.command("normalize-full")
def substage_normalize_full(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Полная нормализация (имя + расширение)."""
    typer.echo(f"Полная нормализация: {input_dir}")
    name_normalizer = NameNormalizer()
    ext_normalizer = ExtensionNormalizer()
    # TODO: Обработать все UNIT в директории

