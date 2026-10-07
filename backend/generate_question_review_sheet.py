"""Собрать лист независимой проверки из подготовленных Backend-вопросов."""

from pathlib import Path

from app.core.question_variants import BACKEND_FAMILIES, prepared_variants


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "09-question-review-sheet.md"
GRADES = (("junior", "Junior"), ("middle", "Middle"), ("senior", "Senior"))


def build_sheet() -> str:
    lines = [
        "# Лист независимой проверки Backend-заданий",
        "",
        "ФИО проверяющего: ____________________    Дата: ____________________",
        "",
        "Решите вопросы самостоятельно, не открывая исходный банк, ключи и объяснения. "
        "Запишите ответы в таблицу в конце листа. Если условие допускает несколько ответов "
        "или не хватает данных, отметьте это в замечании. Не исправляйте вопрос до того, "
        "как второй проверяющий сдаст свой лист.",
        "",
        "Лист содержит три версии каждой из 12 тем: всего 36 вопросов. "
        "Каждый вопрос предполагает один ответ A–D. После независимого решения "
        "сравните ответы с эталоном и обсудите расхождения. Время по каждому грейду "
        "и понятность условий запишите в конце.",
        "",
    ]

    rows = []
    for variant_number in (1, 2, 3):
        lines.extend((f"## Версия {variant_number}", ""))
        for grade, grade_label in GRADES:
            lines.extend((f"### {grade_label}", ""))
            for base_code in BACKEND_FAMILIES:
                variant = prepared_variants(base_code)[variant_number - 1]
                if variant["grade"] != grade:
                    continue
                code = variant["code"]
                lines.extend((f"**{code}.** {variant['question_text']}", ""))
                lines.extend(f"- {option['id']}. {option['text']}" for option in variant["options"])
                lines.append("")
                rows.append(code)

    lines.extend((
        "## Ответы и замечания",
        "",
        "Уверенность: «да» или «нет». В замечании укажите, что именно непонятно "
        "или почему возможен другой ответ. Пустую графу ответа не считайте ошибкой проверяющего.",
        "",
        "| Код | Ответ A–D | Уверен? | Замечание |",
        "|---|---|---|---|",
    ))
    lines.extend(f"| {code} |  |  |  |" for code in rows)
    lines.extend((
        "",
        "Время: Junior ______ мин; Middle ______ мин; Senior ______ мин.",
        "",
        "Общие замечания о сложности и понятности: ________________________________",
        "",
        "После сдачи обоих листов: сравнить ответы друг с другом и с эталоном; "
        "для каждого расхождения записать решение — оставить вопрос, уточнить условие "
        "или заменить. Пробные прохождения людьми разных уровней проводить отдельно: "
        "этот лист проверяет формулировки, но не подтверждает пороги грейда.",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.write_text(build_sheet(), encoding="utf-8", newline="\n")
    print(OUTPUT)
