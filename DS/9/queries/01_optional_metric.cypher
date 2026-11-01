MATCH (n:Lab8Entity:OntologyIndividual)
OPTIONAL MATCH (n)-[:EVALUATED_BY]->(metric:Lab8Entity)
RETURN n.id AS id, n.name AS name, metric.id AS metric_id,
       metric.metricValue AS metric_value
ORDER BY id;
