import argparse
import csv
import getpass
import json
import math
import platform
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import neo4j
from neo4j import GraphDatabase
from neo4j.graph import Node, Path as GraphPath, Relationship

from build_lab8 import ROOT, dump, edge_statement, group_edges, group_nodes, node_statement


def serial(value):
    if isinstance(value, Node):
        return {'element_id': value.element_id, 'labels': sorted(value.labels), 'properties': serial(dict(value))}
    if isinstance(value, Relationship):
        return {'type': value.type, 'source': value.start_node.get('id'),
                'target': value.end_node.get('id'), 'properties': serial(dict(value))}
    if isinstance(value, GraphPath):
        return {'nodes': serial(list(value.nodes)), 'relationships': serial(list(value.relationships))}
    if isinstance(value, dict):
        return {str(k): serial(v) for k,v in value.items()}
    if isinstance(value, (list,tuple)):
        return [serial(v) for v in value]
    if hasattr(value, 'iso_format'):
        return value.iso_format()
    if value is None or isinstance(value, (str,int,float,bool)):
        return value
    return str(value)


def run(session, query, parameters=None):
    started = time.perf_counter()
    result = session.run(query, parameters or {})
    rows = [serial(dict(record)) for record in result]
    summary = result.consume()
    elapsed_ms = (time.perf_counter()-started)*1000
    return rows, summary, elapsed_ms


def plan_totals(plan):
    hits, rows, operators = 0, 0, []
    pending = [plan]
    while pending:
        item = pending.pop()
        if not item:
            continue
        hits += item.get('dbHits', 0)
        rows += item.get('rows', 0)
        operators.append(item.get('operatorType', ''))
        pending.extend(item.get('children', []))
    return {'db_hits_sum': hits, 'operator_rows_sum': rows, 'operators': operators}


