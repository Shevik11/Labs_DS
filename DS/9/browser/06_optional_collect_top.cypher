// 01_optional_metric
MATCH (n:Lab8Entity:OntologyIndividual)
OPTIONAL MATCH (n)-[:EVALUATED_BY]->(metric:Lab8Entity)
RETURN n.id AS id, n.name AS name, metric.id AS metric_id,
       metric.metricValue AS metric_value
ORDER BY id;

// 02_collect_meters
MATCH (h:Lab8Entity:OntologyIndividual {id:"owl:household"})
      -[:HAS_METER]->(m:Lab8Entity:OntologyIndividual)
WITH h,m ORDER BY m.id
RETURN h.id AS household, count(m) AS meter_count,
       collect(m.id) AS meters, collect(m.name) AS meter_names;

// 03_top_high_forecasts
MATCH (f:Lab8Forecast)
WHERE f.targetTime >= localdatetime("2009-09-09T00:00:00")
  AND f.targetTime < localdatetime("2009-09-10T00:00:00")
  AND f.forecastKwh > 1.5613
RETURN f.id AS id, toString(f.targetTime) AS timestamp, f.forecastKwh AS forecast_kwh
ORDER BY forecast_kwh DESC, id
LIMIT 5;
