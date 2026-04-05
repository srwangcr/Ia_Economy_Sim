"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-05 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("run_id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("ticks", sa.Integer(), nullable=False),
        sa.Column("initial_agents", sa.Integer(), nullable=False),
        sa.Column("generation_length", sa.Integer(), nullable=False),
        sa.Column("initial_price", sa.Float(), nullable=False),
        sa.Column("resource_name", sa.String(length=80), nullable=False),
        sa.Column("final_price", sa.Float(), nullable=True),
        sa.Column("total_transactions", sa.Integer(), nullable=True),
        sa.Column("surviving_agents", sa.Integer(), nullable=True),
        sa.Column("mean_wealth", sa.Float(), nullable=True),
        if_not_exists=True,
    )
    op.create_index(op.f("ix_simulation_runs_created_at"), "simulation_runs", ["created_at"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_simulation_runs_status"), "simulation_runs", ["status"], unique=False, if_not_exists=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("resource", sa.String(length=80), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_transactions_resource_price", "transactions", ["resource", "price"], unique=False, if_not_exists=True)
    op.create_index("ix_transactions_run_tick", "transactions", ["run_id", "tick"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_transactions_run_id"), "transactions", ["run_id"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_transactions_tick"), "transactions", ["tick"], unique=False, if_not_exists=True)

    op.create_table(
        "agent_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("species", sa.String(length=32), nullable=False),
        sa.Column("balance", sa.Float(), nullable=False),
        sa.Column("inventory", sa.Integer(), nullable=False),
        sa.Column("energy", sa.Float(), nullable=False),
        sa.Column("risk_tolerance", sa.Float(), nullable=False),
        sa.Column("momentum_bias", sa.Float(), nullable=False),
        sa.Column("reproduction_drive", sa.Float(), nullable=False),
        sa.Column("alive", sa.Boolean(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_agent_snapshots_run_agent", "agent_snapshots", ["run_id", "agent_id"], unique=False, if_not_exists=True)
    op.create_index("ix_agent_snapshots_run_tick", "agent_snapshots", ["run_id", "tick"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_agent_snapshots_run_id"), "agent_snapshots", ["run_id"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_agent_snapshots_tick"), "agent_snapshots", ["tick"], unique=False, if_not_exists=True)

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("tick", sa.Integer(), nullable=False),
        sa.Column("open_price", sa.Float(), nullable=False),
        sa.Column("high_price", sa.Float(), nullable=False),
        sa.Column("low_price", sa.Float(), nullable=False),
        sa.Column("close_price", sa.Float(), nullable=False),
        sa.Column("shock_factor", sa.Float(), nullable=False),
        sa.Column("buyers_count", sa.Integer(), nullable=False),
        sa.Column("sellers_count", sa.Integer(), nullable=False),
        sa.Column("active_agents", sa.Integer(), nullable=False),
        if_not_exists=True,
    )
    op.create_index("ix_market_snapshots_run_tick", "market_snapshots", ["run_id", "tick"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_market_snapshots_run_id"), "market_snapshots", ["run_id"], unique=False, if_not_exists=True)
    op.create_index(op.f("ix_market_snapshots_tick"), "market_snapshots", ["tick"], unique=False, if_not_exists=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_market_snapshots_tick"), table_name="market_snapshots")
    op.drop_index(op.f("ix_market_snapshots_run_id"), table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_run_tick", table_name="market_snapshots")
    op.drop_table("market_snapshots")

    op.drop_index(op.f("ix_agent_snapshots_tick"), table_name="agent_snapshots")
    op.drop_index(op.f("ix_agent_snapshots_run_id"), table_name="agent_snapshots")
    op.drop_index("ix_agent_snapshots_run_tick", table_name="agent_snapshots")
    op.drop_index("ix_agent_snapshots_run_agent", table_name="agent_snapshots")
    op.drop_table("agent_snapshots")

    op.drop_index(op.f("ix_transactions_tick"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_run_id"), table_name="transactions")
    op.drop_index("ix_transactions_run_tick", table_name="transactions")
    op.drop_index("ix_transactions_resource_price", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index(op.f("ix_simulation_runs_status"), table_name="simulation_runs")
    op.drop_index(op.f("ix_simulation_runs_created_at"), table_name="simulation_runs")
    op.drop_table("simulation_runs")