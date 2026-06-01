import asyncio
import os
from typing import Annotated

import psycopg
from psycopg.rows import dict_row
from agents import Agent, Runner, function_tool, set_default_openai_key
from dotenv import load_dotenv

load_dotenv()

# ── Claves ────────────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
set_default_openai_key(OPENAI_API_KEY)

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT", "6543")
DB_NAME     = os.getenv("DB_NAME", "postgres")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

TABLE = '"Airline_Delay_Cause"'   # comillas dobles porque tiene mayúsculas


# ── Conexión a Postgres ───────────────────────────────────────────────────────
def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )


def run_query(sql: str, params=None) -> list[dict]:
    """Ejecuta un SELECT y devuelve una lista de dicts."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return list(rows)


# ── Tools ─────────────────────────────────────────────────────────────────────

@function_tool
def get_delay_by_airline(
    top_n: Annotated[int, "Cuántas aerolíneas mostrar (default 5)"] = 5,
    year:  Annotated[int, "Año a filtrar, 0 = todos los años"]       = 0,
) -> list[dict]:
    """
    Devuelve las aerolíneas con más minutos de retraso totales.
    Incluye total de vuelos, vuelos retrasados y minutos de retraso.
    """
    year_filter = "WHERE year = %(year)s" if year else ""
    sql = f"""
        SELECT
            carrier_name,
            SUM(arr_flights)  AS total_flights,
            SUM(arr_del15)    AS delayed_flights,
            SUM(arr_delay)    AS total_delay_minutes,
            ROUND(SUM(arr_del15)::numeric / NULLIF(SUM(arr_flights), 0) * 100, 2)
                AS pct_delayed
        FROM {TABLE}
        {year_filter}
        GROUP BY carrier_name
        ORDER BY total_delay_minutes DESC
        LIMIT %(top_n)s
    """
    params = {"top_n": top_n, "year": year}
    print(f"[debug] get_delay_by_airline  year={year or 'all'}  top={top_n}")
    return run_query(sql, params)


@function_tool
def get_delay_by_airport(
    top_n: Annotated[int, "Cuántos aeropuertos mostrar (default 5)"] = 5,
    year:  Annotated[int, "Año a filtrar, 0 = todos los años"]       = 0,
) -> list[dict]:
    """
    Devuelve los aeropuertos con más minutos de retraso totales.
    """
    year_filter = "WHERE year = %(year)s" if year else ""
    sql = f"""
        SELECT
            airport_name,
            airport,
            SUM(arr_flights)  AS total_flights,
            SUM(arr_del15)    AS delayed_flights,
            SUM(arr_delay)    AS total_delay_minutes,
            ROUND(SUM(arr_del15)::numeric / NULLIF(SUM(arr_flights), 0) * 100, 2)
                AS pct_delayed
        FROM {TABLE}
        {year_filter}
        GROUP BY airport_name, airport
        ORDER BY total_delay_minutes DESC
        LIMIT %(top_n)s
    """
    params = {"top_n": top_n, "year": year}
    print(f"[debug] get_delay_by_airport  year={year or 'all'}  top={top_n}")
    return run_query(sql, params)


@function_tool
def get_delay_causes(
    year:         Annotated[int, "Año a filtrar, 0 = todos los años"] = 0,
    carrier_name: Annotated[str, "Nombre de aerolínea, vacío = todas"] = "",
) -> dict:
    """
    Desglosa los minutos de retraso por causa:
    aerolínea, clima, sistema de control aéreo (NAS), seguridad y avión tardío.
    """
    conditions = []
    if year:
        conditions.append("year = %(year)s")
    if carrier_name:
        conditions.append("carrier_name ILIKE %(carrier)s")
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            SUM(carrier_delay)      AS carrier_minutes,
            SUM(weather_delay)      AS weather_minutes,
            SUM(nas_delay)          AS nas_minutes,
            SUM(security_delay)     AS security_minutes,
            SUM(late_aircraft_delay) AS late_aircraft_minutes,
            SUM(arr_delay)          AS total_minutes
        FROM {TABLE}
        {where}
    """
    params = {"year": year, "carrier": f"%{carrier_name}%"}
    print(f"[debug] get_delay_causes  year={year or 'all'}  carrier='{carrier_name or 'all'}'")
    rows = run_query(sql, params)
    return rows[0] if rows else {}


