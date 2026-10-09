from app.services.testing_service import build_question_review


def test_review_uses_saved_question_key_and_explains_wrong_or_missing_answers():
    questions = [
        {
            "id": "q1", "code": "Q-1", "topic": "SQL", "question_text": "Что верно?",
            "options": [{"id": "A", "text": "Первый"}, {"id": "B", "text": "Второй"}],
            "correct_answers": ["B"], "explanation": "Верно второе утверждение.",
        },
        {
            "id": "q2", "code": "Q-2", "topic": "HTTP", "question_text": "Какой ответ?",
            "options": [{"id": "A", "text": "Да"}, {"id": "B", "text": "Нет"}],
            "correct_answers": ["A"], "explanation": "Ответ следует из условия.",
        },
    ]

    review = build_question_review(questions, [{"question_id": "q1", "selected_answers": ["A"]}])

    assert review[0].is_correct is False
    assert review[0].selected_answers == ["Первый"]
    assert review[0].correct_answers == ["Второй"]
    assert review[0].explanation == "Верно второе утверждение."
    assert review[1].is_correct is False
    assert review[1].selected_answers == []
    assert review[1].correct_answers == ["Да"]
