import argparse
import csv
import getpass
import json
import math
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import neo4j
import rdflib
from neo4j import GraphDatabase, Query
from rdflib.plugins.sparql import prepareQuery

from build_lab9 import LAB8, ROOT, dump, semantic_graph

sys.path.insert(0, str(LAB8))
from run_neo4j import equivalent, import_graph, plan_totals, run, serial


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sparql_run(graph, prepared, numeric_columns):
    started = time.perf_counter()
    result = graph.query(prepared)
    names = [str(v) for v in result.vars]
    rows, terms = [], []
    for record in result:
        values = dict(zip(names, record))
        rows.append({k: (None if v is None else float(v) if k in numeric_columns else str(v))
                     for k, v in values.items()})
        terms.append({k: None if v is None else v.n3() for k, v in values.items()})
    return rows, terms, (time.perf_counter() - started) * 1000


def stats(values):
    ordered = sorted(values)
    return {'median_wall_ms': statistics.median(ordered),
            'p95_wall_ms': ordered[math.ceil(0.95 * len(ordered)) - 1],
            'min_wall_ms': ordered[0], 'max_wall_ms': ordered[-1], 'repeats': len(ordered)}


def counts(session):
    labels, _, _ = run(session, 'MATCH (n:Lab8Entity) RETURN labels(n) AS labels,count(*) AS count')
    return {'nodes': sum(row['count'] for row in labels),
            'label_sets': {'|'.join(sorted(row['labels'])): row['count'] for row in labels},
            'relationships_by_type': {row['type']: row['count'] for row in run(session,
                'MATCH (:Lab8Entity)-[r]->(:Lab8Entity) RETURN type(r) AS type,count(*) AS count')[0]}}


