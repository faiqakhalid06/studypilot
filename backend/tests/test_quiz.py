from datetime import date, timedelta

from app.quiz import BLANK, make_quiz, sentences, words
from app.schemas import QuizRequest, SubjectIn, TopicIn

TODAY = date(2026, 10, 23)

NOTES_A = (
    "Overfitting happens when a model memorizes the training data instead of learning patterns. "
    "Regularization and more training data help reduce overfitting. "
    "Cross validation measures how well a model generalizes."
)
NOTES_B = (
    "A decision tree splits the data using questions about features. "
    "Pruning removes branches to keep the tree simple. "
    "Entropy measures how mixed a group of labels is."
)


def subject(name="ML", days=20, topics=None):
    topics = topics if topics is not None else [
        TopicIn(name="Overfitting", notes=NOTES_A),
        TopicIn(name="Trees", notes=NOTES_B),
    ]
    return SubjectIn(name=name, exam_date=TODAY + timedelta(days=days), topics=topics)


def quiz(subjects, count=5, seed=1):
    return make_quiz(QuizRequest(subjects=subjects, count=count, seed=seed), today=TODAY)


def test_words_skip_short_and_common_words():
    assert words("The model learns because training data is large") == ["model", "learns", "training", "large"]


def test_sentences_skip_very_short_lines():
    assert sentences("Too short. This sentence has enough words in it.") == ["This sentence has enough words in it."]


def test_quiz_returns_the_asked_number_of_questions():
    assert len(quiz([subject()], count=4).questions) == 4


def test_every_question_has_a_blank_and_the_answer_is_an_option():
    for q in quiz([subject()], count=6).questions:
        assert BLANK in q.text
        assert q.answer in q.options
        assert q.answer.lower() not in q.text.lower().split()
        assert len(set(q.options)) == len(q.options)


def test_same_seed_same_quiz_and_different_seed_can_differ():
    a, b = quiz([subject()], seed=7), quiz([subject()], seed=7)
    assert a == b


def test_weakest_topic_comes_first():
    s = subject(topics=[
        TopicIn(name="Strong", notes=NOTES_A, right=5, total=5),
        TopicIn(name="Weak", notes=NOTES_B, right=0, total=5),
    ])
    assert quiz([s], count=2).questions[0].topic == "Weak"


def test_past_exam_subjects_are_skipped():
    assert quiz([subject(days=-1)]).questions == []


def test_topics_without_notes_are_skipped():
    s = subject(topics=[TopicIn(name="Empty"), TopicIn(name="Has notes", notes=NOTES_A)])
    assert {q.topic for q in quiz([s], count=3).questions} == {"Has notes"}


def test_no_notes_gives_no_questions():
    assert quiz([subject(topics=[TopicIn(name="Empty")])]).questions == []


def test_asking_for_more_than_possible_returns_what_exists():
    s = subject(topics=[TopicIn(name="Small", notes="Binary search finds an item in a sorted list. Stacks follow last in first out order.")])
    assert 0 < len(quiz([s], count=20).questions) <= 2


def test_questions_are_numbered_from_one():
    assert [q.id for q in quiz([subject()], count=3).questions] == [1, 2, 3]