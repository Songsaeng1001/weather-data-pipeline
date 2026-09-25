import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("weather.db")
SQL_DIR = Path("sql")
OUTPUT_PATH = Path("reports/weather_report.md")

SECTIONS = [
    ("Daily temperature per city", "01_daily_temperature_stats.sql"),
    ("Widest temperature range over the next 7 days", "02_widest_temperature_range.sql"),
    ("Hour with the highest chance of rain", "03_peak_rain_hour.sql"),
    ("Change in daily average temperature vs previous day", "04_daily_avg_change.sql"),
]


def run_query(conn, filename):
    sql = (SQL_DIR / filename).read_text()
    cursor = conn.execute(sql)
    headers = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    return headers, rows


def to_markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    for row in rows:
        cells = ["" if value is None else str(value) for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    if not DB_PATH.exists():
        sys.exit(f"{DB_PATH} not found. Run `python ingest.py` first.")

    conn = sqlite3.connect(DB_PATH)
    last_fetched = conn.execute(
        "SELECT MAX(fetched_at) FROM hourly_forecast"
    ).fetchone()[0]

    parts = [
        "# Weather Forecast Report",
        "",
        f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"- Data fetched at (UTC): {last_fetched}",
        "- Source: Open-Meteo hourly forecast, times in Asia/Bangkok",
        "",
    ]
    for title, filename in SECTIONS:
        headers, rows = run_query(conn, filename)
        parts += [f"## {title}", "", to_markdown_table(headers, rows), ""]

    conn.close()

    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(parts), encoding="utf-8")
    print(f"Report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()