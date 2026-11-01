MATCH p=(c:Lab8Entity:OntologyClass)
        -[:SUBCLASS_OF*1..]->(root:Lab8Entity:OntologyClass {id:$rootId})
RETURN DISTINCT c.id AS descendant, c.name AS name, length(p) AS hops
ORDER BY hops, descendant;
