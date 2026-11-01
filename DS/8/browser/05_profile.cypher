// 07_daily_energy
PROFILE
MATCH (m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity) WHERE m.objectId="household" AND m.timestamp >= localdatetime("2009-09-09T00:00:00") AND m.timestamp < localdatetime("2009-09-10T00:00:00") RETURN h.name AS household, date(m.timestamp) AS day, count(m) AS hours, sum(m.numericValue) AS energy_kwh ORDER BY day;

// 08_forecast_errors
PROFILE
MATCH (f:Lab8Forecast)-[:GENERATED_BY]->(model:Lab8Entity) MATCH (f)-[:COMPARED_WITH]->(m:Lab8Observation) WHERE f.targetTime >= localdatetime("2009-09-09T00:00:00") AND f.targetTime < localdatetime("2009-09-10T00:00:00") RETURN model.algorithm AS algorithm, count(f) AS forecasts, avg(abs(f.forecastKwh-m.numericValue)) AS mae_kwh, avg(abs(f.persistenceKwh-m.numericValue)) AS persistence_mae_kwh;

// 09_forecast_paths
PROFILE
MATCH (f:Lab8Forecast)-[:COMPARED_WITH]->(m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity) WHERE f.targetTime >= localdatetime("2009-09-09T00:00:00") AND f.targetTime < localdatetime("2009-09-10T00:00:00") AND f.forecastKwh > 1.5613 RETURN h.name AS household, count(f) AS high_forecasts, max(abs(f.forecastKwh-m.numericValue)) AS max_error_kwh;
