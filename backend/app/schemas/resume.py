from pydantic import BaseModel


class ResumeParsedData(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    city: str | None = None
    specialization: str | None = None
    suggested_grade: str | None = None
    extracted_skills: list[str] = []
    text_preview: str = ""
