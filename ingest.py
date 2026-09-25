import json
import logging
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
)
logger = logging.getLogger(__name__)

API_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_VARS = "temperature_2m,precipitation_probability"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
DB_PATH = "weather.db"
SCHEMA_PATH = "schema.sql"
TIMEZONE = "Asia/Bangkok"

CITIES = [
    {"name": "Bangkok", "lat": 13.7563, "lon": 100.5018},
    {"name": "Chiang Mai", "lat": 18.7883, "lon": 98.9853},
    {"name": "Phuket", "lat": 7.8804, "lon": 98.3923},
    {"name": "Khon Kaen", "lat": 16.4322, "lon": 102.8236},
    {"name": "Hat Yai", "lat": 7.0086, "lon": 100.4747},
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

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
        except (requests.Timeout, requests.ConnectionError) as e:
            error = e
        else:
            if response.status_code not in RETRYABLE_STATUS:
                response.raise_for_status()
                return response.json()
            error = f"HTTP {response.status_code}"

        if attempt < MAX_RETRIES:
            wait = RETRY_BACKOFF_SECONDS * 2 ** (attempt - 1)
            logger.warning(
                "%s: attempt %d/%d failed (%s), retrying in %ds",
                city["name"],
                attempt,
                MAX_RETRIES,
                error,
                wait,
            )
            time.sleep(wait)

    raise RuntimeError(f"gave up after {MAX_RETRIES} attempts ({error})")


def get_city_id(conn, name):
    row = conn.execute("SELECT city_id FROM cities WHERE name = ?", (name,)).fetchone()
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
    for ts, temp, rain in zip(
        hourly["time"],
        hourly["temperature_2m"],
        hourly["precipitation_probability"],
        strict=True,
    ):
        rows.append((city_id, ts, temp, rain, fetched_at))
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
    start = time.perf_counter()

    conn = get_connection()
    init_schema(conn)
    upsert_cities(conn)

    run_time = datetime.now(timezone.utc)
    fetched_at = run_time.isoformat(timespec="seconds")
    fetched_hour = run_time.strftime("%Y-%m-%dT%H")

    succeeded, failed = [], []
    total_rows = 0

    for city in CITIES:
        name = city["name"]
        try:
            data = fetch_forecast(city)
            city_id = get_city_id(conn, name)
            save_raw(conn, city_id, data, fetched_at, fetched_hour)
            rows = transform(city_id, data, fetched_at)
            load_forecast(conn, rows)
            delete_stale(conn, city_id, rows)
            conn.commit()
            succeeded.append(name)
            total_rows += len(rows)
            logger.info("%s: loaded %d rows", name, len(rows))
        except Exception:
            conn.rollback()
            failed.append(name)
            logger.exception("%s: failed, rolled back", name)

    conn.close()

    elapsed = time.perf_counter() - start
    logger.info(
        "Done: %d/%d cities succeeded, %d rows loaded, %.2fs elapsed",
        len(succeeded),
        len(CITIES),
        total_rows,
        elapsed,
    )
    if failed:
        logger.warning("Failed cities: %s", ", ".join(failed))
        sys.exit(1)


if __name__ == "__main__":
    main()
