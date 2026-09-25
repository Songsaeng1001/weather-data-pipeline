WITH daily AS (
    SELECT
        c.name                 AS city,
        date(h.forecast_time)  AS day,
        AVG(h.temperature_c)   AS avg_temp_c
    FROM hourly_forecast AS h
    JOIN cities AS c ON c.city_id = h.city_id
    GROUP BY c.name, date(h.forecast_time)
)
SELECT
    city,
    day,
    ROUND(avg_temp_c, 1) AS avg_temp_c,
    ROUND(
        avg_temp_c - LAG(avg_temp_c) OVER (PARTITION BY city ORDER BY day),
        1
    ) AS change_from_prev_day_c
FROM daily
ORDER BY city, day;