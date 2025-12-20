"""
Decision Engine для разрешения конфликтов между источниками истины.

Реализует формализованные сценарии из эталонного подхода для определения
истинного типа файла на основе MIME, Signature и Extension.
"""
from typing import Dict, Any, Optional
from pathlib import Path


class TypeDecisionEngine:
    """
    Decision Engine для разрешения конфликтов между источниками истины.

    Реализует 7 формализованных сценариев из эталонного подхода.
    """

    # Порог confidence для принятия решения
    CONFIDENCE_THRESHOLD = 0.7

    def resolve(
        self,
        mime_type: str,
        mime_confidence: float,
        signature_type: Optional[str],
        signature_confidence: float,
        extension: str,
    ) -> Dict[str, Any]:
        """
        Разрешает конфликты между источниками истины.

        Args:
            mime_type: MIME тип файла
            mime_confidence: уверенность MIME (0.0-1.0)
            signature_type: тип по сигнатуре или None
            signature_confidence: уверенность сигнатуры (0.0-1.0)
            extension: расширение файла

        Returns:
            Словарь с решением:
            - true_type: истинный тип файла
            - classification: "direct" | "normalize" | "ambiguous"
            - scenario: идентификатор сценария ("2.1", "2.2", и т.д.)
            - confidence: общий уровень уверенности
            - sources_agreement: все ли источники согласны
            - conflict_reason: причина конфликта (если есть)
        """
        # Нормализуем типы для сравнения
        mime_norm = self._normalize_type(mime_type)
        sig_norm = self._normalize_type(signature_type) if signature_type else None
        ext_norm = self._normalize_type_from_extension(extension)

        # Специальная обработка для zip_or_office: если signature указывает на zip_or_office,
        # а MIME на zip, то для сравнения используем zip_or_office для обоих
        if sig_norm == "zip_or_office" and mime_norm == "zip":
            mime_norm = "zip_or_office"

        # Scenario 2.1: Все три совпали
        if mime_norm == sig_norm == ext_norm and sig_norm:
            return {
                "true_type": sig_norm,
                "classification": "direct",
                "scenario": "2.1",
                "confidence": 1.0,
                "sources_agreement": True,
                "conflict_reason": None,
            }

        # Scenario 2.2: MIME+Signature совпали ≠ Extension
        if mime_norm == sig_norm != ext_norm and sig_norm:
            # Для zip_or_office и ole2 нельзя определить correct_extension до структурного парсинга
            if sig_norm in ["zip_or_office", "ole2"]:
                return {
                    "true_type": sig_norm,
                    "classification": "normalize",
                    "scenario": "2.2",
                    "confidence": min(mime_confidence, signature_confidence),
                    "sources_agreement": False,
                    "conflict_reason": f"MIME+Signature={sig_norm} but Extension={ext_norm}, needs structural parsing",
                    "correct_extension": None,  # Будет определен после структурного парсинга
                }
            correct_ext = self._type_to_extension(sig_norm)
            return {
                "true_type": sig_norm,
                "classification": "normalize",
                "scenario": "2.2",
                "confidence": min(mime_confidence, signature_confidence),
                "sources_agreement": False,
                "conflict_reason": f"MIME+Signature={sig_norm} but Extension={ext_norm}",
                "correct_extension": correct_ext,
            }

        # Scenario 2.3: Signature+Extension совпали ≠ MIME
        if sig_norm == ext_norm != mime_norm and sig_norm:
            # Для zip_or_office и ole2 нельзя определить correct_extension до структурного парсинга
            if sig_norm in ["zip_or_office", "ole2"]:
                return {
                    "true_type": sig_norm,
                    "classification": "normalize",
                    "scenario": "2.3",
                    "confidence": signature_confidence,
                    "sources_agreement": False,
                    "conflict_reason": f"Signature+Extension={sig_norm} but MIME={mime_norm}, needs structural parsing",
                    "correct_extension": None,  # Будет определен после структурного парсинга
                }
            correct_ext = self._type_to_extension(sig_norm)
            return {
                "true_type": sig_norm,
                "classification": "normalize",
                "scenario": "2.3",
                "confidence": signature_confidence,
                "sources_agreement": False,
                "conflict_reason": f"Signature+Extension={sig_norm} but MIME={mime_norm}",
                "correct_extension": correct_ext,
            }

        # Scenario 2.4: MIME+Extension совпали ≠ Signature
        if mime_norm == ext_norm != sig_norm and mime_norm:
            correct_ext = self._type_to_extension(mime_norm)
            if mime_confidence >= self.CONFIDENCE_THRESHOLD:
                return {
                    "true_type": mime_norm,
                    "classification": "direct",
                    "scenario": "2.4",
                    "confidence": mime_confidence,
                    "sources_agreement": False,
                    "conflict_reason": f"MIME+Extension={mime_norm} but Signature={sig_norm}",
                    "correct_extension": None,
                }
            else:
                return {
                    "true_type": None,
                    "classification": "ambiguous",
                    "scenario": "2.4",
                    "confidence": mime_confidence,
                    "sources_agreement": False,
                    "conflict_reason": f"Low MIME confidence ({mime_confidence})",
                    "correct_extension": None,
                }

        # Scenario 2.5: Все три разные
        if mime_norm and sig_norm and ext_norm and mime_norm != sig_norm != ext_norm and mime_norm != ext_norm:
            # Приоритет: signature → mime → extension
            if signature_confidence >= self.CONFIDENCE_THRESHOLD:
                correct_ext = self._type_to_extension(sig_norm)
                return {
                    "true_type": sig_norm,
                    "classification": "normalize",
                    "scenario": "2.5",
                    "confidence": signature_confidence,
                    "sources_agreement": False,
                    "conflict_reason": "All sources differ, using signature",
                    "correct_extension": correct_ext,
                }
            elif mime_confidence >= self.CONFIDENCE_THRESHOLD:
                correct_ext = self._type_to_extension(mime_norm)
                return {
                    "true_type": mime_norm,
                    "classification": "normalize",
                    "scenario": "2.5",
                    "confidence": mime_confidence,
                    "sources_agreement": False,
                    "conflict_reason": "All sources differ, using MIME",
                    "correct_extension": correct_ext,
                }
            else:
                return {
                    "true_type": None,
                    "classification": "ambiguous",
                    "scenario": "2.5",
                    "confidence": max(signature_confidence, mime_confidence),
                    "sources_agreement": False,
                    "conflict_reason": "All sources differ, low confidence",
                    "correct_extension": None,
                }

        # Scenario 2.6: MIME = octet-stream
        if mime_type == "application/octet-stream":
            if sig_norm:
                correct_ext = self._type_to_extension(sig_norm)
                return {
                    "true_type": sig_norm,
                    "classification": "normalize",
                    "scenario": "2.6",
                    "confidence": signature_confidence,
                    "sources_agreement": False,
                    "conflict_reason": "MIME=octet-stream, using signature",
                    "correct_extension": correct_ext,
                }
            elif ext_norm:
                correct_ext = self._type_to_extension(ext_norm)
                return {
                    "true_type": ext_norm,
                    "classification": "normalize",
                    "scenario": "2.6",
                    "confidence": 0.5,  # Низкая уверенность для extension
                    "sources_agreement": False,
                    "conflict_reason": "MIME=octet-stream, using extension",
                    "correct_extension": correct_ext,
                }
            else:
                return {
                    "true_type": None,
                    "classification": "ambiguous",
                    "scenario": "2.6",
                    "confidence": 0.0,
                    "sources_agreement": False,
                    "conflict_reason": "MIME=octet-stream, no other sources",
                    "correct_extension": None,
                }

        # Scenario 2.7: Signature отсутствует
        if not sig_norm:
            if mime_confidence >= self.CONFIDENCE_THRESHOLD:
                correct_ext = self._type_to_extension(mime_norm)
                return {
                    "true_type": mime_norm,
                    "classification": "normalize",
                    "scenario": "2.7",
                    "confidence": mime_confidence,
                    "sources_agreement": False,
                    "conflict_reason": "No signature, using MIME",
                    "correct_extension": correct_ext,
                }
            elif ext_norm:
                correct_ext = self._type_to_extension(ext_norm)
                return {
                    "true_type": ext_norm,
                    "classification": "normalize",
                    "scenario": "2.7",
                    "confidence": 0.5,
                    "sources_agreement": False,
                    "conflict_reason": "No signature, low MIME confidence, using extension",
                    "correct_extension": correct_ext,
                }
            else:
                return {
                    "true_type": None,
                    "classification": "ambiguous",
                    "scenario": "2.7",
                    "confidence": 0.0,
                    "sources_agreement": False,
                    "conflict_reason": "No signature, no reliable sources",
                    "correct_extension": None,
                }

        # Fallback
        return {
            "true_type": mime_norm or ext_norm,
            "classification": "ambiguous",
            "scenario": "unknown",
            "confidence": 0.0,
            "sources_agreement": False,
            "conflict_reason": "Unable to resolve",
            "correct_extension": None,
        }

    def _normalize_type(self, detected_type: Optional[str]) -> Optional[str]:
        """
        Нормализует тип для сравнения.

        Args:
            detected_type: Тип файла (MIME или signature type)

        Returns:
            Нормализованный тип для внутреннего сравнения
        """
        if not detected_type:
            return None

        # Специальные случаи для zip_or_office и ole2
        if detected_type == "zip_or_office":
            return "zip_or_office"
        if detected_type == "ole2":
            return "ole2"

        # Маппинг MIME типов на внутренние типы
        mime_to_type = {
            "application/pdf": "pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "application/msword": "doc",
            "application/vnd.ms-excel": "xls",
            "application/vnd.ms-powerpoint": "ppt",
            "application/zip": "zip",
            "application/x-zip-compressed": "zip",
            "application/x-rar": "rar",
            "application/x-7z-compressed": "7z",
            "application/x-7z": "7z",
            "image/jpeg": "jpeg",
            "image/png": "png",
            "image/gif": "gif",
            "image/tiff": "tiff",
            "text/html": "html",
            "text/xml": "xml",
            "application/xml": "xml",
            "text/plain": "txt",
            "application/rtf": "rtf",
            "text/rtf": "rtf",
        }

        normalized = mime_to_type.get(detected_type)
        if normalized:
            return normalized

        # Если это уже внутренний тип (pdf, docx, и т.д.), возвращаем как есть
        return detected_type.lower()

    def _normalize_type_from_extension(self, extension: str) -> Optional[str]:
        """
        Нормализует тип из расширения.

        Args:
            extension: Расширение файла (с точкой или без)

        Returns:
            Нормализованный тип или None
        """
        if not extension:
            return None
        ext_clean = extension.lstrip(".").lower()
        return ext_clean if ext_clean else None

    def _type_to_extension(self, file_type: str) -> Optional[str]:
        """
        Конвертирует тип файла в расширение.

        Args:
            file_type: Внутренний тип файла (pdf, docx, и т.д.)

        Returns:
            Расширение с точкой или None
        """
        TYPE_TO_EXTENSION = {
            "pdf": ".pdf",
            "docx": ".docx",
            "doc": ".doc",
            "xlsx": ".xlsx",
            "xls": ".xls",
            "pptx": ".pptx",
            "ppt": ".ppt",
            "zip_archive": ".zip",
            "zip": ".zip",
            "rar_archive": ".rar",
            "rar": ".rar",
            "7z_archive": ".7z",
            "7z": ".7z",
            "jpeg": ".jpeg",
            "jpg": ".jpg",
            "png": ".png",
            "gif": ".gif",
            "tiff": ".tiff",
            "html": ".html",
            "xml": ".xml",
            "txt": ".txt",
            "rtf": ".rtf",
        }
        return TYPE_TO_EXTENSION.get(file_type)


