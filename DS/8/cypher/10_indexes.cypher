CREATE RANGE INDEX lab8_observation_time IF NOT EXISTS FOR (n:Lab8Observation) ON (n.objectId, n.timestamp);
CREATE RANGE INDEX lab8_forecast_time IF NOT EXISTS FOR (n:Lab8Forecast) ON (n.targetTime);
CREATE RANGE INDEX lab8_entity_name IF NOT EXISTS FOR (n:Lab8Entity) ON (n.name);
CALL db.awaitIndexes(300);
SHOW INDEXES;
