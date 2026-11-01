// C1_household_meters
MATCH (:Lab8Entity:OntologyIndividual {id:"owl:household"})-[:HAS_METER]->(m:Lab8Entity:OntologyIndividual)
RETURN m.iri AS meter ORDER BY meter;

// C2_forecast_provenance
MATCH (f:Lab8Entity:OntologyIndividual:ForecastResult)-[:GENERATED_BY]->(m:Lab8Entity:OntologyIndividual),
      (f)-[:EVALUATED_BY]->(metric:Lab8Entity:OntologyIndividual)
RETURN f.iri AS forecast, m.iri AS model, f.forecastKwh AS value,
       metric.metricValue AS mae, metric.evaluationScope AS scope
ORDER BY forecast,model;

// C3_inferred_visualization
MATCH (v:Lab8Entity:OntologyIndividual:ForecastVisualization)
RETURN v.iri AS view ORDER BY view;
