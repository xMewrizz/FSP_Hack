"""Осторожное извлечение полей потребности из текста работодателя.

Возвращаем только явно найденные сведения. Пустые поля работодатель заполняет
сам; результат разбора никогда не сохраняется без его подтверждения.
"""

import re


SPECIALIZATIONS = (
    ("Fullstack", r"\bfull[ -]?stack\b|\bфулл[ -]?ст[еэ]к\w*\b"),
    ("Data Science / ML", r"\bdata[ -]?scien\w*\b|\bmachine[ -]?learning\b|\bml[ -]?инженер\w*\b|\bдата[ -]?са[йи]ентист\w*\b"),
    ("DevOps / SRE", r"\bdevops\b|\bsre\b|\bдевопс\w*\b"),
    ("QA / Testing", r"\bqa\b|\bтестировщик\w*\b|\bинженер\w* по тестированию\b"),
    ("GameDev", r"\bgame[ -]?dev\b|\bгеймдев\w*\b|\bразработчик\w* игр\b"),
    ("Mobile", r"\bmobile[ -]?developer\b|\bмобильн\w* разработчик\w*\b|\bandroid[ -]?разработчик\w*\b|\bios[ -]?разработчик\w*\b"),
    ("System Programming / C++", r"\bсистемн\w* программист\w*\b|\bsystem[ -]?programmer\b|\bc\+\+[ -]?разработчик\w*\b"),
    ("Frontend", r"\bfront[ -]?end\b|\bфронтенд\w*\b|\bфронт[ -]?енд\w*\b"),
    ("Backend", r"\bback[ -]?end\b|\bб[эе]кенд\w*\b|\bб[эе]к[ -]?енд\w*\b"),
)

GRADES = (
    ("lead", r"\b(?:tech[ -]?lead|team[ -]?lead|lead|тимлид\w*|техлид\w*)\b"),
    ("senior", r"\b(?:senior|sr\.?|сеньор\w*|старш\w* разработчик\w*)\b"),
    ("middle", r"\b(?:middle|mid\.?|мидл\w*)\b"),
    ("junior", r"\b(?:junior|jun\.?|джун\w*|младш\w* разработчик\w*)\b"),
)

SKILLS = (
    ("Python", r"\bpython\b|\bпитон\b"),
    ("JavaScript", r"\bjavascript\b|\bjs\b"),
    ("TypeScript", r"\btypescript\b|\bts\b"),
    ("Java", r"\bjava\b"),
    ("Go", r"\bgolang\b|\bGo\b"),
    ("C++", r"(?<!\w)c\+\+(?!\w)"),
    ("C#", r"(?<!\w)c#(?!\w)"),
    ("Kotlin", r"\bkotlin\b"),
    ("Swift", r"\bswift\b"),
    ("SQL", r"\bsql\b"),
    ("PostgreSQL", r"\bpostgres(?:ql)?\b|\bпостгрес\w*\b"),
    ("MySQL", r"\bmysql\b"),
    ("Redis", r"\bredis\b"),
    ("MongoDB", r"\bmongodb\b"),
    ("FastAPI", r"\bfastapi\b"),
    ("Django", r"\bdjango\b"),
    ("Spring", r"\bspring\b"),
    ("React", r"\breact\b"),
    ("Vue", r"\bvue(?:\.js)?\b"),
    ("Angular", r"\bangular\b"),
    ("Node.js", r"\bnode(?:\.js)?\b"),
    ("Docker", r"\bdocker\b|\bдокер\w*\b"),
    ("Kubernetes", r"\bkubernetes\b|\bk8s\b"),
    ("CI/CD", r"\bci\s*/\s*cd\b|\bgitlab[ -]?ci\b|\bgithub[ -]?actions\b"),
    ("Git", r"\bgit\b"),
    ("Linux", r"\blinux\b"),
    ("Terraform", r"\bterraform\b"),
    ("Kafka", r"\bkafka\b"),
    ("Pandas", r"\bpandas\b"),
    ("PyTorch", r"\bpytorch\b"),
    ("TensorFlow", r"\btensorflow\b"),
    ("A/B-тесты", r"\ba\s*/\s*b[ -]?тест\w*\b|\bа\s*/\s*б[ -]?тест\w*\b"),
)

