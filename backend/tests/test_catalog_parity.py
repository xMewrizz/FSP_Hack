"""B-01: паритет Python- и TypeScript-справочников без общего кодогена.

Сверяет backend/app/core/catalog.py с frontend/src/catalog.ts простым
парсингом строк (сборку не усложняем, зависимостей нет).
Pure-тест: app.models не импортируется, работает при сломанном backend.
"""

from pathlib import Path
import re

from app.core import catalog as catalog_py


TS_PATH = Path(__file__).resolve().parents[2] / "frontend" / "src" / "catalog.ts"


def _array_block(text: str, name: str) -> str:
    match = re.search(rf"{name}[^=]*=\s*\[(.*?)\];", text, re.S)
    assert match, f"в catalog.ts не найден массив {name}"
    return match.group(1)


def _read_ts() -> dict[str, list[str]]:
    assert TS_PATH.exists(), f"нет файла {TS_PATH}"
    text = TS_PATH.read_text(encoding="utf-8")
    grades_block = _array_block(text, "ALL_GRADES")
    return {
        "specs": re.findall(r'"([^"]+)"', _array_block(text, "ALL_SPECIALIZATIONS")),
        "grades": re.findall(r'value:\s*"([^"]+)"', grades_block),
        "test_specs": re.findall(r'"([^"]+)"', _array_block(text, "TESTABLE_SPECIALIZATIONS")),
        "test_grades": re.findall(r'"([^"]+)"', _array_block(text, "TESTABLE_GRADES")),
    }


def test_specs_parity():
    ts = _read_ts()
    assert ts["specs"] == catalog_py.ALL_SPECIALIZATIONS


def test_grades_parity():
    ts = _read_ts()
    assert [g["value"] if isinstance(g, dict) else g for g in ts["grades"]] == catalog_py.ALL_GRADES
    assert all(v == v.lower() for v in ts["grades"]), "значения грейдов в TS — lowercase"


def test_testable_parity():
    ts = _read_ts()
    assert ts["test_specs"] == catalog_py.TESTABLE_SPECIALIZATIONS
    assert ts["test_grades"] == catalog_py.TESTABLE_GRADES
