"""Code-enforced honesty checks."""

from app.services.honesty import bullet_violation, letter_warnings, new_numbers, numbers_in

MISSING = ["Docker", "Kubernetes", "AWS"]


def test_numbers_are_normalised() -> None:
    assert numbers_in("Cut load time by 30 % for 1,200 users") == {"30%", "1,200"}
    assert numbers_in("Improved accuracy by [add real number]") == set()


def test_new_numbers_detects_invented_metrics() -> None:
    assert new_numbers("Built a chatbot", "Built a chatbot used by 500 students") == ["500"]
    assert new_numbers("Served 500 students", "Served 500+ students") == []
    assert new_numbers("Led a team of 3", "Led a 3-person team") == []


def test_plain_rephrasing_is_allowed() -> None:
    original = "Made an API with FastAPI for the campus bot"
    rewritten = "Built REST APIs with FastAPI to power a campus chatbot"
    assert bullet_violation(original, rewritten, MISSING) is None


def test_placeholder_metric_is_allowed() -> None:
    assert bullet_violation("Sped up the pipeline", "Sped up the data pipeline by [add real number]%", MISSING) is None


def test_invented_number_is_rejected() -> None:
    problem = bullet_violation("Sped up the pipeline", "Sped up the pipeline by 40%", MISSING)
    assert problem is not None and "40%" in problem


def test_missing_skill_claim_is_rejected() -> None:
    problem = bullet_violation("Deployed the app on Render", "Deployed the app with Docker on Render", MISSING)
    assert problem is not None and "Docker" in problem


def test_missing_skill_already_in_original_is_fine() -> None:
    assert bullet_violation("Tried Docker for local dev", "Used Docker for local development", MISSING) is None


def test_letter_warnings() -> None:
    profile = "Built REST APIs with FastAPI. Served 200 students."
    body = "I bring 3 years of Docker experience and served 200 students. Impact: [add real number]."
    warnings = letter_warnings(body, profile, MISSING)
    assert any("Docker" in w for w in warnings)
    assert any("3" in w and "numbers" in w for w in warnings)
    assert any("[add real number]" in w for w in warnings)
    assert letter_warnings("I built REST APIs with FastAPI.", profile, MISSING) == []
