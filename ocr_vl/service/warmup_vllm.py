#!/usr/bin/env python3
"""
Warmup скрипт для компиляции kernels и предзагрузки моделей в память
Выполняется при старте контейнера (non-blocking)
"""
import os
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PADDLEX_HOME = Path(os.environ.get("PADDLEX_HOME", "/home/paddleocr/.paddlex"))
MODEL_ROOT = PADDLEX_HOME / "official_models"
DET_DIR = MODEL_ROOT / "PP-OCRv5_server_det_infer"
REC_DIR = MODEL_ROOT / "PP-OCRv5_server_rec_infer"
CLS_DIR = MODEL_ROOT / "PP-LCNet_x1_0_doc_ori_infer"
LAYOUT_DIR = MODEL_ROOT / "PP-DocLayout_plus-L_infer"
TABLE_DET_DIR = MODEL_ROOT / "RT-DETR-L_wired_table_cell_det_infer"
TABLE_CLS_DIR = MODEL_ROOT / "PP-LCNet_x1_0_table_cls_infer"
VL_DIR = MODEL_ROOT / "PaddleOCR-VL_infer"
STRUCTURE_CFG = Path("/app/PP-StructureV3.yaml")

def warmup_ocr():
    """Warmup OCR системы"""
    try:
        from paddleocr import PaddleOCR
        logger.info("Warming up PP-OCRv5...")
        ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ch',
            show_log=False,
            use_gpu=True,
            det_model_dir=str(DET_DIR) if DET_DIR.exists() else None,
            rec_model_dir=str(REC_DIR) if REC_DIR.exists() else None,
            cls_model_dir=str(CLS_DIR) if CLS_DIR.exists() else None,
        )
        # Тестовый образ для warmup (если доступен)
        sample_img = os.environ.get("WARMUP_IMG", "/workspace/test_images/warmup.png")
        if os.path.exists(sample_img):
            logger.info(f"Running OCR warmup on {sample_img}")
            result = ocr.ocr(sample_img, cls=True)
            logger.info("OCR warmup completed")
        else:
            logger.info(f"Warmup image not found: {sample_img} (skipping)")
    except Exception as e:
        logger.warning(f"OCR warmup failed: {e}")

def warmup_structure():
    """Warmup Structure detection"""
    try:
        from paddlex.pipelines.structure.layout import StructureV3
        logger.info("Warming up PP-StructureV3...")
        struct = StructureV3(
            paddlex_config=str(STRUCTURE_CFG) if STRUCTURE_CFG.exists() else None,
            layout_model_dir=str(LAYOUT_DIR) if LAYOUT_DIR.exists() else None,
            table_model_dir=str(TABLE_DET_DIR) if TABLE_DET_DIR.exists() else None,
            table_cls_model_dir=str(TABLE_CLS_DIR) if TABLE_CLS_DIR.exists() else None,
            device="gpu",
            device_id=0,
        )
        sample_img = os.environ.get("WARMUP_IMG", "/workspace/test_images/warmup.png")
        if os.path.exists(sample_img):
            logger.info(f"Running Structure warmup on {sample_img}")
            result = struct.run(sample_img)
            logger.info("Structure warmup completed")
        else:
            logger.info(f"Warmup image not found: {sample_img} (skipping)")
    except ImportError:
        logger.info("PP-StructureV3 not available (skipping warmup)")
    except Exception as e:
        logger.warning(f"Structure warmup failed: {e}")

def warmup_vllm():
    """Проверка доступности vLLM endpoint"""
    try:
        import requests
        vllm_url = os.environ.get("VLLM_URL", "http://127.0.0.1:8080/v1/markdown")
        health_url = vllm_url.replace("/v1/markdown", "/health")
        logger.info(f"Checking vLLM health: {health_url}")
        resp = requests.get(health_url, timeout=5)
        if resp.status_code == 200:
            logger.info("vLLM endpoint is available")
        else:
            logger.warning(f"vLLM health check returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"vLLM health check failed: {e}")


def warmup_vl():
    """Warmup PaddleOCR-VL"""
    try:
        from paddleocr import PaddleOCRVL
        logger.info("Warming up PaddleOCR-VL...")
        vl = PaddleOCRVL(
            model_dir=str(VL_DIR) if VL_DIR.exists() else None,
            batch_size=1,
        )
        sample_img = os.environ.get("WARMUP_IMG", "/workspace/test_images/warmup.png")
        if os.path.exists(sample_img):
            logger.info(f"Running VL warmup on {sample_img}")
            _ = vl.predict(sample_img)
            logger.info("PaddleOCR-VL warmup completed")
        else:
            logger.info(f"Warmup image not found: {sample_img} (skipping)")
    except Exception as e:
        logger.warning(f"PaddleOCR-VL warmup failed: {e}")

if __name__ == "__main__":
    logger.info("Starting warmup process...")
    
    # Настройка переменных окружения
    os.environ.setdefault('PADDLEX_HOME', '/home/paddleocr/.paddlex')
    os.environ.setdefault('HF_HOME', '/home/paddleocr/.cache/huggingface')
    
    # Выполняем warmup (non-blocking, errors не критичны)
    warmup_ocr()
    warmup_structure()
    warmup_vl()
    warmup_vllm()
    
    logger.info("Warmup process completed")

