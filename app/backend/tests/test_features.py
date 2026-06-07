# Pragmatic integration tests. Skips cleanly if the DB/LLM aren't reachable.
import csv
import os

import pytest

CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "csv", "ai_test_questions.csv"
)


def _reachable():
    """Return True if we can introspect the DB and reach the LLM."""
    try:
        from app.services.schema_introspect import get_schema_string
        schema = get_schema_string()
        return bool(schema)
    except Exception:
        return False


# Skip the whole module gracefully when the environment isn't up.
pytestmark = pytest.mark.skipif(
    not _reachable(), reason="DB/LLM not reachable; skipping live tests."
)


def _load_questions():
    rows = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append((row["ai_feature"], row["sample_question"]))
    return rows


def test_health_logic_imports():
    # Basic import-level sanity: main and graph load.
    import main  # noqa: F401
    from app.agents import graph  # noqa: F401
    assert hasattr(graph, "answer")


def test_nl2sql_question():
    from app.agents import graph
    result = graph.answer("test-nl2sql", "Which tenants have overdue payments?")
    assert result["intent"] in ("nl2sql", "recommend")
    assert result["answer"].strip()


def test_rag_question():
    from app.agents import graph
    result = graph.answer("test-rag", "What is the late payment policy?")
    assert result["intent"] in ("rag", "nl2sql")
    assert result["answer"].strip()


def test_recommend_question():
    from app.agents import graph
    result = graph.answer(
        "test-rec", "Recommend 2 bedroom properties in Austin under 2000")
    assert result["intent"] in ("recommend", "nl2sql")
    assert result["answer"].strip()


def test_all_questions_load():
    questions = _load_questions()
    assert len(questions) >= 5
