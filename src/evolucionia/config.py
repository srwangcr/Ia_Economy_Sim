from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    initial_agents: int = 60
    ticks: int = 120
    generation_length: int = 30
    initial_price: float = 10.0
    seed: int = 42
    resource_name: str = "ore"
    output_dir: Path = Path(".")


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///evolucionia_runs.db"),
        initial_agents=int(os.getenv("INITIAL_AGENTS", "60")),
        ticks=int(os.getenv("TICKS", "120")),
        generation_length=int(os.getenv("GENERATION_LENGTH", "30")),
        initial_price=float(os.getenv("INITIAL_PRICE", "10.0")),
        seed=int(os.getenv("SIMULATION_SEED", "42")),
        resource_name=os.getenv("RESOURCE_NAME", "ore"),
    )
