from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random


class Species(str, Enum):
    MINER = "miner"
    SPECULATOR = "speculator"
    CONSUMER = "consumer"


@dataclass
class Agent:
    agent_id: int
    species: Species
    balance: float
    inventory: int
    energy: float
    buy_threshold: float
    sell_threshold: float
    production_rate: int = 1
    risk_tolerance: float = 0.5
    momentum_bias: float = 0.5
    reproduction_drive: float = 0.5
    alive: bool = True
    generation: int = 0

    def wealth(self, price: float) -> float:
        return self.balance + self.inventory * price

    def gene_vector(self) -> list[float]:
        return [
            self.buy_threshold,
            self.sell_threshold,
            float(self.production_rate),
            self.risk_tolerance,
            self.momentum_bias,
            self.reproduction_drive,
        ]

    def species_bias(self) -> float:
        if self.species == Species.MINER:
            return 0.8
        if self.species == Species.CONSUMER:
            return 0.35
        return 0.6

    def mutate_child(self, new_id: int) -> "Agent":
        def jitter(value: float, spread: float) -> float:
            return max(0.5, value * random.uniform(1 - spread, 1 + spread))

        return Agent(
            agent_id=new_id,
            species=self.species,
            balance=max(0.0, self.balance * 0.2),
            inventory=0,
            energy=max(5.0, self.energy * 0.75),
            buy_threshold=jitter(self.buy_threshold, 0.15),
            sell_threshold=jitter(self.sell_threshold, 0.15),
            production_rate=max(1, int(round(jitter(self.production_rate, 0.2)))),
            risk_tolerance=min(1.5, max(0.05, jitter(self.risk_tolerance, 0.2))),
            momentum_bias=min(1.5, max(0.05, jitter(self.momentum_bias, 0.2))),
            reproduction_drive=min(1.5, max(0.05, jitter(self.reproduction_drive, 0.2))),
            alive=True,
            generation=self.generation + 1,
        )

    def apply_macro_pressure(self, scarcity: float) -> None:
        if self.species == Species.MINER:
            self.energy = max(0.0, self.energy - scarcity * 0.2)
            self.production_rate = max(1, int(round(self.production_rate / max(0.8, scarcity))))
            self.reproduction_drive = max(0.05, self.reproduction_drive * (1 + (1 - scarcity) * 0.02))
        elif self.species == Species.CONSUMER:
            self.energy = max(0.0, self.energy - scarcity * 0.1)
            self.risk_tolerance = max(0.05, self.risk_tolerance * (1 + scarcity * 0.01))
        else:
            self.buy_threshold = max(0.5, self.buy_threshold * (1 + scarcity * 0.02))
            self.sell_threshold = max(self.buy_threshold + 0.1, self.sell_threshold * (1 + scarcity * 0.01))
            self.momentum_bias = min(1.5, max(0.05, self.momentum_bias * (1 + (scarcity - 1.0) * 0.03)))
