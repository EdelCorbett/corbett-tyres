"""add statement locks

Revision ID: 1d4e71825e59
Revises: e358627a3290
Create Date: 2026-02-10 10:40:15.048138

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d4e71825e59'
down_revision: Union[str, Sequence[str], None] = 'e358627a3290'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "statement_locks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "customer_id", "month", "year",
            name="uq_statement_lock"
        ),
    )



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("statement_locks")
