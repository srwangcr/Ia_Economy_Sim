from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _build_alembic_config(tmp_path: Path) -> Config:
    project_root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "migration_test.db"

    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return config


def test_alembic_upgrade_and_downgrade_roundtrip(tmp_path: Path) -> None:
    config = _build_alembic_config(tmp_path)

    command.upgrade(config, "head")

    db_url = config.get_main_option("sqlalchemy.url")
    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"simulation_runs", "transactions", "agent_snapshots", "market_snapshots"}.issubset(tables)

    command.downgrade(config, "base")
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) <= {"alembic_version"}
