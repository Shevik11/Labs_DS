import json,os,re
from pathlib import Path
from collections import defaultdict
from neo4j import GraphDatabase
R=Path(__file__).parent
uri=os.getenv('NEO4J_URI','bolt://127.0.0.1:17692')
pw=os.getenv('NEO4J_PASSWORD')
with GraphDatabase.driver(uri,auth=('neo4j',pw) if pw else None) as d:
 with d.session(database='neo4j') as s:
  s.run('CREATE CONSTRAINT lab8_entity_id IF NOT EXISTS FOR (n:Lab8Entity) REQUIRE n.id IS UNIQUE').consume()
  nodes=json.loads((R/'data/nodes.json').read_text('utf-8'))
  rels=json.loads((R/'data/relationships.json').read_text('utf-8'))
  grouped=defaultdict(list)
  for n in nodes:
   assert all(re.fullmatch(r'[A-Za-z0-9_]+',l) for l in n['labels'])
   grouped[':'.join(n['labels'])].append(dict(n['properties'],id=n['id']))
  for labels,rows in grouped.items():
   for i in range(0,len(rows),1000):s.run('UNWIND $rows AS p MERGE (n:Lab8Entity {id:p.id}) SET n:'+labels+' SET n += p',rows=rows[i:i+1000]).consume()
  grouped=defaultdict(list)
  for e in rels:
   assert re.fullmatch(r'[A-Z0-9_]+',e['type'])
   grouped[e['type']].append(e)
  for typ,rows in grouped.items():
   for i in range(0,len(rows),1000):s.run('UNWIND $rows AS p MATCH (a:Lab8Entity {id:p.source}),(b:Lab8Entity {id:p.target}) MERGE (a)-[e:'+typ+']->(b) SET e += p.properties',rows=rows[i:i+1000]).consume()
  counts=dict(s.run('MATCH (n:Lab8Entity) WITH count(n) AS nodes MATCH (:Lab8Entity)-[r]->(:Lab8Entity) RETURN nodes,count(r) AS relationships').single())
  (R/'results/import.json').write_text(json.dumps(counts,indent=2),'utf-8')
  print(counts)
