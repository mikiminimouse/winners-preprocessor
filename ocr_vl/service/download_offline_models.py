#!/usr/bin/env python3
"""
Download/validate offline models for PaddleOCR-VL image build.
- First tries local unpacked folders in offline_models/official_models.
- If missing, downloads tar from BOS (preferred).
- Optional fallback to HuggingFace (requires HF_TOKEN env).
"""
import os
import tarfile
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Optional

try:
    from huggingface_hub import snapshot_download
except Exception:
    snapshot_download = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("download_offline_models")

# Base paths
REPO_ROOT = Path(__file__).resolve().parent
LOCAL_MODELS = REPO_ROOT / "offline_models" / "official_models"
PADDLEX_HOME = Path(os.environ.get("PADDLEX_HOME", "/home/paddleocr/.paddlex"))
TARGET_MODELS = PADDLEX_HOME / "official_models"

# BOS sources (preferred, offline-friendly once downloaded)
BOS_MODELS: Dict[str, List[str]] = {
    "PP-DocLayout_plus-L_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayout_plus-L_infer.tar",
    ],
    "PP-DocLayoutV2_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-DocLayoutV2_infer.tar",
    ],
    "PP-OCRv5_server_det_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_det_infer.tar",
    ],
    "PP-OCRv5_server_rec_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-OCRv5_server_rec_infer.tar",
    ],
    "PP-LCNet_x1_0_doc_ori_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_doc_ori_infer.tar",
    ],
    "RT-DETR-L_wired_table_cell_det_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/RT-DETR-L_wired_table_cell_det_infer.tar",
    ],
    "PP-LCNet_x1_0_table_cls_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PP-LCNet_x1_0_table_cls_infer.tar",
    ],
    "PaddleOCR-VL_infer": [
        "https://paddle-model-ecology.bj.bcebos.com/paddlex/official_inference_model/paddle3.0.0/PaddleOCR-VL_infer.tar",
    ],
}

# Optional HF fallback (very large download)
HF_FALLBACK: Dict[str, str] = {
    "PaddleOCR-VL_infer": "PaddlePaddle/PaddleOCR-VL",
}


def safe_extract_tar(tar_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path, "r:*") as tar:
        tar.extractall(dest)


def download_file(url: str, dest: Path) -> bool:
    import urllib.request
    try:
        log.info(f"Downloading {url}")
        with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return True
    except Exception as e:
        log.warning(f"Download failed from {url}: {e}")
        return False


def ensure_model(model_name: str, target_base: Path) -> None:
    target_dir = target_base / model_name
    if target_dir.exists() and any(target_dir.iterdir()):
        log.info(f"✔ {model_name} already present at {target_dir}")
        return

    # If local pre-unpacked models exist, copy them
    local_dir = LOCAL_MODELS / model_name
    if local_dir.exists() and any(local_dir.iterdir()):
        log.info(f"Copying local model {model_name} -> {target_dir}")
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(local_dir, target_dir, dirs_exist_ok=True)
        return

    # Try BOS tars
    urls = BOS_MODELS.get(model_name, [])
    for url in urls:
        tar_name = url.split("/")[-1]
        tar_path = target_base / tar_name
        if download_file(url, tar_path):
            try:
                safe_extract_tar(tar_path, target_base)
                tar_path.unlink(missing_ok=True)
                log.info(f"✔ Downloaded and extracted {model_name} from BOS")
                return
            except Exception as e:
                log.warning(f"Failed to extract {model_name} from {tar_path}: {e}")
                tar_path.unlink(missing_ok=True)

    # HF fallback (only for PaddleOCR-VL, heavy)
    if model_name in HF_FALLBACK and snapshot_download:
        repo_id = HF_FALLBACK[model_name]
        token = os.environ.get("HF_TOKEN")
        try:
            log.info(f"Downloading {model_name} from HF repo {repo_id}")
            snapshot_dir = snapshot_download(repo_id=repo_id, token=token)
            shutil.copytree(snapshot_dir, target_dir, dirs_exist_ok=True)
            log.info(f"✔ Downloaded {model_name} from HF")
            return
        except Exception as e:
            log.warning(f"HF fallback failed for {model_name}: {e}")

    raise RuntimeError(f"Failed to obtain model {model_name}")


def main():
    TARGET_MODELS.mkdir(parents=True, exist_ok=True)
    for name in BOS_MODELS.keys():
        ensure_model(name, TARGET_MODELS)

    # Summary
    total = 0
    log.info("=== Models prepared ===")
    for d in sorted(TARGET_MODELS.iterdir()):
        if d.is_dir():
            sz = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            total += sz
            log.info(f"{d.name}: {sz/(1024*1024*1024):.2f} GB at {d}")
    log.info(f"Total size: {total/(1024*1024*1024):.2f} GB")


if __name__ == "__main__":
    main()

