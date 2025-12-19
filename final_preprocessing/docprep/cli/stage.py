"""
Stage - этап внутри цикла (classifier, pending, merge).
"""
import typer
from pathlib import Path

from ..engine.classifier import Classifier

app = typer.Typer(name="stage", help="Этап внутри цикла")


@app.command("classifier")
def stage_classifier(
    cycle: int = typer.Option(..., "--cycle", help="Номер цикла (1, 2, 3)"),
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Прогнать classifier по всей директории."""
    typer.echo(f"Classifier цикла {cycle}: {input_dir}")
    classifier_engine = Classifier()
    # TODO: Реализовать


@app.command("pending")
def stage_pending(
    cycle: int = typer.Option(..., "--cycle", help="Номер цикла (1, 2, 3)"),
    pending_dir: Path = typer.Option(..., "--pending", help="Pending директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Обработать все Pending_N."""
    typer.echo(f"Обработка Pending_{cycle}: {pending_dir}")
    # TODO: Реализовать


@app.command("merge")
def stage_merge(
    cycle: int = typer.Option(..., "--cycle", help="Номер цикла (1, 2, 3)"),
    source_dir: Path = typer.Option(..., "--source", help="Исходная директория"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Перенести готовые юниты в Merge_N."""
    typer.echo(f"Merge цикла {cycle}: {source_dir}")
    # TODO: Реализовать

