MATCH p=(c:Lab8Entity:OntologyClass {id:$classId})
        -[:SUBCLASS_OF*1..]->(a:Lab8Entity:OntologyClass)
RETURN DISTINCT a.id AS ancestor, a.name AS name, length(p) AS hops
ORDER BY hops, ancestor;
