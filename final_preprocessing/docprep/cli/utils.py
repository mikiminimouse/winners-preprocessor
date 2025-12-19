"""
Utils - сервисные команды.
"""
import typer
from pathlib import Path

from ..core.config import init_directory_structure
from ..utils.paths import find_units

app = typer.Typer(name="utils", help="Сервисные команды")


@app.command("init-date")
def utils_init_date(
    date: str = typer.Argument(..., help="Дата в формате YYYY-MM-DD"),
    data_dir: Path = typer.Option(None, "--data-dir", help="Базовая директория Data (по умолчанию ./Data)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Создать структуру директорий для даты согласно PRD."""
    from ..core.config import DATA_BASE_DIR, init_directory_structure
    
    if data_dir is None:
        data_dir = DATA_BASE_DIR
    
    if verbose:
        typer.echo(f"Инициализация структуры для даты: {date}")
        typer.echo(f"Базовая директория: {data_dir}")
    
    init_directory_structure(data_dir, date)
    typer.echo(f"✓ Структура директорий создана для {date}")


@app.command("clean")
def utils_clean(
    directory: Path = typer.Argument(..., help="Директория для очистки"),
    confirm: bool = typer.Option(False, "--confirm", help="Подтверждение"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Очистить директорию."""
    if not confirm:
        typer.echo("Используйте --confirm для подтверждения", err=True)
        raise typer.Exit(1)

    typer.echo(f"Очистка директории: {directory}")
    # TODO: Реализовать безопасную очистку


@app.command("stats")
def utils_stats(
    directory: Path = typer.Argument(..., help="Директория для статистики"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Показать статистику по директории."""
    typer.echo(f"Статистика: {directory}")
    units = find_units(directory)
    typer.echo(f"Всего UNIT: {len(units)}")
    # TODO: Добавить детальную статистику

