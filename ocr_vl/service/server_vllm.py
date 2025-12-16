#!/usr/bin/env python3
"""
FastAPI сервер для PaddleOCR-VL обработки (Variant B: vLLM-based)
Минимальный оркестратор - собирает артефакты и отправляет на internal vLLM endpoint
"""
import os
import tempfile
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pdf2image import convert_from_path
import boto3
from botocore.exceptions import ClientError, BotoCoreError

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация FastAPI
app = FastAPI(
    title="PaddleOCR-VL Service (vLLM Variant)",
    description="OCR service using paddlex-genai-vllm-server internal API. Use /docs for interactive API documentation.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Конфигурация из переменных окружения
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/workspace/output"))
TEMP_DIR = Path("/app/temp")
PADDLEX_HOME = os.environ.get("PADDLEX_HOME", "/home/paddleocr/.paddlex")
MODEL_ROOT = Path(PADDLEX_HOME) / "official_models"
DET_DIR = MODEL_ROOT / "PP-OCRv5_server_det_infer"
REC_DIR = MODEL_ROOT / "PP-OCRv5_server_rec_infer"
CLS_DIR = MODEL_ROOT / "PP-LCNet_x1_0_doc_ori_infer"
LAYOUT_DIR = MODEL_ROOT / "PP-DocLayout_plus-L_infer"
TABLE_DET_DIR = MODEL_ROOT / "RT-DETR-L_wired_table_cell_det_infer"
TABLE_CLS_DIR = MODEL_ROOT / "PP-LCNet_x1_0_table_cls_infer"
VL_DIR = MODEL_ROOT / "PaddleOCR-VL_infer"
STRUCTURE_CFG = Path("/app/PP-StructureV3.yaml")

# vLLM endpoint (internal) - Variant B (always on)
VLLM_URL = os.environ.get("VLLM_URL", "http://127.0.0.1:8080/v1/markdown")
USE_VLM_API = True

# Конфигурация cloud.ru Object Storage
CLOUDRU_S3_ENDPOINT = os.getenv("CLOUDRU_S3_ENDPOINT")
CLOUDRU_S3_BUCKET = os.getenv("CLOUDRU_S3_BUCKET")
CLOUDRU_S3_ACCESS_KEY = os.getenv("CLOUDRU_S3_ACCESS_KEY")
CLOUDRU_S3_SECRET_KEY = os.getenv("CLOUDRU_S3_SECRET_KEY")

# Инициализация S3 клиента (если настроены credentials)
s3_client = None
if all([CLOUDRU_S3_ENDPOINT, CLOUDRU_S3_BUCKET, CLOUDRU_S3_ACCESS_KEY, CLOUDRU_S3_SECRET_KEY]):
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=CLOUDRU_S3_ENDPOINT,
            aws_access_key_id=CLOUDRU_S3_ACCESS_KEY,
            aws_secret_access_key=CLOUDRU_S3_SECRET_KEY
        )
        logger.info(f"S3 client initialized for bucket: {CLOUDRU_S3_BUCKET}")
    except Exception as e:
        logger.warning(f"Failed to initialize S3 client: {e}")
        s3_client = None
else:
    logger.info("Cloud.ru S3 credentials not configured, skipping S3 upload")


structure_pipeline = None
ocr_detector = None
vl_parser = None


def init_pipelines():
    global structure_pipeline, ocr_detector, vl_parser
    # StructureV3 with YAML
    if structure_pipeline is None:
        try:
            from paddlex.pipelines.structure.layout import StructureV3
            structure_pipeline = StructureV3(
                paddlex_config=str(STRUCTURE_CFG) if STRUCTURE_CFG.exists() else None,
                layout_model_dir=str(LAYOUT_DIR) if LAYOUT_DIR.exists() else None,
                table_model_dir=str(TABLE_DET_DIR) if TABLE_DET_DIR.exists() else None,
                table_cls_model_dir=str(TABLE_CLS_DIR) if TABLE_CLS_DIR.exists() else None,
                device="gpu",
                device_id=0,
            )
            logger.info("StructureV3 initialized (GPU, batch=1)")
        except Exception as e:
            logger.warning(f"StructureV3 init failed: {e}")
            structure_pipeline = None
    # OCR det/rec/cls
    if ocr_detector is None:
        try:
            from paddleocr import PaddleOCR
            ocr_detector = PaddleOCR(
                use_angle_cls=True,
                lang='ch',
                show_log=True,
                use_gpu=True,
                det_model_dir=str(DET_DIR) if DET_DIR.exists() else None,
                rec_model_dir=str(REC_DIR) if REC_DIR.exists() else None,
                cls_model_dir=str(CLS_DIR) if CLS_DIR.exists() else None,
                det_db_score_mode="fast",
                det_limit_side_len=4096,
                det_limit_type="max",
                rec_batch_num=1,
            )
            logger.info("PaddleOCR (PP-OCRv5) initialized (GPU, batch=1)")
        except Exception as e:
            logger.warning(f"PaddleOCR init failed: {e}")
            ocr_detector = None
    # PaddleOCR-VL (VLDocParser)
    if vl_parser is None:
        try:
            from paddleocr import PaddleOCRVL
            vl_parser = PaddleOCRVL(
                model_dir=str(VL_DIR) if VL_DIR.exists() else None,
                batch_size=1,
            )
            logger.info("PaddleOCR-VL initialized (GPU, batch=1)")
        except Exception as e:
            logger.warning(f"PaddleOCR-VL init failed: {e}")
            vl_parser = None


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске сервера"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    init_pipelines()
    logger.info(f"FastAPI server started. VLLM_URL: {VLLM_URL}, USE_VLM_API: {USE_VLM_API}")


