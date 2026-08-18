"""backend integrity constraints

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


USER_FOREIGN_KEYS = (
    ("learner_profiles", "learner_profiles_user_id_fkey"),
    ("user_skill_states", "user_skill_states_user_id_fkey"),
    ("assessments", "assessments_user_id_fkey"),
    ("learning_plans", "learning_plans_user_id_fkey"),
    ("lesson_sessions", "lesson_sessions_user_id_fkey"),
    ("user_errors", "user_errors_user_id_fkey"),
    ("user_vocabulary_states", "user_vocabulary_states_user_id_fkey"),
    ("conversation_sessions", "conversation_sessions_user_id_fkey"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.add_column("learner_profiles", sa.Column("last_learning_date", sa.Date(), nullable=True))
    op.add_column("knowledge_sources", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ALTER COLUMN embedding TYPE vector(1536)
        USING CASE WHEN embedding IS NULL THEN NULL ELSE embedding::text::vector END
        """
    )
    op.execute(
        """
        DELETE FROM assessment_attempts AS duplicate
        USING assessment_attempts AS original
        WHERE duplicate.assessment_id = original.assessment_id
          AND duplicate.item_key = original.item_key
          AND duplicate.id::text > original.id::text
        """
    )
    op.create_unique_constraint("uq_assessment_attempt_item", "assessment_attempts", ["assessment_id", "item_key"])
    for table, constraint in USER_FOREIGN_KEYS:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "users", ["user_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("assessment_attempts_assessment_id_fkey", "assessment_attempts", type_="foreignkey")
    op.create_foreign_key("assessment_attempts_assessment_id_fkey", "assessment_attempts", "assessments", ["assessment_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("conversation_messages_session_id_fkey", "conversation_messages", type_="foreignkey")
    op.create_foreign_key("conversation_messages_session_id_fkey", "conversation_messages", "conversation_sessions", ["session_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("knowledge_chunks_source_id_fkey", "knowledge_chunks", type_="foreignkey")
    op.create_foreign_key("knowledge_chunks_source_id_fkey", "knowledge_chunks", "knowledge_sources", ["source_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE knowledge_chunks
        ALTER COLUMN embedding TYPE json
        USING CASE WHEN embedding IS NULL THEN NULL ELSE embedding::text::json END
        """
    )
    op.drop_constraint("knowledge_chunks_source_id_fkey", "knowledge_chunks", type_="foreignkey")
    op.create_foreign_key("knowledge_chunks_source_id_fkey", "knowledge_chunks", "knowledge_sources", ["source_id"], ["id"])
    op.drop_constraint("conversation_messages_session_id_fkey", "conversation_messages", type_="foreignkey")
    op.create_foreign_key("conversation_messages_session_id_fkey", "conversation_messages", "conversation_sessions", ["session_id"], ["id"])
    op.drop_constraint("assessment_attempts_assessment_id_fkey", "assessment_attempts", type_="foreignkey")
    op.create_foreign_key("assessment_attempts_assessment_id_fkey", "assessment_attempts", "assessments", ["assessment_id"], ["id"])
    for table, constraint in reversed(USER_FOREIGN_KEYS):
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(constraint, table, "users", ["user_id"], ["id"])
    op.drop_constraint("uq_assessment_attempt_item", "assessment_attempts", type_="unique")
    op.drop_column("knowledge_sources", "created_at")
    op.drop_column("learner_profiles", "last_learning_date")
    op.drop_column("users", "is_admin")
    op.drop_table("refresh_tokens")
