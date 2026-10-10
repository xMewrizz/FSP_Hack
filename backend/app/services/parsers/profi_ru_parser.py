from __future__ import annotations

import re
from typing import Any

from app.services.parsers.date_utils import parse_experience_duration_text
from app.services.parsers.schemas import ExternalWorkPeriod, ParsedExternalProfile, ProfiRuActivityCheck


class ProfiRuParser:
    """
    Парсер и модуль анализа профилей специалистов Профи.ру (profi.ru).
    
    Особенности и ключевой регламент:
    - Профили на Профи.ру (например, https://profi.ru/it_freelance/data-scientist/)
      содержат сведения об услугах, частной практике, рейтинге и заказах.
    - Это НЕ обязательно классическое резюме с формальной историей работы.
    - КЛЮЧЕВОЕ ПРАВИЛО СИСТЕМЫ:
      Само наличие подработки, фриланса или репетиторства на Профи.ру
      НЕ ОЗНАЧАЕТ завышения опыта («не крутит опыт») и не является нарушением.
      Оно лишь дополняет картину навыков кандидата и подтверждает практическую активность.
    """

    CATALOG_URL = "https://profi.ru/it_freelance/data-scientist/"

    @classmethod
    def check_profi_policy(cls) -> ProfiRuActivityCheck:
        """
        Возвращает официальную политику валидации платформы в отношении Профи.ру.
        Подтверждает, что подработка и репетиторство не наказываются как завышение опыта.
        """
        return ProfiRuActivityCheck(
            catalog_url=cls.CATALOG_URL,
            is_freelance_or_tutoring=True,
            does_not_indicate_inflated_experience=True,
            legal_summary=(
                "Профили на Профи.ру рассматриваются исключительно как дополнительное подтверждение "
                "навыков (фриланс, частная практика, консультации, репетиторство). "
                "Наличие профиля или заказов на Профи.ру ни при каких обстоятельствах не трактуется "
                "как признак накрутки опыта («возможно крутит опыт»)."
            ),
        )

    @classmethod
    def parse_specialist_catalog(cls, html_text: str) -> list[dict[str, Any]]:
        """
        Парсит страницу каталога специалистов (https://profi.ru/it_freelance/data-scientist/).
        Извлекает карточки: имя, услуги, рейтинг, число отзывов/заказов, стаж частной практики.
        """
        items: list[dict[str, Any]] = []

        card_blocks = re.split(
            r'<(?:div|article)[^>]*class="[^"]*(?:specialist-card|profile-card|ui-card)[^"]*"[^>]*>',
            html_text,
            flags=re.IGNORECASE,
        )[1:]

        if not card_blocks:
            card_blocks = re.findall(
                r'(<a[^>]*href="[^"]*(?:/profile/|/p/)[^"]*"[^>]*>.*?</a>.*?(?:отзыв|рейтинг|заказ).*?)(?=<a[^>]*href="[^"]*(?:/profile/|/p/)|$)',
                html_text,
                re.DOTALL | re.IGNORECASE,
            )

        for card in card_blocks:
            name_match = re.search(r'<(?:h3|h4|div)[^>]*class="[^"]*(?:name|title)[^"]*"[^>]*>(.*?)</(?:h3|h4|div)>', card, re.DOTALL | re.IGNORECASE)
            name = cls._clean_text(name_match.group(1)) if name_match else "Специалист Профи.ру"

            url_match = re.search(r'href="([^"]*(?:/profile/|/p/)[^"]*)"', card, re.IGNORECASE)
            url = url_match.group(1) if url_match else None

            rating_match = re.search(r'(?:рейтинг|оценка)[:\s]*<strong>([0-9.,]+)</strong>', card, re.IGNORECASE)
            if not rating_match:
                rating_match = re.search(r'\b([45]\.[0-9]{1,2})\b', card)
            rating = float(rating_match.group(1).replace(",", ".")) if rating_match else None

            orders_match = re.search(r'(\d+)\s*(?:заказ[а-я]*|выполнен[а-я]*\s*заказ)', card, re.IGNORECASE)
            orders_count = int(orders_match.group(1)) if orders_match else None

            # Стаж частной практики или репетиторства
            exp_match = re.search(r'(?:опыт|стаж|практика)[:\s]*([^\n<,]+)', card, re.IGNORECASE)
            exp_text = cls._clean_text(exp_match.group(1)) if exp_match else ""
            exp_months = parse_experience_duration_text(exp_text)

            items.append({
                "name": name,
                "url": url,
                "rating": rating,
                "orders_count": orders_count,
                "experience_text": exp_text,
                "experience_months": exp_months,
            })

        return items

    @classmethod
    def parse_profile(cls, html_text: str, profile_url: str = "") -> ParsedExternalProfile:
        """
        Парсит профиль специалиста на Профи.ру.
        Извлекает перечень оказываемых услуг, заказы, рейтинг и стаж практики.
        Помечает профиль флагом is_freelance_or_part_time = True.
        """
        name_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.DOTALL | re.IGNORECASE)
        name = cls._clean_text(name_match.group(1)) if name_match else "Специалист Профи.ру"

        rating_match = re.search(r'(?:рейтинг|оценка)[:\s]*([0-9.,]+)', html_text, re.IGNORECASE)
        if not rating_match:
            rating_match = re.search(r'\b([45]\.[0-9]{1,2})\b', html_text)
        rating = float(rating_match.group(1).replace(",", ".")) if rating_match else None

        orders_match = re.search(r'(\d+)\s*(?:заказ[а-я]*|отзыв[а-я]*)', html_text, re.IGNORECASE)
        orders_count = int(orders_match.group(1)) if orders_match else None

        # Услуги и специализации
        services = []
        service_matches = re.findall(
            r'<(?:div|span|li)[^>]*class="[^"]*(?:service-name|spec-item|tag)[^"]*"[^>]*>(.*?)</(?:div|span|li)>',
            html_text,
            re.DOTALL | re.IGNORECASE,
        )
        for s in service_matches:
            cl = cls._clean_text(s)
            if cl and cl not in services:
                services.append(cl)

        # Стаж частной практики
        exp_match = re.search(r'(?:опыт|стаж|частная практика|репетиторский стаж)[:\s]*([^\n<]+)', html_text, re.IGNORECASE)
        exp_text = cls._clean_text(exp_match.group(1)) if exp_match else ""
        exp_months = parse_experience_duration_text(exp_text)

        work_periods: list[ExternalWorkPeriod] = []
        if exp_months > 0 or services:
            work_periods.append(
                ExternalWorkPeriod(
                    company="Профи.ру (Частная практика / Фриланс)",
                    role=", ".join(services[:3]) if services else "Частный специалист",
                    duration_months=exp_months,
                    is_current=True,
                    description=f"Выполнено заказов: {orders_count or 0}, рейтинг: {rating or '—'}",
                )
            )

        identifier = profile_url.rstrip("/").split("/")[-1] if profile_url else None

        return ParsedExternalProfile(
            source="profi_ru",
            source_name="Профи.ру (Частная практика)",
            url=profile_url or "https://profi.ru/it_freelance/data-scientist/",
            identifier=identifier,
            full_name=name,
            headline="Частный специалист / Фрилансер на Профи.ру",
            total_experience_months=exp_months,
            work_periods=work_periods,
            skills=services,
            rating=rating,
            orders_count=orders_count,
            is_freelance_or_part_time=True,
            terms_and_access_note=(
                "Профиль дополняет картину практическими заказами. "
                "Наличие подработки не является завышением опыта."
            ),
        )

    @staticmethod
    def _clean_text(raw: str) -> str:
        no_tags = re.sub(r"<[^>]+>", "", raw)
        return re.sub(r"\s+", " ", no_tags).strip()
