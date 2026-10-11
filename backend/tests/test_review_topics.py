import pytest
import uuid

from conftest import TestingSessionLocal
from app.models.test import TestSession as StoredTestSession
from app.services import testing_service as testing_module

from app.schemas.testing import QuestionReview
from app.services.testing_service import finish_review_topics, load_review_topics, missed_answer_pairs


def _item(text: str, answer: str, correct: bool) -> QuestionReview:
    return QuestionReview(
        code="Q",
        topic="Тема банка",
        question_text=text,
        selected_answers=[answer],
        correct_answers=["верный"],
        is_correct=correct,
        explanation="",
    )


def test_only_wrong_answers_are_sent_and_capped_at_ten():
    review = [_item("верный вопрос", "да", True)]
    review.extend(_item(f"вопрос {index}", "неверно", False) for index in range(12))
    pairs = missed_answer_pairs(review)
    assert len(pairs) == 10
    assert pairs[0] == {"question": "вопрос 0", "answer": "неверно"}
    assert all("верный вопрос" not in pair["question"] for pair in pairs)


@pytest.mark.asyncio
async def test_perfect_review_does_not_need_the_model():
    topics, status = await load_review_topics(
        [_item("вопрос", "верный", True)],
        skill_code="ds_python",
        specialization="Data Science / ML",
        grade="junior",
    )
    assert topics == []
    assert status == "none"


@pytest.mark.asyncio
async def test_topics_are_saved_after_result_without_regrading(monkeypatch):
    session = StoredTestSession(
        user_id=uuid.uuid4(), candidate_profile_id=uuid.uuid4(),
        specialization="Backend", target_grade="junior", status="completed",
        score=0, max_score=1, percentage=0, passed=False,
        review_topics_status="pending", review_topics=[],
        questions_snapshot=[{
            "id": "q1", "code": "Q-1", "topic": "Python", "question_text": "Что делает list.copy()?",
            "options": [{"id": "a", "text": "Глубокая копия"}, {"id": "b", "text": "Поверхностная копия"}],
            "correct_answers": ["b"], "explanation": "",
        }],
        answers_data=[{"question_id": "q1", "selected_answers": ["a"]}],
    )
    async with TestingSessionLocal() as db:
        db.add(session)
        await db.commit()
    async def fake_topics(review, **kwargs):
        assert review[0].is_correct is False
        return ["Поверхностное копирование списков"], "ready"
    monkeypatch.setattr(testing_module, "load_review_topics", fake_topics)
    await finish_review_topics(session.id, TestingSessionLocal)
    async with TestingSessionLocal() as db:
        stored = await db.get(StoredTestSession, session.id)
        assert stored.score == 0
        assert stored.review_topics_status == "ready"
        assert stored.review_topics == ["Поверхностное копирование списков"]