def _needs_structural_parsing(sources: Dict[str, Any], true_type: Optional[str]) -> bool:
    """
    Определяет, нужен ли структурный парсинг для окончательного определения типа.

    Args:
        sources: Словарь с источниками истины
        true_type: Предполагаемый тип из Decision Engine

    Returns:
        True если нужен структурный парсинг
    """
    # Нужен парсинг для zip_or_office (различать ZIP от DOCX/XLSX/PPTX)
    if sources.get("signature_type") == "zip_or_office" or true_type == "zip_or_office":
        return True

    # Нужен парсинг для ole2 (различать DOC/XLS/PPT)
    if sources.get("signature_type") == "ole2" or true_type == "ole2":
        return True

    return False


def resolve_type_decision(sources: Dict[str, Any], file_path: Path) -> Dict[str, Any]:
    """
    Главная функция для разрешения конфликтов типов.

    Использует TypeDecisionEngine и добавляет структурный парсинг при необходимости.

    Args:
        sources: Словарь с источниками истины из collect_truth_sources()
        file_path: Путь к файлу (для структурного парсинга если нужно)

    Returns:
        Словарь с решением Decision Engine
    """
    engine = TypeDecisionEngine()

    decision = engine.resolve(
        mime_type=sources["mime_type"],
        mime_confidence=sources["mime_confidence"],
        signature_type=sources["signature_type"],
        signature_confidence=sources["signature_confidence"],
        extension=sources["extension"],
    )

    # Добавляем источники для прозрачности
    decision["sources"] = sources

    # Определяем, нужен ли структурный парсинг
    decision["needs_structural_parsing"] = _needs_structural_parsing(
        sources, decision.get("true_type")
    )

    return decision

