from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from .models import Agent, Decision


@dataclass(frozen=True)
class AgentDecision:
    agent_id: int
    decision: Decision


def _decide_payload(payload: tuple[Agent, float, float]) -> AgentDecision:
    agent, price, trend = payload
    return AgentDecision(agent_id=agent.agent_id, decision=agent.decide(price, trend))


class DecisionBackend(Protocol):
    def evaluate(self, agents: list[Agent], price: float, trend: float) -> list[AgentDecision]:
        ...

    def close(self) -> None:
        ...


class SerialDecisionBackend:
    def evaluate(self, agents: list[Agent], price: float, trend: float) -> list[AgentDecision]:
        return [_decide_payload((agent, price, trend)) for agent in agents]

    def close(self) -> None:
        return None


class ProcessDecisionBackend:
    def __init__(self, workers: int = 2):
        self.executor = ProcessPoolExecutor(max_workers=max(1, workers))

    def evaluate(self, agents: list[Agent], price: float, trend: float) -> list[AgentDecision]:
        payload = [(agent, price, trend) for agent in agents]
        return list(self.executor.map(_decide_payload, payload))

    def close(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=False)


def build_decision_backend(name: str, workers: int = 2) -> DecisionBackend:
    normalized = (name or "serial").strip().lower()
    if normalized == "process":
        return ProcessDecisionBackend(workers=workers)
    return SerialDecisionBackend()
