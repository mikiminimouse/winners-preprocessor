#!/usr/bin/env python3
"""Простой тест state machine transitions для начальной проверки"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.append('/root/winners_preprocessor/final_preprocessing')

from docprep.core.state_machine import UnitState, ALLOWED_TRANSITIONS

def test_basic_transitions():
    """Тестирование основных разрешенных переходов"""

    print("🧪 Testing Basic State Machine Transitions")
    print("=" * 50)

    # Тест 1: Проверка разрешенных переходов
    test_cases = [
        ("RAW", "CLASSIFIED_1"),
        ("CLASSIFIED_1", "PENDING_CONVERT"),
        ("PENDING_CONVERT", "CLASSIFIED_2"),
        ("MERGED_DIRECT", "READY_FOR_DOCLING"),
    ]

    passed = 0
    total = len(test_cases)

    for from_state, to_state in test_cases:
        from_unit = UnitState[from_state]
        to_unit = UnitState[to_state]

        allowed = ALLOWED_TRANSITIONS.get(from_unit, [])
        is_allowed = to_unit in allowed

        status = "✅ PASS" if is_allowed else "❌ FAIL"
        print(f"{status} {from_state} → {to_state}")

        if is_allowed:
            passed += 1

    print(f"\n📊 Results: {passed}/{total} transitions allowed")
    success_rate = (passed / total) * 100
    print(f"Success rate: {success_rate:.1f}%")

    return success_rate >= 80

def test_invalid_transitions():
    """Тестирование запрещенных переходов"""

    print("\n🧪 Testing Invalid Transitions")
    print("=" * 30)

    # Тест запрещенных переходов
    invalid_cases = [
        ("RAW", "READY_FOR_DOCLING"),  # Пропуск стадий
        ("EXCEPTION_1", "RAW"),        # Обратный переход
        ("READY_FOR_DOCLING", "CLASSIFIED_1"),  # Из финального состояния
    ]

    passed = 0
    total = len(invalid_cases)

    for from_state, to_state in invalid_cases:
        from_unit = UnitState[from_state]
        to_unit = UnitState[to_state]

        allowed = ALLOWED_TRANSITIONS.get(from_unit, [])
        is_allowed = to_unit in allowed

        # Для invalid cases мы ожидаем False
        expected_invalid = not is_allowed
        status = "✅ PASS" if expected_invalid else "❌ FAIL"
        print(f"{status} {from_state} → {to_state} (should be blocked)")

        if expected_invalid:
            passed += 1

    print(f"\n📊 Results: {passed}/{total} invalid transitions correctly blocked")
    success_rate = (passed / total) * 100
    print(f"Success rate: {success_rate:.1f}%")

    return success_rate >= 80

def main():
    print("🚀 State Machine Basic Validation")
    print("=" * 40)

    test1_pass = test_basic_transitions()
    test2_pass = test_invalid_transitions()

    print("\n" + "=" * 40)
    print("📋 FINAL SUMMARY")
    print("=" * 40)

    if test1_pass and test2_pass:
        print("🎉 STATE MACHINE BASIC VALIDATION PASSED!")
        print("✅ Valid transitions are allowed")
        print("✅ Invalid transitions are blocked")
        return 0
    else:
        print("⚠️  STATE MACHINE BASIC VALIDATION FAILED")
        if not test1_pass:
            print("❌ Some valid transitions are blocked")
        if not test2_pass:
            print("❌ Some invalid transitions are allowed")
        return 1

if __name__ == '__main__':
    sys.exit(main())