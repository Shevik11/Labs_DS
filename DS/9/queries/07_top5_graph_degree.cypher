MATCH (n:Lab8Entity)
OPTIONAL MATCH (n)-[r]-(other:Lab8Entity)
WITH n,count(r) AS degree
RETURN n.id AS id, n.name AS name, labels(n) AS labels, degree
ORDER BY degree DESC,id
LIMIT 5;
