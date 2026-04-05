from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Any, Protocol, cast

from deap import base, creator, tools

from .models import Agent, Species


GENE_BOUNDS = [
    (1.5, 24.0),
    (2.0, 30.0),
    (1.0, 6.0),
    (0.05, 1.5),
    (0.05, 1.5),
    (0.05, 1.5),
]


def _ensure_deap_types() -> None:
    if not hasattr(creator, "FitnessAgent"):
        creator.create("FitnessAgent", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Genome"):
        creator.create("Genome", list, fitness=getattr(creator, "FitnessAgent"))

GenomeType = cast(type[list[float]], getattr(creator, "Genome"))


# Tipado para métodos registrados dinámicamente en Toolbox
class EvoToolbox(Protocol):
    def clone(self, x: list[float]) -> list[float]: ...
    def mate(self, x: list[float], y: list[float]) -> Any: ...
    def mutate(self, x: list[float]) -> Any: ...


_ensure_deap_types()

_CREATOR = cast(Any, creator)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_genes(genes: list[float]) -> list[float]:
    normalized: list[float] = []
    for index, value in enumerate(genes):
        lower, upper = GENE_BOUNDS[index]
        normalized.append(_clamp(float(value), lower, upper))
    return normalized


def build_toolbox(seed: int) -> base.Toolbox:
    rng = random.Random(seed)
    toolbox = base.Toolbox()
    toolbox.register("clone", lambda genome: _CREATOR.Genome(list(genome)))
    toolbox.register("mate", tools.cxBlend, alpha=0.35)
    toolbox.register("mutate", tools.mutGaussian, mu=0.0, sigma=0.18, indpb=0.45)
    toolbox.register("random", rng.random)
    return toolbox


def encode_agent(agent: Agent):
    genome = GenomeType(agent.gene_vector())
    return genome


def decode_agent(parent: Agent, genes: list[float], new_id: int) -> Agent:
    normalized = _normalize_genes(genes)
    buy_threshold, sell_threshold, production_rate, risk_tolerance, momentum_bias, reproduction_drive = normalized
    return Agent(
        agent_id=new_id,
        species=parent.species,
        balance=max(0.0, parent.balance * 0.18),
        inventory=0,
        energy=max(4.0, parent.energy * 0.72),
        buy_threshold=buy_threshold,
        sell_threshold=max(buy_threshold + 0.25, sell_threshold),
        production_rate=max(1, int(round(production_rate))),
        risk_tolerance=risk_tolerance,
        momentum_bias=momentum_bias,
        reproduction_drive=reproduction_drive,
        alive=True,
        generation=parent.generation + 1,
    )


def build_child(
    parent_a: Agent,
    parent_b: Agent,
    new_id: int,
    toolbox: base.Toolbox,
    rng: random.Random
) -> Agent:
    tb = cast(EvoToolbox, toolbox)

    genome_a = encode_agent(parent_a)
    genome_b = encode_agent(parent_b)
    child_a = tb.clone(genome_a)
    child_b = tb.clone(genome_b)
    tb.mate(child_a, child_b)
    if rng.random() < 0.85:
        tb.mutate(child_a)

    child_genes = _normalize_genes(list(child_a))
    dominant_parent = parent_a if parent_a.wealth(1.0) >= parent_b.wealth(1.0) else parent_b
    return decode_agent(dominant_parent, child_genes, new_id)


def rank_children(parents: list[Agent]) -> list[tuple[Agent, Agent]]:
    if len(parents) < 2:
        return []
    pairings: list[tuple[Agent, Agent]] = []
    pool = parents[:]
    for index, parent in enumerate(pool):
        partner = pool[(index + 1) % len(pool)]
        if parent.agent_id != partner.agent_id:
            pairings.append((parent, partner))
    return pairings