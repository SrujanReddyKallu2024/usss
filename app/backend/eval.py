# Run all test questions through the agent and print a results table. Run: python eval.py
import csv
import os
import time

from app.agents import graph

CSV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "csv", "ai_test_questions.csv"
)


def load_questions():
    """Read the sample questions from the shared CSV."""
    questions = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append(row["sample_question"])
    return questions


def main():
    questions = load_questions()
    print(f"Evaluating {len(questions)} questions...\n")
    print(f"{'#':<3} {'intent':<10} {'rows/src':<9} {'ms':<7} {'ok':<4} question")
    print("-" * 90)

    passed = 0
    for i, q in enumerate(questions, start=1):
        try:
            result = graph.answer(f"eval-{i}", q)
            ok = result["status"] == "ok" and bool(result["answer"].strip())
            # Show row_count for SQL paths, else number of sources.
            if result["row_count"] is not None:
                info = str(result["row_count"])
            else:
                info = str(len(result["sources"]))
            intent = result["intent"] or "?"
            ms = result["latency_ms"]
        except Exception as e:
            ok = False
            info = "-"
            intent = "ERROR"
            ms = 0
            print(f"    error: {e}")

        if ok:
            passed += 1
        mark = "ok" if ok else "FAIL"
        print(f"{i:<3} {intent:<10} {info:<9} {ms:<7} {mark:<4} {q[:50]}")
        time.sleep(8)  # space calls out so the free-tier provider doesn't throttle

    print("-" * 90)
    print(f"Summary: {passed}/{len(questions)} passed.")


if __name__ == "__main__":
    main()
