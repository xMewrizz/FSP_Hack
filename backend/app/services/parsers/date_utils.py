from __future__ import annotations

import re
from datetime import date

RU_MONTHS = {
    "январь": 1,
    "января": 1,
    "янв": 1,
    "февраль": 2,
    "февраля": 2,
    "фев": 2,
    "март": 3,
    "марта": 3,
    "мар": 3,
    "апрель": 4,
    "апреля": 4,
    "апр": 4,
    "май": 5,
    "мая": 5,
    "июнь": 6,
    "июня": 6,
    "июн": 6,
    "июль": 7,
    "июля": 7,
    "июл": 7,
    "август": 8,
    "августа": 8,
    "авг": 8,
    "сентябрь": 9,
    "сентября": 9,
    "сен": 9,
    "октябрь": 10,
    "октября": 10,
    "окт": 10,
    "ноябрь": 11,
    "ноября": 11,
    "ноя": 11,
    "декабрь": 12,
    "декабря": 12,
    "дек": 12,
}


def parse_experience_duration_text(text: str) -> int:
    """Извлекает общее количество месяцев из строки вида '3 года 5 месяцев' или '1 год'."""
    if not text:
        return 0
    years_match = re.search(r"\b(\d{1,2})\s*(?:года?|лет)\b", text, re.IGNORECASE)
    months_match = re.search(r"\b(\d{1,2})\s*(?:месяц[а-я]*|мес(?:\.|\b))", text, re.IGNORECASE)

    years = int(years_match.group(1)) if years_match else 0
    months = int(months_match.group(1)) if months_match else 0
    if years > 60:
        years = 0
    return years * 12 + months


def parse_date_span(
    span_text: str,
    default_year: int = 2026,
    default_month: int = 10,
) -> tuple[int | None, int | None, int | None, int | None, int, bool]:
    """
    Разбирает диапазон дат (например: 'сентябрь 2021 — настоящее время' или '01.2020 - 05.2023').
    Возвращает: (start_year, start_month, end_year, end_month, duration_months, is_current).
    """
    if not span_text:
        return None, None, None, None, 0, False

    clean = span_text.lower().strip()
    is_current = bool(
        re.search(r"(?:настоящее(?:\s+время)?|по\s+н\.?\s*в\.?|н\.?\s*в\.?|сейчас|current|present)", clean)
    )

    # 1. Поиск числовых месяцев и годов: MM.YYYY - MM.YYYY
    num_matches = list(re.finditer(r"(\d{1,2})[./](\d{4})", clean))
    if len(num_matches) >= 2:
        sm, sy = int(num_matches[0].group(1)), int(num_matches[0].group(2))
        em, ey = int(num_matches[1].group(1)), int(num_matches[1].group(2))
        duration = max(1, (ey - sy) * 12 + (em - sm) + 1)
        return sy, sm, ey, em, duration, is_current

    if len(num_matches) == 1 and is_current:
        sm, sy = int(num_matches[0].group(1)), int(num_matches[0].group(2))
        ey, em = default_year, default_month
        duration = max(1, (ey - sy) * 12 + (em - sm) + 1)
        return sy, sm, ey, em, duration, True

    # 2. Поиск текстовых месяцев: 'сентябрь 2021'
    month_year_pattern = re.compile(
        r"([а-яa-z]+)\s+(\d{4})",
        re.IGNORECASE,
    )
    text_matches = []
    for m in month_year_pattern.finditer(clean):
        month_word = m.group(1).lower()
        yr = int(m.group(2))
        if month_word in RU_MONTHS:
            text_matches.append((RU_MONTHS[month_word], yr))

    if len(text_matches) >= 2:
        sm, sy = text_matches[0]
        em, ey = text_matches[1]
        duration = max(1, (ey - sy) * 12 + (em - sm) + 1)
        return sy, sm, ey, em, duration, is_current

    if len(text_matches) == 1 and is_current:
        sm, sy = text_matches[0]
        ey, em = default_year, default_month
        duration = max(1, (ey - sy) * 12 + (em - sm) + 1)
        return sy, sm, ey, em, duration, True

    # 3. Только годы: 2019 - 2023 или 2021 - н.в.
    year_matches = [int(y) for y in re.findall(r"\b(20\d{2}|19\d{2})\b", clean)]
    if len(year_matches) >= 2:
        sy, ey = year_matches[0], year_matches[1]
        duration = max(1, (ey - sy) * 12)
        return sy, 1, ey, 12, duration, is_current

    if len(year_matches) == 1 and is_current:
        sy = year_matches[0]
        ey = default_year
        duration = max(1, (ey - sy) * 12 + (default_month - 1) + 1)
        return sy, 1, ey, default_month, duration, True

    # 4. Если в строке уже указана продолжительность в скобках, например '(2 года 8 месяцев)'
    parenthesized_duration = parse_experience_duration_text(clean)
    if parenthesized_duration > 0:
        return None, None, None, None, parenthesized_duration, is_current

    return None, None, None, None, 0, is_current
