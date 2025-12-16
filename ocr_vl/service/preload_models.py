#!/usr/bin/env python3
"""
Скрипт предзагрузки моделей из HuggingFace (build-time).
Требуется переменная окружения HF_TOKEN (передается как ARG HF_TOKEN).
Модели сохраняются в: $PADDLEX_HOME/official_models/<repo_name>/...
"""
import os
import sys
from pathlib import Path
from huggingface_hub import snapshot_download

print("=" * 70)
print("ПРЕДЗАГРУЗКА МОДЕЛЕЙ PIPELINE (HuggingFace)")
print("=" * 70)
print()

HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    print("⚠️  HF_TOKEN не задан — предзагрузка пропущена.")
    sys.exit(0)

paddlex_home = os.environ.get("PADDLEX_HOME", "/home/paddleocr/.paddlex")
os.environ["PADDLEX_HOME"] = paddlex_home
os.environ["HF_HOME"] = os.environ.get("HF_HOME", "/home/paddleocr/.cache/huggingface")

models_dir = Path(paddlex_home) / "official_models"
models_dir.mkdir(parents=True, exist_ok=True)

# Список целевых репозиториев HF (актуальные официальные)
targets = [
    # VL модель
    "PaddlePaddle/PaddleOCR-VL",
    # Layout
    "PaddlePaddle/PP-StructureV3-Layout-Base",
    # OCR det/rec/cls (PP-OCRv5)
    "PaddlePaddle/PP-OCRv5-det",
    "PaddlePaddle/PP-OCRv5-rec",
    "PaddlePaddle/PP-OCRv5-cls",
    # Таблицы (опционально, добавляем для полноты)
    "PaddlePaddle/PP-StructureV3-Table-Det",
    "PaddlePaddle/PP-StructureV3-Table-Rec",
]

loaded = []
failed = []

for repo in targets:
    target_dir = models_dir / repo.split("/")[-1]
    try:
        print(f"-> скачивание {repo} ...")
        snapshot_download(
            repo_id=repo,
            local_dir=str(target_dir),
            token=HF_TOKEN,
            resume_download=True,
            local_dir_use_symlinks=False,
        )
        loaded.append(repo)
        size = sum(f.stat().st_size for f in target_dir.rglob("*") if f.is_file())
        print(f"   ✅ ok ({size/(1024*1024):.1f} MB)")
    except Exception as e:
        failed.append((repo, str(e)))
        print(f"   ⚠️ fail: {e}")

print("\n" + "=" * 70)
print("ИТОГИ")
print("=" * 70)
print(f"✅ Успешно: {len(loaded)}")
for r in loaded:
    print(f"   - {r}")

if failed:
    print(f"\n⚠️ Не удалось: {len(failed)}")
    for r, err in failed:
        print(f"   - {r}: {err}")

print("=" * 70)

# Завершаем успехом даже при частичных неудачах: build не должен падать
sys.exit(0)

