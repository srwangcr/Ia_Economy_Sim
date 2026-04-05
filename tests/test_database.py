from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect

from evolucionia.database import build_engine, init_db


def test_init_db_creates_run_scoped_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "schema.db"
    engine = build_engine(f"sqlite:///{db_path}")
    init_db(engine)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {"simulation_runs", "transactions", "agent_snapshots", "market_snapshots"}.issubset(tables)