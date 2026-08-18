from datetime import datetime, timezone

from app.ai.context import ContextBuilder, TutorContext
from app.domain.learning import MasteryService, PlacementEngine, PriorityInput, PersonalizationEngine, SRSService, SRSState
from app.rag.retrieval import Candidate, HybridRetriever, RetrievalQuery


def test_personalization_prioritizes_weak_relevant_skill() -> None:
    engine = PersonalizationEngine()
    weak = engine.priority(PriorityInput(.25,.6,1,1,10,3,1))
    strong = engine.priority(PriorityInput(.8,.8,1,1,2,0,1))
    assert weak > strong


def test_prerequisite_readiness_gates_priority() -> None:
    engine = PersonalizationEngine()
    ready = engine.priority(PriorityInput(.4,.5,1,1,7,1,1))
    blocked = engine.priority(PriorityInput(.4,.5,1,1,7,1,.2))
    assert blocked < ready * .25


def test_mastery_moves_toward_evidence_and_is_bounded() -> None:
    service = MasteryService()
    assert service.update(.4,.9,.7,.9) > .4
    assert service.update(.4,.1,.7,.9) < .4
    assert service.update(.98,1,1,1) <= .98


def test_srs_sm2_progression_and_reset() -> None:
    service = SRSService(); now = datetime.now(timezone.utc)
    first, due = service.review(SRSState(), 5, now)
    second, _ = service.review(first, 4, now)
    reset, _ = service.review(second, 1, now)
    assert first.interval_days == 1 and due > now
    assert second.interval_days == 6
    assert reset.repetitions == 0 and reset.interval_days == 1


def test_placement_converges_and_has_upper_limit() -> None:
    engine = PlacementEngine(); ability, confidence = .5, .1
    done = False
    for count in range(engine.max_questions):
        ability, confidence, done = engine.update(ability, confidence, .9, .55, count)
    assert done and ability > .5 and confidence >= .7


def test_context_builder_limits_history_and_budget() -> None:
    context = TutorContext("B1 backend developer","Interview",["articles"],["latency"],[{"role":"user","content":str(i)} for i in range(20)],["knowledge"])
    output = ContextBuilder(max_chars=500,recent_message_limit=3).build(context)
    assert len(output) <= 500
    assert "user: 19" in output and "user: 0" not in output


def test_hybrid_retrieval_applies_metadata_and_exact_terms() -> None:
    candidates = [
        Candidate("Cache invalidation can reduce stale reads", {"source_type":"OFFICIAL_DOCUMENTATION","specialization":"BACKEND","technical_authority":1.0}, [1,0]),
        Candidate("General travel vocabulary", {"source_type":"LANGUAGE_TEXTBOOK","technical_authority":0.2}, [0,1]),
    ]
    result = HybridRetriever().rank(RetrievalQuery("cache invalidation", {"OFFICIAL_DOCUMENTATION"}, "BACKEND"), candidates, [1,0])
    assert len(result) == 1 and "Cache invalidation" in result[0].content

