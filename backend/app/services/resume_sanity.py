"""Проверки текста резюме до внешних источников.

Смотрим только то, что уже лежит в PDF. Неверная дата или явно битый контакт
становятся сообщением для кандидата. Такие находки не отклоняют анкету.
"""

from __future__ import annotations

import calendar
import re
from datetime import date


YEAR_MIN = 1950
MAX_SPAN_YEARS = 60
NOW = r"(?:н\.?\s*в\.?|настоящее(?:\s+время)?|сейчас)"
YEAR_RANGE = re.compile(
    rf"(?<![\d.])(?P<start>\d{{4}})\s*[-–—]\s*(?P<end>\d{{4}}|{NOW})(?!\d)",
    re.IGNORECASE,
)
MONTH_RANGE = re.compile(
    r"(?<!\d)(?P<sm>\d{1,2})\.(?P<sy>\d{4})\s*[-–—]\s*(?P<em>\d{1,2})\.(?P<ey>\d{4})(?!\d)"
)
MONTH_POINT = re.compile(r"(?<!\d)(?P<month>\d{1,2})\.(?P<year>\d{4})(?!\d)")
FULL_DATE = re.compile(r"(?<!\d)(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{4})(?!\d)")
BIRTH = re.compile(
    r"(?:дата рождения|родил(?:ся|ась))\s*[:\-]?\s*(\d{1,2})[./](\d{1,2})[./](\d{4})",
    re.IGNORECASE,
)
EMAIL_CANDIDATE = re.compile(r"[\w.+-]+@[\w.-]+")
EMAIL_STRICT = re.compile(r"^[\w.+-]+@[\w-]+(?:\.[\w-]+)+$")
PHONE_LABEL = re.compile(
    r"(?:телефон|тел\.|phone|мобильный)\s*[:\-]?\s*(\+?[\d\s()\-]{5,30})",
    re.IGNORECASE,
)
COMPANY_LABEL = re.compile(
    r"(?:компания|работодатель|организация|company|employer)\s*[:\-–—]\s*(?P<name>.+)$",
    re.IGNORECASE,
)
NOT_COMPANY = {
    "опыт",
    "опыт работы",
    "работа",
    "стаж",
    "проект",
    "проекты",
    "компания",
    "работодатель",
    "backend",
    "frontend",
    "developer",
    "разработчик",
    "python",
    "fastapi",
    "django",
    "postgresql",
    "react",
    "javascript",
    "typescript",
    "golang",
    "java",
}


def resume_warnings(text: str, today: date | None = None) -> list[str]:
    """Сообщения о явных ошибках в тексте. Пустой список значит, что таких ошибок нет."""
    current = today or date.today()
    warnings: list[str] = []
    covered: list[tuple[int, int]] = []
    work_starts: list[int] = []

    for match in MONTH_RANGE.finditer(text):
        covered.append(match.span())
        message, start_year = _month_range_problem(match, current.year)
        if message:
            warnings.append(message)
        elif start_year is not None:
            work_starts.append(start_year)

    for match in YEAR_RANGE.finditer(text):
        if _inside(match.start(), covered):
            continue
        message, start_year = _year_range_problem(match, current.year)
        if message:
            warnings.append(message)
        elif start_year is not None:
            work_starts.append(start_year)

    for match in FULL_DATE.finditer(text):
        covered.append(match.span())
        day = int(match.group("day"))
        month = int(match.group("month"))
        year = int(match.group("year"))
        if _year_token(year) and not _real_date(year, month, day):
            warnings.append(f"Неверная дата: {_compact(match.group(0))}. Такой календарной даты нет.")

    for match in MONTH_POINT.finditer(text):
        if _inside(match.start(), covered):
            continue
        month = int(match.group("month"))
        year = int(match.group("year"))
        if _year_token(year) and not 1 <= month <= 12:
            warnings.append(f"Неверная дата: {_compact(match.group(0))}. Такого месяца нет.")

    birth = _birth_date(text)
    if birth is not None:
        for start_year in work_starts:
            if start_year < birth.year + 14:
                warnings.append(
                    f"Срок с {start_year} начинается раньше 14 лет от даты рождения {birth.strftime('%d.%m.%Y')}."
                )

    for match in EMAIL_CANDIDATE.finditer(text):
        address = match.group(0).strip(".,;")
        if ".." in address or EMAIL_STRICT.fullmatch(address) is None:
            warnings.append(f"Адрес почты распознан с ошибкой: {address}.")

    for match in PHONE_LABEL.finditer(text):
        raw = match.group(1).strip(" .,;")
        digits = re.sub(r"\D", "", raw)
        if len(digits) != 11 or digits[0] not in "78":
            warnings.append(f"Телефон распознан с ошибкой: {raw}. Нужны 11 цифр, начиная с +7 или 8.")

    warnings.extend(_company_warnings(text))
    return _unique(warnings)


