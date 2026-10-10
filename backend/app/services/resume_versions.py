"""Compare work-history lines from resumes saved by the same candidate."""

import re

from app.services.resume_sanity import MONTH_RANGE, YEAR_RANGE


COMPANY = re.compile(r"^(?:компания|работодатель|организация)\s*[:\-–—]\s*(.+)$", re.I)
ROLE = re.compile(r"^(?:должность|позиция|роль)\s*[:\-–—]\s*(.+)$", re.I)


def work_history_lines(text: str) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        line = " ".join(line.split()).strip()
        if line and (MONTH_RANGE.search(line) or YEAR_RANGE.search(line)):
            result.append(line[:500])
    return result[:100]


def changed_work_lines(previous: list[str], current: list[str]) -> dict[str, list[str]]:
    old = {line.casefold() for line in previous}
    new = {line.casefold() for line in current}
    return {
        "added": [line for line in current if line.casefold() not in old],
        "removed": [line for line in previous if line.casefold() not in new],
    }


def labeled_work_entries(text: str) -> dict[tuple[str, str], tuple[str, str]]:
    """Read only clearly labelled work blocks; do not guess employers or roles."""
    entries: dict[tuple[str, str], tuple[str, str]] = {}
    for block in re.split(r"\n\s*\n", text):
        company = role = period = None
        for raw_line in block.splitlines():
            line = " ".join(raw_line.split()).strip()
            if match := COMPANY.match(line):
                company = match.group(1).strip()[:150]
            elif match := ROLE.match(line):
                role = match.group(1).strip()[:150]
            if match := MONTH_RANGE.search(line) or YEAR_RANGE.search(line):
                period = match.group(0)
        if company and role and period:
            entries[(company.casefold(), period.casefold())] = (company, role)
    return entries


def changed_roles(previous_text: str, current_text: str) -> list[str]:
    before = labeled_work_entries(previous_text)
    after = labeled_work_entries(current_text)
    return [
        f"{company}, {period}: «{before[key][1]}» → «{role}»"
        for key, (company, role) in after.items()
        if key in before and before[key][1].casefold() != role.casefold()
        for period in (key[1],)
    ]
