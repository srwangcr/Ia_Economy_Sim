from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestMetrics:
    aligned_points: int
    mape_price: float
    mean_return_gap: float
    volatility_gap: float
    directional_accuracy: float
    ks_distance: float
    composite_score: float


def _pick_price_column(dataframe: pd.DataFrame) -> str:
    candidates = ["close", "Close", "price", "Price", "close_price"]
    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate
    raise ValueError("El dataset de referencia debe incluir una columna de precio de cierre (close/price).")


def _safe_returns(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    clean = clean[clean > 0]
    if clean.empty:
        return pd.Series(dtype=float)
    return np.log(clean).diff().dropna()


def _ks_distance(a: pd.Series, b: pd.Series) -> float:
    if a.empty or b.empty:
        return 1.0
    a_values = np.sort(a.to_numpy())
    b_values = np.sort(b.to_numpy())
    merged = np.sort(np.concatenate([a_values, b_values]))
    cdf_a = np.searchsorted(a_values, merged, side="right") / len(a_values)
    cdf_b = np.searchsorted(b_values, merged, side="right") / len(b_values)
    return float(np.max(np.abs(cdf_a - cdf_b)))


def compare_market_series(simulated_market: pd.DataFrame, real_market: pd.DataFrame) -> BacktestMetrics:
    if simulated_market.empty:
        raise ValueError("No hay snapshots de mercado simulados para validar.")

    sim_prices = pd.to_numeric(simulated_market["close_price"], errors="coerce").dropna().reset_index(drop=True)
    real_col = _pick_price_column(real_market)
    real_prices = pd.to_numeric(real_market[real_col], errors="coerce").dropna().reset_index(drop=True)

    aligned = int(min(len(sim_prices), len(real_prices)))
    if aligned < 8:
        raise ValueError("No hay suficientes datos alineados para backtesting (minimo recomendado: 8 puntos).")

    sim_aligned = sim_prices.iloc[:aligned]
    real_aligned = real_prices.iloc[:aligned]

    epsilon = 1e-9
    mape = float(((sim_aligned - real_aligned).abs() / (real_aligned.abs() + epsilon)).mean() * 100.0)

    sim_returns = _safe_returns(sim_aligned)
    real_returns = _safe_returns(real_aligned)
    returns_aligned = int(min(len(sim_returns), len(real_returns)))
    if returns_aligned == 0:
        raise ValueError("No se pudieron calcular retornos validos para el backtesting.")

    sim_returns = sim_returns.iloc[:returns_aligned]
    real_returns = real_returns.iloc[:returns_aligned]

    mean_gap = float(abs(sim_returns.mean() - real_returns.mean()))
    vol_gap = float(abs(sim_returns.std(ddof=0) - real_returns.std(ddof=0)))

    sim_sign = np.sign(sim_returns.to_numpy())
    real_sign = np.sign(real_returns.to_numpy())
    directional_accuracy = float(np.mean(sim_sign == real_sign))

    sim_std = (sim_returns - sim_returns.mean()) / (sim_returns.std(ddof=0) + epsilon)
    real_std = (real_returns - real_returns.mean()) / (real_returns.std(ddof=0) + epsilon)
    ks_dist = _ks_distance(sim_std, real_std)

    # Lower is better. Combines price fit and stylized-fact behavior.
    score = float((mape * 0.5) + (mean_gap * 100.0 * 0.15) + (vol_gap * 100.0 * 0.15) + ((1.0 - directional_accuracy) * 100.0 * 0.1) + (ks_dist * 100.0 * 0.1))

    return BacktestMetrics(
        aligned_points=aligned,
        mape_price=round(mape, 6),
        mean_return_gap=round(mean_gap, 8),
        volatility_gap=round(vol_gap, 8),
        directional_accuracy=round(directional_accuracy, 6),
        ks_distance=round(ks_dist, 6),
        composite_score=round(score, 6),
    )


def membership_adjustment_recommendations(metrics: BacktestMetrics) -> list[str]:
    recommendations: list[str] = []
    if metrics.volatility_gap > 0.02:
        recommendations.append(
            "Reducir momentum_bias promedio y elevar sell_threshold en especuladores para amortiguar oscilaciones."
        )
    if metrics.directional_accuracy < 0.52:
        recommendations.append(
            "Aumentar el peso de tendencia en reglas de compra/venta para mejorar coherencia direccional."
        )
    if metrics.mape_price > 12.0:
        recommendations.append(
            "Recalibrar buy_threshold/sell_threshold por especie con optimizacion por grid search usando este score compuesto."
        )
    if metrics.ks_distance > 0.25:
        recommendations.append(
            "Ajustar risk_tolerance y reproduction_drive para acercar la distribucion de retornos simulados a la real."
        )
    if not recommendations:
        recommendations.append("El modelo se encuentra razonablemente alineado con la serie de referencia para estas metricas.")
    return recommendations


def load_reference_dataset(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)