def _year_token(year: int) -> bool:
    """Год календаря либо соседняя опечатка вроде 1019 вместо 2019."""
    return 1800 <= year <= 2199 or 1000 <= year <= 1099


def _compact(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()


def _inside(position: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= position < end for start, end in spans)


def _real_date(year: int, month: int, day: int) -> bool:
    if not 1 <= month <= 12:
        return False
    return 1 <= day <= calendar.monthrange(year, month)[1]


def _birth_date(text: str) -> date | None:
    match = BIRTH.search(text)
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    if not _real_date(year, month, day):
        return None
    return date(year, month, day)


def _year_range_problem(match: re.Match[str], current_year: int) -> tuple[str | None, int | None]:
    raw = _compact(match.group(0))
    start = int(match.group("start"))
    end_raw = match.group("end")
    end = current_year if not end_raw.isdigit() else int(end_raw)
    if not _year_token(start) and not _year_token(end):
        return None, None
    message = _range_message(raw, start, end, current_year)
    return message, None if message else start


def _month_range_problem(match: re.Match[str], current_year: int) -> tuple[str | None, int | None]:
    raw = _compact(match.group(0))
    start_month = int(match.group("sm"))
    start_year = int(match.group("sy"))
    end_month = int(match.group("em"))
    end_year = int(match.group("ey"))
    if not _year_token(start_year) and not _year_token(end_year):
        return None, None
    if not 1 <= start_month <= 12:
        return f"Неверная дата: {raw}. Такого месяца нет.", None
    if not 1 <= end_month <= 12:
        return f"Неверная дата: {raw}. Такого месяца нет.", None
    if (end_year, end_month) < (start_year, start_month):
        return f"Неверная дата: {raw}. Дата окончания раньше даты начала.", None
    message = _range_message(raw, start_year, end_year, current_year)
    return message, None if message else start_year


def _range_message(raw: str, start: int, end: int, current_year: int) -> str | None:
    if start < YEAR_MIN or start > current_year:
        return f"Неверная дата: {raw}. Год {start} не может стоять в сроке работы."
    if end < start:
        return f"Неверная дата: {raw}. Дата окончания раньше даты начала."
    if end > current_year + 1:
        return f"Неверная дата: {raw}. Год {end} ещё не наступил."
    if end - start > MAX_SPAN_YEARS:
        return f"Неверная дата: {raw}. Срок длиннее {MAX_SPAN_YEARS} лет, проверьте годы."
    return None


def _company_warnings(text: str) -> list[str]:
    warnings: list[str] = []
    for line in text.splitlines() or [text]:
        for name in _companies_on_line(line):
            if len(name) < 3:
                warnings.append(f"Название компании «{name}» короче 3 символов.")
            elif len(name) >= 50:
                warnings.append(f"Название компании «{name}» длиннее 50 символов.")
    return warnings


def _companies_on_line(line: str) -> list[str]:
    label = COMPANY_LABEL.search(line)
    if label:
        name = _clean_company(_cut_dates(label.group("name")))
        return [name] if name else []
    if YEAR_RANGE.search(line) is None and MONTH_RANGE.search(line) is None:
        return []
    names: list[str] = []
    for part in re.split(r"\s*[|,;/]\s*|\s+[—–-]\s+", _cut_dates(line)):
        name = _clean_company(part)
        if name and name.casefold() not in NOT_COMPANY:
            names.append(name)
    return names


def _cut_dates(value: str) -> str:
    without_months = MONTH_RANGE.sub(" ", value)
    return YEAR_RANGE.sub(" ", without_months)


def _clean_company(raw: str) -> str:
    name = re.sub(r"\s+", " ", raw).strip(" \t\"'«»„“”.,;|")
    return name


def _unique(warnings: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in warnings:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
