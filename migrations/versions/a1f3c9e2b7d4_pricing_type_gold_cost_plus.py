"""products.pricing_type: GOLD_COST_PLUS için kolon 10 → 20 karakter

Revision ID: a1f3c9e2b7d4
Revises: dc757c9582c5
Create Date: 2026-11-08 19:30:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f3c9e2b7d4"
down_revision: str | Sequence[str] | None = "dc757c9582c5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = sa.Enum("FIXED", "GOLD", name="pricingtype", native_enum=False, length=10)
NEW = sa.Enum("FIXED", "GOLD", "GOLD_COST_PLUS", name="pricingtype", native_enum=False, length=20)


def upgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column("pricing_type", existing_type=OLD, type_=NEW, existing_nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("products") as batch_op:
        batch_op.alter_column("pricing_type", existing_type=NEW, type_=OLD, existing_nullable=False)
