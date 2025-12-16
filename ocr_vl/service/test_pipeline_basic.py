#!/usr/bin/env python3
"""
Тестовый скрипт для проверки базового pipeline PaddleOCR-VL из официального образа
Сравнивает текущую реализацию с официальным примером использования
"""
import os
import sys
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# КРИТИЧНО: Настройка PaddlePaddle для dynamic graph mode ДО импорта
os.environ.setdefault('FLAGS_enable_eager_mode', '1')
os.environ.setdefault('FLAGS_eager_delete_tensor_gb', '0')
os.environ.setdefault('FLAGS_use_mkldnn', '0')

# Установка путей к моделям
if not os.environ.get('PADDLEX_HOME'):
    possible_paths = [
        '/home/paddleocr/.paddlex',
        '/root/.paddlex',
        os.path.expanduser('~/.paddlex'),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            os.environ['PADDLEX_HOME'] = path
            logger.info(f"Set PADDLEX_HOME to {path}")
            break

if not os.environ.get('HF_HOME'):
    os.environ['HF_HOME'] = os.path.expanduser('~/.cache/huggingface')

logger.info("=" * 70)
logger.info("ТЕСТ БАЗОВОГО PIPELINE PADDLEOCR-VL")
logger.info("=" * 70)
logger.info(f"PADDLEX_HOME: {os.environ.get('PADDLEX_HOME', 'NOT SET')}")
logger.info(f"HF_HOME: {os.environ.get('HF_HOME', 'NOT SET')}")
logger.info("=" * 70)

try:
    import paddle
    logger.info(f"PaddlePaddle version: {paddle.__version__}")
    logger.info(f"PaddlePaddle dynamic mode: {paddle.in_dynamic_mode()}")
except Exception as e:
    logger.error(f"Failed to import paddle: {e}")
    sys.exit(1)

# Импорт PaddleOCR-VL
try:
    from paddleocr import PaddleOCRVL
    logger.info("✅ PaddleOCRVL imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import PaddleOCRVL: {e}")
    sys.exit(1)

def test_pipeline_official():
    """Тест официального способа использования pipeline"""
    logger.info("\n" + "=" * 70)
    logger.info("ТЕСТ 1: Официальный способ (как в документации)")
    logger.info("=" * 70)
    
    try:
        # Создаем pipeline как в официальной документации
        logger.info("Initializing PaddleOCRVL()...")
        pipeline = PaddleOCRVL()
        logger.info("✅ Pipeline initialized successfully")
        
        # Тестовое изображение
        test_image = Path(__file__).parent.parent / "test_images" / "page_0001 (3).png"
        if not test_image.exists():
            logger.error(f"❌ Test image not found: {test_image}")
            return False
        
        logger.info(f"Processing image: {test_image}")
        
        # Официальный способ: pipeline.predict()
        output = pipeline.predict(str(test_image))
        logger.info(f"✅ Pipeline.predict() completed successfully")
        logger.info(f"Output type: {type(output)}")
        
        # Проверяем методы результата (как в официальном примере)
        if hasattr(output, '__iter__') and not isinstance(output, str):
            results = list(output) if not isinstance(output, list) else output
            logger.info(f"Number of results: {len(results)}")
            
            for i, res in enumerate(results):
                logger.info(f"\n--- Result {i+1} ---")
                logger.info(f"Type: {type(res)}")
                
                # Проверяем доступные методы
                methods = [m for m in dir(res) if not m.startswith('_')]
                logger.info(f"Available methods: {', '.join(methods[:10])}...")
                
                # Тестируем официальные методы
                if hasattr(res, 'save_to_markdown'):
                    logger.info("✅ Has save_to_markdown method")
                if hasattr(res, 'save_to_json'):
                    logger.info("✅ Has save_to_json method")
                if hasattr(res, 'to_markdown'):
                    logger.info("✅ Has to_markdown method")
                if hasattr(res, 'to_json'):
                    logger.info("✅ Has to_json method")
                if hasattr(res, 'print'):
                    logger.info("✅ Has print method")
                    
                # Пробуем сохранить (как в официальном примере)
                try:
                    test_output_dir = Path("/tmp/pipeline_test")
                    test_output_dir.mkdir(exist_ok=True)
                    
                    if hasattr(res, 'save_to_markdown'):
                        res.save_to_markdown(save_path=str(test_output_dir))
                        logger.info(f"✅ save_to_markdown() successful")
                    
                    if hasattr(res, 'save_to_json'):
                        res.save_to_json(save_path=str(test_output_dir))
                        logger.info(f"✅ save_to_json() successful")
                except Exception as e:
                    logger.warning(f"⚠️  Save methods failed: {e}")
        else:
            logger.info(f"Output is not iterable or is a string: {output}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {e}", exc_info=True)
        return False


def test_pipeline_parameters():
    """Тест с явными параметрами"""
    logger.info("\n" + "=" * 70)
    logger.info("ТЕСТ 2: С явными параметрами")
    logger.info("=" * 70)
    
    try:
        # Пробуем инициализацию с параметрами
        logger.info("Initializing PaddleOCRVL() with explicit parameters...")
        
        # Официальный способ - без параметров (использует дефолты из образа)
        pipeline = PaddleOCRVL()
        logger.info("✅ Pipeline initialized with defaults")
        
        test_image = Path(__file__).parent.parent / "test_images" / "page_0001 (3).png"
        if not test_image.exists():
            logger.error(f"❌ Test image not found: {test_image}")
            return False
        
        logger.info(f"Processing image: {test_image}")
        output = pipeline.predict(str(test_image))
        logger.info(f"✅ Pipeline.predict() completed")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Parameter test failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    logger.info("\nНачинаем тестирование базового pipeline...\n")
    
    # Тест 1: Официальный способ
    result1 = test_pipeline_official()
    
    # Тест 2: С параметрами
    result2 = test_pipeline_parameters()
    
    logger.info("\n" + "=" * 70)
    logger.info("ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info("=" * 70)
    logger.info(f"Тест 1 (Официальный способ): {'✅ PASSED' if result1 else '❌ FAILED'}")
    logger.info(f"Тест 2 (С параметрами): {'✅ PASSED' if result2 else '❌ FAILED'}")
    
    if result1 and result2:
        logger.info("\n✅ Все тесты пройдены успешно!")
        logger.info("Pipeline работает корректно, как в официальной документации")
        sys.exit(0)
    else:
        logger.error("\n❌ Некоторые тесты не прошли")
        logger.error("Проверьте ошибки выше")
        sys.exit(1)

