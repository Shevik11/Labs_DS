"""Check the user-exported WebProtege ontology without changing either input."""
from pathlib import Path
import json, hashlib, contextlib, io, shutil
from rdflib import Graph, Namespace, BNode, URIRef
from rdflib.namespace import RDF, OWL
from rdflib.collection import Collection
from rdflib.compare import isomorphic
import owlready2 as ow

ROOT = Path(__file__).resolve().parent
E = Namespace('https://example.org/lnu/energy-visualization#')

def normalize(g):
    result = Graph()
    for triple in g:
        result.add(triple)
    # These OWL axioms use unordered sets. Do not sort arbitrary RDF lists.
    for kind, predicate in [(OWL.AllDisjointClasses, OWL.members),
                            (OWL.AllDifferent, OWL.distinctMembers)]:
        for node in list(result.subjects(RDF.type, kind)):
            head = result.value(node, predicate)
            if head is None:
                continue
            values = list(Collection(result, head))
            Collection(result, head).clear()
            result.remove((node, predicate, head))
            replacement = BNode()
            Collection(result, replacement, sorted(values, key=str))
            result.add((node, predicate, replacement))
    # inverseOf is symmetric, regardless of which property is written first.
    for a, b in list(result.subject_objects(OWL.inverseOf)):
        result.remove((a, OWL.inverseOf, b))
        a, b = sorted([a, b], key=str)
        result.add((a, OWL.inverseOf, b))
    return result

def main():
    original = Graph().parse(ROOT/'energy_ontology.owl')
    exported = Graph().parse(ROOT/'energy_ontology_webprotege.owl')
    checks = {'same_triple_count': len(original) == len(exported),
              'equivalent_after_owl_set_and_inverse_normalization':
                  isomorphic(normalize(original), normalize(exported))}
    counts = {}
    for name, type_, expected in [('classes', OWL.Class, 31),
                                  ('object_properties', OWL.ObjectProperty, 28),
                                  ('data_properties', OWL.DatatypeProperty, 34),
                                  ('individuals', OWL.NamedIndividual, 26)]:
        counts[name] = len({s for s in exported.subjects(RDF.type, type_) if isinstance(s, URIRef)})
        checks[name] = counts[name] == expected
    assert all(checks.values()), checks
    ow.JAVA_EXE = shutil.which('java') or 'java'
    world = ow.World()
    with (ROOT/'energy_ontology_webprotege.owl').open('rb') as stream:
        world.get_ontology(str(E).rstrip('#')).load(fileobj=stream)
    log = io.StringIO()
    try:
        with contextlib.redirect_stderr(log):
            ow.sync_reasoner(world, infer_property_values=True, debug=2)
    finally:
        (ROOT/'results/webprotege_hermit.log').write_text(log.getvalue(), encoding='utf-8')
    checks['hermit_consistent'] = True
    checks['no_unsatisfiable_named_classes'] = not list(world.inconsistent_classes())
    inferred = Graph()
    for triple in world.as_rdflib_graph():
        inferred.add(triple)
    checks['inferred_forecast_visualization'] = (E.forecastChart, RDF.type, E.ForecastVisualization) in inferred
    checks['inferred_recorded_by'] = (E.measurement1, E.recordedBy, E.meter) in inferred
    query_checks = []
    for reference in json.loads((ROOT/'results/query_results.json').read_text(encoding='utf-8')):
        rows = [{str(k): str(v) for k, v in row.asdict().items()}
                for row in inferred.query(reference['query'])]
        key = lambda row: json.dumps(row, sort_keys=True)
        passed = sorted(rows, key=key) == sorted(reference['rows'], key=key)
        checks['query_' + reference['id']] = passed
        query_checks.append({'id': reference['id'], 'rows': rows, 'matches_original': passed})
    result = {'status': 'passed' if all(checks.values()) else 'failed',
              'original_triples': len(original), 'exported_triples': len(exported),
              'raw_rdf_graphs_isomorphic': isomorphic(original, exported),
              'normalization': ['unordered OWL AllDisjointClasses/AllDifferent members',
                                'symmetric owl:inverseOf orientation'],
              'export_sha256': hashlib.sha256((ROOT/'energy_ontology_webprotege.owl').read_bytes()).hexdigest(),
              'counts': counts, 'checks': checks, 'queries': query_checks,
              'reasoner_environment': 'HermiT through local Owlready2; not WebProtege'}
    (ROOT/'results/webprotege_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    assert all(checks.values()), checks
    print(json.dumps({'status': result['status'], 'checks': len(checks), 'counts': counts}))

if __name__ == '__main__':
    main()
