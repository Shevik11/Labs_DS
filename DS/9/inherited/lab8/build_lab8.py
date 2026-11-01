import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from rdflib import Graph, Literal, OWL, RDF, RDFS, URIRef

ROOT = Path(__file__).resolve().parent
NS = 'https://example.org/lnu/energy-visualization#'
TEMPORAL = {'timestamp', 'targetTime', 'startTime', 'endTime'}
BASE_LABEL = 'Lab8Entity'

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def local(term):
    return str(term).rsplit('#', 1)[-1]

def relname(name):
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).upper()

def label_for(graph, subject):
    return str(next(graph.objects(subject, RDFS.label), local(subject)))

def literal_value(value):
    converted = value.toPython()
    if isinstance(converted, bool):
        return converted
    if isinstance(converted, int):
        return converted
    if str(value.datatype).endswith(('#decimal', '#double', '#float')):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite RDF literal')
        return number
    return str(value)

def cypher(value):
    if isinstance(value, dict):
        return '{' + ','.join('`' + k.replace('`', '``') + '`:' + cypher(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(cypher(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False, allow_nan=False)

def node_statement(labels, temporal):
    query = 'UNWIND $rows AS row\nMERGE (n:Lab8Entity {id: row.id})\nSET n += row.properties\n'
    extra = [x for x in sorted(labels) if x != BASE_LABEL]
    if extra:
        query += 'SET n' + ''.join(':' + x for x in extra) + '\n'
    for key in sorted(temporal):
        query += f'SET n.{key} = localdatetime(row.properties.{key})\n'
    return query + 'RETURN count(*) AS processed'

def edge_statement(kind):
    assert re.fullmatch(r'[A-Z][A-Z_0-9]*', kind)
    return ('UNWIND $rows AS row\nMATCH (a:Lab8Entity {id: row.source})\n'
            'MATCH (b:Lab8Entity {id: row.target})\n'
            f'MERGE (a)-[r:{kind}]->(b)\nSET r += row.properties\nRETURN count(*) AS processed')

def group_nodes(nodes):
    groups = defaultdict(list)
    for node in nodes:
        temporal = tuple(sorted(set(node['properties']) & TEMPORAL))
        groups[(tuple(sorted(node['labels'])), temporal)].append(node)
    return groups

def browser_script(nodes, edges):
    blocks, totals = [], []
    for index, ((labels, temporal), rows) in enumerate(group_nodes(nodes).items()):
        alias = f'n{index}'
        statement = node_statement(labels, temporal).replace('$rows', cypher(rows))
        statement = statement.rsplit('RETURN count(*) AS processed', 1)[0] + f'RETURN count(*) AS {alias}'
        blocks.append('CALL () {\n' + statement + '\n}')
        totals.append(alias)
    for index, (kind, rows) in enumerate(group_edges(edges).items()):
        alias = f'r{index}'
        statement = edge_statement(kind).replace('$rows', cypher(rows))
        statement = statement.rsplit('RETURN count(*) AS processed', 1)[0] + f'RETURN count(*) AS {alias}'
        blocks.append('CALL () {\n' + statement + '\n}')
        totals.append(alias)
    return '\n'.join(blocks) + '\nRETURN ' + ', '.join(totals) + ';\n'

def group_edges(edges):
    groups = defaultdict(list)
    for edge in edges:
        groups[edge['type']].append(edge)
    return groups

def main():
    for folder in ('data', 'cypher', 'queries', 'browser', 'results', 'figures', 'results/screenshots'):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    asserted = Graph().parse(ROOT / 'inputs/lab6.owl')
    # Owlready2 emits numeric blank-node IDs; prefix them in memory for strict RDF/XML.
    xml = ET.fromstring((ROOT / 'inputs/lab6_inferred.owl').read_bytes())
    node_key = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}nodeID'
    for element in xml.iter():
        if node_key in element.attrib:
            element.attrib[node_key] = 'b' + element.attrib[node_key]
    inferred = Graph().parse(data=ET.tostring(xml), format='xml')
    combined = asserted + inferred
    classes = {x for x in asserted.subjects(RDF.type, OWL.Class) if isinstance(x, URIRef) and str(x).startswith(NS)}
    individuals = set(asserted.subjects(RDF.type, OWL.NamedIndividual))
    object_properties = set(asserted.subjects(RDF.type, OWL.ObjectProperty))
    data_properties = set(asserted.subjects(RDF.type, OWL.DatatypeProperty))
    nodes, edge_lookup = {}, {}

    def node(node_id, labels, **properties):
        if node_id in nodes:
            raise ValueError('Duplicate node: ' + node_id)
        nodes[node_id] = {'id': node_id, 'labels': sorted(set(labels) | {BASE_LABEL}),
                             'properties': {'scope': 'lab8_energy', **properties}}

    def edge(source, kind, target, **properties):
        key = (source, kind, target)
        if key in edge_lookup:
            raise ValueError('Duplicate relationship: ' + str(key))
        edge_lookup[key] = {'source': source, 'type': kind, 'target': target, 'properties': properties}

    for cls in sorted(classes):
        identifier = 'class:' + local(cls)
        node(identifier, ['OntologyClass'], name=label_for(asserted, cls), iri=str(cls), source='lab6.owl')
    for cls in sorted(classes):
        for parent in asserted.objects(cls, RDFS.subClassOf):
            if parent in classes:
                edge('class:' + local(cls), 'SUBCLASS_OF', 'class:' + local(parent), provenance='asserted')
    for prop in sorted(object_properties | data_properties):
        node('property:' + local(prop), ['OntologyProperty'], name=label_for(asserted, prop), iri=str(prop),
             propertyKind='object' if prop in object_properties else 'datatype',
             neo4jName=relname(local(prop)) if prop in object_properties else local(prop),
             functional=(prop, RDF.type, OWL.FunctionalProperty) in asserted)
        for pred, kind in ((RDFS.domain, 'DOMAIN'), (RDFS.range, 'RANGE')):
            for target in asserted.objects(prop, pred):
                if target in classes:
                    edge('property:' + local(prop), kind, 'class:' + local(target), provenance='asserted')

    for individual in sorted(individuals):
        explicit_types = {x for x in asserted.objects(individual, RDF.type) if x in classes}
        all_types = {x for x in combined.objects(individual, RDF.type) if x in classes} | explicit_types
        pending = list(all_types)
        while pending:
            cls = pending.pop()
            for parent in asserted.objects(cls, RDFS.subClassOf):
                if parent in classes and parent not in all_types:
                    all_types.add(parent)
                    pending.append(parent)
        props = {'name': label_for(asserted, individual), 'iri': str(individual), 'source': 'lab6.owl',
                 'comment': str(next(asserted.objects(individual, RDFS.comment), ''))}
        for prop in data_properties:
            values = list(asserted.objects(individual, prop))
            if values:
                if len(values) != 1:
                    raise ValueError('Multivalued datatype property requires explicit projection: ' + str(prop))
                props[local(prop)] = literal_value(values[0])
        node('owl:' + local(individual), ['OntologyIndividual'] + sorted(local(x) for x in all_types), **props)
        for cls in sorted(all_types):
            edge('owl:' + local(individual), 'TYPE_OF', 'class:' + local(cls),
                 provenance='asserted' if cls in explicit_types else 'inferred_lab6_or_subclass')
    for source in sorted(individuals):
        for prop in sorted(object_properties):
            for target in sorted(set(combined.objects(source, prop))):
                if target in individuals:
                    edge('owl:' + local(source), relname(local(prop)), 'owl:' + local(target),
                         iri=str(prop), provenance='asserted' if (source, prop, target) in asserted else 'inferred_lab6')

    ontology_ids = set(nodes)
    ontology_edges = list(edge_lookup.values())
    rows = list(csv.DictReader((ROOT / 'inputs/hourly_clean.csv').open(encoding='utf-8')))
    predictions = list(csv.DictReader((ROOT / 'inputs/test_predictions.csv').open(encoding='utf-8')))
    metrics = json.loads((ROOT / 'inputs/metrics.json').read_text(encoding='utf-8'))
    threshold = metrics['split']['high_threshold_kwh']
    first = datetime.fromisoformat(rows[0]['timestamp'])
    last = datetime.fromisoformat(rows[-1]['timestamp'])
    expected_hours = int((last - first).total_seconds() / 3600) + 1
    node('data:hourlyDataset', ['Dataset'], name='Усі повні години з ЛР1', recordCount=len(rows),
         source='lab1/hourly_clean.csv', sourceURI=metrics['source']['url'], license='CC BY 4.0')
    node('data:hourlySeries', ['TimeSeries'], name='Повний доступний годинний ряд ЛР1',
         stepMinutes=60, missingCount=expected_hours - len(rows), source='lab1/hourly_clean.csv')
    node('data:hourlyPeriod', ['TimeInterval'], name='Період усіх годинних вимірювань',
         startTime=first.isoformat(), endTime=(last + timedelta(hours=1)).isoformat(),
         timeContext='Час джерела без UTC-зсуву; localdatetime, не Europe/Kyiv')
    edge('data:hourlyDataset', 'CONTAINS_SERIES', 'data:hourlySeries', provenance='lab8_extension')
    edge('data:hourlySeries', 'SERIES_OF', 'owl:household', provenance='lab8_extension')
    edge('data:hourlySeries', 'SERIES_INDICATOR', 'owl:energy', provenance='lab8_extension')
    edge('data:hourlySeries', 'COVERS_INTERVAL', 'data:hourlyPeriod', provenance='lab8_extension')
    by_time = {}
    for row in rows:
        ts = datetime.fromisoformat(row['timestamp']).isoformat()
        identifier = 'measurement:' + ts
        if ts in by_time:
            raise ValueError('Duplicate hourly timestamp')
        by_time[ts] = row
        node(identifier, ['Measurement', 'EnergyMeasurement', 'Lab8Observation'],
             name='Енергія ' + ts, timestamp=ts, numericValue=float(row['energy_kwh']),
             activePowerKw=float(row['Global_active_power']), voltageV=float(row['Voltage']),
             objectId='household', unit='kWh', qualityFlag='complete_hour', source='lab1/hourly_clean.csv')
        edge('data:hourlySeries', 'HAS_MEASUREMENT', identifier, provenance='lab1')
        edge(identifier, 'MEASUREMENT_OF', 'owl:household', provenance='lab8_materialized_chain')
        edge(identifier, 'RECORDED_BY', 'owl:meter', provenance='lab8_channel_mapping')
        edge(identifier, 'OBSERVES_INDICATOR', 'owl:energy', provenance='lab1')
        edge(identifier, 'HAS_UNIT', 'owl:kWh', provenance='lab1')
    for row in predictions:
        ts = datetime.fromisoformat(row['target_timestamp']).isoformat()
        if ts not in by_time or abs(float(by_time[ts]['energy_kwh']) - float(row['actual_kwh'])) > 1e-9:
            raise ValueError('Forecast target differs from the hourly observation: ' + ts)
        identifier = 'forecast:' + ts
        high = float(row['predicted_kwh']) > threshold
        node(identifier, ['ForecastResult', 'AnalysisResult', 'Lab8Forecast',
                          'HighConsumptionForecast' if high else 'NonHighConsumptionForecast'],
             name='Прогноз ' + ts, targetTime=ts, forecastKwh=float(row['predicted_kwh']),
             actualKwh=float(row['actual_kwh']), persistenceKwh=float(row['persistence_kwh']),
             actualHigh=int(row['actual_high']), predictedHigh=int(row['predicted_high']),
             probabilityHigh=float(row['probability_high']), highByRegression=high,
             source='lab1/test_predictions.csv', thresholdKwh=threshold)
        edge(identifier, 'GENERATED_BY', 'owl:regressor', provenance='lab1')
        edge(identifier, 'COMPARED_WITH', 'measurement:' + ts, provenance='lab8_extension')
        edge(identifier, 'DERIVED_FROM_SERIES', 'data:hourlySeries', provenance='lab8_target_series')
    edges = sorted(edge_lookup.values(), key=lambda e: (e['type'], e['source'], e['target']))
    node_list = sorted(nodes.values(), key=lambda n: n['id'])
    missing = {(e['source'], e['target']) for e in edges if e['source'] not in nodes or e['target'] not in nodes}
    if missing:
        raise ValueError('Dangling endpoints: ' + str(missing))
    dump(ROOT / 'data/nodes.json', node_list)
    dump(ROOT / 'data/relationships.json', edges)
    with (ROOT / 'data/nodes.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['id', 'labels', 'properties_json'])
        writer.writerows((n['id'], ';'.join(n['labels']), json.dumps(n['properties'], ensure_ascii=False)) for n in node_list)
    with (ROOT / 'data/relationships.csv').open('w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['source', 'type', 'target', 'properties_json'])
        writer.writerows((e['source'], e['type'], e['target'], json.dumps(e['properties'], ensure_ascii=False)) for e in edges)
    dump(ROOT / 'data/rdf_triples.json', sorted([[s.n3(), p.n3(), o.n3()] for s, p, o in asserted]))
    constraint = 'CREATE CONSTRAINT lab8_entity_id IF NOT EXISTS FOR (n:Lab8Entity) REQUIRE n.id IS UNIQUE'
    indexes = [
        'CREATE RANGE INDEX lab8_observation_time IF NOT EXISTS FOR (n:Lab8Observation) ON (n.objectId, n.timestamp)',
        'CREATE RANGE INDEX lab8_forecast_time IF NOT EXISTS FOR (n:Lab8Forecast) ON (n.targetTime)',
        'CREATE RANGE INDEX lab8_entity_name IF NOT EXISTS FOR (n:Lab8Entity) ON (n.name)',
    ]
    (ROOT / 'cypher/00_constraint.cypher').write_text(constraint + ';\n', encoding='utf-8')
    (ROOT / 'cypher/10_indexes.cypher').write_text(';\n'.join(indexes) + ';\nCALL db.awaitIndexes(300);\nSHOW INDEXES;\n', encoding='utf-8')
    dump(ROOT / 'data/schema.json', {'constraint': constraint, 'indexes': indexes})

    start = datetime.fromisoformat(predictions[0]['target_timestamp']).replace(hour=0).isoformat()
    end = (datetime.fromisoformat(start) + timedelta(days=1)).isoformat()
    params = {'objectId': 'household', 'start': start, 'end': end, 'threshold': threshold}
    queries = [
        ('01_counts', 'Кількість вузлів і зв’язків', 'MATCH (n:Lab8Entity) RETURN count(n) AS nodes'),
        ('02_ontology_graph', 'Онтологія та успадкування',
         'MATCH p=(c:Lab8Entity:OntologyClass)-[:SUBCLASS_OF]->(parent:Lab8Entity:OntologyClass) RETURN p'),
        ('03_household', 'Об’єкт та засоби обліку',
         "MATCH p=(h:Lab8Entity {id: 'owl:household'})-[:HAS_METER]->(m:Lab8Entity) RETURN p"),
        ('04_semantic_forecast', 'Походження прогнозу й результат семантичного висновку №6',
         "MATCH p=(v:Lab8Entity {id:'owl:forecastChart'})-[:PRESENTS_RESULT]->(f:Lab8Entity)-[:GENERATED_BY]->(m:Lab8Entity) RETURN p, f.forecastKwh AS forecast_kwh, labels(v) AS visualization_types, labels(f) AS forecast_types"),
        ('05_hourly_window', 'Вимірювання за добу',
         'MATCH (m:Lab8Observation) WHERE m.objectId=$objectId AND m.timestamp >= localdatetime($start) AND m.timestamp < localdatetime($end) RETURN m.timestamp AS timestamp, m.numericValue AS energy_kwh ORDER BY timestamp'),
        ('06_high_forecasts', 'Перші прогнози понад навчальний поріг',
         'MATCH (f:Lab8Forecast) WHERE f.targetTime >= localdatetime($start) AND f.targetTime < localdatetime($end) AND f.forecastKwh > $threshold RETURN f.targetTime AS timestamp, f.forecastKwh AS forecast_kwh, f.predictedHigh AS classifier_label ORDER BY timestamp'),
        ('07_daily_energy', 'Агрегація енергії та шлях до об’єкта',
         'MATCH (m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity) WHERE m.objectId=$objectId AND m.timestamp >= localdatetime($start) AND m.timestamp < localdatetime($end) RETURN h.name AS household, date(m.timestamp) AS day, count(m) AS hours, sum(m.numericValue) AS energy_kwh ORDER BY day'),
        ('08_forecast_errors', 'Похибки прогнозів зі зв’язками на модель та факт',
         'MATCH (f:Lab8Forecast)-[:GENERATED_BY]->(model:Lab8Entity) MATCH (f)-[:COMPARED_WITH]->(m:Lab8Observation) WHERE f.targetTime >= localdatetime($start) AND f.targetTime < localdatetime($end) RETURN model.algorithm AS algorithm, count(f) AS forecasts, avg(abs(f.forecastKwh-m.numericValue)) AS mae_kwh, avg(abs(f.persistenceKwh-m.numericValue)) AS persistence_mae_kwh'),
        ('09_forecast_paths', 'Багатокроковий шлях прогноз → факт → об’єкт',
         'MATCH (f:Lab8Forecast)-[:COMPARED_WITH]->(m:Lab8Observation)-[:MEASUREMENT_OF]->(h:Lab8Entity) WHERE f.targetTime >= localdatetime($start) AND f.targetTime < localdatetime($end) AND f.forecastKwh > $threshold RETURN h.name AS household, count(f) AS high_forecasts, max(abs(f.forecastKwh-m.numericValue)) AS max_error_kwh'),
        ('10_measurement_graph', 'Граф одного реального вимірювання',
         "MATCH (m:Lab8Entity {id:'measurement:2009-09-09T20:00:00'})-[r:MEASUREMENT_OF|RECORDED_BY|HAS_UNIT|OBSERVES_INDICATOR]->(n:Lab8Entity) RETURN m,r,n"),
        ('11_all_test_mae', 'Відтворення MAE на всіх 9530 збережених прогнозах',
         'MATCH (f:Lab8Forecast)-[:COMPARED_WITH]->(m:Lab8Observation) RETURN count(f) AS test_rows, avg(abs(f.forecastKwh-m.numericValue)) AS mae_kwh, avg(abs(f.persistenceKwh-m.numericValue)) AS persistence_mae_kwh'),
    ]
    query_specs = []
    for identifier, title, query in queries:
        (ROOT / 'queries' / (identifier + '.cypher')).write_text(query + ';\n', encoding='utf-8')
        query_specs.append({'id': identifier, 'title': title, 'query': query,
                            'benchmark': identifier[:2] in {'07','08','09'}})
    dump(ROOT / 'queries/catalog.json', query_specs)
    dump(ROOT / 'queries/parameters.json', params)
    readable = []
    for spec in query_specs:
        concrete = spec['query']
        for key, value in params.items():
            concrete = concrete.replace('$' + key, cypher(value))
        readable.append('// ' + spec['id'] + ': ' + spec['title'] + '\n' + concrete + ';\n')
    (ROOT / 'browser/04_queries.cypher').write_text('\n'.join(readable), encoding='utf-8')
    (ROOT / 'browser/00_constraint.cypher').write_text(constraint + ';\n', encoding='utf-8')
    (ROOT / 'browser/01_ontology.cypher').write_text(browser_script([nodes[x] for x in sorted(ontology_ids)], ontology_edges), encoding='utf-8')
    # Browser-only fallback imports a one-day subset; the API route imports ALL records.
    subset_ids = {n['id'] for n in node_list if n['id'] in ontology_ids or n['id'].startswith('data:') or
                  start <= n['properties'].get('timestamp', n['properties'].get('targetTime', '')) < end}
    subset_nodes = [n for n in node_list if n['id'] in subset_ids - ontology_ids]
    subset_edges = [e for e in edges if e['source'] in subset_ids and e['target'] in subset_ids and
                    not (e['source'] in ontology_ids and e['target'] in ontology_ids)]
    # Full-series metadata must describe the actual subset when using the browser route.
    subset_nodes = json.loads(json.dumps(subset_nodes))
    subset_observations = sum('Lab8Observation' in n['labels'] for n in subset_nodes)
    for n in subset_nodes:
        p = n['properties']
        if n['id'] == 'data:hourlyDataset':
            p.update(name='Браузерний фрагмент: ' + start[:10], recordCount=subset_observations)
        elif n['id'] == 'data:hourlySeries':
            p.update(name='Годинний ряд браузерного фрагмента', missingCount=24-subset_observations)
        elif n['id'] == 'data:hourlyPeriod':
            p.update(name='Одна доба браузерного фрагмента', startTime=start, endTime=end)
    (ROOT / 'browser/02_day_data.cypher').write_text(browser_script(subset_nodes, subset_edges), encoding='utf-8')
    (ROOT / 'browser/03_indexes.cypher').write_text(';\n'.join(indexes) + ';\nCALL db.awaitIndexes(300);\n', encoding='utf-8')
    profiled = []
    for spec in query_specs:
        if spec['benchmark']:
            concrete = spec['query']
            for key,value in params.items():
                concrete = concrete.replace('$'+key, cypher(value))
            profiled.append('// ' + spec['id'] + '\nPROFILE\n' + concrete + ';\n')
    (ROOT / 'browser/05_profile.cypher').write_text('\n'.join(profiled), encoding='utf-8')
    summary = {
        'variant': 'Енергетика / Програмне забезпечення / Візуалізація',
        'nodes': len(nodes), 'relationships': len(edges), 'classes': len(classes),
        'ontology_individuals': len(individuals), 'object_properties': len(object_properties),
        'datatype_properties': len(data_properties), 'ontology_nodes': len(ontology_ids),
        'asserted_rdf_triples': len(asserted), 'rdf_union_triples': len(combined),
        'hourly_observations': len(rows), 'forecasts': len(predictions),
        'missing_hours_full_series': expected_hours-len(rows),
        'relationship_types': dict(sorted(Counter(e['type'] for e in edges).items())),
        'labels': dict(sorted(Counter(label for n in node_list for label in n['labels']).items())),
        'browser_subset': {'start': start, 'end': end, 'nodes': len(subset_ids),
                           'relationships': len(ontology_edges)+len(subset_edges),
                           'observations': subset_observations,
                           'forecasts': sum('Lab8Forecast' in n['labels'] for n in subset_nodes)},
        'threshold_kwh': threshold,
        'python_reference': {
            'mae_kwh': sum(abs(float(r['predicted_kwh'])-float(r['actual_kwh'])) for r in predictions)/len(predictions),
            'persistence_mae_kwh': sum(abs(float(r['persistence_kwh'])-float(r['actual_kwh'])) for r in predictions)/len(predictions),
            'daily_energy_kwh': sum(float(r['energy_kwh']) for ts,r in by_time.items() if start <= ts < end),
            'daily_hours': sum(start <= ts < end for ts in by_time),
        },
        'inputs_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'inputs').iterdir()) if p.is_file()},
        'checks': {'unique_node_ids': True, 'no_dangling_edges': True, 'all_forecast_targets_match_observations': True,
                   'finite_numbers': True, 'ontology_projection_built': True},
        'neo4j_execution': 'See results/<environment>_<timestamp>/validation.json; not implied by this build.'
    }
    if not math.isclose(summary['python_reference']['mae_kwh'], metrics['regression']['mae_kwh'], abs_tol=1e-12):
        raise ValueError('MAE does not match Lab1')
    dump(ROOT/'results/build_validation.json', summary)
    print(json.dumps({k:summary[k] for k in ('nodes','relationships','classes','ontology_individuals','hourly_observations','forecasts','browser_subset')}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
