"""Benchmark suite for rubric calibration.

Contains test fixtures with known expected outcomes for
calibrating rubric weights and thresholds.
"""

from typing import Any

# Benchmark fixtures with known quality levels
BENCHMARK_FIXTURES = {
    "clean_project": {
        "description": "Well-structured project with tests, docs, and CI",
        "expected_score": 85,
        "expected_grade": "B",
        "expected_findings": 0,
        "expected_coverage": 100,
        "expected_confidence": 100,
        "characteristics": {
            "has_tests": True,
            "has_ci": True,
            "has_docs": True,
            "has_linting": True,
            "no_secrets": True,
            "no_vulnerabilities": True,
        },
    },
    "prototype_project": {
        "description": "Working prototype with minimal testing",
        "expected_score": 55,
        "expected_grade": "D",
        "expected_findings": 5,
        "expected_coverage": 40,
        "expected_confidence": 60,
        "characteristics": {
            "has_tests": False,
            "has_ci": False,
            "has_docs": True,
            "has_linting": False,
            "no_secrets": True,
            "no_vulnerabilities": True,
        },
    },
    "insecure_project": {
        "description": "Project with security vulnerabilities",
        "expected_score": 30,
        "expected_grade": "F",
        "expected_findings": 8,
        "expected_coverage": 60,
        "expected_confidence": 80,
        "expected_blockers": 2,
        "characteristics": {
            "has_tests": True,
            "has_ci": False,
            "has_docs": False,
            "has_linting": False,
            "no_secrets": False,
            "no_vulnerabilities": False,
        },
    },
    "overengineered_project": {
        "description": "Simple project with excessive complexity",
        "expected_score": 65,
        "expected_grade": "C",
        "expected_findings": 3,
        "expected_coverage": 80,
        "expected_confidence": 70,
        "characteristics": {
            "has_tests": True,
            "has_ci": True,
            "has_docs": True,
            "has_linting": True,
            "no_secrets": True,
            "no_vulnerabilities": True,
            "high_complexity": True,
        },
    },
}


def load_benchmark_fixtures() -> dict[str, Any]:
    """Load all benchmark fixtures."""
    return BENCHMARK_FIXTURES


def validate_score_against_expected(
    actual_score: int,
    expected_score: int,
    tolerance: int = 10,
) -> bool:
    """Check if actual score is within tolerance of expected."""
    return abs(actual_score - expected_score) <= tolerance


def generate_benchmark_report(results: dict[str, Any]) -> str:
    """Generate a markdown report of benchmark results."""
    lines = [
        "# VibeGrade Benchmark Report",
        "",
        "## Summary",
        "",
        f"- Total fixtures: {len(BENCHMARK_FIXTURES)}",
        f"- Passed: {sum(1 for r in results.values() if r.get('passed', False))}",
        f"- Failed: {sum(1 for r in results.values() if not r.get('passed', False))}",
        "",
        "## Details",
        "",
    ]

    for name, result in results.items():
        lines.append(f"### {name}")
        lines.append(f"- Expected: {result.get('expected_score', 'N/A')}")
        lines.append(f"- Actual: {result.get('actual_score', 'N/A')}")
        lines.append(f"- Passed: {result.get('passed', False)}")
        lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    fixtures = load_benchmark_fixtures()
    print(f"Loaded {len(fixtures)} benchmark fixtures")
    for name, fixture in fixtures.items():
        print(f"  - {name}: expected score {fixture['expected_score']}")
