from __future__ import annotations

from pathlib import Path

from evolucionia.config import Settings
from evolucionia.database import (
    build_engine,
    init_db,
    load_agent_snapshots,
    load_market_snapshots,
    load_simulation_runs,
    load_transactions,
    session_factory,
)
from evolucionia.simulation import SimulationEngine


def make_settings(database_url: str) -> Settings:
    return Settings(
        database_url=database_url,
        initial_agents=12,
        ticks=8,
        generation_length=4,
        initial_price=10.0,
        seed=11,
        resource_name="ore",
    )


def test_simulation_creates_run_and_snapshots(tmp_path: Path) -> None:
    db_path = tmp_path / "simulation.db"
    engine = build_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session = session_factory(engine)()
    try:
        simulation = SimulationEngine(make_settings(f"sqlite:///{db_path}"), session)
        summary = simulation.run(6)

        assert len(summary) == 6
        assert simulation.summary()["run_id"]

        runs_df = load_simulation_runs(engine)
        market_df = load_market_snapshots(engine)
        agent_df = load_agent_snapshots(engine)
        transaction_df = load_transactions(engine)

        assert len(runs_df) == 1
        assert runs_df.iloc[0]["status"] == "completed"
        assert len(market_df) == 6
        assert not agent_df.empty
        assert transaction_df["run_id"].nunique() == 1
        assert transaction_df["run_id"].iloc[0] == simulation.run_id
    finally:
        session.close()


def test_simulation_summary_reports_consistent_counts(tmp_path: Path) -> None:
    db_path = tmp_path / "summary.db"
    engine = build_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session = session_factory(engine)()
    try:
        simulation = SimulationEngine(make_settings(f"sqlite:///{db_path}"), session)
        simulation.run(4)
        summary = simulation.summary()

        assert summary["agents"] >= summary["alive"]
        assert summary["transactions"] >= 0
        assert summary["final_price"] > 0
        assert summary["run_id"] == simulation.run_id
    finally:
        session.close()