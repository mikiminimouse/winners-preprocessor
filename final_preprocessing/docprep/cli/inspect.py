"""
Inspect - отладка и анализ UNIT.
"""
import typer
import json
from pathlib import Path

from ..core.manifest import load_manifest
from ..utils.paths import find_units

app = typer.Typer(name="inspect", help="Отладка и анализ")


@app.command("tree")
def inspect_tree(
    directory: Path = typer.Argument(..., help="Директория для анализа"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Показать дерево директории."""
    typer.echo(f"Дерево директории: {directory}")
    # TODO: Реализовать вывод дерева


@app.command("units")
def inspect_units(
    directory: Path = typer.Argument(..., help="Директория с UNIT"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Показать список UNIT с состояниями."""
    typer.echo(f"UNIT в директории: {directory}")
    units = find_units(directory)
    for unit_path in units:
        manifest_path = unit_path / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = load_manifest(unit_path)
                state = manifest.get("state_machine", {}).get("current_state", "unknown")
                typer.echo(f"  {unit_path.name}: {state}")
            except Exception:
                typer.echo(f"  {unit_path.name}: (ошибка загрузки manifest)")
        else:
            typer.echo(f"  {unit_path.name}: (нет manifest)")


@app.command("manifest")
def inspect_manifest(
    unit_id: str = typer.Argument(..., help="ID UNIT"),
    directory: Path = typer.Option(..., "--directory", help="Директория поиска"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Подробный вывод"),
):
    """Показать manifest конкретного UNIT."""
    unit_path = directory / unit_id
    if not unit_path.exists():
        typer.echo(f"UNIT не найден: {unit_path}", err=True)
        raise typer.Exit(1)

    manifest_path = unit_path / "manifest.json"
    if not manifest_path.exists():
        typer.echo(f"Manifest не найден: {manifest_path}", err=True)
        raise typer.Exit(1)

    try:
        manifest = load_manifest(unit_path)
        typer.echo(json.dumps(manifest, indent=2, ensure_ascii=False))
    except Exception as e:
        typer.echo(f"Ошибка загрузки manifest: {e}", err=True)
        raise typer.Exit(1)