def equivalent(a,b):
    if isinstance(a,(int,float)) and not isinstance(a,bool) and isinstance(b,(int,float)) and not isinstance(b,bool):
        return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)
    if isinstance(a,dict) and isinstance(b,dict):
        return a.keys()==b.keys() and all(equivalent(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(equivalent(x,y) for x,y in zip(a,b))
    return a==b


def measure(session, specs, params, folder, stage, repeats):
    benchmarks = [q for q in specs if q['benchmark']]
    samples, answers, profiles = [], {}, {}
    for spec in benchmarks:
        for _ in range(3):
            run(session,spec['query'],params)
    for iteration in range(repeats):
        order = benchmarks if iteration % 2 == 0 else list(reversed(benchmarks))
        for spec in order:
            rows,summary,wall = run(session,spec['query'],params)
            answers[spec['id']] = rows
            samples.append({'stage':stage,'query':spec['id'],'iteration':iteration+1,
                            'wall_ms':wall,'result_available_ms':summary.result_available_after,
                            'result_consumed_ms':summary.result_consumed_after,
                            'returned_rows':len(rows),
                            'json_utf8_bytes':len(json.dumps(rows,ensure_ascii=False).encode('utf-8'))})
    stats = {}
    for spec in benchmarks:
        rows,summary,_ = run(session,'PROFILE\n'+spec['query'],params)
        plan = serial(summary.profile)
        profiles[spec['id']] = {'plan':plan,**plan_totals(plan)}
        selected = [r for r in samples if r['query']==spec['id']]
        walls = sorted(r['wall_ms'] for r in selected)
        stats[spec['id']] = {'median_wall_ms':statistics.median(walls),
                             'p95_wall_ms':walls[math.ceil(.95*len(walls))-1],
                             'min_wall_ms':min(walls),'max_wall_ms':max(walls),
                             'returned_rows':selected[0]['returned_rows'],
                             'json_utf8_bytes':selected[0]['json_utf8_bytes'],
                             **plan_totals(plan)}
    dump(folder/(stage+'_profiles.json'),profiles)
    dump(folder/(stage+'_answers.json'),answers)
    dump(folder/(stage+'_summary.json'),stats)
    with (folder/(stage+'_samples.csv')).open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(samples[0]))
        writer.writeheader()
        writer.writerows(samples)
    return stats,answers


def import_graph(session,nodes,edges):
    created_nodes,created_edges=0,0
    groups = list(group_nodes(nodes).items())
    for index,((labels,temporal),rows) in enumerate(groups):
        for offset in range(0,len(rows),1000):
            chunk=rows[offset:offset+1000]
            result=session.run(node_statement(labels,temporal),rows=chunk)
            processed=result.single()['processed']
            summary=result.consume()
            if processed!=len(chunk):
                raise RuntimeError('Node import did not process all rows')
            created_nodes+=summary.counters.nodes_created
        if len(rows)>1000:
            print(f'  Nodes: {index+1}/{len(groups)}, batch group size {len(rows)}',flush=True)
    for kind,rows in group_edges(edges).items():
        for offset in range(0,len(rows),1000):
            chunk=rows[offset:offset+1000]
            result=session.run(edge_statement(kind),rows=chunk)
            processed=result.single()['processed']
            summary=result.consume()
            if processed!=len(chunk):
                raise RuntimeError('Missing endpoint during import: '+kind)
            created_edges+=summary.counters.relationships_created
    return {'nodes_created':created_nodes,'relationships_created':created_edges}


def main():
    parser=argparse.ArgumentParser(description='Import lab 8 and save real Neo4j evidence on disk D.')
    parser.add_argument('--uri',help='Copy Bolt URI from your own Sandbox Connection details')
    parser.add_argument('--user',default='neo4j')
    parser.add_argument('--database',default='neo4j')
    parser.add_argument('--environment',choices=['sandbox','local'],default='sandbox')
    parser.add_argument('--no-auth',action='store_true',help='Only for the isolated local verification server')
    parser.add_argument('--repeats',type=int,default=10)
    parser.add_argument('--verify-idempotence',action='store_true')
    args=parser.parse_args()
    if args.repeats<3:
        parser.error('--repeats must be at least 3')
    uri=args.uri or input('Bolt URI from Sandbox Connection details: ').strip()
    if args.no_auth and args.environment!='local':
        parser.error('--no-auth is restricted to --environment local')
    password=None if args.no_auth else getpass.getpass('Neo4j password (hidden, not saved): ')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'results'/(args.environment+'_'+stamp)
    folder.mkdir(parents=True,exist_ok=False)
    validation={'environment':args.environment,'started_at_utc':stamp,'status':'running',
                'python':platform.python_version(),'driver':neo4j.__version__,
                'database':args.database,'repeats':args.repeats,'warmup_runs_per_query':3,
                'credentials_saved':False,'screenshots_captured':False}
    dump(folder/'validation.json',validation)
    driver=None
    try:
        driver=GraphDatabase.driver(uri,auth=None if args.no_auth else (args.user,password),
                                    connection_timeout=30,max_connection_pool_size=5)
        driver.verify_connectivity()
        print('Connected. Result directory:',folder,flush=True)
        nodes=json.loads((ROOT/'data/nodes.json').read_text(encoding='utf-8'))
        edges=json.loads((ROOT/'data/relationships.json').read_text(encoding='utf-8'))
        schema=json.loads((ROOT/'data/schema.json').read_text(encoding='utf-8'))
        specs=json.loads((ROOT/'queries/catalog.json').read_text(encoding='utf-8'))
        params=json.loads((ROOT/'queries/parameters.json').read_text(encoding='utf-8'))
        build=json.loads((ROOT/'results/build_validation.json').read_text(encoding='utf-8'))
        with driver.session(database=args.database) as session:
            version,_,_=run(session,'CALL dbms.components() YIELD name, versions, edition RETURN name,versions,edition')
            validation['server_components']=version
            existing,_,_=run(session,'SHOW INDEXES YIELD name RETURN name')
            existing_names={r['name'] for r in existing}
            baseline_possible=not any(n in existing_names for n in ('lab8_observation_time','lab8_forecast_time'))
            run(session,schema['constraint'])
            print('Importing nodes and relationships...',flush=True)
            validation['import']=import_graph(session,nodes,edges)
            counts,_,_=run(session,'MATCH (n:Lab8Entity) RETURN count(n) AS nodes')
            relationships,_,_=run(session,'MATCH (:Lab8Entity)-[r]->(:Lab8Entity) RETURN type(r) AS type,count(r) AS count ORDER BY type')
            validation['actual_nodes']=counts[0]['nodes']
            validation['actual_relationships_by_type']={r['type']:r['count'] for r in relationships}
            if counts[0]['nodes']!=len(nodes) or validation['actual_relationships_by_type']!=build['relationship_types']:
                raise RuntimeError('Database counts differ from the generated graph; use a fresh Blank Sandbox')
            if args.verify_idempotence:
                print('Checking repeat import...',flush=True)
                validation['repeat_import']=import_graph(session,nodes,edges)
                if any(validation['repeat_import'].values()):
                    raise RuntimeError('MERGE import is not idempotent')
            before=before_answers=None
            if baseline_possible:
                print('Measuring without search indexes...',flush=True)
                before,before_answers=measure(session,specs,params,folder,'before',args.repeats)
            else:
                validation['baseline_note']='Search indexes already existed. No unindexed baseline or speedup is claimed.'
            for statement in schema['indexes']:
                run(session,statement)
            run(session,'CALL db.awaitIndexes(300)')
            index_rows,_,_=run(session,'SHOW INDEXES YIELD name,type,state,populationPercent,labelsOrTypes,properties RETURN name,type,state,populationPercent,labelsOrTypes,properties ORDER BY name')
            dump(folder/'indexes.json',index_rows)
            if any(r['state']!='ONLINE' for r in index_rows if r['name'].startswith('lab8_')):
                raise RuntimeError('A lab8 index is not ONLINE')
            print('Measuring with indexes...',flush=True)
            after,after_answers=measure(session,specs,params,folder,'after',args.repeats)
            if before is not None:
                if not equivalent(before_answers,after_answers):
                    raise RuntimeError('Query answers changed after indexing')
                comparison={key:{'before':before[key],'after':after[key],
                                 'median_ratio_before_over_after':before[key]['median_wall_ms']/after[key]['median_wall_ms']}
                            for key in after}
                dump(folder/'benchmark_comparison.json',comparison)
                validation['benchmark_answers_equivalent']=True
            all_answers={}
            for spec in specs:
                rows,summary,wall=run(session,spec['query'],params)
                all_answers[spec['id']]={'title':spec['title'],'rows':rows,'wall_ms':wall,
                                        'result_available_ms':summary.result_available_after,
                                        'result_consumed_ms':summary.result_consumed_after}
            dump(folder/'query_results.json',all_answers)
            daily=all_answers['07_daily_energy']['rows'][0]
            mae=all_answers['11_all_test_mae']['rows'][0]
            reference=build['python_reference']
            checks={'node_count':counts[0]['nodes']==build['nodes'],
                    'relationship_counts':validation['actual_relationships_by_type']==build['relationship_types'],
                    'test_rows':mae['test_rows']==build['forecasts'],
                    'mae_matches_lab1':math.isclose(mae['mae_kwh'],reference['mae_kwh'],abs_tol=1e-10),
                    'persistence_mae_matches_lab1':math.isclose(mae['persistence_mae_kwh'],reference['persistence_mae_kwh'],abs_tol=1e-10),
                    'daily_hours':daily['hours']==reference['daily_hours'],
                    'daily_energy_matches_python':math.isclose(daily['energy_kwh'],reference['daily_energy_kwh'],abs_tol=1e-10)}
            semantic=all_answers['04_semantic_forecast']['rows']
            checks['lab6_inference_preserved']=bool(semantic and
                'AttentionVisualization' in semantic[0]['visualization_types'] and
                'HighConsumptionForecast' in semantic[0]['forecast_types'])
            validation['checks']=checks
            if not all(checks.values()):
                raise RuntimeError('One or more database validation checks failed')
            graph_rows,_,_=run(session,"MATCH (n:Lab8Entity:OntologyIndividual) RETURN n.id AS id,labels(n) AS labels,properties(n) AS properties ORDER BY id")
            graph_edges,_,_=run(session,"MATCH (a:Lab8Entity:OntologyIndividual)-[r]->(b:Lab8Entity:OntologyIndividual) RETURN a.id AS source,type(r) AS type,b.id AS target,properties(r) AS properties ORDER BY source,type,target")
            dump(folder/'ontology_graph.json',{'nodes':graph_rows,'relationships':graph_edges})
            validation['status']='passed'
            validation['finished_at_utc']=datetime.now(timezone.utc).isoformat()
            dump(folder/'validation.json',validation)
            print('PASS:',len(nodes),'nodes,',len(edges),'relationships.',flush=True)
            print('MAE:',mae['mae_kwh'],'kWh; persistence:',mae['persistence_mae_kwh'],'kWh',flush=True)
            print('Saved:',folder,flush=True)
    except Exception as exc:
        validation['status']='failed'
        # Exception class is sufficient for the saved status; avoids storing endpoint/credential echoes.
        validation['error_type']=type(exc).__name__
        dump(folder/'validation.json',validation)
        raise
    finally:
        if driver is not None:
            driver.close()

if __name__=='__main__':
    main()
