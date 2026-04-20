from __future__ import annotations

import pandas as pd

from evolucionia.validation import compare_market_series, membership_adjustment_recommendations


def test_compare_market_series_returns_metrics() -> None:
    simulated = pd.DataFrame({"close_price": [100, 101, 99, 102, 104, 103, 105, 107, 106, 108]})
    real = pd.DataFrame({"close": [98, 100, 101, 101, 103, 102, 104, 105, 106, 107]})

    metrics = compare_market_series(simulated, real)

    assert metrics.aligned_points == 10
    assert metrics.mape_price >= 0
    assert 0 <= metrics.directional_accuracy <= 1
    assert metrics.ks_distance >= 0


def test_membership_adjustment_recommendations_are_generated() -> None:
    simulated = pd.DataFrame({"close_price": [50, 60, 40, 62, 38, 65, 35, 66, 34, 68, 33, 70]})
    real = pd.DataFrame({"close": [50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61]})

    metrics = compare_market_series(simulated, real)
    recommendations = membership_adjustment_recommendations(metrics)

    assert recommendations
    assert all(isinstance(item, str) and item for item in recommendations)
