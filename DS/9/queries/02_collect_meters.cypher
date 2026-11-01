MATCH (h:Lab8Entity:OntologyIndividual {id:$householdId})
      -[:HAS_METER]->(m:Lab8Entity:OntologyIndividual)
WITH h,m ORDER BY m.id
RETURN h.id AS household, count(m) AS meter_count,
       collect(m.id) AS meters, collect(m.name) AS meter_names;
