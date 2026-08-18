from app.curriculum import DEPENDENCIES, SKILLS, VOCABULARY


def test_dependencies_reference_seeded_skills() -> None:
    ids = {skill[0] for skill in SKILLS}
    assert all(skill in ids and prereq in ids for skill, prereq in DEPENDENCIES)


def test_backend_seed_contains_real_collocations() -> None:
    collocations = {phrase for item in VOCABULARY for phrase in item[3]}
    assert "deploy to production" in collocations
    assert "reduce latency" in collocations
    assert "introduce a breaking change" in collocations