def compare_languages(session, params, folder, repeats, reference):
    asserted, _, semantic = semantic_graph()
    pairs = load(ROOT / 'comparison/catalog.json')
    results, samples = {}, []
    for pair in pairs:
        identifier = pair['id']
        prepared = prepareQuery(pair['sparql'])
        sparql_rows, terms, first_ms = sparql_run(semantic, prepared, pair['numeric_columns'])
        explicit_rows, explicit_terms, _ = sparql_run(asserted, prepared, pair['numeric_columns'])
        cypher_rows, _, cypher_first_ms = run(session, pair['cypher'], params)
        if not equivalent(sparql_rows, cypher_rows):
            dump(folder / ('mismatch_' + identifier + '.json'), {'sparql': sparql_rows, 'cypher': cypher_rows})
            raise RuntimeError('SPARQL/Cypher mismatch: ' + identifier)
        for _ in range(3):
            sparql_run(semantic, prepared, pair['numeric_columns'])
            run(session, pair['cypher'], params)
        for iteration in range(repeats):
            order = ['sparql', 'cypher'] if iteration % 2 == 0 else ['cypher', 'sparql']
            for engine in order:
                if engine == 'sparql':
                    rows, _, wall_ms = sparql_run(semantic, prepared, pair['numeric_columns'])
                else:
                    rows, _, wall_ms = run(session, pair['cypher'], params)
                if not equivalent(sparql_rows, rows):
                    raise RuntimeError('Answers changed during benchmarking: ' + identifier)
                samples.append({'pair': identifier, 'engine': engine, 'iteration': iteration + 1,
                                'wall_ms': wall_ms, 'returned_rows': len(rows)})
        results[identifier] = {'question': pair['question'], 'equivalent': True,
                              'sparql_rows': sparql_rows, 'sparql_rdf_terms': terms,
                              'cypher_rows': cypher_rows,
                              'asserted_only_sparql_rows': explicit_rows,
                              'asserted_only_rdf_terms': explicit_terms,
                              'first_execution_wall_ms': {'sparql': first_ms, 'cypher': cypher_first_ms},
                              **{engine: stats([s['wall_ms'] for s in samples
                                                if s['pair'] == identifier and s['engine'] == engine])
                                 for engine in ['sparql', 'cypher']}}
        dump(folder / 'language_comparison.json', results)
        dump(folder / 'language_samples.json', samples)
        print(identifier, ': equivalent,', len(sparql_rows), 'rows', flush=True)
    with (folder / 'language_samples.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)
    dump(folder / 'comparison_method.json', {
        'sparql_engine': 'RDFLib ' + rdflib.__version__ + ', in-process Graph, prepared SPARQL 1.1',
        'cypher_engine': 'Neo4j over Bolt using neo4j Python driver ' + neo4j.__version__,
        'common_scope': '26 original named ontology individuals; no full-CSV-only individuals in these questions.',
        'rdf_asserted_triples': len(asserted), 'rdf_semantic_triples': len(semantic),
        'neo4j_physical_nodes': reference['nodes'], 'neo4j_physical_relationships': reference['relationships'],
        'warmup_runs_per_query_per_engine': 3, 'repeats': repeats,
        'order': 'SPARQL/Cypher order alternates on every repeat',
        'excluded_from_repeated_timing': ['graph parsing', 'SPARQL prepareQuery', 'first executions', 'PROFILE'],
        'timed': 'Execution, full result consumption and Python materialization; Cypher includes Bolt round trip.',
        'limits': ['Different physical representations and execution stacks; not an isolated language-speed comparison.',
                   'Warm caches and tiny common result sets; conclusions apply only to these questions and this run.',
                   'Saved HermiT inferences plus superclass membership are materialized on both sides; no live OWL reasoner.']})
    lines = ['# Збережене порівняння SPARQL / Cypher', '',
             'Це матеріали виконання для майбутнього звіту. Усі три відповіді збігаються.', '',
             '| Питання | Рядків | SPARQL, медіана ms | Cypher, медіана ms |',
             '|---|---:|---:|---:|']
    for identifier, result in results.items():
        lines.append(f"| {identifier} | {len(result['sparql_rows'])} | {result['sparql']['median_wall_ms']:.4f} | {result['cypher']['median_wall_ms']:.4f} |")
    lines += ['', 'Сирі повтори: language_samples.csv; RDF-терми та відповіді: language_comparison.json.',
              'SPARQL виконується в RDFLib у процесі Python; Cypher — через Bolt. Порівнюються ті самі питання',
              'про 26 початкових індивідів, але фізичні сховища різні: RDF містить OWL-аксіоми й збережені висновки,',
              'а Neo4j також містить повні годинні дані. Часи описують ці реалізації; загальну перевагу мови з них не встановлюємо.',
              'Перші виконання, підготовка SPARQL і PROFILE не входять у повторні вимірювання.', '']
    (folder / 'comparison_notes.md').write_text('\n'.join(lines), encoding='utf-8')
    return results


def main():
    parser = argparse.ArgumentParser(description='Run missing lab9 work and preserve evidence; does not create a report.')
    parser.add_argument('--uri')
    parser.add_argument('--user', default='neo4j')
    parser.add_argument('--database', default='neo4j')
    parser.add_argument('--environment', choices=['local', 'sandbox'], default='sandbox')
    parser.add_argument('--no-auth', action='store_true')
    parser.add_argument('--import-data', action='store_true', help='Import full inherited graph twice using MERGE; otherwise read-only.')
    parser.add_argument('--repeats', type=int, default=10)
    args = parser.parse_args()
    if args.repeats < 3:
        parser.error('--repeats must be >= 3')
    uri = args.uri or input('Bolt URI із Sandbox Connection details: ').strip()
    if args.no_auth and (args.environment != 'local' or urlsplit(uri).hostname not in ('localhost', '127.0.0.1', '::1')):
        parser.error('--no-auth is limited to a loopback local verification server')
    password = None if args.no_auth else getpass.getpass('Пароль Neo4j (не зберігається): ')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT / 'results' / (args.environment + '_' + stamp)
    folder.mkdir(parents=True)
    validation = {'status': 'running', 'environment': args.environment, 'started_at_utc': stamp,
                  'python': platform.python_version(), 'neo4j_driver': neo4j.__version__,
                  'rdflib': rdflib.__version__, 'credentials_saved': False,
                  'screenshots_captured': False, 'report_created': False,
                  'lab8_reuse_manifest': 'results/audit/lab8_snapshot_manifest.json'}
    dump(folder / 'validation.json', validation)
    print('Results:', folder, flush=True)
    driver = None
    try:
        reference = load(ROOT / 'results/build_validation.json')
        build8 = load(LAB8 / 'results/build_validation.json')
        params = load(ROOT / 'queries/parameters.json')
        catalog = load(ROOT / 'queries/catalog.json')
        driver = GraphDatabase.driver(uri, auth=None if args.no_auth else (args.user, password),
                                      connection_timeout=20, max_connection_pool_size=2)
        driver.verify_connectivity()
        with driver.session(database=args.database) as session:
            validation['server_components'] = run(session, 'CALL dbms.components() YIELD name,versions,edition RETURN name,versions,edition')[0]
            if args.import_data:
                schema = load(LAB8 / 'data/schema.json')
                run(session, schema['constraint'])
                nodes = load(LAB8 / 'data/nodes.json')
                edges = load(LAB8 / 'data/relationships.json')
                print('Import inherited graph (MERGE)...', flush=True)
                validation['import'] = import_graph(session, nodes, edges)
                before_repeat = counts(session)
                print('Verify second MERGE import...', flush=True)
                validation['repeat_import'] = import_graph(session, nodes, edges)
                after_repeat = counts(session)
                validation['repeat_import_counts_unchanged'] = before_repeat == after_repeat
                dump(folder / 'repeat_import_counts.json', {'before': before_repeat, 'after': after_repeat})
                if any(validation['repeat_import'].values()) or before_repeat != after_repeat:
                    raise RuntimeError('Repeated import changed graph counts')
                for statement in schema['indexes']:
                    run(session, statement)
                run(session, 'CALL db.awaitIndexes(300)')
            actual = counts(session)
            dump(folder / 'graph_counts.json', actual)
            if (actual['nodes'] != reference['nodes'] or actual['label_sets'] != reference['label_sets']
                    or actual['relationships_by_type'] != build8['relationship_types']):
                raise RuntimeError('Expected full inherited lab8 graph (43746 nodes); use --import-data if database is empty or partial')
            constraints = run(session, 'SHOW CONSTRAINTS YIELD name,type,labelsOrTypes,properties RETURN name,type,labelsOrTypes,properties ORDER BY name')[0]
            indexes = run(session, 'SHOW INDEXES YIELD name,type,state,labelsOrTypes,properties RETURN name,type,state,labelsOrTypes,properties ORDER BY name')[0]
            dump(folder / 'constraints.json', constraints)
            dump(folder / 'indexes.json', indexes)
            class_ids = run(session, 'MATCH (n:Lab8Entity:OntologyClass) RETURN n.id AS id ORDER BY id')[0]
            individual_ids = run(session, 'MATCH (n:Lab8Entity:OntologyIndividual) RETURN n.id AS id ORDER BY id')[0]
            dump(folder / 'source_reconciliation.json', {
                'source_asserted_triples': reference['source_asserted_triples'],
                'source_classes': len(reference['class_ids']), 'source_individuals': len(reference['individual_ids']),
                'actual_class_ids': class_ids, 'actual_individual_ids': individual_ids,
                'mapping': '993 RDF triples project to schema/individual nodes, properties and edges; counts are not one-to-one.',
                'full_graph_extensions': {'hourly_observations': 34085, 'forecasts': 9530}})
            answers = {}
            for spec in catalog:
                rows, summary, wall = run(session, Query(spec['query'], timeout=60), params)
                answers[spec['id']] = {'question': spec['question'], 'origin': spec['origin'],
                                       'features': spec['features'], 'rows': rows, 'wall_ms': wall,
                                       'result_available_ms': summary.result_available_after,
                                       'result_consumed_ms': summary.result_consumed_after}
                dump(folder / 'query_results.json', answers)
                print(spec['id'], ':', len(rows), 'rows', flush=True)
            profiles = {}
            for query_id in ['03_top_high_forecasts', '09_forecast_mae']:
                spec = next(s for s in catalog if s['id'] == query_id)
                rows, summary, _ = run(session, 'PROFILE\n' + spec['query'], params)
                plan = serial(summary.profile)
                profiles[query_id] = {'plan': plan, **plan_totals(plan),
                                      'same_results': equivalent(rows, answers[query_id]['rows'])}
            dump(folder / 'profiles.json', profiles)
            pairs = compare_languages(session, params, folder, args.repeats, reference)
            project_rows = lambda key: [{'id': row['id'], 'degree': row['degree']} for row in answers[key]['rows']]
            old_mae = load(LAB8 / 'results/sandbox_20261016T054342525797Z/query_results.json')['08_forecast_errors']['rows']
            source_nodes = load(LAB8 / 'data/nodes.json')
            expected_forecasts = sorted(
                [n for n in source_nodes if 'Lab8Forecast' in n['labels']
                 and params['start'] <= n['properties']['targetTime'] < params['end']
                 and n['properties']['forecastKwh'] > params['threshold']],
                key=lambda n: (-n['properties']['forecastKwh'], n['id']))[:5]
            checks = {
                'full_node_count': actual['nodes'] == 43746,
                'full_relationship_count': sum(actual['relationships_by_type'].values()) == 199287,
                'class_ids_match_source': [r['id'] for r in class_ids] == reference['class_ids'],
                'individual_ids_match_source': [r['id'] for r in individual_ids] == reference['individual_ids'],
                'unique_id_constraint_present': any(r['name'] == 'lab8_entity_id' and r['type'] in ('UNIQUENESS', 'NODE_PROPERTY_UNIQUENESS') for r in constraints),
                'all_four_inherited_indexes_online': len([r for r in indexes if r['name'].startswith('lab8_') and r['state'] == 'ONLINE']) == 4,
                'optional_preserves_26_individuals': len(answers['01_optional_metric']['rows']) == 26,
                'optional_nulls_are_present': any(r['metric_id'] is None for r in answers['01_optional_metric']['rows']),
                'collect_returns_both_meters': answers['02_collect_meters']['rows'][0]['meters'] == ['owl:meter', 'owl:submeter'],
                'top_forecasts_match_source_filter_order_limit': [r['id'] for r in answers['03_top_high_forecasts']['rows']] == [n['id'] for n in expected_forecasts],
                'all_ancestors_match_independent_bfs': {r['ancestor']: r['hops'] for r in answers['04_ancestors']['rows']} == reference['ancestors'],
                'all_descendants_match_independent_bfs': {r['descendant']: r['hops'] for r in answers['05_descendants']['rows']} == reference['descendants'],
                'shortest_hops_matches_independent_bfs': len(answers['06_shortest_path']['rows']) == 1 and answers['06_shortest_path']['rows'][0]['hops'] == reference['shortest_hops'],
                'shortest_path_is_within_original_individuals': all(n in reference['individual_ids'] for r in answers['06_shortest_path']['rows'] for n in r['node_ids']),
                'full_graph_shortest_matches_independent_bfs': len(answers['11_shortest_full_graph']['rows']) == 1 and answers['11_shortest_full_graph']['rows'][0]['hops'] == reference['shortest_full_graph_hops'],
                'top5_graph_matches_independent_edge_counts': project_rows('07_top5_graph_degree') == reference['top5_graph_degree'],
                'top5_class_matches_independent_edge_counts': project_rows('08_top5_class_degree') == reference['top5_class_degree'],
                'reused_daily_mae_matches_lab8_sandbox': equivalent(answers['09_forecast_mae']['rows'], old_mae),
                'profile_did_not_change_answers': all(p['same_results'] for p in profiles.values()),
                'three_pairs_equivalent': len(pairs) == 3 and all(p['equivalent'] for p in pairs.values()),
                'asserted_turtle_isomorphic': reference['asserted_turtle_isomorphic'],
            }
            validation['checks'] = checks
            if not all(checks.values()):
                raise RuntimeError('Validation failed: ' + ', '.join(k for k, v in checks.items() if not v))
            validation['status'] = 'passed'
            validation['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
            dump(folder / 'validation.json', validation)
            dump(ROOT / 'results' / ('latest_' + args.environment + '.json'),
                 {'folder': folder.relative_to(ROOT).as_posix(), 'status': 'passed'})
            print('PASS:', sum(checks.values()), 'checks.', flush=True)
    except Exception as exc:
        validation['status'] = 'failed'
        validation['error_type'] = type(exc).__name__
        dump(folder / 'validation.json', validation)
        raise
    finally:
        if driver is not None:
            driver.close()


if __name__ == '__main__':
    main()
