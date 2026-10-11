"""Показать предложения настроенной модели на разных описаниях потребности.

Запуск: python check_need_suggestions.py
По умолчанию обращается к запущенному через Compose ML-сервису на порту 8001.
"""

import argparse
import asyncio
import json
from time import perf_counter

import httpx


CASES = [
    (
        "Рекомендации услуг по поведению",
        "Нужно внедрить ML-модель на сайт консалтинговой компании. Она будет анализировать "
        "поведение пользователей на сайте и затем предлагать им подходящие услуги.",
    ),
    (
        "Backend, явный стек",
        "Ищем Middle Backend-разработчика. Нужно делать API сервиса заказов на Python и FastAPI, "
        "работать с PostgreSQL. Redis будет плюсом. Удалённо, зарплата 200–300 тыс. ₽ на руки.",
    ),
    (
        "Backend, стек не указан",
        "Команде нужен разработчик внутреннего сервиса записи клиентов. Нужно проектировать API, "
        "хранить данные, настроить авторизацию и разобраться с нагрузкой. Технологии ещё не выбрали.",
    ),
    (
        "Анализ данных",
        "Ищем специалиста по анализу данных: исследовать продуктовые метрики, строить SQL-витрины, "
        "проводить A/B-тесты, работать с Python и pandas. Spark будет плюсом.",
    ),
    (
        "Frontend",
        "Нужно разрабатывать интерфейс личного кабинета на React и TypeScript, работать с API, "
        "следить за доступностью и производительностью страниц. Docker знать необязательно.",
    ),
    (
        "DevOps",
        "Ищем DevOps-инженера: поддерживать Kubernetes-кластеры, автоматизировать развёртывание "
        "через CI/CD, следить за логами и метриками. Terraform нужен для инфраструктуры.",
    ),
    (
        "Тестирование",
        "Инженеру по тестированию предстоит проверять веб-приложение и API, писать автотесты, "
        "разбирать ошибки вместе с разработчиками. Знание Python желательно, но не обязательно.",
    ),
    (
        "Мобильная разработка",
        "Нужен Android-разработчик для приложения доставки. Основные задачи — Kotlin, работа с API, "
        "офлайн-хранение данных и публикация обновлений приложения.",
    ),
    (
        "ML-инженерия",
        "Нужно обучать модели классификации, проверять качество на отложенной выборке и внедрять "
        "модель в сервис. Работаем на Python, SQL нужен для подготовки данных, Docker будет плюсом.",
    ),
]


async def main(url: str, direct: bool = False, only: set[str] | None = None) -> None:
    async with httpx.AsyncClient(timeout=120.0) as client:
        for name, description in CASES:
            if only and name not in only:
                continue
            started = perf_counter()
            try:
                if direct:
                    from need_llm import suggest_need
                    result = await suggest_need(description, client)
                else:
                    response = await client.post(url, json={"text": description})
                    response.raise_for_status()
                    result = response.json()
                elapsed = perf_counter() - started
                print(f"\n{name} — {elapsed:.1f} с")
                print(description)
                print(json.dumps({
                    "specialization": result.get("specialization"),
                    "required_grade": result.get("required_grade"),
                    "required_skills": result.get("required_skills"),
                    "salary_min": result.get("salary_min"),
                    "salary_max": result.get("salary_max"),
                    "salary_tax_type": result.get("salary_tax_type"),
                }, ensure_ascii=False, indent=2))
            except httpx.HTTPError as exc:
                print(f"\n{name} — ошибка через {perf_counter() - started:.1f} с: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8001/parse-need")
    parser.add_argument("--direct", action="store_true", help="Проверить настроенного провайдера напрямую без Compose")
    parser.add_argument("--only", nargs="*", help="Проверить только выбранные названия кейсов")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.direct, set(args.only) if args.only else None))
