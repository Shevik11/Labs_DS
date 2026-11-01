MATCH (a:Lab8Entity {id:"owl:analyst"}), (b:Lab8Entity {id:"owl:kWh"})
MATCH p=shortestPath((a)-[*1..8]-(b))
RETURN p, length(p) AS hops, [n IN nodes(p) | n.id] AS node_ids,
       [r IN relationships(p) | type(r)] AS relationship_types;
