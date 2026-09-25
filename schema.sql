PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS cities (
    city_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    timezone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_api_responses (
    raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
    city_id INTEGER NOT NULL REFERENCES cities(city_id),
    fetched_hour TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    payload TEXT NOT NULL,
    UNIQUE (city_id, fetched_hour)
);

CREATE TABLE IF NOT EXISTS hourly_forecast (
    city_id INTEGER NOT NULL REFERENCES cities(city_id),
    forecast_time TEXT NOT NULL,
    temperature_c REAL,
    precipitation_probability_pct INTEGER,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (city_id, forecast_time)
);

