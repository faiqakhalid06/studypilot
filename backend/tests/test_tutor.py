from app.tutor import chunk_notes, words


def test_chunk_notes_splits_into_pairs():
    notes = "One. Two. Three. Four. Five."
    assert chunk_notes(notes) == ["One. Two.", "Three. Four.", "Five."]


def test_words_ignores_stop_words_and_plurals():
    assert "tree" in words("What are decision trees?")
    assert "what" not in words("What are decision trees?")