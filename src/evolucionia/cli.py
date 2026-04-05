from __future__ import annotations

import argparse

from .config import Settings, load_settings
from .database import build_engine, init_db, session_factory
from .simulation import SimulationEngine


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evolucionia")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run the market simulation")
    run_parser.add_argument("--ticks", type=int, default=None)
    run_parser.add_argument("--agents", type=int, default=None)
    run_parser.add_argument("--seed", type=int, default=None)
    run_parser.add_argument("--database-url", type=str, default=None)
    run_parser.add_argument("--initial-price", type=float, default=None)
    return parser


def _resolve_settings(args: argparse.Namespace) -> Settings:
    base = load_settings()
    return Settings(
        database_url=args.database_url or base.database_url,
        initial_agents=args.agents or base.initial_agents,
        ticks=args.ticks or base.ticks,
        generation_length=base.generation_length,
        initial_price=args.initial_price or base.initial_price,
        seed=args.seed or base.seed,
        resource_name=base.resource_name,
        output_dir=base.output_dir,
    )


def run_simulation(args: argparse.Namespace) -> dict:
    settings = _resolve_settings(args)
    engine = build_engine(settings.database_url)
    init_db(engine)
    session = session_factory(engine)()
    try:
        simulation = SimulationEngine(settings, session)
        simulation.run(settings.ticks)
        return simulation.summary()
    finally:
        session.close()


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        summary = run_simulation(args)
        print("Simulation complete")
        for key, value in summary.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
