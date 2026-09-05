"""add slack_links table

Revision ID: 0d247978a39d
Revises: b87416c6768d
Create Date: 2026-09-05 09:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0d247978a39d"
down_revision: Union[str, None] = "b87416c6768d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slack_links",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("slack_user_id", sa.Text(), unique=True, nullable=False),
        sa.Column(
            "api_token_id",
            UUID(as_uuid=True),
            sa.ForeignKey("api_tokens.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_slack_links_api_token_id",
        "slack_links",
        ["api_token_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_slack_links_api_token_id", table_name="slack_links")
    op.drop_table("slack_links")