AMOUNT = r"(?:\d{1,3}(?:[ \u00a0]\d{3})+|\d{2,7})"
UNIT = r"(?:тыс(?:яч)?\.?|[кk])"
RANGE = re.compile(
    rf"(?<!\d)(?P<low>{AMOUNT})\s*(?P<low_unit>{UNIT})?\s*"
    rf"(?:[-–—]|до)\s*(?P<high>{AMOUNT})\s*(?P<high_unit>{UNIT})?\s*"
    r"(?P<currency>₽|руб(?:лей|ля|\.)?)?",
    re.IGNORECASE,
)


def _salary(text: str) -> tuple[int | None, int | None, str | None]:
    for match in RANGE.finditer(text):
        context = text[max(0, match.start() - 40):match.end() + 15].lower()
        if not match.group("currency") and not re.search(r"зарплат\w*|оклад\w*|бюджет\w*|доход\w*|₽|руб", context):
            continue
        low = int(match.group("low").replace(" ", "").replace("\u00a0", ""))
        high = int(match.group("high").replace(" ", "").replace("\u00a0", ""))
        low_unit = match.group("low_unit")
        high_unit = match.group("high_unit")
        if high_unit and not low_unit and low < 1000:
            low_unit = high_unit
        if low_unit:
            low *= 1000
        if high_unit:
            high *= 1000
        if 10000 <= low <= high <= 10000000:
            tax = None
            if re.search(r"на руки|после вычета|net\b", context):
                tax = "net"
            elif re.search(r"до вычета|gross\b", context):
                tax = "gross"
            return low, high, tax
    return None, None, None


def _negated(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 35):start].lower()
    after = text[end:end + 25].lower()
    return bool(
        re.search(r"(?:не\s+(?:нужен|нужна|нужны|требуется|обязателен|обязательна|обязательно)|без|желательно)\s*$", before)
        or re.match(r"\s+(?:не\s+(?:нужен|нужна|нужны|требуется|обязателен|обязательна|обязательно)|будет плюсом)\b", after)
    )


def parse_need(text: str) -> dict:
    specializations = [name for name, pattern in SPECIALIZATIONS if re.search(pattern, text, re.IGNORECASE)]
    specialization = specializations[0] if len(specializations) == 1 else None

    grades = [name for name, pattern in GRADES if re.search(pattern, text, re.IGNORECASE)]
    grade = grades[0] if len(grades) == 1 else None

    found_skills = []
    for name, pattern in SKILLS:
        matches = (
            sorted(
                [*re.finditer(r"\bGo\b", text), *re.finditer(r"\bgolang\b", text, re.IGNORECASE)],
                key=lambda match: match.start(),
            )
            if name == "Go" else re.finditer(pattern, text, re.IGNORECASE)
        )
        for match in matches:
            if not _negated(text, match.start(), match.end()):
                found_skills.append((match.start(), name))
                break
    skills = [{"name": name, "weight": 3} for _, name in sorted(found_skills)]

    salary_min, salary_max, salary_tax_type = _salary(text)
    formats = []
    if re.search(r"\bудал[её]нн\w*\b|\bremote\b", text, re.IGNORECASE):
        formats.append("remote")
    if re.search(r"\bгибрид\w*\b|\bhybrid\b", text, re.IGNORECASE):
        formats.append("hybrid")
    if re.search(r"\bофис\w*\b|\bon[ -]?site\b", text, re.IGNORECASE):
        formats.append("office")

    return {
        "specialization": specialization,
        "required_grade": grade,
        "required_skills": skills,
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_tax_type": salary_tax_type,
        "work_format": formats[0] if len(formats) == 1 else None,
    }
