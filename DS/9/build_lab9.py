import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter, deque
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef
from rdflib.compare import isomorphic

ROOT = Path(__file__).resolve().parent
LAB8 = ROOT / 'inherited/lab8'
NS = 'https://example.org/lnu/energy-visualization#'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def semantic_graph():
    asserted = Graph().parse(LAB8 / 'inputs/lab6.owl')
    xml = ET.fromstring((LAB8 / 'inputs/lab6_inferred.owl').read_bytes())
    key = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}nodeID'
    for element in xml.iter():
        if key in element.attrib:
            element.attrib[key] = 'b' + element.attrib[key]
    inferred = Graph().parse(data=ET.tostring(xml), format='xml')
    union = asserted + inferred
    classes = {s for s in asserted.subjects(RDF.type, OWL.Class)
               if isinstance(s, URIRef) and str(s).startswith(NS)}
    # Match the lab8 projection's existing, materialized named-class membership.
    # This is not a new OWL reasoner run and does not claim full OWL closure.
    for person in asserted.subjects(RDF.type, OWL.NamedIndividual):
        pending = [c for c in union.objects(person, RDF.type) if c in classes]
        seen = set(pending)
        while pending:
            cls = pending.pop()
            for parent in asserted.objects(cls, RDFS.subClassOf):
                if parent in classes and parent not in seen:
                    seen.add(parent)
                    pending.append(parent)
        for cls in seen:
            union.add((person, RDF.type, cls))
    return asserted, inferred, union


