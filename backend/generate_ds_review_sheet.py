"""Собрать лист независимой проверки из подготовленных Data Science-вопросов."""

from pathlib import Path
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.question_bank_ds import DS_FAMILIES
from app.core.question_variants import prepared_variants


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "19-ds-question-review-sheet.md"
GRADES = (("junior", "Junior"), ("middle", "Middle"), ("senior", "Senior"))


def build_sheet() -> str:
    family_count = len(DS_FAMILIES)
    lines = [
        "# Лист независимой проверки Data Science-заданий",
        "",
        "ФИО проверяющего: ____________________    Дата: ____________________",
        "",
        "Лист содержит подготовленные Data Science задания для независимой проверки. "
        "Охватываются 4 ключевые компетенции: Data Analysis & Prep, ML Modeling & Evaluation, "
        "Deep Learning & NLP/LLM, Production ML & MLOps по уровням Junior, Middle, Senior. "
        "Каждый вопрос зафиксирован в 3 вариантах условий (всего "
        f"{family_count * 3} заданий). "
        "Решайте самостоятельно, не открывая банк вопросов и ключи. "
        "В замечаниях отмечайте неоднозначности формулировок или альтернативные трактовки.",
        "",
    ]

    rows = []
    for variant_number in (1, 2, 3):
        lines.extend((f"## Версия {variant_number}", ""))
        for grade, grade_label in GRADES:
            lines.extend((f"### {grade_label}", ""))
            for base_code in DS_FAMILIES:
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
        "или почему возможен другой ответ.",
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
        "Ключи сверены с авторитетной документацией (scikit-learn, PyTorch, pandas, "
        "Hugging Face, Google SRE/MLOps, Feast).",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    OUTPUT.write_text(build_sheet(), encoding="utf-8", newline="\n")
    print(OUTPUT)
