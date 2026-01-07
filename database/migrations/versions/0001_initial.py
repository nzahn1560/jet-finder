"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2024-08-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("force_password_reset", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "performance_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("manufacturer", sa.String(), nullable=False),
        sa.Column("engine_type", sa.String(), nullable=False),
        sa.Column("range_nm", sa.Integer(), nullable=False),
        sa.Column("cruise_speed_knots", sa.Integer(), nullable=False),
        sa.Column("max_passengers", sa.Integer(), nullable=False),
        sa.Column("max_altitude_ft", sa.Integer(), nullable=False),
        sa.Column("cabin_volume_cuft", sa.Float(), nullable=True),
        sa.Column("baggage_volume_cuft", sa.Float(), nullable=True),
        sa.Column("runway_requirement_ft", sa.Integer(), nullable=True),
        sa.Column("hourly_cost_usd", sa.Float(), nullable=True),
        sa.Column("annual_maintenance_usd", sa.Float(), nullable=True),
        sa.Column("purchase_price_usd", sa.Float(), nullable=True),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "pricing_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("price_usd", sa.Integer(), nullable=False),
        sa.Column("billing_cycle_months", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price_usd", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("engine_type", sa.String(), nullable=False),
        sa.Column("contact_email", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("payment_plan", sa.String(), nullable=False, server_default="monthly"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("rejected_reason", sa.String(), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("performance_profile_id", sa.Integer(), sa.ForeignKey("performance_profiles.id"), nullable=True),
        sa.Column("pricing_plan_id", sa.Integer(), sa.ForeignKey("pricing_plans.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("listings")
    op.drop_table("pricing_plans")
    op.drop_table("performance_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

