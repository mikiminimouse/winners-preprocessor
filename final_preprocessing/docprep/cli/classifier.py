"""
Classifier - отдельный контроль классификатора для тестов.
"""
import typer
from pathlib import Path

from ..engine.classifier import Classifier

app = typer.Typer(name="classifier", help="Управление классификатором")


@app.command("run")
def classifier_run(
    input_dir: Path = typer.Option(..., "--input", help="Входная директория"),
    cycle: int = typer.Option(1, "--cycle", help="Номер цикла"),
    report_only: bool = typer.Option(False, "--report-only", help="Только отчёт"),
    confidence_threshold: float = typer.Option(0.9, "--confidence-threshold", help="Порог уверенности"),
    dump_json: bool = typer.Option(False, "--dump-json", help="Вывести JSON"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Запускает классификатор."""
    typer.echo(f"Классификация: {input_dir} (цикл {cycle})")
    classifier = Classifier()
    # TODO: Реализовать классификацию с отчётом

