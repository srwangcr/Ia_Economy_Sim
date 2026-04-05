from __future__ import annotations

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .config import Settings
from .database import (
    build_engine,
    init_db,
    load_agent_snapshots,
    load_market_snapshots,
    load_simulation_runs,
    load_transactions,
    session_factory,
)
from .simulation import SimulationEngine


st.set_page_config(page_title="EvolucionIA", layout="wide", page_icon="📈")

st.markdown(
    """
<style>
    :root {
        --bg: #0b1020;
        --panel: rgba(16, 24, 48, 0.88);
        --panel-border: rgba(120, 160, 255, 0.18);
        --text: #e8eefc;
        --muted: #97a3c6;
        --accent: #6ee7b7;
        --accent-2: #7dd3fc;
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(125, 211, 252, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(110, 231, 183, 0.16), transparent 26%),
            linear-gradient(180deg, #07111f 0%, #0b1020 42%, #0f172a 100%);
        color: var(--text);
    }
    section[data-testid="stSidebar"] {
        background: rgba(7, 15, 31, 0.96);
        border-right: 1px solid rgba(148, 163, 184, 0.14);
    }
    .hero {
        padding: 1.2rem 1.25rem 0.35rem 1.25rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.18), rgba(16, 185, 129, 0.12));
        border: 1px solid rgba(148, 163, 184, 0.16);
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.28);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0;
        color: var(--text);
        font-size: 2.3rem;
        letter-spacing: -0.04em;
    }
    .hero p {
        margin: 0.35rem 0 0 0;
        color: var(--muted);
    }
    .metric-card {
        background: var(--panel);
        border: 1px solid var(--panel-border);
        border-radius: 18px;
        padding: 1rem 1.1rem;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.22);
    }
    .explanation {
        background: rgba(15, 23, 42, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 16px;
        padding: 0.85rem 0.95rem;
        color: var(--muted);
        line-height: 1.45;
        margin-bottom: 0.75rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_engine(database_url: str):
    engine = build_engine(database_url)
    init_db(engine)
    return engine


def run_simulation(engine, settings: Settings) -> dict:
    session = session_factory(engine)()
    try:
        simulation = SimulationEngine(settings, session)
        simulation.run(settings.ticks)
        return simulation.summary()
    finally:
        session.close()


def make_candlestick(market_df: pd.DataFrame, max_tick: int | None = None):
    if market_df.empty:
        return None
    view = market_df if max_tick is None else market_df[market_df["tick"] <= max_tick]
    if view.empty:
        return None
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=view["tick"],
                open=view["open_price"],
                high=view["high_price"],
                low=view["low_price"],
                close=view["close_price"],
                name="Precio",
                increasing_line_color="#34d399",
                decreasing_line_color="#fb7185",
            )
        ]
    )
    fig.update_layout(
        margin=dict(l=12, r=12, t=24, b=12),
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8eefc"),
    )
    return fig


def make_price_line(market_df: pd.DataFrame, max_tick: int | None = None):
    if market_df.empty:
        return None
    view = market_df if max_tick is None else market_df[market_df["tick"] <= max_tick]
    if view.empty:
        return None
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=view["tick"],
            y=view["close_price"],
            mode="lines",
            name="Cierre",
            line=dict(color="#7dd3fc", width=2.5),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=view["tick"],
            y=view["shock_factor"],
            mode="lines",
            name="Shock macro",
            line=dict(color="#fbbf24", width=1.8, dash="dot"),
            yaxis="y2",
        )
    )
    if max_tick is not None:
        fig.add_vline(x=max_tick, line_dash="dash", line_color="#a78bfa")
    fig.update_layout(
        margin=dict(l=12, r=12, t=24, b=12),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8eefc"),
        yaxis=dict(title="Precio"),
        yaxis2=dict(title="Shock", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def format_run_label(row: pd.Series | dict) -> str:
    timestamp = row.get("created_at")
    if pd.isna(timestamp):
        timestamp_text = "sin fecha"
    else:
        timestamp_text = pd.to_datetime(timestamp).strftime("%Y-%m-%d %H:%M")
    price = row.get("final_price")
    status = row.get("status", "unknown")
    return f"{timestamp_text} · {status} · cierre {price:.2f}" if pd.notna(price) else f"{timestamp_text} · {status}"


def render_metrics(market_df: pd.DataFrame, transaction_df: pd.DataFrame, agent_df: pd.DataFrame, run_row: pd.Series | None, current_tick: int):
    visible_market = market_df if current_tick <= 0 else market_df[market_df["tick"] <= current_tick]
    visible_transactions = transaction_df if current_tick <= 0 else transaction_df[transaction_df["tick"] <= current_tick]
    visible_agents = agent_df if current_tick <= 0 else agent_df[agent_df["tick"] <= current_tick]

    final_price = float(visible_market["close_price"].iloc[-1]) if not visible_market.empty else 0.0
    if not visible_agents.empty:
        latest_tick = visible_agents["tick"].max()
        active_agents = int(visible_agents[visible_agents["tick"] == latest_tick]["agent_id"].nunique())
    else:
        active_agents = 0
    total_transactions = int(len(visible_transactions))
    if run_row is not None and pd.notna(run_row.get("mean_wealth")) and current_tick <= 0:
        mean_wealth = float(run_row.get("mean_wealth"))
    elif not visible_agents.empty:
        latest_tick = visible_agents["tick"].max()
        latest_agents = visible_agents[visible_agents["tick"] == latest_tick].copy()
        latest_agents["wealth"] = latest_agents["balance"] + latest_agents["inventory"] * final_price
        mean_wealth = float(latest_agents["wealth"].mean())
    else:
        mean_wealth = 0.0

    columns = st.columns(4)
    cards = [
        ("Precio visible", f"{final_price:.2f}"),
        ("Transacciones visibles", f"{total_transactions}"),
        ("Agentes activos", f"{active_agents}"),
        ("Riqueza media", f"{mean_wealth:.2f}"),
    ]
    for column, (label, value) in zip(columns, cards):
        with column:
            st.markdown(
                f"<div class='metric-card'><div style='font-size:0.9rem;color:#97a3c6'>{label}</div><div style='font-size:1.9rem;font-weight:700;color:#f8fafc'>{value}</div></div>",
                unsafe_allow_html=True,
            )


def current_state_story(market_df: pd.DataFrame, agent_df: pd.DataFrame, transaction_df: pd.DataFrame, tick: int) -> str:
    if tick <= 0 or market_df.empty:
        return "Elegí una corrida y mové el control de reproducción para ver cómo cambia el mercado tick por tick."

    visible_market = market_df[market_df["tick"] <= tick]
    visible_agents = agent_df[agent_df["tick"] <= tick]
    visible_transactions = transaction_df[transaction_df["tick"] <= tick]
    current_row = visible_market.iloc[-1]
    current_agents = visible_agents[visible_agents["tick"] == visible_agents["tick"].max()]
    survivors = int(current_agents["alive"].sum()) if not current_agents.empty else 0

    return (
        f"Tick {tick}: el precio de cierre está en {current_row['close_price']:.2f}, "
        f"con {int(current_row['buyers_count'])} compradores y {int(current_row['sellers_count'])} vendedores. "
        f"Se observan {len(visible_transactions)} transacciones acumuladas y {survivors} agentes vivos en el último snapshot visible."
    )


def main():
    st.markdown(
        """
        <div class="hero">
            <h1>EvolucionIA</h1>
            <p>Mercado de agentes con evolución genética, ledger transaccional y reproducción de la simulación paso a paso.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    database_url = st.sidebar.text_input("DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///evolucionia_runs.db"))
    initial_agents = st.sidebar.slider("Agentes iniciales", 15, 250, 60, 5)
    ticks = st.sidebar.slider("Ticks", 20, 240, 120, 10)
    initial_price = st.sidebar.slider("Precio inicial", 1.0, 50.0, 10.0, 0.5)
    seed = st.sidebar.number_input("Seed", value=42, step=1)

    settings = Settings(
        database_url=database_url,
        initial_agents=initial_agents,
        ticks=ticks,
        generation_length=30,
        initial_price=initial_price,
        seed=int(seed),
    )

    engine = get_engine(database_url)

    if st.sidebar.button("Ejecutar simulacion", use_container_width=True):
        with st.spinner("Corriendo simulacion..."):
            summary = run_simulation(engine, settings)
        st.session_state["selected_run_id"] = summary["run_id"]
        st.toast("Simulacion completada", icon="✅")
        st.rerun()

    runs_df = load_simulation_runs(engine)
    if runs_df.empty:
        st.info("Todavia no hay corridas almacenadas. Ejecuta una simulacion desde la barra lateral.")
        return

    run_options = runs_df["run_id"].tolist()
    labels = {row["run_id"]: format_run_label(row) for row in runs_df.to_dict("records")}
    default_run_id = st.session_state.get("selected_run_id", run_options[0])
    if default_run_id not in run_options:
        default_run_id = run_options[0]

    selected_run_id = st.selectbox(
        "Corrida",
        options=run_options,
        index=run_options.index(default_run_id),
        format_func=lambda value: labels.get(value, value),
    )
    st.session_state["selected_run_id"] = selected_run_id

    run_row = runs_df[runs_df["run_id"] == selected_run_id].iloc[0]
    market_df = load_market_snapshots(engine, selected_run_id)
    agent_df = load_agent_snapshots(engine, selected_run_id)
    transaction_df = load_transactions(engine, selected_run_id)

    max_tick = int(market_df["tick"].max()) if not market_df.empty else 0
    replay_mode = st.toggle("Reproducción guiada", value=True)
    current_tick = max_tick
    if replay_mode and max_tick > 0:
        current_tick = st.slider("Tick visible", 1, max_tick, min(max_tick, max(1, st.session_state.get("dashboard_tick", 1))))
        st.session_state["dashboard_tick"] = current_tick
    else:
        st.session_state["dashboard_tick"] = max_tick

    render_metrics(market_df, transaction_df, agent_df, run_row, current_tick)

    st.markdown(
        f"<div class='explanation'><strong>Qué estás viendo:</strong> {current_state_story(market_df, agent_df, transaction_df, current_tick)}</div>",
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1.35, 1])
    with col_left:
        fig = make_candlestick(market_df, current_tick if replay_mode else None)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Este gráfico muestra la evolución del precio por tick. Las velas resumen apertura, máximo, mínimo y cierre para ver volatilidad y shocks macro.")

    with col_right:
        line_fig = make_price_line(market_df, current_tick if replay_mode else None)
        st.plotly_chart(line_fig, use_container_width=True)
        st.caption("La línea azul es el precio de cierre. La línea punteada amarilla marca el shock macroeconómico aplicado en cada tick.")

    lower_left, lower_right = st.columns(2)
    if not agent_df.empty:
        visible_agents = agent_df if current_tick <= 0 else agent_df[agent_df["tick"] <= current_tick]
        latest_tick = visible_agents["tick"].max()
        latest_agents = visible_agents[visible_agents["tick"] == latest_tick].copy()
        final_price = float(market_df[market_df["tick"] <= current_tick]["close_price"].iloc[-1]) if not market_df.empty else 0.0
        latest_agents["wealth"] = latest_agents["balance"] + latest_agents["inventory"] * final_price

        with lower_left:
            wealth_fig = go.Figure(data=[go.Histogram(x=latest_agents["wealth"], nbinsx=18, marker_color="#7dd3fc")])
            wealth_fig.update_layout(
                title="Distribucion de riqueza",
                margin=dict(l=12, r=12, t=40, b=12),
                height=360,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8eefc"),
            )
            st.plotly_chart(wealth_fig, use_container_width=True)
            st.caption("El histograma compara la riqueza actual de los agentes visibles. Sirve para detectar concentración, desigualdad o posibles monopolios.")

        with lower_right:
            survival_df = latest_agents.groupby("species", as_index=False)["alive"].mean()
            survival_fig = go.Figure(data=[go.Bar(x=survival_df["species"], y=survival_df["alive"], marker_color="#34d399")])
            survival_fig.update_layout(
                title="Supervivencia por especie",
                yaxis_title="Proporcion viva",
                margin=dict(l=12, r=12, t=40, b=12),
                height=360,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#e8eefc"),
            )
            st.plotly_chart(survival_fig, use_container_width=True)
            st.caption("Esta barra resume qué porcentaje de cada especie sigue vivo en el tick seleccionado. Es útil para ver selección natural y adaptación.")

    st.subheader("Ultimas transacciones")
    st.dataframe(transaction_df.tail(20), use_container_width=True, hide_index=True)
    st.caption("Cada fila representa una transacción individual del ledger. Es la fuente para auditar el mercado y reconstruir el historial completo.")

    st.subheader("Historico de corridas")
    history_view = runs_df[["created_at", "status", "seed", "ticks", "initial_agents", "final_price", "total_transactions", "mean_wealth"]].copy()
    st.dataframe(history_view, use_container_width=True, hide_index=True)
    st.caption("Usá este historial para comparar corridas con parámetros distintos y evaluar cómo cambian precio, transacciones y riqueza media.")


if __name__ == "__main__":
    main()