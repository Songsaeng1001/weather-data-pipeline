WITH ranked AS (
    SELECT
        c.name                              AS city,
        date(h.forecast_time)               AS day,
        strftime('%H:%M', h.forecast_time)  AS hour,
        h.precipitation_probability_pct     AS rain_prob_pct,
        ROW_NUMBER() OVER (
            PARTITION BY h.city_id, date(h.forecast_time)
            ORDER BY h.precipitation_probability_pct DESC, h.forecast_time ASC
        ) AS rn
    FROM hourly_forecast AS h
    JOIN cities AS c ON c.city_id = h.city_id
    WHERE h.precipitation_probability_pct IS NOT NULL
)
SELECT city, day, hour, rain_prob_pct
FROM ranked
WHERE rn = 1
ORDER BY city, day;
