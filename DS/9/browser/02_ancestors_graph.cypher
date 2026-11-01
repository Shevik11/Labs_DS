MATCH p=(:Lab8Entity:OntologyClass {id:"class:HighConsumptionForecast"})-[:SUBCLASS_OF*1..]->(:Lab8Entity:OntologyClass)
RETURN p;
