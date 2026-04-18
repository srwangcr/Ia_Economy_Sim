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
from evolucionia.models import ConsumerAgent, MinerAgent, SpeculatorAgent, Species, create_agent
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


def test_elite_selection_returns_top_wealthy_agents(tmp_path: Path) -> None:
    db_path = tmp_path / "elite.db"
    engine = build_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session = session_factory(engine)()
    try:
        simulation = SimulationEngine(make_settings(f"sqlite:///{db_path}"), session)
        simulation.price = 10.0
        simulation.agents = [
            create_agent(agent_id=1, species=Species.MINER, balance=220.0, inventory=2, energy=10.0, buy_threshold=9.0, sell_threshold=13.0, reproduction_drive=1.0),
            create_agent(agent_id=2, species=Species.SPECULATOR, balance=200.0, inventory=1, energy=10.0, buy_threshold=8.5, sell_threshold=13.5, reproduction_drive=0.9),
            create_agent(agent_id=3, species=Species.CONSUMER, balance=180.0, inventory=1, energy=10.0, buy_threshold=10.0, sell_threshold=15.0, reproduction_drive=0.85),
            create_agent(agent_id=4, species=Species.MINER, balance=160.0, inventory=2, energy=10.0, buy_threshold=9.5, sell_threshold=14.0, reproduction_drive=0.8),
            create_agent(agent_id=5, species=Species.SPECULATOR, balance=20.0, inventory=0, energy=10.0, buy_threshold=8.0, sell_threshold=13.0, reproduction_drive=0.5),
            create_agent(agent_id=6, species=Species.CONSUMER, balance=10.0, inventory=0, energy=10.0, buy_threshold=11.0, sell_threshold=16.0, reproduction_drive=0.4),
        ]

        elite = simulation._select_elite(simulation._alive_agents())
        elite_ids = {agent.agent_id for agent in elite}

        assert len(elite) == 4
        assert elite_ids == {1, 2, 3, 4}
    finally:
        session.close()


def test_fuzzy_decisions_return_expected_actions() -> None:
    miner = MinerAgent(
        agent_id=1,
        balance=100.0,
        inventory=4,
        energy=4.0,
        buy_threshold=9.5,
        sell_threshold=12.0,
        production_rate=2,
        risk_tolerance=0.3,
        momentum_bias=0.5,
        reproduction_drive=0.8,
    )
    assert miner.decide(price=13.0, trend=0.2) == "sell"

    consumer = ConsumerAgent(
        agent_id=2,
        balance=50.0,
        inventory=0,
        energy=6.0,
        buy_threshold=11.0,
        sell_threshold=15.0,
        production_rate=1,
        risk_tolerance=0.2,
        momentum_bias=0.4,
        reproduction_drive=0.5,
    )
    assert consumer.decide(price=8.0, trend=0.0) == "buy"

    speculator = SpeculatorAgent(
        agent_id=3,
        balance=20.0,
        inventory=2,
        energy=10.0,
        buy_threshold=9.0,
        sell_threshold=10.5,
        production_rate=1,
        risk_tolerance=0.9,
        momentum_bias=0.2,
        reproduction_drive=0.5,
    )
    assert speculator.decide(price=20.0, trend=-8.0) == "sell"


def test_evolution_can_improve_average_wealth(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "evolution_gain.db"
    engine = build_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session = session_factory(engine)()
    try:
        simulation = SimulationEngine(make_settings(f"sqlite:///{db_path}"), session)
        simulation.price = 10.0
        simulation.agents = [
            create_agent(agent_id=1, species=Species.MINER, balance=220.0, inventory=2, energy=10.0, buy_threshold=9.0, sell_threshold=13.0, reproduction_drive=1.5),
            create_agent(agent_id=2, species=Species.MINER, balance=210.0, inventory=2, energy=10.0, buy_threshold=9.0, sell_threshold=13.0, reproduction_drive=1.5),
            create_agent(agent_id=3, species=Species.SPECULATOR, balance=195.0, inventory=2, energy=10.0, buy_threshold=8.5, sell_threshold=12.5, reproduction_drive=1.4),
            create_agent(agent_id=4, species=Species.CONSUMER, balance=190.0, inventory=2, energy=10.0, buy_threshold=10.0, sell_threshold=14.5, reproduction_drive=1.4),
        ]
        simulation.next_agent_id = 5

        before = sum(agent.wealth(simulation.price) for agent in simulation.agents) / len(simulation.agents)

        def wealthy_child(parent_a, parent_b, new_id, toolbox, rng):
            return create_agent(
                agent_id=new_id,
                species=parent_a.species,
                balance=parent_a.balance * 1.2,
                inventory=1,
                energy=8.0,
                buy_threshold=parent_a.buy_threshold,
                sell_threshold=parent_a.sell_threshold,
                production_rate=parent_a.production_rate,
                risk_tolerance=parent_a.risk_tolerance,
                momentum_bias=parent_a.momentum_bias,
                reproduction_drive=parent_a.reproduction_drive,
                generation=parent_a.generation + 1,
            )

        monkeypatch.setattr("evolucionia.simulation.build_child", wealthy_child)
        simulation._maybe_reproduce()

        after = sum(agent.wealth(simulation.price) for agent in simulation.agents) / len(simulation.agents)
        assert after > before
    finally:
        session.close()