"""merge

Revision ID: babbc400623f
Revises: 0d247978a39d, d9d6c2c804e7
Create Date: 2026-09-05 11:10:32.623100+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'babbc400623f'
down_revision: Union[str, None] = ('0d247978a39d', 'd9d6c2c804e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
