# ✈️ Agente de Retrasos de Vuelos

Agente inteligente que responde preguntas en lenguaje natural sobre retrasos, cancelaciones y causas de demoras en vuelos de EE.UU., consultando una base de datos PostgreSQL en Supabase.

---

## 📋 Descripción

Este proyecto implementa un agente conversacional usando el SDK `openai-agents` de OpenAI, conectado a una base de datos PostgreSQL alojada en Supabase. El agente interpreta preguntas del usuario, decide qué herramienta usar, ejecuta la consulta SQL correspondiente y responde en lenguaje natural con los datos reales.

---

## 🗄️ Base de datos

La tabla `Airline_Delay_Cause` contiene registros mensuales de vuelos en aeropuertos de EE.UU. reportados por el BTS (Bureau of Transportation Statistics).

| Columna | Descripción |
|---|---|
| `year` / `month` | Período del registro |
| `carrier` / `carrier_name` | Código y nombre de la aerolínea |
| `airport` / `airport_name` | Código y nombre del aeropuerto |
| `arr_flights` | Total de vuelos que llegaron |
| `arr_del15` | Vuelos con retraso mayor a 15 minutos |
| `arr_cancelled` | Vuelos cancelados |
| `arr_diverted` | Vuelos desviados |
| `arr_delay` | Minutos totales de retraso |
| `carrier_delay` | Retraso atribuido a la aerolínea |
| `weather_delay` | Retraso por condiciones climáticas |
| `nas_delay` | Retraso por sistema de control aéreo (NAS) |
| `security_delay` | Retraso por seguridad |
| `late_aircraft_delay` | Retraso por avión que llegó tarde de vuelo anterior |

**Cobertura:** ~398,000 registros · 51 aerolíneas · 425 aeropuertos · 2003–2025

---

## 🛠️ Herramientas del agente

El agente tiene 5 herramientas disponibles que ejecutan consultas SQL reales contra la base de datos:

| Herramienta | Descripción |
|---|---|
| `get_delay_by_airline` | Ranking de aerolíneas por minutos de retraso totales |
| `get_delay_by_airport` | Ranking de aeropuertos por minutos de retraso totales |
| `get_delay_causes` | Desglose de retrasos por causa (clima, aerolínea, NAS, seguridad, avión tardío) |
| `get_stats_by_period` | Estadísticas de vuelos, retrasos y cancelaciones por año y/o mes |
| `get_cancellations` | Ranking de aerolíneas por vuelos cancelados |

Todas las herramientas aceptan filtros opcionales por año y permiten ajustar cuántos resultados mostrar.

---

## 💬 Ejemplos de preguntas

```
¿Cuál fue la aerolínea con más retrasos en 2024?
¿Qué aeropuerto tiene el peor historial histórico de retrasos?
¿Cuál es la causa más común de retrasos para American Airlines?
Dame las estadísticas de enero 2020
¿Qué aerolínea canceló más vuelos en 2023?
¿Cuántos vuelos se retrasaron en total en 2019?
```

---

## 🚀 Instalación y uso

### Requisitos previos

- Python 3.11+
- Cuenta de OpenAI con créditos disponibles
- Acceso a la base de datos en Supabase

### 1. Crear entorno virtual

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia el archivo de ejemplo y completa tus credenciales:

```bash
cp .env.example .env
```

Edita el `.env` con tus datos:

```env
OPENAI_API_KEY=sk-...tu-clave-aqui...

DB_HOST=aws-1-us-east-1.pooler.supabase.com
DB_PORT=6543
DB_NAME=postgres
DB_USER=postgres.utlrodvxsysqktstqlkq
DB_PASSWORD=tu-password-aqui
```

> 💡 **Importante:** Nunca subas el archivo `.env` a GitHub. Agrégalo a tu `.gitignore`.

### 4. Correr el agente

```bash
python flight_agent.py
```

Verás algo así:

```
✈️  Agente de Retrasos de Vuelos
   Escribe tu pregunta o 'salir' para terminar.

Tú: ¿Cuál fue la aerolínea con más retrasos en 2024?
[debug] get_delay_by_airline  year=2024  top=5

🤖 Agente: En 2024, Southwest Airlines fue la aerolínea con más minutos
de retraso acumulados, con 8,432,150 minutos en total...
```

---

## 🧠 ¿Cómo funciona el agente?

```
Usuario hace una pregunta en lenguaje natural
    → El agente (gpt-4.1-mini) decide qué herramienta usar
        → La herramienta ejecuta un SELECT en PostgreSQL/Supabase
            → El agente interpreta los resultados
                → Responde en lenguaje natural
```

El agente usa el SDK `openai-agents` que maneja automáticamente el loop de decisión, eliminando la necesidad de gestionar manualmente las llamadas a funciones y sus respuestas.

---

## 📁 Estructura del proyecto

```
.
├── flight_agent.py     # Agente principal con todas las herramientas
├── requirements.txt    # Dependencias del proyecto
├── .env.example        # Plantilla de variables de entorno
├── .env                # Tu configuración local (no subir a Git)
└── README.md           # Este archivo
```

---

## 💡 Conceptos utilizados

- **Function Calling / Tools**: El modelo detecta cuándo llamar una herramienta y con qué parámetros, en lugar de responder solo con texto.
- **Agent Loop**: El SDK `openai-agents` maneja automáticamente el ciclo de razonamiento → acción → observación → respuesta.
- **SQL seguro**: Todas las consultas son solo de lectura (`SELECT`) con parámetros parametrizados para evitar inyección SQL.
- **Connection Pooler**: La conexión usa el Transaction Pooler de Supabase para mayor eficiencia y compatibilidad con IPv4.