def main():
    nodes = json.loads((LAB8 / 'data/nodes.json').read_text(encoding='utf-8'))
    edges = json.loads((LAB8 / 'data/relationships.json').read_text(encoding='utf-8'))
    by_id = {n['id']: n for n in nodes}
    individual_ids = {n['id'] for n in nodes if 'OntologyIndividual' in n['labels']}
    domain_types = sorted({e['type'] for e in edges
                           if e['source'] in individual_ids and e['target'] in individual_ids})
    query_specs = [
        ('01_optional_metric', 'Які онтологічні екземпляри мають метрику оцінювання, а які — ні?',
         '''MATCH (n:Lab8Entity:OntologyIndividual)
OPTIONAL MATCH (n)-[:EVALUATED_BY]->(metric:Lab8Entity)
RETURN n.id AS id, n.name AS name, metric.id AS metric_id,
       metric.metricValue AS metric_value
ORDER BY id''', ['MATCH', 'OPTIONAL MATCH', 'ORDER BY']),
        ('02_collect_meters', 'Які засоби обліку належать домогосподарству?',
         '''MATCH (h:Lab8Entity:OntologyIndividual {id:$householdId})
      -[:HAS_METER]->(m:Lab8Entity:OntologyIndividual)
WITH h,m ORDER BY m.id
RETURN h.id AS household, count(m) AS meter_count,
       collect(m.id) AS meters, collect(m.name) AS meter_names''',
         ['MATCH', 'parameters', 'count', 'collect', 'ORDER BY']),
        ('03_top_high_forecasts', 'Які п’ять найбільших прогнозів понад поріг за обрану добу?',
         '''MATCH (f:Lab8Forecast)
WHERE f.targetTime >= localdatetime($start)
  AND f.targetTime < localdatetime($end)
  AND f.forecastKwh > $threshold
RETURN f.id AS id, toString(f.targetTime) AS timestamp, f.forecastKwh AS forecast_kwh
ORDER BY forecast_kwh DESC, id
LIMIT 5''', ['MATCH', 'WHERE', 'parameters', 'ORDER BY', 'LIMIT']),
        ('04_ancestors', 'Які всі предки класу прогнозу підвищеного споживання?',
         '''MATCH p=(c:Lab8Entity:OntologyClass {id:$classId})
        -[:SUBCLASS_OF*1..]->(a:Lab8Entity:OntologyClass)
RETURN DISTINCT a.id AS ancestor, a.name AS name, length(p) AS hops
ORDER BY hops, ancestor''', ['MATCH', 'variable_length', 'parameters']),
        ('05_descendants', 'Які всі нащадки кореневого класу DomainEntity?',
         '''MATCH p=(c:Lab8Entity:OntologyClass)
        -[:SUBCLASS_OF*1..]->(root:Lab8Entity:OntologyClass {id:$rootId})
RETURN DISTINCT c.id AS descendant, c.name AS name, length(p) AS hops
ORDER BY hops, descendant''', ['MATCH', 'variable_length', 'parameters']),
        ('06_shortest_path', 'Який найкоротший шлях від аналітика до kWh у підграфі 26 початкових індивідів?',
         '''MATCH (a:Lab8Entity:OntologyIndividual {id:$pathStart}),
      (b:Lab8Entity:OntologyIndividual {id:$pathEnd})
MATCH p=shortestPath((a)-[:''' + '|'.join(domain_types) + '''*1..8]-(b))
WHERE all(n IN nodes(p) WHERE n:OntologyIndividual)
RETURN p, length(p) AS hops,
       [n IN nodes(p) | n.id] AS node_ids,
       [r IN relationships(p) | type(r)] AS relationship_types''',
         ['MATCH', 'shortestPath', 'parameters']),
        ('07_top5_graph_degree', 'Які п’ять вузлів мають найбільшу кількість інцидентних ребер у повному графі?',
         '''MATCH (n:Lab8Entity)
OPTIONAL MATCH (n)-[r]-(other:Lab8Entity)
WITH n,count(r) AS degree
RETURN n.id AS id, n.name AS name, labels(n) AS labels, degree
ORDER BY degree DESC,id
LIMIT 5''', ['MATCH', 'OPTIONAL MATCH', 'count', 'ORDER BY', 'LIMIT', 'degree']),
        ('08_top5_class_degree', 'Які п’ять онтологічних понять найбільш зв’язані у повному графі?',
         '''MATCH (n:Lab8Entity:OntologyClass)
OPTIONAL MATCH (n)-[r]-(other:Lab8Entity)
WITH n,count(r) AS degree
RETURN n.id AS id, n.name AS name, degree
ORDER BY degree DESC,id
LIMIT 5''', ['MATCH', 'OPTIONAL MATCH', 'count', 'ORDER BY', 'LIMIT', 'degree']),
        ('09_forecast_mae', 'Яка середня абсолютна похибка прогнозів за обрану добу?',
         (LAB8 / 'queries/08_forecast_errors.cypher').read_text(encoding='utf-8').strip().rstrip(';'),
         ['MATCH', 'WHERE', 'parameters', 'count', 'avg']),
        ('10_ancestor_graph', 'Як виглядає підграф усіх предків обраного класу?',
         '''MATCH p=(:Lab8Entity:OntologyClass {id:$classId})-[:SUBCLASS_OF*1..]->(:Lab8Entity:OntologyClass)
RETURN p''', ['MATCH', 'variable_length', 'parameters', 'graph_visualization']),
        ('11_shortest_full_graph', 'Який найкоротший шлях від аналітика до kWh, якщо дозволити також вузли класів?',
         '''MATCH (a:Lab8Entity {id:$pathStart}), (b:Lab8Entity {id:$pathEnd})
MATCH p=shortestPath((a)-[*1..8]-(b))
RETURN p, length(p) AS hops, [n IN nodes(p) | n.id] AS node_ids,
       [r IN relationships(p) | type(r)] AS relationship_types''',
         ['MATCH', 'shortestPath', 'parameters', 'graph_visualization']),
    ]
    catalog = []
    for identifier, question, query, features in query_specs:
        origin = 'reused_lab8_query_08' if identifier.startswith('09_') else 'new_lab9'
        path = ROOT / 'queries' / (identifier + '.cypher')
        path.parent.mkdir(exist_ok=True)
        path.write_text(query + ';\n', encoding='utf-8')
        catalog.append({'id': identifier, 'question': question, 'query': query,
                        'features': features, 'origin': origin})
    params = {'householdId': 'owl:household', 'classId': 'class:HighConsumptionForecast',
              'rootId': 'class:DomainEntity', 'pathStart': 'owl:analyst', 'pathEnd': 'owl:kWh',
              **json.loads((LAB8 / 'queries/parameters.json').read_text(encoding='utf-8'))}
    dump(ROOT / 'queries/parameters.json', params)
    dump(ROOT / 'queries/catalog.json', catalog)
    prefix = 'PREFIX energy: <' + NS + '>\n'
    pairs = [
        {'id': 'C1_household_meters', 'question': 'Які засоби обліку належать домогосподарству?',
         'sparql': prefix + 'SELECT ?meter WHERE { energy:household energy:hasMeter ?meter } ORDER BY ?meter',
         'cypher': '''MATCH (:Lab8Entity:OntologyIndividual {id:$householdId})-[:HAS_METER]->(m:Lab8Entity:OntologyIndividual)
RETURN m.iri AS meter ORDER BY meter''', 'numeric_columns': [],
         'previous_sparql': 'D:/LNU/DS/5/queries/01_household_meters.rq'},
        {'id': 'C2_forecast_provenance', 'question': 'Які модель, прогноз і метрика оцінювання пов’язані між собою?',
         'sparql': prefix + '''SELECT ?forecast ?model ?value ?mae ?scope WHERE {
  ?forecast a energy:ForecastResult; energy:generatedBy ?model;
    energy:forecastKwh ?value; energy:evaluatedBy ?metric .
  ?metric energy:metricValue ?mae; energy:evaluationScope ?scope
} ORDER BY ?forecast ?model''',
         'cypher': '''MATCH (f:Lab8Entity:OntologyIndividual:ForecastResult)-[:GENERATED_BY]->(m:Lab8Entity:OntologyIndividual),
      (f)-[:EVALUATED_BY]->(metric:Lab8Entity:OntologyIndividual)
RETURN f.iri AS forecast, m.iri AS model, f.forecastKwh AS value,
       metric.metricValue AS mae, metric.evaluationScope AS scope
ORDER BY forecast,model''', 'numeric_columns': ['value', 'mae'],
         'previous_sparql': 'D:/LNU/DS/5/queries/03_forecast_provenance.rq'},
        {'id': 'C3_inferred_visualization', 'question': 'Які подання мають тип ForecastVisualization з урахуванням збережених висновків?',
         'sparql': prefix + 'SELECT ?view WHERE { ?view a energy:ForecastVisualization } ORDER BY ?view',
         'cypher': '''MATCH (v:Lab8Entity:OntologyIndividual:ForecastVisualization)
RETURN v.iri AS view ORDER BY view''', 'numeric_columns': [],
         'previous_sparql': 'D:/LNU/DS/5/queries/04_inferred_visualization.rq'},
    ]
    for pair in pairs:
        for field, ext in [('sparql', 'rq'), ('cypher', 'cypher')]:
            file = ROOT / 'comparison' / (pair['id'] + '.' + ext)
            file.parent.mkdir(exist_ok=True)
            file.write_text(pair[field] + (';\n' if ext == 'cypher' else '\n'), encoding='utf-8')
    dump(ROOT / 'comparison/catalog.json', pairs)
    asserted, inferred, union = semantic_graph()
    (ROOT / 'data').mkdir(exist_ok=True)
    asserted.serialize(ROOT / 'data/ontology_asserted.ttl', format='turtle')
    union.serialize(ROOT / 'data/ontology_semantic.ttl', format='turtle')
    roundtrip = Graph().parse(ROOT / 'data/ontology_asserted.ttl')
    if not isomorphic(asserted, roundtrip):
        raise RuntimeError('Turtle roundtrip changed the source graph')
    degree = Counter()
    adjacency = {}
    full_adjacency = {}
    parents = {}
    for edge in edges:
        degree[edge['source']] += 1
        degree[edge['target']] += 1
        full_adjacency.setdefault(edge['source'], set()).add(edge['target'])
        full_adjacency.setdefault(edge['target'], set()).add(edge['source'])
        if edge['type'] == 'SUBCLASS_OF':
            parents.setdefault(edge['source'], []).append(edge['target'])
        if edge['source'] in individual_ids and edge['target'] in individual_ids:
            adjacency.setdefault(edge['source'], set()).add(edge['target'])
            adjacency.setdefault(edge['target'], set()).add(edge['source'])
    def distances(start, graph):
        result = {start: 0}
        pending = deque([start])
        while pending:
            current = pending.popleft()
            for other in graph.get(current, []):
                if other not in result:
                    result[other] = result[current] + 1
                    pending.append(other)
        return result
    ancestors = distances(params['classId'], parents)
    ancestors.pop(params['classId'])
    descendants = {n: d[params['rootId']] for n in parents
                   for d in [distances(n, parents)] if params['rootId'] in d}
    root_distances = distances(params['pathStart'], adjacency)
    reference = {'nodes': len(nodes), 'relationships': len(edges),
                 'labels': dict(sorted(Counter(label for n in nodes for label in n['labels']).items())),
                 'label_sets': dict(sorted(Counter('|'.join(sorted(n['labels'])) for n in nodes).items())),
                 'class_ids': sorted(n['id'] for n in nodes if 'OntologyClass' in n['labels']),
                 'individual_ids': sorted(individual_ids),
                 'ancestors': ancestors, 'descendants': descendants,
                 'shortest_hops': root_distances[params['pathEnd']],
                 'shortest_full_graph_hops': distances(params['pathStart'], full_adjacency)[params['pathEnd']],
                 'top5_graph_degree': [{'id': n, 'degree': degree[n]}
                                       for n in sorted(by_id, key=lambda n: (-degree[n], n))[:5]],
                 'top5_class_degree': [{'id': n, 'degree': degree[n]}
                                       for n in sorted((n for n in by_id if 'OntologyClass' in by_id[n]['labels']),
                                                       key=lambda n: (-degree[n], n))[:5]],
                 'source_asserted_triples': len(asserted), 'source_inferred_file_triples': len(inferred),
                 'semantic_triples': len(union), 'asserted_turtle_isomorphic': True,
                 'reasoning': 'Saved HermiT facts from lab6 plus named-individual superclass membership from lab8; no new OWL reasoning.',
                 'seed': None, 'deterministic': 'No sampling or random generation is used.'}
    dump(ROOT / 'results/build_validation.json', reference)
    # Literal commands let the user run each screenshot query without setting parameters.
    browser = ROOT / 'browser'
    browser.mkdir(exist_ok=True)
    def literals(query):
        for key in sorted(params, key=len, reverse=True):
            query = query.replace('$' + key, json.dumps(params[key], ensure_ascii=False))
        return query
    (browser / '01_constraints.cypher').write_text(
        "SHOW CONSTRAINTS YIELD name,type,labelsOrTypes,properties\nWHERE name='lab8_entity_id'\nRETURN name,type,labelsOrTypes,properties;\n", encoding='utf-8')
    for filename, query_id in [('02_ancestors_graph', '10_ancestor_graph'),
                               ('03_shortest_path', '06_shortest_path'),
                               ('04_top5_concepts', '08_top5_class_degree')]:
        query = next(x['query'] for x in catalog if x['id'] == query_id)
        (browser / (filename + '.cypher')).write_text(literals(query) + ';\n', encoding='utf-8')
    (browser / '05_comparison.cypher').write_text(
        '\n\n'.join('// ' + p['id'] + '\n' + literals(p['cypher']) + ';' for p in pairs) + '\n', encoding='utf-8')
    (browser / '06_optional_collect_top.cypher').write_text(
        '\n\n'.join('// ' + q['id'] + '\n' + literals(q['query']) + ';' for q in catalog[:3]) + '\n', encoding='utf-8')
    (browser / '07_shortest_full_graph.cypher').write_text(
        literals(catalog[-1]['query']) + ';\n', encoding='utf-8')
    print('Built', len(catalog), 'Cypher scenarios and', len(pairs), 'SPARQL/Cypher pairs.')
    print('RDF:', len(asserted), 'asserted /', len(union), 'semantic triples.')
    print('Independent shortest path:', reference['shortest_hops'], 'hops.')


if __name__ == '__main__':
    main()
