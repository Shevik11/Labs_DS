from pathlib import Path
import json
import logging
logging.getLogger('neo4j.notifications').setLevel(logging.ERROR)
from neo4j import GraphDatabase
from build_lab8 import ROOT, dump
from run_neo4j import serial
from rdflib import Graph
from rdflib.compare import isomorphic
from rdflib.util import from_n3

checks={}
with GraphDatabase.driver('bolt://127.0.0.1:17687',auth=None) as driver:
    with driver.session(database='neo4j') as session:
        for name in ['01_ontology.cypher','02_day_data.cypher']:
            transaction=session.begin_transaction()
            try:
                result=transaction.run((ROOT/'browser'/name).read_text(encoding='utf-8'))
                processed=[serial(dict(record)) for record in result]
                summary=result.consume()
                checks[name]={'status':'passed','execution':'executed and rolled back against full local graph',
                              'processed':processed,'new_nodes':summary.counters.nodes_created,
                              'new_relationships':summary.counters.relationships_created}
            finally:
                transaction.rollback()
        count=session.run('MATCH (n:Lab8Entity) RETURN count(n) AS n').single()['n']
        assert count==43746
        period=session.run("MATCH (n:Lab8Entity {id:'data:hourlyDataset'}) RETURN n.recordCount AS n").single()['n']
        assert period==34085
        checks['full_graph_unchanged_after_rollback']=True
triples=json.loads((ROOT/'data/rdf_triples.json').read_text(encoding='utf-8'))
restored=Graph()
for triple in triples:
    restored.add(tuple(from_n3(term) for term in triple))
original=Graph().parse(ROOT/'inputs/lab6.owl')
assert isomorphic(original,restored)
checks['rdf_triples_roundtrip_isomorphic']=True
checks['source_rdf_triples']=len(original)
dump(ROOT/'results/browser_validation.json',checks)
print(json.dumps(checks,ensure_ascii=False,indent=2))
