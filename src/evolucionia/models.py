from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
import random


class Species(str, Enum):
    MINER = "miner"
    SPECULATOR = "speculator"
    CONSUMER = "consumer"


Decision = Literal["buy", "sell", "both", "hold"]


def _low_membership(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.0
    return max(0.0, min(1.0, (threshold - value) / threshold))


def _high_membership(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 0.0
    return max(0.0, min(1.0, (value - threshold) / threshold))


def _trend_up(trend: float, price: float) -> float:
    if price <= 0:
        return 0.0
    return max(0.0, min(1.0, trend / price))


def _trend_down(trend: float, price: float) -> float:
    if price <= 0:
        return 0.0
    return max(0.0, min(1.0, (-trend) / price))


@dataclass
class Agent(ABC):
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

    @abstractmethod
    def decide(self, price: float, trend: float) -> Decision:
        raise NotImplementedError

    @abstractmethod
    def evolve(self, scarcity: float) -> None:
        raise NotImplementedError

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


@dataclass
class MinerAgent(Agent):
    species: Species = field(default=Species.MINER, init=False)

    def decide(self, price: float, trend: float) -> Decision:
        price_low = _low_membership(price, self.buy_threshold)
        price_high = _high_membership(price, self.sell_threshold)
        stock_high = _high_membership(float(self.inventory), 2.0)
        energy_low = _low_membership(self.energy, 10.0)
        trend_up = _trend_up(trend, price)

        sell_score = 0.5 * stock_high + 0.3 * price_high + 0.2 * energy_low
        buy_score = 0.35 * price_low + 0.25 * trend_up + 0.4 * (1.0 - self.risk_tolerance)
        if sell_score >= 0.4 and self.inventory > 0:
            return "sell"
        if buy_score >= 0.55 and self.balance >= price:
            return "buy"
        return "hold"

    def evolve(self, scarcity: float) -> None:
        self.energy = max(0.0, self.energy - scarcity * 0.2)
        self.production_rate = max(1, int(round(self.production_rate / max(0.8, scarcity))))
        self.reproduction_drive = max(0.05, self.reproduction_drive * (1 + (1 - scarcity) * 0.02))


@dataclass
class SpeculatorAgent(Agent):
    species: Species = field(default=Species.SPECULATOR, init=False)

    def decide(self, price: float, trend: float) -> Decision:
        price_low = _low_membership(price, self.buy_threshold)
        price_high = _high_membership(price, self.sell_threshold)
        trend_up = _trend_up(trend, price)
        trend_down = _trend_down(trend, price)

        buy_score = 0.4 * price_low + 0.35 * trend_up * self.momentum_bias + 0.25 * (1.0 - self.risk_tolerance)
        sell_score = 0.45 * price_high + 0.35 * trend_down * (1.25 - self.momentum_bias) + 0.2 * self.risk_tolerance
        can_buy = buy_score >= 0.48 and self.balance >= price
        can_sell = sell_score >= 0.48 and self.inventory > 0
        if can_buy and can_sell:
            return "both"
        if can_buy:
            return "buy"
        if can_sell:
            return "sell"
        return "hold"

    def evolve(self, scarcity: float) -> None:
        self.buy_threshold = max(0.5, self.buy_threshold * (1 + scarcity * 0.02))
        self.sell_threshold = max(self.buy_threshold + 0.1, self.sell_threshold * (1 + scarcity * 0.01))
        self.momentum_bias = min(1.5, max(0.05, self.momentum_bias * (1 + (scarcity - 1.0) * 0.03)))


@dataclass
class ConsumerAgent(Agent):
    species: Species = field(default=Species.CONSUMER, init=False)

    def decide(self, price: float, trend: float) -> Decision:
        price_low = _low_membership(price, self.buy_threshold)
        stock_low = _low_membership(float(self.inventory), 2.0)
        energy_low = _low_membership(self.energy, 10.0)
        buy_score = 0.45 * price_low + 0.35 * stock_low + 0.2 * energy_low
        if buy_score >= 0.42 and self.balance >= price:
            return "buy"
        return "hold"

    def evolve(self, scarcity: float) -> None:
        self.energy = max(0.0, self.energy - scarcity * 0.1)
        self.risk_tolerance = max(0.05, self.risk_tolerance * (1 + scarcity * 0.01))


def create_agent(
    *,
    agent_id: int,
    species: Species,
    balance: float,
    inventory: int,
    energy: float,
    buy_threshold: float,
    sell_threshold: float,
    production_rate: int = 1,
    risk_tolerance: float = 0.5,
    momentum_bias: float = 0.5,
    reproduction_drive: float = 0.5,
    alive: bool = True,
    generation: int = 0,
) -> Agent:
    payload = {
        "agent_id": agent_id,
        "balance": balance,
        "inventory": inventory,
        "energy": energy,
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold,
        "production_rate": production_rate,
        "risk_tolerance": risk_tolerance,
        "momentum_bias": momentum_bias,
        "reproduction_drive": reproduction_drive,
        "alive": alive,
        "generation": generation,
    }
    if species == Species.MINER:
        return MinerAgent(**payload)
    if species == Species.SPECULATOR:
        return SpeculatorAgent(**payload)
    return ConsumerAgent(**payload)

