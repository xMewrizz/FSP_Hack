"""Compare work-history lines from resumes saved by the same candidate."""

from app.services.resume_sanity import MONTH_RANGE, YEAR_RANGE


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
