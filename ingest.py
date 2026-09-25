import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import requests

API_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "temperature_2m,precipitation_probability"
DB_PATH = "weather.db"
SCHEMA_PATH = "schema.sql"
TIMEZONE = "Asia/Bangkok"

CITIES = [
    {"name": "Bangkok",    "lat": 13.7563, "lon": 100.5018},
    {"name": "Chiang Mai", "lat": 18.7883, "lon": 98.9853},
    {"name": "Phuket",     "lat": 7.8804,  "lon": 98.3923},
    {"name": "Khon Kaen",  "lat": 16.4322, "lon": 102.8236},
    {"name": "Hat Yai",    "lat": 7.0086,  "lon": 100.4747},
]
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_schema(conn):
    schema = Path(SCHEMA_PATH).read_text()
    conn.executescript(schema)

def upsert_cities(conn):
    for city in CITIES:
        conn.execute(
            """
            INSERT INTO cities (name, latitude, longitude, timezone)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                latitude  = excluded.latitude,
                longitude = excluded.longitude,
                timezone  = excluded.timezone
            """,
            (city["name"], city["lat"], city["lon"], TIMEZONE),
        )
    conn.commit()
def fetch_forecast(city):
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "hourly": HOURLY_VARS,
        "forecast_days": 7,
        "timezone": TIMEZONE,
    }
    response = requests.get(API_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def get_city_id(conn, name):
    row = conn.execute(
        "SELECT city_id FROM cities WHERE name = ?", (name,)
    ).fetchone()
    return row[0]

def save_raw(conn, city_id, payload, fetched_at, fetched_hour):
    conn.execute(
        """
        INSERT INTO raw_api_responses (city_id, fetched_hour, fetched_at, payload)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(city_id, fetched_hour) DO UPDATE SET
            fetched_at = excluded.fetched_at,
            payload    = excluded.payload
        """,
        (city_id, fetched_hour, fetched_at, json.dumps(payload)),
    )
def transform(city_id, payload, fetched_at):
    hourly = payload["hourly"]
    rows = []
    for time, temp, rain in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
        strict=True,
    ):
        rows.append((city_id, time, temp, rain, fetched_at))
    return rows

def load_forecast(conn, rows):
    conn.executemany(
        """
        INSERT INTO hourly_forecast
            (city_id, forecast_time, temperature_c, precipitation_probability_pct, fetched_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(city_id, forecast_time) DO UPDATE SET
            temperature_c                 = excluded.temperature_c,
            precipitation_probability_pct = excluded.precipitation_probability_pct,
            fetched_at                    = excluded.fetched_at
        """,
        rows,
    )

def delete_stale(conn, city_id, rows):
    earliest = min(row[1] for row in rows)
    conn.execute(
        "DELETE FROM hourly_forecast WHERE city_id = ? AND forecast_time < ?",
        (city_id, earliest),
    )
    
def main():
    conn = get_connection()
    init_schema(conn)
    upsert_cities(conn)

    run_time = datetime.now(timezone.utc)
    fetched_at = run_time.isoformat(timespec="seconds")
    fetched_hour = run_time.strftime("%Y-%m-%dT%H")

    for city in CITIES:
        data = fetch_forecast(city)
        city_id = get_city_id(conn, city["name"])
        save_raw(conn, city_id, data, fetched_at, fetched_hour)
        rows = transform(city_id, data, fetched_at)
        load_forecast(conn, rows)
        delete_stale(conn, city_id, rows)
        conn.commit()
        print(city["name"], "- loaded", len(rows), "rows")

    conn.close()


if __name__ == "__main__":
    main()
