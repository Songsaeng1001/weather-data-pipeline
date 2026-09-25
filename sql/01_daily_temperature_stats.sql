SELECT
    c.name                          AS city,
    date(h.forecast_time)           AS day,
    ROUND(AVG(h.temperature_c), 1)  AS avg_temp_c,
    MAX(h.temperature_c)            AS max_temp_c,
    MIN(h.temperature_c)            AS min_temp_c
FROM hourly_forecast AS h
JOIN cities AS c ON c.city_id = h.city_id
GROUP BY c.name, date(h.forecast_time)
ORDER BY c.name, day;