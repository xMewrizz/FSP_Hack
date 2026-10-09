import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from need_parser import parse_need


class NeedParserTests(unittest.TestCase):
    def test_explicit_backend_need(self):
        draft = parse_need(
            "Ищем Middle Backend-разработчика. Нужны Python, FastAPI и PostgreSQL. "
            "Docker не нужен. Зарплата 200–300 тыс. ₽ на руки. Работа удалённая."
        )
        self.assertEqual(draft["specialization"], "Backend")
        self.assertEqual(draft["required_grade"], "middle")
        self.assertEqual([item["name"] for item in draft["required_skills"]], ["Python", "FastAPI", "PostgreSQL"])
        self.assertEqual((draft["salary_min"], draft["salary_max"], draft["salary_tax_type"]), (200000, 300000, "net"))
        self.assertEqual(draft["work_format"], "remote")

    def test_python_alone_does_not_imply_specialization_or_grade(self):
        draft = parse_need("Нужен разработчик с опытом Python. Зарплата обсуждается, формат согласуем.")
        self.assertIsNone(draft["specialization"])
        self.assertIsNone(draft["required_grade"])
        self.assertIsNone(draft["salary_min"])
        self.assertIsNone(draft["work_format"])
        self.assertEqual(draft["required_skills"], [{"name": "Python", "weight": 3}])

    def test_conflicting_grade_and_format_are_not_guessed(self):
        draft = parse_need("Ищем Junior или Middle Backend, работа удалённо или в офисе, Python обязателен.")
        self.assertIsNone(draft["required_grade"])
        self.assertIsNone(draft["work_format"])
        self.assertEqual(draft["specialization"], "Backend")

    def test_data_science_keeps_python_without_backend_assumption(self):
        draft = parse_need(
            "Нужен Data Scientist: Python, Pandas, SQL. Оклад 250000-350000 рублей до вычета, гибрид."
        )
        self.assertEqual(draft["specialization"], "Data Science / ML")
        self.assertEqual((draft["salary_min"], draft["salary_max"], draft["salary_tax_type"]), (250000, 350000, "gross"))
        self.assertEqual(draft["work_format"], "hybrid")

    def test_optional_skill_is_not_marked_required(self):
        draft = parse_need("Ищем Backend-разработчика. Нужны Python и SQL, желательно Docker, Kafka будет плюсом.")
        self.assertEqual([item["name"] for item in draft["required_skills"]], ["Python", "SQL"])


if __name__ == "__main__":
    unittest.main()
