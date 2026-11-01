MATCH (n:Lab8Entity:OntologyClass)
OPTIONAL MATCH (n)-[r]-(other:Lab8Entity)
WITH n,count(r) AS degree
RETURN n.id AS id, n.name AS name, degree
ORDER BY degree DESC,id
LIMIT 5;
