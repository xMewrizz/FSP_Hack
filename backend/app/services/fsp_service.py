from typing import Any
import httpx
from app.core.config import settings
from app.schemas.fsp import FSPAchievementSchema, FSPMockAthlete, FSPVerificationResult

FSP_REGISTRY_FIXTURES: dict[str, dict[str, Any]] = {
    "FSP-77-001": {
        "fsp_id": "FSP-77-001",
        "full_name": "Алексей Смирнов",
        "sport_category": "Мастер спорта РФ по спортивному программированию",
        "rating": 2680.5,
        "region": "Москва",
        "achievements": [
            {
                "fsp_id": "FSP-77-001",
                "tournament_name": "Чемпионат России по спортивному программированию 2025",
                "year": 2025,
                "rank_or_place": "1 место (Золото)",
                "sport_category": "Мастер спорта",
                "score_or_rating": 2680.5,
                "verified": False,
            },
            {
                "fsp_id": "FSP-77-001",
                "tournament_name": "Кубок Федерации спортивного программирования 2024",
                "year": 2024,
                "rank_or_place": "2 место (Серебро)",
                "sport_category": "Мастер спорта",
                "score_or_rating": 2540.0,
                "verified": False,
            },
            {
                "fsp_id": "FSP-77-001",
                "tournament_name": "Всероссийские студенческие соревнования ФСП",
                "year": 2023,
                "rank_or_place": "1 место",
                "sport_category": "КМС",
                "score_or_rating": 2400.0,
                "verified": False,
            },
        ],
    },
    "FSP-78-042": {
        "fsp_id": "FSP-78-042",
        "full_name": "Екатерина Кузнецова",
        "sport_category": "Кандидат в мастера спорта (КМС)",
        "rating": 2320.0,
        "region": "Санкт-Петербург",
        "achievements": [
            {
                "fsp_id": "FSP-78-042",
                "tournament_name": "Кубок Санкт-Петербурга по спортивному программированию 2025",
                "year": 2025,
                "rank_or_place": "1 место",
                "sport_category": "КМС",
                "score_or_rating": 2320.0,
                "verified": False,
            },
            {
                "fsp_id": "FSP-78-042",
                "tournament_name": "Чемпионат Северо-Западного ФО по алгоритмическому программированию",
                "year": 2024,
                "rank_or_place": "3 место",
                "sport_category": "КМС",
                "score_or_rating": 2210.0,
                "verified": False,
            },
        ],
    },
    "FSP-54-105": {
        "fsp_id": "FSP-54-105",
        "full_name": "Дмитрий Волков",
        "sport_category": "1-й спортивный разряд",
        "rating": 1950.0,
        "region": "Новосибирская область",
        "achievements": [
            {
                "fsp_id": "FSP-54-105",
                "tournament_name": "Региональный турнир Сибири ФСП 2025",
                "year": 2025,
                "rank_or_place": "4 место",
                "sport_category": "1-й разряд",
                "score_or_rating": 1950.0,
                "verified": False,
            },
        ],
    },
    "FSP-16-088": {
        "fsp_id": "FSP-16-088",
        "full_name": "Алина Гарифуллина",
        "sport_category": "Кандидат в мастера спорта (КМС)",
        "rating": 2290.0,
        "region": "Республика Татарстан",
        "achievements": [
            {
                "fsp_id": "FSP-16-088",
                "tournament_name": "Открытый кубок Казани по продуктовому хакатону ФСП 2025",
                "year": 2025,
                "rank_or_place": "1 место",
                "sport_category": "КМС",
                "score_or_rating": 2290.0,
                "verified": False,
            },
        ],
    },
}


class FSPService:
    @staticmethod
    def get_all_demo_athletes() -> list[FSPMockAthlete]:
        return [
            FSPMockAthlete(
                fsp_id=item["fsp_id"],
                full_name=item["full_name"],
                sport_category=item["sport_category"],
                rating=item["rating"],
                region=item["region"],
                achievements=[FSPAchievementSchema(**ach) for ach in item["achievements"]],
            )
            for item in FSP_REGISTRY_FIXTURES.values()
        ]

    @staticmethod
    async def verify_fsp_id(fsp_id: str | None) -> FSPVerificationResult:
        if not fsp_id or not fsp_id.strip():
            return FSPVerificationResult(
                found=False,
                fsp_id="",
                message="ID не указан",
            )

        clean_id = fsp_id.strip().upper()

        if settings.FSP_API_URL:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"{settings.FSP_API_URL}/athletes/{clean_id}")
                    if resp.status_code == 200:
                        data = resp.json()
                        achievements = [FSPAchievementSchema(**ach) for ach in data.get("achievements", [])]
                        return FSPVerificationResult(
                            found=True,
                            fsp_id=clean_id,
                            athlete_name=data.get("full_name"),
                            sport_category=data.get("sport_category"),
                            achievements_count=len(achievements),
                            achievements=achievements,
                            message="Верифицировано через внешний реестр ФСП",
                        )
            except Exception:
                pass

        if clean_id in FSP_REGISTRY_FIXTURES:
            data = FSP_REGISTRY_FIXTURES[clean_id]
            achievements = [FSPAchievementSchema(**ach) for ach in data["achievements"]]
            return FSPVerificationResult(
                found=True,
                fsp_id=clean_id,
                athlete_name=data["full_name"],
                sport_category=data["sport_category"],
                achievements_count=len(achievements),
                achievements=achievements,
                message=f"Найдена тестовая запись: {data['full_name']} ({data['sport_category']}). Личность кандидата не подтверждена.",
            )

        return FSPVerificationResult(
            found=False,
            fsp_id=clean_id,
            message="Запись не найдена в демонстрационных данных",
        )


fsp_service = FSPService()
