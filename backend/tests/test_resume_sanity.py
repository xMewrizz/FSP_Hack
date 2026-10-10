import io
from datetime import date

from reportlab.pdfgen import canvas

from app.services.pdf_service import pdf_service
from app.services.resume_sanity import resume_warnings


def test_typo_year_is_reported():
    warnings = resume_warnings("Опыт работы 1019-2020, Python", today=date(2026, 10, 10))
    assert warnings == ["Неверная дата: 1019-2020. Год 1019 не может стоять в сроке работы."]


def test_ordinary_period_and_open_end_are_quiet():
    today = date(2026, 10, 10)
    assert resume_warnings("Backend, 2019-2020, Python", today=today) == []
    assert resume_warnings("Backend, 2019 — н.в.", today=today) == []


def test_end_before_start_future_year_and_long_span():
    today = date(2026, 10, 10)
    assert "окончания раньше" in resume_warnings("Работа 2020-2019", today=today)[0]
    assert "ещё не наступил" in resume_warnings("Контракт 2024-2035", today=today)[0]
    assert "длиннее 60 лет" in resume_warnings("Стаж 1950-2026", today=today)[0]


def test_impossible_month_and_calendar_day():
    today = date(2026, 10, 10)
    assert "Такого месяца нет" in resume_warnings("Проект 13.2019-02.2020", today=today)[0]
    assert "календарной даты нет" in resume_warnings("Дата 32.01.2020", today=today)[0]


def test_work_before_age_fourteen():
    warnings = resume_warnings(
        "Дата рождения: 01.01.2010\nОпыт: 2018-2020",
        today=date(2026, 10, 10),
    )
    assert any("раньше 14 лет" in item for item in warnings)


def test_ports_are_not_dates_and_valid_contacts_are_quiet():
    text = "Порты 8080-8090, почта anna@example.com, Телефон: +7 999 123-45-67"
    assert resume_warnings(text, today=date(2026, 10, 10)) == []


def test_broken_email_and_phone():
    warnings = resume_warnings(
        "Почта mail..me@gmail.com, Телефон: 12345",
        today=date(2026, 10, 10),
    )
    assert any("почты" in item and "mail..me@gmail.com" in item for item in warnings)
    assert any("Телефон распознан с ошибкой: 12345" in item for item in warnings)


def test_company_name_too_short_or_too_long():
    today = date(2026, 10, 10)
    short = resume_warnings("Компания: АБ, 2019-2020", today=today)
    assert short == ["Название компании «АБ» короче 3 символов."]
    long_name = "Север" + "о" * 45
    assert len(long_name) == 50
    long = resume_warnings(f"Компания: {long_name}", today=today)
    assert long == [f"Название компании «{long_name}» длиннее 50 символов."]
    assert resume_warnings("Компания: Яндекс, 2019-2020", today=today) == []
    assert resume_warnings("Янд, 2019-2020", today=today) == []


def test_pdf_parser_returns_date_warning_without_rejecting_file():
    buffer = io.BytesIO()
    sheet = canvas.Canvas(buffer)
    sheet.drawString(40, 750, "Experience 1019-2020 Python Backend")
    sheet.save()

    parsed = pdf_service.parse_resume_pdf(buffer.getvalue())

    assert parsed.warnings == ["Неверная дата: 1019-2020. Год 1019 не может стоять в сроке работы."]
    assert "Python" in parsed.extracted_skills
    assert parsed.specialization == "Backend"
