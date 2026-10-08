"""Собрать лист независимой проверки из подготовленных Backend-вопросов."""

from pathlib import Path

from app.core.question_variants import BACKEND_FAMILIES, prepared_variants


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "09-question-review-sheet.md"
GRADES = (("junior", "Junior"), ("middle", "Middle"), ("senior", "Senior"))


def build_sheet() -> str:
    family_count = len(BACKEND_FAMILIES)
    lines = [
        "# Лист независимой проверки Backend-заданий",
        "",
        "ФИО проверяющего: ____________________    Дата: ____________________",
        "",
        "Лист пригодится, если появится человек, знакомый с Backend, "
        "или для будущих пробных прохождений. Заполнять его всей команде не нужно. Если тема незнакома, "
        "оставьте ответ пустым и отметьте это в замечании: угадывать не нужно. "
        "Решайте самостоятельно, не открывая исходный банк, ключи и объяснения. "
        "Если условие допускает несколько ответов или не хватает данных, "
        "запишите это в замечании. Не исправляйте вопрос до разбора ответов.",
        "",
        f"Лист содержит три версии каждой из {family_count} заданий: всего {family_count * 3} вопросов. "
        "Каждый вопрос предполагает один ответ A–D. После независимого решения "
        "сравните ответы с текущим ключом в коде и обсудите расхождения. "
        "Сам ключ нужно проверить по техническому источнику или воспроизводимому примеру. "
        "Время по каждому грейду "
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
        "Текущие ключи сверены с источниками в отдельном документе. "
        "Спорный вопрос не использовать для оценки грейда, пока не принято решение: "
        "оставить, уточнить или заменить. Пробные прохождения людьми разных уровней "
        "проводить отдельно: этот лист не подтверждает пороги грейда.",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.write_text(build_sheet(), encoding="utf-8", newline="\n")
    print(OUTPUT)
