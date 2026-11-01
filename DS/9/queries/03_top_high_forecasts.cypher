MATCH (f:Lab8Forecast)
WHERE f.targetTime >= localdatetime($start)
  AND f.targetTime < localdatetime($end)
  AND f.forecastKwh > $threshold
RETURN f.id AS id, toString(f.targetTime) AS timestamp, f.forecastKwh AS forecast_kwh
ORDER BY forecast_kwh DESC, id
LIMIT 5;
