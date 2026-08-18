from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp


@dataclass(frozen=True)
class PriorityInput:
    mastery: float
    confidence: float
    career_relevance: float
    goal_relevance: float
    days_since_practice: float
    error_frequency: int
    prerequisite_readiness: float


class PersonalizationEngine:
    def priority(self, item: PriorityInput) -> float:
        weakness = 1 - item.mastery
        uncertainty = 1 + (1 - item.confidence) * 0.2
        forgetting = 1 + min(item.days_since_practice / 14, 1.5)
        errors = 1 + min(item.error_frequency, 5) * 0.12
        relevance = 0.45 * item.career_relevance + 0.55 * item.goal_relevance
        return round(weakness * uncertainty * forgetting * errors * relevance * item.prerequisite_readiness, 5)


class MasteryService:
    def update(self, mastery: float, score: float, difficulty: float, confidence: float) -> float:
        evidence = (score - mastery) * (0.12 + difficulty * 0.08) * max(0.25, confidence)
        return round(min(0.98, max(0.02, mastery + evidence)), 4)


@dataclass(frozen=True)
class SRSState:
    repetitions: int = 0
    interval_days: int = 0
    ease_factor: float = 2.5


class SRSService:
    def review(self, state: SRSState, quality: int, now: datetime | None = None) -> tuple[SRSState, datetime]:
        quality = max(0, min(5, quality))
        if quality < 3:
            next_state = SRSState(0, 1, max(1.3, state.ease_factor - 0.2))
        else:
            repetitions = state.repetitions + 1
            interval = 1 if repetitions == 1 else 6 if repetitions == 2 else round(state.interval_days * state.ease_factor)
            ease = max(1.3, state.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            next_state = SRSState(repetitions, max(1, interval), round(ease, 2))
        due = (now or datetime.now(timezone.utc)) + timedelta(days=next_state.interval_days)
        return next_state, due


@dataclass(frozen=True)
class VocabularyReviewEvaluation:
    recall_correct: bool
    context_correct: bool
    contains_term: bool
    quality: int


class VocabularyReviewService:
    @staticmethod
    def evaluate(term: str, recall_answer: str, context_sentence: str) -> VocabularyReviewEvaluation:
        def normalize(value: str) -> str:
            return re.sub(r"[^a-z0-9 ]", "", value.casefold()).strip()

        recall_correct = normalize(recall_answer) == normalize(term)
        contains_term = bool(re.search(rf"(?<![a-z0-9]){re.escape(term.casefold())}(?![a-z0-9])", context_sentence.casefold()))
        enough_context = len(re.findall(r"[A-Za-z0-9'-]+", context_sentence)) >= 6
        context_correct = contains_term and enough_context
        quality = 5 if recall_correct and context_correct and len(context_sentence.split()) >= 10 else 4 if recall_correct and context_correct else 3 if context_correct else 2 if recall_correct else 1
        return VocabularyReviewEvaluation(recall_correct, context_correct, contains_term, quality)


class PlacementEngine:
    max_questions = 7

    def update(self, ability: float, confidence: float, score: float, difficulty: float, count: int) -> tuple[float, float, bool]:
        learning_rate = 0.32 / (1 + count * 0.08)
        expected = 1 / (1 + exp(-5 * (ability - difficulty)))
        new_ability = min(0.98, max(0.02, ability + learning_rate * (score - expected)))
        new_confidence = min(0.95, confidence + 0.13 + abs(score - expected) * 0.03)
        done = count + 1 >= self.max_questions
        return round(new_ability, 4), round(new_confidence, 4), done

    @staticmethod
    def cefr(ability: float) -> str:
        thresholds = ((0.25, "A1"), (0.42, "A2"), (0.62, "B1"), (0.78, "B2"), (0.97, "C1"))
        return next((level for ceiling, level in thresholds if ability < ceiling), "C2")
