# EvolucionIA

EvolucionIA es un simulador de mercado con agentes heterogeneos, persistencia transaccional y un dashboard para analizar la dinamica economica.

## Que incluye

- Agentes con perfiles distintos: mineros, especuladores y consumidores.
- Log de transacciones, snapshots y metadatos por corrida en una base SQL.
- Evolucion genetica basada en DEAP para recombinar rasgos de agentes elite.
- Decision difusa para compras y ventas segun precio, inventario y tendencia.
- Dashboard en Streamlit con historial de corridas, velas, riqueza y supervivencia.
- Soporte para PostgreSQL via `DATABASE_URL`.

## Arranque rapido

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

El dashboard tiene modo de reproducción para recorrer la simulación tick por tick. Cuando activás la opción de reproducción guiada, el control de tick deja ver el estado visible en cada momento.

Cada gráfico trae una explicación breve:

- Velas: resume apertura, máximo, mínimo y cierre por tick.
- Línea de precio: muestra el cierre y el shock macroeconómico.
- Distribución de riqueza: compara cuánto acumula cada agente.
- Supervivencia por especie: resume la presión evolutiva sobre cada grupo.
- Ledger de transacciones: lista cada operación para auditar el mercado.

## Migraciones

Alembic quedó preparado en `migrations/`. Para aplicar el esquema inicial en PostgreSQL o SQLite:

```bash
.venv/bin/alembic upgrade head
```

La app sigue creando tablas si hace falta, pero ahora tenés migraciones reproducibles para entregar o desplegar.

## Base de datos

Por defecto usa SQLite local para facilitar pruebas. Si queres PostgreSQL, exporta `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/evolucionia
```

La simulacion escribe en tablas con `run_id`, lo que permite comparar historicos y consultar corridas anteriores desde el dashboard.

## Estructura

- `src/evolucionia/simulation.py`: motor principal.
- `src/evolucionia/database.py`: capa de persistencia.
- `src/evolucionia/dashboard.py`: analisis visual.
- `src/evolucionia/cli.py`: comandos de linea.