@function_tool
def get_stats_by_period(
    year:  Annotated[int, "Año requerido (obligatorio)"],
    month: Annotated[int, "Mes 1-12, 0 = todo el año"] = 0,
) -> list[dict]:
    """
    Estadísticas mensuales o anuales: vuelos, retrasos, cancelaciones y desviados.
    """
    conditions = ["year = %(year)s"]
    if month:
        conditions.append("month = %(month)s")
    where = "WHERE " + " AND ".join(conditions)

    group  = "year, month" if not month else "year, month"
    sql = f"""
        SELECT
            year,
            month,
            SUM(arr_flights)   AS total_flights,
            SUM(arr_del15)     AS delayed_flights,
            SUM(arr_cancelled) AS cancelled_flights,
            SUM(arr_diverted)  AS diverted_flights,
            SUM(arr_delay)     AS total_delay_minutes,
            ROUND(SUM(arr_del15)::numeric / NULLIF(SUM(arr_flights), 0) * 100, 2)
                AS pct_delayed
        FROM {TABLE}
        {where}
        GROUP BY {group}
        ORDER BY year, month
    """
    params = {"year": year, "month": month}
    print(f"[debug] get_stats_by_period  year={year}  month={month or 'all'}")
    return run_query(sql, params)


@function_tool
def get_cancellations(
    top_n: Annotated[int, "Cuántas aerolíneas mostrar (default 5)"] = 5,
    year:  Annotated[int, "Año a filtrar, 0 = todos los años"]       = 0,
) -> list[dict]:
    """
    Ranking de aerolíneas por vuelos cancelados.
    """
    year_filter = "WHERE year = %(year)s" if year else ""
    sql = f"""
        SELECT
            carrier_name,
            SUM(arr_flights)   AS total_flights,
            SUM(arr_cancelled) AS cancelled_flights,
            ROUND(SUM(arr_cancelled)::numeric / NULLIF(SUM(arr_flights), 0) * 100, 2)
                AS pct_cancelled
        FROM {TABLE}
        {year_filter}
        GROUP BY carrier_name
        ORDER BY cancelled_flights DESC
        LIMIT %(top_n)s
    """
    params = {"top_n": top_n, "year": year}
    print(f"[debug] get_cancellations  year={year or 'all'}  top={top_n}")
    return run_query(sql, params)


# ── Agente ────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Eres un asistente experto en análisis de retrasos y cancelaciones de vuelos en aeropuertos de EE.UU.

Tienes acceso a una base de datos con registros desde 2003 hasta 2025 que incluye:
- 51 aerolíneas y 425 aeropuertos
- Causas de retraso: aerolínea, clima, sistema de control aéreo (NAS), seguridad, avión tardío
- Datos mensuales de vuelos, retrasos (>15 min), cancelaciones y desviados

Cuando respondas:
- Usa las herramientas disponibles para consultar datos reales
- Presenta los números de forma clara y legible
- Convierte minutos a horas cuando sea más de 120 minutos
- Si te preguntan por una aerolínea específica, busca por nombre parcial
- Siempre menciona el período de los datos que estás mostrando
"""

agent = Agent(
    name="Agente de Vuelos",
    instructions=SYSTEM_PROMPT,
    tools=[
        get_delay_by_airline,
        get_delay_by_airport,
        get_delay_causes,
        get_stats_by_period,
        get_cancellations,
    ],
)


# ── Chat loop ─────────────────────────────────────────────────────────────────

async def main():
    print("✈️  Agente de Retrasos de Vuelos")
    print("   Escribe tu pregunta o 'salir' para terminar.\n")

    while True:
        user_input = input("Tú: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["salir", "exit", "quit"]:
            print("👋 ¡Hasta luego!")
            break

        result = await Runner.run(agent, input=user_input)
        print(f"\n🤖 Agente: {result.final_output}\n")


if __name__ == "__main__":
    asyncio.run(main())