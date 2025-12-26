#!/usr/bin/env python3
"""
State Machine Transition Tester
Согласно creative design: Hierarchical Testing Framework - UNIT Level
"""

import sys
import os
import json
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

# Добавляем путь к модулям
sys.path.append('/root/winners_preprocessor/final_preprocessing')

# Импортируем необходимые компоненты
from docprep.core.state_machine import UnitState, ALLOWED_TRANSITIONS, UnitStateMachine
from docprep.core.unit_processor import UnitProcessor
from docprep.engine.classifier import Classifier

class FileType(Enum):
    """Типы файлов для тестирования"""
    DOC = "doc"
    DOCX = "docx"
    XLS = "xls"
    XLSX = "xlsx"
    PPT = "ppt"
    PPTX = "pptx"
    PDF = "pdf"
    TXT = "txt"
    ZIP = "zip"
    EMPTY = "empty"
    CORRUPT = "corrupt"

@dataclass
class TestCase:
    """Тестовый сценарий для transition testing"""
    name: str
    file_type: FileType
    expected_category: str

@dataclass
class TransitionMetrics:
    """Метрики для каждого transition"""
    transition: str
    test_case: str
    success: bool
    duration: float
    actual_state: Optional[UnitState] = None
    error_message: Optional[str] = None

@dataclass
class TransitionTestResults:
    """Результаты тестирования всех transitions"""
    results: List[TransitionMetrics] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def add_result(self, transition: str, test_case: TestCase, success: bool, duration: float, actual_state: Optional[UnitState] = None, error: Optional[str] = None):
        """Добавить результат теста"""
        metrics = TransitionMetrics(
            transition=transition,
            test_case=test_case.name,
            success=success,
            duration=duration,
            actual_state=actual_state,
            error_message=error
        )
        self.results.append(metrics)

    def add_failure(self, transition: str, test_case: TestCase, error: str):
        """Добавить failed результат"""
        self.add_result(transition, test_case, False, 0.0, None, error)

    def generate_summary(self):
        """Сгенерировать сводку результатов"""
        total_tests = len(self.results)
        successful_tests = len([r for r in self.results if r.success])
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0

        # Группировка по transitions
        transition_stats = {}
        for result in self.results:
            if result.transition not in transition_stats:
                transition_stats[result.transition] = {"total": 0, "success": 0, "avg_duration": 0.0}
            transition_stats[result.transition]["total"] += 1
            if result.success:
                transition_stats[result.transition]["success"] += 1
            transition_stats[result.transition]["avg_duration"] += result.duration

        # Вычисление средних duration
        for stats in transition_stats.values():
            stats["avg_duration"] = stats["avg_duration"] / stats["total"] if stats["total"] > 0 else 0
            stats["success_rate"] = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0

        self.summary = {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": success_rate,
            "transition_stats": transition_stats,
            "failed_tests": [r for r in self.results if not r.success]
        }

