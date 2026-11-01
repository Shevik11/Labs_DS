MATCH (f:Lab8Entity:OntologyIndividual:ForecastResult)-[:GENERATED_BY]->(m:Lab8Entity:OntologyIndividual),
      (f)-[:EVALUATED_BY]->(metric:Lab8Entity:OntologyIndividual)
RETURN f.iri AS forecast, m.iri AS model, f.forecastKwh AS value,
       metric.metricValue AS mae, metric.evaluationScope AS scope
ORDER BY forecast,model;
