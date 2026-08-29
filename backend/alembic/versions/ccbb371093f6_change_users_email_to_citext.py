"""change users.email to CITEXT

Revision ID: ccbb371093f6
Revises: e8b260225eb1
Create Date: 2026-08-29 18:26:22.774531+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ccbb371093f6'
down_revision: Union[str, None] = 'e8b260225eb1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change users.email from plain TEXT to CITEXT for case-insensitive uniqueness.
    # The CITEXT extension was already created in migration e8b260225eb1.
    op.alter_column('users', 'email',
               existing_type=sa.TEXT(),
               type_=postgresql.CITEXT(),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # Revert CITEXT back to TEXT (removes case-insensitive uniqueness guarantee).
    op.alter_column('users', 'email',
               existing_type=postgresql.CITEXT(),
               type_=sa.TEXT(),
               existing_nullable=False)
    # ### end Alembic commands ###
