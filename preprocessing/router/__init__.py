"""Router microservice for document preprocessing."""
from .config import *
from .mongo import get_mongo_client, get_mongo_metadata_client
from .file_detection import detect_file_type

__all__ = ["get_mongo_client", "get_mongo_metadata_client", "detect_file_type"]
