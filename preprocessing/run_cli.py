#!/usr/bin/env python3
"""Точка входа для CLI."""
import sys
import importlib.util
from pathlib import Path

# Загружаем cli.py напрямую, избегая конфликта с директорией cli/
cli_path = Path(__file__).parent / "cli.py"
spec = importlib.util.spec_from_file_location("cli_main", cli_path)
cli_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli_main)

if __name__ == "__main__":
    cli_main.main()
