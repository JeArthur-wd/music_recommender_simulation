"""Runs the full reliability harness (src/evaluate.py) as part of the test suite."""

from src.evaluate import run_all


def test_reliability_harness_passes_every_check():
    report = run_all(use_llm=False)
    failures = [f"{c.suite}: {c.name} -> {c.detail}" for c in report.checks if not c.passed]
    assert not failures, "\n".join(failures)
    summary = report.summary()
    assert summary["total"] >= 150
    assert summary["avg_confidence"] >= 0.8
