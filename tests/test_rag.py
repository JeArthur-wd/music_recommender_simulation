import pytest

from src.rag import Document, KnowledgeBase, stem, tokenize


@pytest.fixture(scope="module")
def kb():
    return KnowledgeBase.load()


def test_tokenize_drops_stopwords_and_stems():
    assert tokenize("I want some music for Studying") == ["study"]
    assert stem("beats") == "beat" and stem("memories") == "memory"
    assert "r&b" in tokenize("smooth R&B")


@pytest.mark.parametrize("query, expected_id", [
    ("music for studying", "activity-study"),
    ("gym workout", "activity-workout"),
    ("help me fall asleep", "activity-sleep"),
    ("I am heartbroken after a breakup", "mood-sad"),
    ("road trip with friends", "activity-roadtrip"),
    ("date night dinner", "activity-dinner"),
    ("pop punk", "genre-punk"),
])
def test_retrieval_ranks_the_relevant_doc_first(kb, query, expected_id):
    results = kb.retrieve(query)
    assert results, f"nothing retrieved for {query!r}"
    assert results[0].doc.id == expected_id


def test_retrieval_is_sorted_and_respects_k(kb):
    results = kb.retrieve("calm acoustic music for a rainy study session", k=3)
    assert len(results) <= 3
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_irrelevant_query_retrieves_nothing(kb):
    assert kb.retrieve("asdf qwerty zxcv") == []


def test_every_doc_hint_points_at_valid_values(kb):
    from src.recommender import load_songs
    songs = load_songs("data/songs.csv")
    genres = {s["genre"] for s in songs}
    moods = {s["mood"] for s in songs}
    tags = {t for s in songs for t in s["mood_tags"]}
    for doc in kb.documents:
        hints = doc.hints
        assert hints.get("genre") is None or hints["genre"] in genres, doc.id
        assert hints.get("mood") is None or hints["mood"] in moods, doc.id
        assert 0.0 <= hints["energy"] <= 1.0, doc.id
        assert set(hints.get("mood_tags", [])) <= tags, doc.id
        assert set(hints.get("related_genres", [])) <= genres, doc.id


def test_empty_knowledge_base_is_rejected():
    with pytest.raises(ValueError):
        KnowledgeBase([])


def test_custom_documents_can_be_indexed():
    kb = KnowledgeBase([
        Document("a", "genre", "Sea shanties", "Songs sailors sing", ["shanty", "sailor"], {}),
        Document("b", "genre", "Polka", "Accordion dance music", ["polka", "accordion"], {}),
    ])
    assert kb.retrieve("accordion polka")[0].doc.id == "b"
