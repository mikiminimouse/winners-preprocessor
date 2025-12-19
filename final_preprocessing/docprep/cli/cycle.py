"""
Cycle - управление отдельным циклом (1, 2, 3).
"""
import typer
from pathlib import Path

from ..engine.classifier import Classifier
from ..core.config import get_cycle_paths

app = typer.Typer(name="cycle", help="Управление отдельным циклом")


@app.command("run")
def cycle_run(
    cycle_num: int = typer.Argument(..., help="Номер цикла (1, 2, 3)"),
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    pending_dir: Path = typer.Option(..., "--pending", help="Pending директория"),
    merge_dir: Path = typer.Option(..., "--merge", help="Merge директория"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Режим проверки"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Запускает полный цикл обработки."""
    if cycle_num < 1 or cycle_num > 3:
        typer.echo("Цикл должен быть 1, 2 или 3", err=True)
        raise typer.Exit(1)

    typer.echo(f"Запуск цикла {cycle_num}: {input_dir}")
    # TODO: Реализовать полный цикл


@app.command("classify")
def cycle_classify(
    cycle_num: int = typer.Argument(..., help="Номер цикла (1, 2, 3)"),
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Выполняет только классификацию цикла."""
    if cycle_num < 1 or cycle_num > 3:
        typer.echo("Цикл должен быть 1, 2 или 3", err=True)
        raise typer.Exit(1)

    typer.echo(f"Классификация цикла {cycle_num}: {input_dir}")
    classifier_engine = Classifier()
    # TODO: Реализовать классификацию


@app.command("process")
def cycle_process(
    cycle_num: int = typer.Argument(..., help="Номер цикла (1, 2, 3)"),
    pending_dir: Path = typer.Option(..., "--pending", help="Pending директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Выполняет только обработку Pending директории."""
    if cycle_num < 1 or cycle_num > 3:
        typer.echo("Цикл должен быть 1, 2 или 3", err=True)
        raise typer.Exit(1)

    typer.echo(f"Обработка Pending_{cycle_num}: {pending_dir}")
    # TODO: Реализовать обработку

