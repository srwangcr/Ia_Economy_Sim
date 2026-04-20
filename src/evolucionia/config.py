from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    read_database_url: str | None = None
    initial_agents: int = 60
    ticks: int = 120
    generation_length: int = 30
    initial_price: float = 10.0
    seed: int = 42
    resource_name: str = "ore"
    compute_backend: str = "serial"
    compute_workers: int = 2
    output_dir: Path = Path(".")


def load_settings() -> Settings:
    read_database_url = os.getenv("READ_DATABASE_URL")
    compute_workers = int(os.getenv("COMPUTE_WORKERS", "2"))
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///evolucionia_runs.db"),
        read_database_url=read_database_url or None,
        initial_agents=int(os.getenv("INITIAL_AGENTS", "60")),
        ticks=int(os.getenv("TICKS", "120")),
        generation_length=int(os.getenv("GENERATION_LENGTH", "30")),
        initial_price=float(os.getenv("INITIAL_PRICE", "10.0")),
        seed=int(os.getenv("SIMULATION_SEED", "42")),
        resource_name=os.getenv("RESOURCE_NAME", "ore"),
        compute_backend=os.getenv("COMPUTE_BACKEND", "serial").strip().lower() or "serial",
        compute_workers=max(1, compute_workers),
    )
