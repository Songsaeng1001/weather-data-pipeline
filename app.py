import sqlite3
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = Path("weather.db")
SQL_DIR = Path("sql")

st.set_page_config(page_title="Thailand Weather Forecast", layout="wide")


def read_sql(query):
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(query, conn)
    finally:
        conn.close()


def read_sql_file(filename):
    return read_sql((SQL_DIR / filename).read_text())


if not DB_PATH.exists():
    st.error("weather.db not found. Run `python ingest.py` first.")
    st.stop()

hourly = read_sql(
    """
    SELECT c.name AS city, h.forecast_time, h.temperature_c,
           h.precipitation_probability_pct
    FROM hourly_forecast AS h
    JOIN cities AS c ON c.city_id = h.city_id
    ORDER BY h.forecast_time
    """
)
hourly["forecast_time"] = pd.to_datetime(hourly["forecast_time"])
last_fetched = read_sql("SELECT MAX(fetched_at) AS t FROM hourly_forecast")["t"].iloc[0]

st.title("Thailand 7-Day Weather Forecast")
st.caption(f"Source: Open-Meteo · times in Asia/Bangkok · data fetched at {last_fetched}")

cities = sorted(hourly["city"].unique())
selected = st.multiselect("Cities", cities, default=cities)
if not selected:
    st.info("Select at least one city.")
    st.stop()
filtered = hourly[hourly["city"].isin(selected)]

widest = read_sql_file("02_widest_temperature_range.sql").iloc[0]
st.metric(
    label=f"Widest 7-day temperature range: {widest['city']}",
    value=f"{widest['temp_range_c']} °C",
)

st.subheader("Hourly temperature (°C)")
temp_chart = (
    alt.Chart(filtered)
    .mark_line()
    .encode(
        x=alt.X("forecast_time:T", title="Time"),
        y=alt.Y("temperature_c:Q", title="°C", scale=alt.Scale(zero=False)),
        color=alt.Color("city:N", title="City"),
    )
)
st.altair_chart(temp_chart)

st.subheader("Hourly chance of rain (%)")
st.line_chart(
    filtered.pivot(index="forecast_time", columns="city", values="precipitation_probability_pct")
)

st.subheader("Daily temperature summary")
daily = read_sql_file("01_daily_temperature_stats.sql")
st.dataframe(daily[daily["city"].isin(selected)], hide_index=True)