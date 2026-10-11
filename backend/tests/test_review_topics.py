import pytest

from app.schemas.testing import QuestionReview
from app.services.testing_service import load_review_topics, missed_answer_pairs


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
