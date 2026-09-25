import sqlite3
from pathlib import Path

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
def main():
    conn = get_connection()
    init_schema(conn)
    upsert_cities(conn)
    conn.close()


if __name__ == "__main__":
    main()
