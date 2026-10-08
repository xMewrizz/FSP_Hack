"""Собрать для рецензента ключи новых вопросов и ссылки на первоисточники."""

from pathlib import Path

from app.core.question_bank_sources import SOURCE_FAMILIES
from app.core.question_bank_curriculum import CURRICULUM_FAMILIES
from app.core.question_variants import prepared_variants


OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "13-backend-question-sources.md"


def build_sheet() -> str:
    lines = [
        "# Источники новых Backend-заданий",
        "",
        "Здесь перечислены источники для 12 ранее добавленных вопросов и 84 новых вопросов базового набора. Три версии одного кода проверяют одно правило и не считаются тремя самостоятельными вопросами. Формулировки написаны для проекта, тексты источников не копировались.",
        "",
        "Ссылки помогают проверить технический факт и ключ. Они не доказывают, что вопрос подходит заявленному грейду, что варианты одинаково сложны или что тест определяет квалификацию. Для этого нужен разбор с Backend-специалистом и пробные прохождения. Кандидату этот файл и ключи до завершения теста не показывать.",
        "",
        "| Код | Навык | Проверяемое правило | Ключи V1 / V2 / V3 | Источник |",
        "|---|---|---|---|---|",
    ]
    for code, family in {**CURRICULUM_FAMILIES, **SOURCE_FAMILIES}.items():
        keys = " / ".join(variant["correct_answers"][0] for variant in prepared_variants(code))
        source = family["source_url"]
        lines.append(f"| {code} | {family['topic']} | {family['skill']} | {keys} | [Документация]({source}) |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.write_text(build_sheet(), encoding="utf-8", newline="\n")
    print(OUTPUT)
