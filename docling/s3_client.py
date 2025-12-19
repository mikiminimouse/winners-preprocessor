"""
Cloud.ru Object Storage (S3 API) клиент для интеграции с Docling Pipeline.
Используется для загрузки PDF страниц в S3 и генерации pre-signed URLs для Granite-Docling.
"""
import os
import logging
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CloudRuS3Client:
    """Клиент для работы с Cloud.ru Object Storage (S3 API)"""
    
    def __init__(
        self,
        endpoint_url: str = "https://s3.cloud.ru",  # Cloud.ru endpoint (без bucket в пути)
        access_key_id: Optional[str] = None,
        secret_access_key: Optional[str] = None,
        bucket_name: str = "bucket-winners223",
        region_name: str = "ru-central-1"  # Правильный регион для Cloud.ru
    ):
        """
        Инициализация S3 клиента для Cloud.ru
        
        Args:
            endpoint_url: Cloud.ru S3 endpoint
            access_key_id: Cloud.ru API Access Key в формате tenant_id:key_id
                          (например: "502f76f0-9017-493d-bda4-9e1bb278da84:ce94860ccc8780b2bc5f00f31459d24e")
            secret_access_key: Cloud.ru API Secret Key
            bucket_name: Имя bucket (bucket-winners223)
            region_name: Регион (ru-central-1)
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        
        # Получаем credentials из переменных окружения, если не переданы
        # Cloud.ru требует формат tenant_id:key_id для access_key_id
        access_key_from_env = os.getenv("CLOUDRU_S3_ACCESS_KEY")
        
        # Если есть отдельные переменные для tenant_id и key_id, формируем access_key
        if not access_key_id and not access_key_from_env:
            tenant_id = os.getenv("CLOUDRU_S3_TENANT_ID")
            key_id = os.getenv("CLOUDRU_S3_KEY_ID")
            if tenant_id and key_id:
                access_key_from_env = f"{tenant_id}:{key_id}"
        
        self.access_key_id = access_key_id or access_key_from_env
        self.secret_access_key = secret_access_key or os.getenv("CLOUDRU_S3_SECRET_KEY")
        
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError(
                "Cloud.ru S3 credentials not provided. "
                "Set CLOUDRU_S3_ACCESS_KEY and CLOUDRU_S3_SECRET_KEY environment variables."
            )
        
        # Создаем S3 клиент
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name=region_name
        )
        
        logger.info(f"Cloud.ru S3 client initialized for bucket: {self.bucket_name}")
    
    def upload_file(
        self,
        local_path: Path,
        object_key: str,
        acl: str = 'private',
        content_type: Optional[str] = None
    ) -> bool:
        """
        Загружает файл в Cloud.ru S3
        
        Args:
            local_path: Локальный путь к файлу
            object_key: Ключ объекта в S3 (например, "pages/page_001.png")
            acl: Access Control List ('private' по умолчанию)
            content_type: MIME тип файла (автоопределяется если None)
        
        Returns:
            True если успешно, False иначе
        """
        try:
            extra_args = {'ACL': acl}
            if content_type:
                extra_args['ContentType'] = content_type
            
            self.s3_client.upload_file(
                Filename=str(local_path),
                Bucket=self.bucket_name,
                Key=object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"File uploaded to S3: s3://{self.bucket_name}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return False
    
    def generate_presigned_url(
        self,
        object_key: str,
        expires_in: int = 3600,
        use_public_url: bool = True
    ) -> Optional[str]:
        """
        Генерирует URL для доступа к объекту в S3
        
        Args:
            object_key: Ключ объекта в S3
            expires_in: Время жизни URL в секундах (по умолчанию 1 час) - не используется для публичных URLs
            use_public_url: Если True, использует прямой публичный URL (требует Bucket Policy)
                           Если False, генерирует pre-signed URL
        
        Returns:
            URL или None в случае ошибки
        """
        try:
            if use_public_url:
                # Используем virtual hosted style URL (работает с Bucket Policy)
                # Формат: https://bucket-name.s3.cloud.ru/object-key
                public_url = f"https://{self.bucket_name}.s3.cloud.ru/{object_key}"
                logger.debug(f"Generated public URL (virtual hosted style) for: {object_key}")
                return public_url
            else:
                # Генерируем pre-signed URL с virtual hosted style
                # Cloud.ru S3 требует virtual hosted style для pre-signed URLs
                url = self.s3_client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_key
                    },
                    ExpiresIn=expires_in
                )
                # Преобразуем в virtual hosted style если нужно
                # boto3 может вернуть path style, нужно преобразовать
                if 's3.cloud.ru/' in url and f'/{self.bucket_name}/' in url:
                    # Преобразуем path style в virtual hosted style
                    url = url.replace(f'https://s3.cloud.ru/{self.bucket_name}/', f'https://{self.bucket_name}.s3.cloud.ru/')
                
                logger.debug(f"Generated pre-signed URL for: {object_key} (expires in {expires_in}s)")
                return url
            
        except ClientError as e:
            logger.error(f"Error generating URL: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating URL: {e}")
            return None
    
    def upload_and_get_url(
        self,
        local_path: Path,
        object_key: str,
        expires_in: int = 3600,
        acl: str = 'private',
        content_type: Optional[str] = None,
        use_public_url: bool = True
    ) -> Optional[str]:
        """
        Загружает файл в S3 и возвращает URL (удобный метод)
        
        Args:
            local_path: Локальный путь к файлу
            object_key: Ключ объекта в S3
            expires_in: Время жизни URL в секундах (для pre-signed URLs)
            acl: Access Control List
            content_type: MIME тип файла
            use_public_url: Если True, использует прямой публичный URL (требует Bucket Policy)
        
        Returns:
            URL или None в случае ошибки
        """
        if self.upload_file(local_path, object_key, acl, content_type):
            return self.generate_presigned_url(object_key, expires_in, use_public_url)
        return None
    
    def delete_file(self, object_key: str) -> bool:
        """
        Удаляет файл из S3
        
        Args:
            object_key: Ключ объекта в S3
        
        Returns:
            True если успешно, False иначе
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"File deleted from S3: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def file_exists(self, object_key: str) -> bool:
        """
        Проверяет существование файла в S3
        
        Args:
            object_key: Ключ объекта в S3
        
        Returns:
            True если файл существует, False иначе
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True
        except ClientError:
            return False

