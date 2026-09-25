SELECT
    c.name                                          AS city,
    ROUND(MAX(h.temperature_c) - MIN(h.temperature_c), 1) AS temp_range_c,
    MAX(h.temperature_c)                            AS max_temp_c,
    MIN(h.temperature_c)                            AS min_temp_c
FROM hourly_forecast AS h
JOIN cities AS c ON c.city_id = h.city_id
GROUP BY c.name
ORDER BY temp_range_c DESC
LIMIT 1;