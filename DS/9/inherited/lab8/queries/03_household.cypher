MATCH p=(h:Lab8Entity {id: 'owl:household'})-[:HAS_METER]->(m:Lab8Entity) RETURN p;
