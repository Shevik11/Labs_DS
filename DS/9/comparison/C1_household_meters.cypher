MATCH (:Lab8Entity:OntologyIndividual {id:$householdId})-[:HAS_METER]->(m:Lab8Entity:OntologyIndividual)
RETURN m.iri AS meter ORDER BY meter;
