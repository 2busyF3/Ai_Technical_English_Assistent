"""AI call traceability

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ai_call_metadata", sa.Column("user_id", sa.String(36), nullable=True))
    op.add_column("ai_call_metadata", sa.Column("response_id", sa.String(100), nullable=True))
    op.create_foreign_key(
        "ai_call_metadata_user_id_fkey",
        "ai_call_metadata",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_ai_call_metadata_user_id", "ai_call_metadata", ["user_id"])
    op.create_index("ix_ai_call_metadata_response_id", "ai_call_metadata", ["response_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_call_metadata_response_id", table_name="ai_call_metadata")
    op.drop_index("ix_ai_call_metadata_user_id", table_name="ai_call_metadata")
    op.drop_constraint("ai_call_metadata_user_id_fkey", "ai_call_metadata", type_="foreignkey")
    op.drop_column("ai_call_metadata", "response_id")
    op.drop_column("ai_call_metadata", "user_id")
