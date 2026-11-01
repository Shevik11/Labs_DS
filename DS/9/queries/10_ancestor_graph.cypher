MATCH p=(:Lab8Entity:OntologyClass {id:$classId})-[:SUBCLASS_OF*1..]->(:Lab8Entity:OntologyClass)
RETURN p;
