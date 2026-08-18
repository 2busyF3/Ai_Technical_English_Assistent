from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="Learner", min_length=2, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DeleteAccountRequest(BaseModel):
    password: str


class PreferencesRequest(BaseModel):
    daily_learning_minutes: int = Field(ge=10, le=90)
    native_explanations: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict[str, Any]


class OnboardingRequest(BaseModel):
    native_language: str = "Russian"
    target_cefr: str = "B2"
    specialization: str
    experience_level: str
    technologies: list[str] = Field(min_length=1, max_length=15)
    professional_goals: list[str] = Field(min_length=1, max_length=8)
    daily_learning_minutes: int = Field(ge=10, le=90)
    preferred_exercise_types: list[str] = Field(default_factory=list)


class AssessmentAnswer(BaseModel):
    assessment_id: str
    item_key: str
    answer: str = Field(min_length=1, max_length=3000)


class ExerciseAnswer(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)


class VocabularyReviewRequest(BaseModel):
    recall_answer: str = Field(min_length=1, max_length=200)
    context_sentence: str = Field(min_length=3, max_length=1000)


class TutorRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=4000)
    mode: Literal["free_conversation", "technical_interview", "lesson_support"] = "free_conversation"


class TutorUIBlock(BaseModel):
    type: Literal["VOCAB_CARD", "FEEDBACK", "QUIZ", "PROGRESS_UPDATE", "CODE_SNIPPET"]
    payload: dict[str, Any]


class TutorResponse(BaseModel):
    message: str
    ui_blocks: list[TutorUIBlock] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    technical_correctness: float = Field(ge=0, le=1)
    grammar_accuracy: float = Field(ge=0, le=1)
    vocabulary_range: float = Field(ge=0, le=1)
    technical_vocabulary: float = Field(ge=0, le=1)
    clarity: float = Field(ge=0, le=1)
    task_completion: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    is_relevant: bool
    is_keyword_stuffing: bool
    feedback: str = Field(min_length=1, max_length=1000)
    errors: list[dict[str, Any]] = Field(default_factory=list)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