class StateMachineTransitionTester:
    """Тестирование всех переходов state machine с метриками и аналитикой"""

    def __init__(self, test_data_dir: Optional[Path] = None):
        self.test_data_dir = test_data_dir or Path(tempfile.mkdtemp())
        self.test_data_dir.mkdir(exist_ok=True)

        # Инициализация компонентов
        self.classifier = Classifier()
        self.unit_processor = UnitProcessor()

        # Построение матрицы тестовых сценариев
        self.transition_matrix = self._build_transition_matrix()

    def _build_transition_matrix(self) -> Dict[str, List[TestCase]]:
        """Создание матрицы тестовых сценариев для каждого перехода"""

        matrix = {}

        # RAW → CLASSIFIED_1 переходы
        matrix["RAW→CLASSIFIED_1"] = [
            TestCase("single_doc_file", FileType.DOC, "convert/doc"),
            TestCase("single_pdf_file", FileType.PDF, "direct/pdf"),
            TestCase("zip_archive", FileType.ZIP, "extract/zip"),
            TestCase("excel_file", FileType.XLS, "convert/xls"),
            TestCase("text_file", FileType.TXT, "normalize/txt"),
        ]

        # RAW → EXCEPTION_1 (пустые UNIT)
        matrix["RAW→EXCEPTION_1"] = [
            TestCase("empty_unit", FileType.EMPTY, "exception/ambiguous"),
        ]

        # RAW → MERGED_DIRECT (direct файлы)
        matrix["RAW→MERGED_DIRECT"] = [
            TestCase("direct_pdf", FileType.PDF, "direct/pdf"),
        ]

        # CLASSIFIED_1 → PENDING_CONVERT
        matrix["CLASSIFIED_1→PENDING_CONVERT"] = [
            TestCase("doc_to_convert", FileType.DOC, "convert/doc"),
            TestCase("xls_to_convert", FileType.XLS, "convert/xls"),
            TestCase("ppt_to_convert", FileType.PPT, "convert/ppt"),
        ]

        # CLASSIFIED_1 → PENDING_EXTRACT
        matrix["CLASSIFIED_1→PENDING_EXTRACT"] = [
            TestCase("zip_to_extract", FileType.ZIP, "extract/zip"),
        ]

        # CLASSIFIED_1 → PENDING_NORMALIZE
        matrix["CLASSIFIED_1→PENDING_NORMALIZE"] = [
            TestCase("txt_to_normalize", FileType.TXT, "normalize/txt"),
        ]

        # CLASSIFIED_1 → MERGED_DIRECT
        matrix["CLASSIFIED_1→MERGED_DIRECT"] = [
            TestCase("direct_pdf_classified", FileType.PDF, "direct/pdf"),
        ]

        # PENDING_CONVERT → CLASSIFIED_2
        matrix["PENDING_CONVERT→CLASSIFIED_2"] = [
            TestCase("converted_doc", FileType.DOC, "convert/doc"),
        ]

        # MERGED_DIRECT → READY_FOR_DOCLING
        matrix["MERGED_DIRECT→READY_FOR_DOCLING"] = [
            TestCase("ready_direct_pdf", FileType.PDF, "direct/pdf"),
        ]

        # Recovery paths
        matrix["EXCEPTION_1→CLASSIFIED_1"] = [
            TestCase("recovered_empty", FileType.EMPTY, "exception/ambiguous"),
        ]

        return matrix

    def _create_test_unit(self, test_case: TestCase) -> Path:
        """Создание тестовой UNIT директории с файлом"""

        # Создаем UNIT директорию
        unit_dir = self.test_data_dir / f"UNIT_test_{test_case.name}_{int(time.time())}"
        unit_dir.mkdir(exist_ok=True)

        # Создаем файл в зависимости от типа
        if test_case.file_type == FileType.EMPTY:
            # Пустая директория - не создаем файл
            pass
        elif test_case.file_type == FileType.CORRUPT:
            # Поврежденный файл
            file_path = unit_dir / f"corrupt.{test_case.file_type.value}"
            with open(file_path, 'wb') as f:
                f.write(b'\x00\x01\x02invalid_header')
        else:
            # Нормальный файл
            file_path = unit_dir / f"test.{test_case.file_type.value}"
            if test_case.file_type in [FileType.DOC, FileType.XLS, FileType.PPT]:
                # Для office файлов создаем минимальный бинарный контент
                with open(file_path, 'wb') as f:
                    f.write(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1' + b'\x00' * 100)  # OLE2 header
            elif test_case.file_type == FileType.ZIP:
                # Создаем простой ZIP файл
                import zipfile
                with zipfile.ZipFile(file_path, 'w') as zf:
                    zf.writestr('test.txt', 'test content')
            else:
                # Текстовый файл
                with open(file_path, 'w') as f:
                    f.write(f"Test content for {test_case.name}")

        return unit_dir

    def _execute_transition(self, unit_dir: Path, transition: str) -> UnitState:
        """Выполнение конкретного перехода"""

        from_state, to_state = transition.split("→")
        from_unit_state = UnitState[from_state]
        expected_to_state = UnitState[to_state]

        # Инициализируем state machine
        sm = UnitStateMachine(unit_dir.name, unit_dir / "manifest.json")

        # Устанавливаем начальное состояние
        sm._current_state = from_unit_state

        # Выполняем логику перехода в зависимости от целевого состояния
        if to_state.startswith("CLASSIFIED"):
            # Запуск классификации
            result = self.classifier.classify_unit(unit_dir)
            return result.get("state", UnitState.EXCEPTION_1)

        elif to_state.startswith("PENDING"):
            # Эти переходы обрабатываются классификатором
            result = self.classifier.classify_unit(unit_dir)
            return result.get("state", UnitState.EXCEPTION_1)

        elif to_state == "MERGED_DIRECT":
            # Direct merge - файл должен быть уже классифицирован
            result = self.classifier.classify_unit(unit_dir)
            return result.get("state", UnitState.EXCEPTION_1)

        elif to_state == "READY_FOR_DOCLING":
            # Финальный merge
            result = self.classifier.classify_unit(unit_dir)
            return result.get("state", UnitState.EXCEPTION_1)

        elif to_state.startswith("EXCEPTION"):
            # Exception состояния
            return UnitState.EXCEPTION_1

        else:
            raise ValueError(f"Unknown transition target: {to_state}")

    def _validate_transition(self, unit_dir: Path, transition: str, actual_state: UnitState) -> bool:
        """Валидация корректности перехода"""

        from_state, expected_to_state = transition.split("→")
        expected_state = UnitState[expected_to_state]

        # Проверяем, разрешен ли переход
        if expected_state not in ALLOWED_TRANSITIONS.get(UnitState[from_state], []):
            print(f"❌ Invalid transition: {transition}")
            return False

        # Проверяем соответствие actual и expected состояния
        if actual_state != expected_state:
            print(f"❌ State mismatch: expected {expected_state}, got {actual_state}")
            return False

        # Проверяем manifest.json
        manifest = unit_dir / "manifest.json"
        if manifest.exists():
            try:
                with open(manifest) as f:
                    data = json.load(f)
                    manifest_state = data.get("current_state")
                    if manifest_state != expected_state.value:
                        print(f"❌ Manifest state mismatch: {manifest_state} vs {expected_state.value}")
                        return False
            except Exception as e:
                print(f"❌ Manifest read error: {e}")
                return False

        return True

    def run_transition_tests(self) -> TransitionTestResults:
        """Запуск всех transition тестов с метриками"""

        results = TransitionTestResults()

        print(f"🚀 Starting State Machine Transition Testing")
        print(f"📁 Test data directory: {self.test_data_dir}")
        print(f"📊 Total transitions to test: {len(self.transition_matrix)}")
        print("=" * 60)

        for transition, test_cases in self.transition_matrix.items():
            print(f"\n🔄 Testing transition: {transition}")
            print(f"📋 Test cases: {len(test_cases)}")

            for test_case in test_cases:
                try:
                    print(f"  🧪 Running: {test_case.name}")

                    # Создаем тестовую UNIT
                    unit_dir = self._create_test_unit(test_case)

                    # Выполняем transition
                    start_time = time.time()
                    new_state = self._execute_transition(unit_dir, transition)
                    duration = time.time() - start_time

                    # Валидируем transition
                    is_valid = self._validate_transition(unit_dir, transition, new_state)

                    # Записываем результат
                    results.add_result(transition, test_case, is_valid, duration, new_state)

                    status = "✅ PASS" if is_valid else "❌ FAIL"
                    print(f"    {status} | {test_case.name} | {new_state.value} | {duration:.3f}s")

                except Exception as e:
                    print(f"    💥 CRASH | {test_case.name} | Error: {e}")
                    results.add_failure(transition, test_case, str(e))

        # Генерируем сводку
        results.generate_summary()

        print("\n" + "=" * 60)
        print("📊 FINAL RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total tests: {results.summary['total_tests']}")
        print(f"Successful: {results.summary['successful_tests']}")
        print(f"Success rate: {results.summary['success_rate']:.1f}%")

        print("\n📈 Per-Transition Statistics:")
        for trans, stats in results.summary['transition_stats'].items():
            print(f"  {trans}: {stats['success']}/{stats['total']} ({stats['success_rate']:.1f}%) | Avg: {stats['avg_duration']:.3f}s")

        if results.summary['failed_tests']:
            print(f"\n❌ Failed tests: {len(results.summary['failed_tests'])}")
            for failed in results.summary['failed_tests'][:5]:  # Показываем первые 5
                print(f"  - {failed.transition} | {failed.test_case} | {failed.error_message}")

        return results

def main():
    """Основная функция тестирования"""

    import argparse
    parser = argparse.ArgumentParser(description="State Machine Transition Tester")
    parser.add_argument("--output-dir", type=str, help="Output directory for test results")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Создаем tester
    tester = StateMachineTransitionTester()

    # Запускаем тесты
    results = tester.run_transition_tests()

    # Сохраняем результаты
    output_file = Path(args.output_dir) / "state_machine_test_results.json" if args.output_dir else Path("state_machine_test_results.json")

    with open(output_file, 'w') as f:
        json.dump({
            "summary": results.summary,
            "results": [vars(r) for r in results.results]
        }, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {output_file}")

    # Выход с соответствующим кодом
    success_rate = results.summary['success_rate']
    if success_rate >= 90:
        print("🎉 STATE MACHINE VALIDATION PASSED!")
        return 0
    else:
        print(f"⚠️  STATE MACHINE VALIDATION FAILED (Success rate: {success_rate:.1f}%)")
        return 1

if __name__ == '__main__':
    sys.exit(main())