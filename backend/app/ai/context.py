from dataclasses import dataclass


@dataclass
class TutorContext:
    learner_summary: str
    current_goal: str
    recent_errors: list[str]
    due_vocabulary: list[str]
    recent_messages: list[dict[str, str]]
    retrieved_knowledge: list[str]


class ContextBuilder:
    def __init__(self, max_chars: int = 9000, recent_message_limit: int = 8):
        self.max_chars = max_chars
        self.recent_message_limit = recent_message_limit

    def build(self, context: TutorContext) -> str:
        parts = [
            f"Learner: {context.learner_summary}",
            f"Goal: {context.current_goal}",
            "Important recurring errors: " + ", ".join(context.recent_errors[:5]),
            "Vocabulary due: " + ", ".join(context.due_vocabulary[:8]),
            "Relevant knowledge:\n" + "\n".join(context.retrieved_knowledge[:4]),
            "Recent conversation:\n" + "\n".join(f"{m['role']}: {m['content']}" for m in context.recent_messages[-self.recent_message_limit:]),
        ]
        return "\n\n".join(parts)[: self.max_chars]

