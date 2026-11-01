// 01_counts: Кількість вузлів і зв’язків
MATCH (n:Lab8Entity) RETURN count(n) AS nodes;

// 02_ontology_graph: Онтологія та успадкування
MATCH p=(c:Lab8Entity:OntologyClass)-[:SUBCLASS_OF]->(parent:Lab8Entity:OntologyClass) RETURN p;

// 03_household: Об’єкт та засоби обліку
MATCH p=(h:Lab8Entity {id: 'owl:household'})-[:HAS_METER]->(m:Lab8Entity) RETURN p;

// 04_semantic_forecast: Походження прогнозу й результат семантичного висновку №6
MATCH p=(v:Lab8Entity {id:'owl:forecastChart'})-[:PRESENTS_RESULT]->(f:Lab8Entity)-[:GENERATED_BY]->(m:Lab8Entity) RETURN p, f.forecastKwh AS forecast_kwh, labels(v) AS visualization_types, labels(f) AS forecast_types;

// 05_hourly_window: Вимірювання за добу
MATCH (m:Lab8Observation) WHERE m.objectId="household" AND m.timestamp >= localdatetime("2009-09-09T00:00:00") AND m.timestamp < localdatetime("2009-09-10T00:00:00") RETURN m.timestamp AS timestamp, m.numericValue AS energy_kwh ORDER BY timestamp;

// 06_high_forecasts: Перші прогнози понад навчальний поріг
MATCH (f:Lab8Forecast) WHERE f.targetTime >= localdatetime("2009-09-09T00:00:00") AND f.targetTime < localdatetime("2009-09-10T00:00:00") AND f.forecastKwh > 1.5613 RETURN f.targetTime AS timestamp, f.forecastKwh AS forecast_kwh, f.predictedHigh AS classifier_label ORDER BY timestamp;

// 07_daily_energy: Агрегація енергії та шлях до об’єкта
MATCH (m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity) WHERE m.objectId="household" AND m.timestamp >= localdatetime("2009-09-09T00:00:00") AND m.timestamp < localdatetime("2009-09-10T00:00:00") RETURN h.name AS household, date(m.timestamp) AS day, count(m) AS hours, sum(m.numericValue) AS energy_kwh ORDER BY day;

// 08_forecast_errors: Похибки прогнозів зі зв’язками на модель та факт
MATCH (f:Lab8Forecast)-[:GENERATED_BY]->(model:Lab8Entity) MATCH (f)-[:COMPARED_WITH]->(m:Lab8Observation) WHERE f.targetTime >= localdatetime("2009-09-09T00:00:00") AND f.targetTime < localdatetime("2009-09-10T00:00:00") RETURN model.algorithm AS algorithm, count(f) AS forecasts, avg(abs(f.forecastKwh-m.numericValue)) AS mae_kwh, avg(abs(f.persistenceKwh-m.numericValue)) AS persistence_mae_kwh;

// 09_forecast_paths: Багатокроковий шлях прогноз → факт → об’єкт
MATCH (f:Lab8Forecast)-[:COMPARED_WITH]->(m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity) WHERE f.targetTime >= localdatetime("2009-09-09T00:00:00") AND f.targetTime < localdatetime("2009-09-10T00:00:00") AND f.forecastKwh > 1.5613 RETURN h.name AS household, count(f) AS high_forecasts, max(abs(f.forecastKwh-m.numericValue)) AS max_error_kwh;

// 10_measurement_graph: Граф одного реального вимірювання
MATCH (m:Lab8Entity {id:'measurement:2009-09-09T20:00:00'})-[r:MEASUREMENT_OF|RECORDED_BY|HAS_UNIT|OBSERVES_INDICATOR]->(n:Lab8Entity) RETURN m,r,n;

// 11_all_test_mae: Відтворення MAE на всіх 9530 збережених прогнозах
MATCH (f:Lab8Forecast)-[:COMPARED_WITH]->(m:Lab8Observation) RETURN count(f) AS test_rows, avg(abs(f.forecastKwh-m.numericValue)) AS mae_kwh, avg(abs(f.persistenceKwh-m.numericValue)) AS persistence_mae_kwh;
