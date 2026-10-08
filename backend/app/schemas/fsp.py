from datetime import datetime
import uuid
from pydantic import BaseModel


class FSPAchievementSchema(BaseModel):
    id: uuid.UUID | None = None
    fsp_id: str
    tournament_name: str
    year: int
    rank_or_place: str
    sport_category: str | None = None
    score_or_rating: float | None = None
    verified: bool = True
    is_demo: bool = True
    disclaimer: str = "Демонстрационные данные стенда. Не является официальной выпиской реестра ФСП"

    model_config = {"from_attributes": True}


class FSPMockAthlete(BaseModel):
    fsp_id: str
    full_name: str
    sport_category: str  # КМС, МС, 1 взрослый и т.д.
    rating: float
    region: str
    is_demo: bool = True
    disclaimer: str = "Демонстрационные данные стенда. Не является официальной выпиской реестра ФСП"
    achievements: list[FSPAchievementSchema]


class FSPLinkRequest(BaseModel):
    fsp_id: str


class FSPVerificationResult(BaseModel):
    found: bool
    fsp_id: str
    athlete_name: str | None = None
    sport_category: str | None = None
    achievements_count: int = 0
    achievements: list[FSPAchievementSchema] = []
    is_demo: bool = True
    disclaimer: str = "Демонстрационные данные стенда. Не является официальной выпиской реестра ФСП"
    message: str
