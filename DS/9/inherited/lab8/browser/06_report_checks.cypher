// 1. Compact table: all four indexes, fully visible. Run this statement separately.
SHOW INDEXES YIELD name, state, type, labelsOrTypes, properties
WHERE name STARTS WITH 'lab8_'
RETURN name, state, type, labelsOrTypes, properties
ORDER BY name;

// 2. Execution plan. Run separately, then open the Plan tab.
PROFILE
MATCH (m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity)
WHERE m.objectId = 'household'
  AND m.timestamp >= localdatetime('2009-09-09T00:00:00')
  AND m.timestamp < localdatetime('2009-09-10T00:00:00')
RETURN h.name AS household, date(m.timestamp) AS day,
       count(m) AS hours, sum(m.numericValue) AS energy_kwh
ORDER BY day;
