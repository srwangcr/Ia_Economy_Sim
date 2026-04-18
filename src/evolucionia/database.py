from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from uuid import uuid4

import pandas as pd
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, create_engine, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class SimulationRunRow(Base):
    __tablename__ = "simulation_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="running", index=True)
    seed: Mapped[int] = mapped_column(Integer)
    ticks: Mapped[int] = mapped_column(Integer)
    initial_agents: Mapped[int] = mapped_column(Integer)
    generation_length: Mapped[int] = mapped_column(Integer)
    initial_price: Mapped[float] = mapped_column(Float)
    resource_name: Mapped[str] = mapped_column(String(80))
    final_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_transactions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    surviving_agents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mean_wealth: Mapped[float | None] = mapped_column(Float, nullable=True)


class TransactionRow(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_run_tick", "run_id", "tick"),
        Index("ix_transactions_run_tick_buyer", "run_id", "tick", "buyer_id"),
        Index("ix_transactions_run_tick_seller", "run_id", "tick", "seller_id"),
        Index("ix_transactions_resource_price", "resource", "price"),
        {"postgresql_partition_by": "HASH (run_id)"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    tick: Mapped[int] = mapped_column(Integer, index=True)
    buyer_id: Mapped[int] = mapped_column(Integer, index=True)
    seller_id: Mapped[int] = mapped_column(Integer, index=True)
    resource: Mapped[str] = mapped_column(String(80), index=True)
    price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AgentSnapshotRow(Base):
    __tablename__ = "agent_snapshots"
    __table_args__ = (
        Index("ix_agent_snapshots_run_tick", "run_id", "tick"),
        Index("ix_agent_snapshots_run_agent", "run_id", "agent_id"),
        Index("ix_agent_snapshots_run_tick_agent", "run_id", "tick", "agent_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    tick: Mapped[int] = mapped_column(Integer, index=True)
    agent_id: Mapped[int] = mapped_column(Integer, index=True)
    species: Mapped[str] = mapped_column(String(32), index=True)
    balance: Mapped[float] = mapped_column(Float)
    inventory: Mapped[int] = mapped_column(Integer)
    energy: Mapped[float] = mapped_column(Float)
    risk_tolerance: Mapped[float] = mapped_column(Float)
    momentum_bias: Mapped[float] = mapped_column(Float)
    reproduction_drive: Mapped[float] = mapped_column(Float)
    alive: Mapped[bool] = mapped_column(Boolean, default=True)
    generation: Mapped[int] = mapped_column(Integer, default=0)


class MarketSnapshotRow(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (
        Index("ix_market_snapshots_run_tick", "run_id", "tick"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(36), index=True)
    tick: Mapped[int] = mapped_column(Integer, index=True)
    open_price: Mapped[float] = mapped_column(Float)
    high_price: Mapped[float] = mapped_column(Float)
    low_price: Mapped[float] = mapped_column(Float)
    close_price: Mapped[float] = mapped_column(Float)
    shock_factor: Mapped[float] = mapped_column(Float)
    buyers_count: Mapped[int] = mapped_column(Integer)
    sellers_count: Mapped[int] = mapped_column(Integer)
    active_agents: Mapped[int] = mapped_column(Integer)


def build_engine(database_url: str):
    return create_engine(database_url, future=True)


def session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db(engine) -> None:
    Base.metadata.create_all(engine)


def new_run_id() -> str:
    return uuid4().hex


def start_run(
    session: Session,
    *,
    run_id: str,
    seed: int,
    ticks: int,
    initial_agents: int,
    generation_length: int,
    initial_price: float,
    resource_name: str,
) -> None:
    session.add(
        SimulationRunRow(
            run_id=run_id,
            seed=seed,
            ticks=ticks,
            initial_agents=initial_agents,
            generation_length=generation_length,
            initial_price=initial_price,
            resource_name=resource_name,
        )
    )


def finalize_run(session: Session, run_id: str, summary: dict) -> None:
    session.execute(
        update(SimulationRunRow)
        .where(SimulationRunRow.run_id == run_id)
        .values(
            status="completed",
            completed_at=datetime.now(timezone.utc),
            final_price=summary.get("final_price"),
            total_transactions=summary.get("transactions"),
            surviving_agents=summary.get("alive"),
            mean_wealth=summary.get("mean_wealth"),
        )
    )


def save_tick(
    session: Session,
    run_id: str,
    tick: int,
    market_row: dict,
    transactions: Iterable[dict],
    agent_rows: Iterable[dict],
) -> None:
    session.add(MarketSnapshotRow(run_id=run_id, tick=tick, **market_row))
    for row in transactions:
        session.add(TransactionRow(run_id=run_id, tick=tick, **row))
    for row in agent_rows:
        session.add(AgentSnapshotRow(run_id=run_id, tick=tick, **row))


def _load_df(engine, stmt) -> pd.DataFrame:
    with engine.begin() as connection:
        return pd.read_sql(stmt, connection)


def load_simulation_runs(engine) -> pd.DataFrame:
    stmt = select(SimulationRunRow).order_by(SimulationRunRow.created_at.desc())
    return _load_df(engine, stmt)


def load_latest_run_id(engine) -> str | None:
    stmt = select(SimulationRunRow.run_id).order_by(SimulationRunRow.created_at.desc()).limit(1)
    dataframe = _load_df(engine, stmt)
    if dataframe.empty:
        return None
    return str(dataframe.iloc[0]["run_id"])


def _table_stmt(table, run_id: str | None = None):
    stmt = select(table)
    if run_id is not None and "run_id" in table.c:
        stmt = stmt.where(table.c.run_id == run_id)
    if "tick" in table.c:
        stmt = stmt.order_by(table.c.tick)
    return stmt


def load_transactions(engine, run_id: str | None = None) -> pd.DataFrame:
    return _load_df(engine, _table_stmt(TransactionRow.__table__, run_id))


def load_agent_snapshots(engine, run_id: str | None = None) -> pd.DataFrame:
    return _load_df(engine, _table_stmt(AgentSnapshotRow.__table__, run_id))


def load_market_snapshots(engine, run_id: str | None = None) -> pd.DataFrame:
    return _load_df(engine, _table_stmt(MarketSnapshotRow.__table__, run_id))