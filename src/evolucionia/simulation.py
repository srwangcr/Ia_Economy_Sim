from __future__ import annotations

from dataclasses import dataclass
import random
from statistics import mean

from sqlalchemy.orm import Session

from .config import Settings
from .database import finalize_run, init_db, new_run_id, save_tick, start_run
from .genetics import build_child, build_toolbox, rank_children
from .models import Agent, Species, create_agent
from .scaling import build_decision_backend


@dataclass
class TickResult:
    tick: int
    price: float
    transactions: int
    buyers: int
    sellers: int
    survivors: int


class SimulationEngine:
    def __init__(self, settings: Settings, session: Session):
        self.settings = settings
        self.session = session
        self.rng = random.Random(settings.seed)
        self.agents = self._create_agents(settings.initial_agents)
        self.next_agent_id = settings.initial_agents + 1
        self.price = settings.initial_price
        self.tick_results: list[TickResult] = []
        self.generation_index = 0
        self.run_id = new_run_id()
        self.toolbox = build_toolbox(settings.seed)
        self.decision_backend = build_decision_backend(settings.compute_backend, settings.compute_workers)

    def _create_agents(self, count: int) -> list[Agent]:
        species_cycle = [Species.MINER, Species.SPECULATOR, Species.CONSUMER]
        agents: list[Agent] = []
        for agent_id in range(1, count + 1):
            species = species_cycle[(agent_id - 1) % len(species_cycle)]
            if species == Species.MINER:
                balance, inventory, energy = 45.0, 2, 12.0
                buy_threshold, sell_threshold, production_rate = 9.5, 14.0, 2
                risk_tolerance, momentum_bias, reproduction_drive = 0.35, 0.55, 0.85
            elif species == Species.SPECULATOR:
                balance, inventory, energy = 60.0, 1, 10.0
                buy_threshold, sell_threshold, production_rate = 8.5, 13.5, 1
                risk_tolerance, momentum_bias, reproduction_drive = 0.8, 0.9, 0.55
            else:
                balance, inventory, energy = 35.0, 0, 14.0
                buy_threshold, sell_threshold, production_rate = 10.5, 15.5, 1
                risk_tolerance, momentum_bias, reproduction_drive = 0.2, 0.35, 0.45
            agents.append(
                create_agent(
                    agent_id=agent_id,
                    species=species,
                    balance=balance,
                    inventory=inventory,
                    energy=energy,
                    buy_threshold=buy_threshold,
                    sell_threshold=sell_threshold,
                    production_rate=production_rate,
                    risk_tolerance=risk_tolerance,
                    momentum_bias=momentum_bias,
                    reproduction_drive=reproduction_drive,
                )
            )
        return agents

    def _macro_shock(self, tick: int) -> float:
        if tick % 40 == 0 and tick > 0:
            return 1.25
        if tick % 27 == 0 and tick > 0:
            return 0.88
        if tick % 19 == 0 and tick > 0:
            return 1.08
        return 1.0

    def _alive_agents(self) -> list[Agent]:
        return [agent for agent in self.agents if agent.alive]

    def _produce_resources(self, scarcity: float) -> None:
        for agent in self._alive_agents():
            agent.evolve(scarcity)
            if agent.species == Species.MINER and agent.energy > 0:
                produced = max(1, int(round(agent.production_rate / max(0.75, scarcity))))
                agent.inventory += produced
                agent.energy = max(0.0, agent.energy - 1.25 * scarcity)
            elif agent.species == Species.CONSUMER:
                if agent.inventory > 0:
                    agent.inventory -= 1
                    agent.energy = min(20.0, agent.energy + 2.5)
                else:
                    agent.energy = max(0.0, agent.energy - 2.0 * scarcity)
            else:
                agent.energy = max(0.0, agent.energy - 0.6 * scarcity)

            if agent.energy <= 0 and agent.species != Species.SPECULATOR and agent.inventory <= 0:
                agent.alive = False

    def _intent_lists(self, price: float, trend: float) -> tuple[list[Agent], list[Agent]]:
        buyers: list[Agent] = []
        sellers: list[Agent] = []
        alive = self._alive_agents()
        decision_rows = self.decision_backend.evaluate(alive, price, trend)
        by_id = {agent.agent_id: agent for agent in alive}
        for row in decision_rows:
            agent = by_id.get(row.agent_id)
            if agent is None:
                continue
            decision = row.decision
            if decision in ("buy", "both"):
                buyers.append(agent)
            if decision in ("sell", "both"):
                sellers.append(agent)

        return buyers, sellers

    def _pick_counterparty(self, source: Agent, candidates: list[Agent]) -> Agent | None:
        viable = [agent for agent in candidates if agent.agent_id != source.agent_id]
        if not viable:
            return None
        return self.rng.choice(viable)

    def _execute_market(self, price: float, buyers: list[Agent], sellers: list[Agent]) -> list[dict]:
        transactions: list[dict] = []
        buyer_pool = buyers[:]
        seller_pool = sellers[:]
        self.rng.shuffle(buyer_pool)
        self.rng.shuffle(seller_pool)

        for buyer in buyer_pool:
            seller = self._pick_counterparty(buyer, seller_pool)
            if seller is None:
                continue
            if buyer.balance < price or seller.inventory <= 0:
                continue

            buyer.balance -= price
            buyer.inventory += 1
            seller.balance += price
            seller.inventory -= 1
            transactions.append(
                {
                    "buyer_id": buyer.agent_id,
                    "seller_id": seller.agent_id,
                    "resource": self.settings.resource_name,
                    "price": round(price, 4),
                    "quantity": 1,
                }
            )

            if seller.inventory <= 0:
                seller_pool = [agent for agent in seller_pool if agent.agent_id != seller.agent_id]
            if buyer.balance < price:
                buyer_pool = [agent for agent in buyer_pool if agent.agent_id != buyer.agent_id]

        return transactions

    def _price_update(self, base_price: float, buyers: list[Agent], sellers: list[Agent], shock: float) -> float:
        pressure = len(buyers) - len(sellers)
        alive_count = max(1, len(self._alive_agents()))
        swing = 0.04 * pressure / alive_count
        updated = base_price * (1 + swing) * shock
        return max(0.75, min(250.0, updated))

    def _select_elite(self, alive_agents: list[Agent]) -> list[Agent]:
        ranked = sorted(alive_agents, key=lambda agent: agent.wealth(self.price), reverse=True)
        elite_count = max(4, len(ranked) // 3)
        return [agent for agent in ranked[:elite_count] if agent.wealth(self.price) >= 85.0]

    def _maybe_reproduce(self) -> None:
        alive = self._alive_agents()
        if len(alive) < 2:
            return

        elite = self._select_elite(alive)
        if len(elite) < 2:
            return

        pairings = rank_children(elite)
        if not pairings:
            return

        target_children = max(1, min(6, int(round(sum(agent.reproduction_drive for agent in elite) / len(elite)))))
        children: list[Agent] = []

        for index in range(target_children):
            parent_a, parent_b = pairings[index % len(pairings)]
            likelihood = min(0.95, (parent_a.reproduction_drive + parent_b.reproduction_drive) / 2.2)
            if self.rng.random() > likelihood:
                continue
            child = build_child(parent_a, parent_b, self.next_agent_id, self.toolbox, self.rng)
            self.next_agent_id += 1
            parent_a.balance *= 0.9
            parent_b.balance *= 0.95
            children.append(child)

        self.agents.extend(children)

    def _remove_extinct_agents(self) -> None:
        for agent in self.agents:
            if agent.alive and agent.balance <= 0 and agent.inventory <= 0 and agent.energy <= 0:
                agent.alive = False

    def _agent_rows(self) -> list[dict]:
        return [
            {
                "agent_id": agent.agent_id,
                "species": agent.species.value,
                "balance": round(agent.balance, 4),
                "inventory": agent.inventory,
                "energy": round(agent.energy, 4),
                "risk_tolerance": round(agent.risk_tolerance, 4),
                "momentum_bias": round(agent.momentum_bias, 4),
                "reproduction_drive": round(agent.reproduction_drive, 4),
                "alive": agent.alive,
                "generation": agent.generation,
            }
            for agent in self.agents
        ]

    def run(self, ticks: int | None = None) -> list[TickResult]:
        init_db(self.session.get_bind())
        total_ticks = ticks or self.settings.ticks
        start_run(
            self.session,
            run_id=self.run_id,
            seed=self.settings.seed,
            ticks=total_ticks,
            initial_agents=self.settings.initial_agents,
            generation_length=self.settings.generation_length,
            initial_price=self.settings.initial_price,
            resource_name=self.settings.resource_name,
        )
        self.session.commit()

        previous_close = self.price
        last_close = self.price

        try:
            for tick in range(1, total_ticks + 1):
                shock = self._macro_shock(tick)
                self._produce_resources(shock)
                alive_agents = self._alive_agents()
                trend = previous_close - last_close
                buyers, sellers = self._intent_lists(previous_close, trend)
                open_price = previous_close
                close_price = self._price_update(previous_close, buyers, sellers, shock)
                transactions = self._execute_market(close_price, buyers, sellers)
                price_candidates = [open_price, close_price, *(transaction["price"] for transaction in transactions)]
                high_price = max(price_candidates)
                low_price = min(price_candidates)
                market_row = {
                    "open_price": round(open_price, 4),
                    "high_price": round(high_price, 4),
                    "low_price": round(low_price, 4),
                    "close_price": round(close_price, 4),
                    "shock_factor": round(shock, 4),
                    "buyers_count": len(buyers),
                    "sellers_count": len(sellers),
                    "active_agents": len(alive_agents),
                }
                self.price = close_price
                self.tick_results.append(
                    TickResult(
                        tick=tick,
                        price=close_price,
                        transactions=len(transactions),
                        buyers=len(buyers),
                        sellers=len(sellers),
                        survivors=len(alive_agents),
                    )
                )
                save_tick(self.session, self.run_id, tick, market_row, transactions, self._agent_rows())
                self.session.commit()
                last_close = previous_close
                previous_close = close_price

                self._remove_extinct_agents()
                if tick % self.settings.generation_length == 0:
                    self._maybe_reproduce()
                    self.generation_index += 1
        finally:
            self.decision_backend.close()

        summary = self.summary()
        finalize_run(self.session, self.run_id, summary)
        self.session.commit()
        return self.tick_results

    def summary(self) -> dict:
        alive = self._alive_agents()
        wealths = [agent.wealth(self.price) for agent in alive]
        return {
            "run_id": self.run_id,
            "agents": len(self.agents),
            "alive": len(alive),
            "final_price": round(self.price, 4),
            "mean_wealth": round(mean(wealths), 4) if wealths else 0.0,
            "generations": self.generation_index,
            "transactions": sum(result.transactions for result in self.tick_results),
        }