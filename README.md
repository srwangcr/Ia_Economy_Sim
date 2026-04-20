# EvolucionIA

EvolucionIA es un simulador de mercado con agentes heterogeneos, persistencia transaccional y un dashboard para analizar la dinamica economica. El codigo actual modela mineros, especuladores y consumidores; ejecuta decisiones de compra/venta con reglas de membresia simples; y guarda cada corrida para poder compararla despues desde Streamlit.

## Como Funciona

El flujo real del motor es este:

```mermaid
flowchart LR
	A[Inicio de corrida] --> B[Crear agentes iniciales]
	B --> C[Tick actual]
	C --> D[Produccion y consumo de recursos]
	D --> E[Decision por agente\nbuy / sell / both / hold]
	E --> F[Matching de compradores y vendedores]
	F --> G[Actualizar precio\ncon presion de mercado y shock macro]
	G --> H[Guardar market_snapshots, transactions y agent_snapshots]
	H --> I{Fin de generacion?}
	I -->|No| C
	I -->|Si| J[Elegir elite por riqueza]
	J --> K[DEAP: crossover y mutacion]
	K --> L[Crear descendencia]
	L --> C
```

Las reglas que usa el codigo son estas:

- Los agentes evalúan precio, tendencia, inventario y energia con funciones de membresia simples.
- Los mineros producen recursos, los consumidores consumen inventario y los especuladores reaccionan más al momentum.
- La reproduccion ocurre al final de cada generacion, tomando elite por riqueza y combinando genes con DEAP.
- Cada tick deja persistencia en SQL con snapshots de mercado, agentes y transacciones.

## Arquitectura

```mermaid
flowchart TB
	CLI[CLI: evolucionia run] --> SIM[SimulationEngine]
	SIM --> DB[(SQLAlchemy / SQL)]
	DB --> RUNS[simulation_runs]
	DB --> MKT[market_snapshots]
	DB --> AG[agent_snapshots]
	DB --> TX[transactions]
	DB --> DASH[Dashboard Streamlit]
	DASH --> G1[Velas]
	DASH --> G2[Línea de precio y shock]
	DASH --> G3[Distribución de riqueza]
	DASH --> G4[Supervivencia por especie]
	DASH --> G5[Ledger y historico]
```

## Que Incluye

- Agentes con perfiles distintos: mineros, especuladores y consumidores.
- Decisiones de compra/venta basadas en membresias de precio, inventario, energia y tendencia.
- Evolucion genetica con DEAP para recombinar umbrales y parametros de riesgo.
- Persistencia por corrida con `run_id`, snapshots por tick y ledger de transacciones.
- Dashboard en Streamlit con reproduccion guiada, velas, precio, riqueza, supervivencia y tabla historica.
- Soporte para SQLite por defecto y PostgreSQL mediante `DATABASE_URL`.

## Arranque Rapido

1. Crear y activar un entorno Python 3.11+.
2. Instalar dependencias.
3. Ejecutar una simulacion:

```bash
.venv/bin/python -m evolucionia.cli run --ticks 120
```

4. Levantar el dashboard:

```bash
.venv/bin/streamlit run dashboard.py
```

## Dashboard

El dashboard permite elegir una corrida, filtrar por tipo de agente y mover un control de reproduccion para ver el estado tick por tick.

```mermaid
flowchart LR
	A[Seleccionar corrida] --> B[Cargar snapshots y transacciones]
	B --> C[Filtrar por especie]
	C --> D[Elegir tick visible]
	D --> E[Actualizar metricas]
	D --> F[Velas]
	D --> G[Línea de precio]
	D --> H[Histograma de riqueza]
	D --> I[Supervivencia por especie]
	D --> J[Ledger y historico]
```

Cada grafico resume una parte concreta del estado de la corrida:

- Velas: apertura, maximo, minimo y cierre por tick.
- Línea de precio: cierre y shock macroeconomico.
- Distribucion de riqueza: comparacion del capital total por agente.
- Supervivencia por especie: proporcion viva por grupo.
- Ledger de transacciones: operaciones individuales para auditar la corrida.

## Migraciones

Alembic esta preparado en `migrations/`. Para aplicar el esquema inicial en PostgreSQL o SQLite:

```bash
.venv/bin/alembic upgrade head
```

La app sigue creando tablas si hace falta, pero las migraciones ya quedan listas para entregar o desplegar.

## Base de Datos

Por defecto usa SQLite local para facilitar pruebas. Si quieres PostgreSQL, exporta `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/evolucionia
```

La simulacion escribe por corrida usando `run_id`, lo que permite comparar historicos y consultar corridas anteriores desde el dashboard.

Optimizaciones incluidas en el codigo actual:

- Indices compuestos en rutas de consulta frecuentes (`run_id`, `tick`, `agent_id` y variantes para buyer/seller).
- Particionado hash opcional de `transactions` por `run_id` en PostgreSQL.

## Estructura

- `src/evolucionia/simulation.py`: motor principal.
- `src/evolucionia/models.py`: agentes y reglas de decision.
- `src/evolucionia/genetics.py`: operadores geneticos con DEAP.
- `src/evolucionia/database.py`: capa de persistencia.
- `src/evolucionia/dashboard.py`: analisis visual.
- `src/evolucionia/cli.py`: comandos de linea.

## Roadmap

Estado actual y siguientes pasos del proyecto:

- Corto plazo: mejorar la lectura de corridas en el dashboard, con filtros mas finos por especie y rango de ticks.
- Corto plazo: sumar pruebas para decisiones de agentes, reproduccion genetica y persistencia por corrida.
- Mediano plazo: ampliar metadatos de cada corrida para comparar estrategias y parametros de forma mas clara.
- Mediano plazo: enriquecer el dashboard con mas vistas agregadas sobre oferta, demanda y distribucion de riqueza.
- Largo plazo: evaluar soporte para escenarios mas complejos, nuevas especies de agentes y configuraciones macroeconomicas adicionales.

---

# EvolucionIA

EvolucionIA is a market simulator with heterogeneous agents, transactional persistence, and a dashboard for analyzing economic dynamics. The current code models miners, speculators, and consumers; executes buy/sell decisions with simple membership rules; and stores each run so it can be compared later in Streamlit.

## How It Works

The actual engine flow is:

```mermaid
flowchart LR
	A[Run starts] --> B[Create initial agents]
	B --> C[Current tick]
	C --> D[Resource production and consumption]
	D --> E[Per-agent decision\nbuy / sell / both / hold]
	E --> F[Buyer/seller matching]
	F --> G[Update price\nwith market pressure and macro shock]
	G --> H[Save market_snapshots, transactions, and agent_snapshots]
	H --> I{End of generation?}
	I -->|No| C
	I -->|Yes| J[Select elite by wealth]
	J --> K[DEAP: crossover and mutation]
	K --> L[Create offspring]
	L --> C
```

The rules used by the code are:

- Agents evaluate price, trend, inventory, and energy with simple membership functions.
- Miners produce resources, consumers spend inventory, and speculators react more strongly to momentum.
- Reproduction happens at the end of each generation, selecting the wealthiest elite and combining genes with DEAP.
- Every tick is persisted in SQL with market, agent, and transaction snapshots.

## Architecture

```mermaid
flowchart TB
	CLI[CLI: evolucionia run] --> SIM[SimulationEngine]
	SIM --> DB[(SQLAlchemy / SQL)]
	DB --> RUNS[simulation_runs]
	DB --> MKT[market_snapshots]
	DB --> AG[agent_snapshots]
	DB --> TX[transactions]
	DB --> DASH[Streamlit dashboard]
	DASH --> G1[Candlesticks]
	DASH --> G2[Price and shock line]
	DASH --> G3[Wealth distribution]
	DASH --> G4[Survival by species]
	DASH --> G5[Ledger and history]
```

## What It Includes

- Distinct agent profiles: miners, speculators, and consumers.
- Buy/sell decisions based on price, inventory, energy, and trend memberships.
- Genetic evolution with DEAP to recombine thresholds and risk parameters.
- Per-run persistence with `run_id`, tick snapshots, and a transaction ledger.
- Streamlit dashboard with guided replay, candlesticks, price, wealth, survival, and run history.
- SQLite by default and PostgreSQL support through `DATABASE_URL`.

## Quick Start

1. Create and activate a Python 3.11+ environment.
2. Install dependencies.
3. Run a simulation:

```bash
.venv/bin/python -m evolucionia.cli run --ticks 120
```

4. Launch the dashboard:

```bash
.venv/bin/streamlit run dashboard.py
```

## Dashboard

The dashboard lets you pick a run, filter by agent type, and move a replay control to inspect the market tick by tick.

```mermaid
flowchart LR
	A[Select run] --> B[Load snapshots and transactions]
	B --> C[Filter by species]
	C --> D[Choose visible tick]
	D --> E[Refresh metrics]
	D --> F[Candlesticks]
	D --> G[Price line]
	D --> H[Wealth histogram]
	D --> I[Survival by species]
	D --> J[Ledger and history]
```

Each chart summarizes a specific part of the run state:

- Candlesticks: open, high, low, and close per tick.
- Price line: closing price and macro shock.
- Wealth distribution: total capital per agent.
- Survival by species: alive ratio by group.
- Transaction ledger: individual operations for auditing the run.

## Migrations

Alembic is set up in `migrations/`. To apply the initial schema on PostgreSQL or SQLite:

```bash
.venv/bin/alembic upgrade head
```

The app still creates tables when needed, but the migrations are now ready for delivery or deployment.

## Database

By default it uses a local SQLite database for easier testing. If you want PostgreSQL, export `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/evolucionia
```

The simulation writes per run using `run_id`, which makes it possible to compare histories and inspect previous runs from the dashboard.

Current code optimizations:

- Composite indexes on frequent query paths (`run_id`, `tick`, `agent_id`, and buyer/seller variants).
- Optional hash partitioning of `transactions` by `run_id` in PostgreSQL.

## Structure

- `src/evolucionia/simulation.py`: main engine.
- `src/evolucionia/models.py`: agents and decision rules.
- `src/evolucionia/genetics.py`: genetic operators with DEAP.
- `src/evolucionia/database.py`: persistence layer.
- `src/evolucionia/dashboard.py`: visual analysis.
- `src/evolucionia/cli.py`: command line entry points.

## Roadmap

Current status and next steps for the project:

- Short term: improve run exploration in the dashboard with finer species and tick-range filters.
- Short term: add tests for agent decisions, genetic reproduction, and run persistence.
- Mid term: expand run metadata so strategies and parameters are easier to compare.
- Mid term: enrich the dashboard with more aggregate views of supply, demand, and wealth distribution.
- Long term: evaluate support for more complex scenarios, new agent species, and additional macroeconomic settings.