@app.get("/")
async def root():
    """Корневой endpoint с информацией о сервисе"""
    return {
        "service": "PaddleOCR-VL Service (vLLM Variant)",
        "version": "2.0.0",
        "description": "OCR service using paddlex-genai-vllm-server internal API",
        "vllm_url": VLLM_URL,
        "use_vlm_api": USE_VLM_API,
        "endpoints": {
            "docs": "/docs - Swagger UI",
            "health": "/health - Health check",
            "ocr_pdf": "/ocr/pdf - POST - OCR processing for PDF"
        }
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    required_dirs = {
        "det": DET_DIR,
        "rec": REC_DIR,
        "cls": CLS_DIR,
        "layout": LAYOUT_DIR,
        "table_det": TABLE_DET_DIR,
        "table_cls": TABLE_CLS_DIR,
    }
    missing = [name for name, path in required_dirs.items() if not (path.exists() and any(path.iterdir()))]
    models_present = len(missing) == 0
    
    # Проверка доступности vLLM (если используется)
    vllm_status = "not_checked"
    if USE_VLM_API:
        try:
            resp = requests.get(VLLM_URL.replace("/v1/markdown", "/health"), timeout=5)
            vllm_status = "available" if resp.status_code == 200 else "unavailable"
        except Exception as e:
            vllm_status = f"warning: {str(e)}"
    
    return {
        "status": "healthy" if models_present else "degraded",
        "models_present": models_present,
        "missing_models": missing,
        "models_path": str(MODEL_ROOT),
        "vllm_status": vllm_status,
        "vllm_url": VLLM_URL,
        "use_vlm_api": USE_VLM_API,
        "output_dir": str(OUTPUT_DIR),
        "s3_storage": "configured" if s3_client is not None else "not_configured"
    }


@app.post("/ocr/pdf")
async def ocr_pdf(file: UploadFile = File(...)):
    """
    Обработка PDF через OCR pipeline (Variant B: vLLM)
    
    Процесс:
    1. Конвертация PDF в изображения (pdf2image)
    2. Обработка через официальные pipelines (PP-StructureV3, PP-OCRv5)
    3. Отправка артефактов на vLLM endpoint для генерации Markdown/JSON
    4. Сохранение результатов
    
    Returns:
        JSON с результатами обработки
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_pdf_path = None
    temp_images = []
    
    try:
        # Сохраняем загруженный PDF во временный файл
        temp_pdf_path = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        content = await file.read()
        temp_pdf_path.write(content)
        temp_pdf_path.flush()
        pdf_path = temp_pdf_path.name
        
        logger.info(f"Processing PDF: {file.filename}")
        
        # 1. Конвертация PDF в изображения
        logger.info("Converting PDF to images...")
        try:
            images = convert_from_path(pdf_path, dpi=300)
            logger.info(f"Converted {len(images)} pages")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to convert PDF to images: {str(e)}")
        
        # Сохраняем изображения временно
        import uuid
        temp_image_paths = []
        for i, image in enumerate(images):
            temp_filename = f"page_{i+1}_{uuid.uuid4().hex[:8]}.jpg"
            temp_img_path = TEMP_DIR / temp_filename
            image.save(temp_img_path, 'JPEG', quality=95)
            temp_image_paths.append(str(temp_img_path))
            temp_images.append(temp_img_path)
        
        init_pipelines()

        payload = {
            "images": temp_image_paths,
            "pdf_path": pdf_path,
            "pages": len(images)
        }
        
        # Layout/Table via StructureV3
        layout_results = []
        if structure_pipeline:
            try:
                for img_path in temp_image_paths:
                    layout_res = structure_pipeline.run(img_path)
                    layout_results.append(layout_res)
                payload["layout"] = layout_results
                logger.info("Layout detection completed")
            except Exception as e:
                logger.warning(f"Layout detection failed: {e}")
        
        # OCR via PP-OCRv5
        ocr_results = []
        if ocr_detector:
            try:
                for img_path in temp_image_paths:
                    ocr_res = ocr_detector.ocr(img_path, cls=True)
                    ocr_results.append(ocr_res)
                payload["ocr"] = ocr_results
                logger.info("OCR processing completed")
            except Exception as e:
                logger.warning(f"OCR processing failed: {e}")

        # PaddleOCR-VL for Markdown (primary)
        vl_markdowns = []
        vl_json = []
        if vl_parser:
            try:
                for img_path in temp_image_paths:
                    res = vl_parser.predict(img_path)
                    # Попытка извлечь markdown/json из объекта результата
                    if hasattr(res, "to_markdown"):
                        vl_markdowns.append(res.to_markdown())
                    elif hasattr(res, "save_to_markdown"):
                        tmp_md = Path(tempfile.mktemp(suffix=".md", dir=TEMP_DIR))
                        res.save_to_markdown(str(tmp_md))
                        vl_markdowns.append(tmp_md.read_text(encoding="utf-8"))
                        tmp_md.unlink(missing_ok=True)
                    else:
                        vl_markdowns.append(str(res))
                    if hasattr(res, "to_json"):
                        vl_json.append(res.to_json())
                payload["vl_docs"] = vl_json
                logger.info("PaddleOCR-VL processing completed")
            except Exception as e:
                logger.warning(f"PaddleOCR-VL processing failed: {e}")

        combined_markdown = "\n\n".join(vl_markdowns) if vl_markdowns else ""

        # 3. Отправка на vLLM endpoint (Variant B) — best-effort, но не валим всю обработку
        vllm_result = None
        if USE_VLM_API:
            logger.info(f"Sending request to vLLM endpoint: {VLLM_URL}")
            try:
                resp = requests.post(
                    VLLM_URL,
                    json=payload,
                    timeout=300,
                    headers={"Content-Type": "application/json"}
                )
                resp.raise_for_status()
                vllm_result = resp.json()
                logger.info("vLLM processing completed")
            except requests.exceptions.RequestException as e:
                logger.warning(f"vLLM request failed (continuing with VL output): {e}")
                vllm_result = None
        
        # 4. Сохранение результатов
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = Path(file.filename).stem
        
        # Сохраняем Markdown и JSON
        md_path = OUTPUT_DIR / f"{timestamp}_{base_filename}.md"
        json_path = OUTPUT_DIR / f"{timestamp}_{base_filename}.json"
        
        # Приоритет: PaddleOCR-VL markdown; дополнительно сохраняем payload и vLLM результат
        md_content = combined_markdown or (vllm_result.get("markdown") if isinstance(vllm_result, dict) else "")
        if not md_content:
            md_content = json.dumps(vllm_result, ensure_ascii=False, indent=2) if vllm_result else ""
        md_path.write_text(md_content, encoding='utf-8')

        json_payload = {
            "payload": payload,
            "vllm_result": vllm_result,
            "vl_markdown_pages": vl_markdowns,
            "vl_json": vl_json,
            "pages": len(images),
            "input_file": file.filename,
        }
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding='utf-8')
        
        logger.info(f"Results saved: {md_path}, {json_path}")
        
        # Загрузка в S3 (если настроено)
        s3_paths = None
        if s3_client and CLOUDRU_S3_BUCKET:
            try:
                s3_md_key = f"ocr-results/{md_path.name}"
                s3_json_key = f"ocr-results/{json_path.name}"
                s3_client.upload_file(str(md_path), CLOUDRU_S3_BUCKET, s3_md_key)
                s3_client.upload_file(str(json_path), CLOUDRU_S3_BUCKET, s3_json_key)
                s3_base_url = CLOUDRU_S3_ENDPOINT.rstrip('/')
                s3_paths = {
                    "markdown": f"{s3_base_url}/{CLOUDRU_S3_BUCKET}/{s3_md_key}",
                    "json": f"{s3_base_url}/{CLOUDRU_S3_BUCKET}/{s3_json_key}"
                }
                logger.info("Files uploaded to S3")
            except Exception as e:
                logger.warning(f"S3 upload failed: {e}")
        
        # Формируем ответ
        response = {
            "status": "success",
            "input_file": file.filename,
            "pages_processed": len(images),
            "local_files": {
                "markdown": str(md_path),
                "json": str(json_path)
            },
            "vl_markdown_used": bool(combined_markdown),
            "vllm_used": USE_VLM_API,
            "timestamp": datetime.now().isoformat()
        }
        
        if s3_paths:
            response["s3_files"] = s3_paths
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in PDF processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    finally:
        # Очистка временных файлов
        if temp_pdf_path and os.path.exists(temp_pdf_path.name):
            try:
                os.unlink(temp_pdf_path.name)
            except Exception as e:
                logger.warning(f"Failed to delete temp PDF: {e}")
        
        for temp_img in temp_images:
            if temp_img.exists():
                try:
                    temp_img.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temp image {temp_img}: {e}")

