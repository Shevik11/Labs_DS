"""Check serialization, completeness, HermiT consistency/inference and query scenarios."""
from pathlib import Path
import contextlib, io, json, shutil, sys, platform
from datetime import datetime
from decimal import Decimal
from importlib.metadata import version
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from rdflib.compare import isomorphic
import owlready2 as ow

ROOT=Path(__file__).resolve().parent
E=Namespace('https://example.org/lnu/energy-visualization#')
RESULTS=ROOT/'results'
RESULTS.mkdir(exist_ok=True)
ow.JAVA_EXE=shutil.which('java') or 'java'
checks=[]

def check(name, condition, detail=None):
    checks.append(dict(name=name,passed=bool(condition),detail=detail))
    if not condition: raise AssertionError(name)

def reason(path, log_name):
    world=ow.World()
    with path.open('rb') as stream:
        ontology=world.get_ontology('https://example.org/lnu/energy-visualization').load(fileobj=stream)
    log=io.StringIO()
    try:
        with contextlib.redirect_stderr(log): ow.sync_reasoner(world,infer_property_values=True,debug=2)
    finally:
        (RESULTS/log_name).write_text(log.getvalue(),encoding='utf-8')
    return world,ontology

def run():
    g=Graph().parse(ROOT/'energy_ontology.owl'); ttl=Graph().parse(ROOT/'energy_ontology.ttl')
    check('RDF/XML and Turtle encode identical graphs',isomorphic(g,ttl))
    structure=json.loads((ROOT/'ontology_structure.json').read_text(encoding='utf-8'))
    check('All 16 concepts from lab 3 retained',len(structure['lab3_mapping'])==16 and all((E[n],RDF.type,OWL.Class) in g for n in structure['lab3_mapping'].values()))
    for p in list(g.subjects(RDF.type,OWL.ObjectProperty))+list(g.subjects(RDF.type,OWL.DatatypeProperty)):
        check('Domain and range: '+str(p).split('#')[-1],g.value(p,RDFS.domain) is not None and g.value(p,RDFS.range) is not None)
    def is_instance(n,c): return any((t,RDFS.subClassOf*'?',c) in g or c in g.transitive_objects(t,RDFS.subClassOf) for t in g.objects(n,RDF.type))
    # Closed-world completeness is separate from OWL's open-world semantics.
    missing=[]
    for c,p in [('DomainEntity','identifier'),('DomainEntity','name'),('Measurement','timestamp'),('Measurement','numericValue'),('Measurement','qualityFlag'),('Measurement','hasUnit'),('Measurement','observesIndicator'),('TimeSeries','seriesOf'),('TimeSeries','seriesIndicator'),('TimeSeries','coversInterval')]:
        for n in g.subjects(RDF.type,OWL.NamedIndividual):
            if is_instance(n,E[c]) and len(list(g.objects(n,E[p])))!=1: missing.append([str(n),p])
    check('Required explicit fields for sample individuals',not missing,missing)
    for period in g.subjects(RDF.type,E.TimeInterval):
        check('Interval ordering: '+period.split('#')[-1],datetime.fromisoformat(str(g.value(period,E.startTime)))<datetime.fromisoformat(str(g.value(period,E.endTime))))
    for ds in g.subjects(RDF.type,E.Dataset):
        ms={m for s in g.objects(ds,E.containsSeries) for m in g.objects(s,E.hasMeasurement)}
        check('Dataset record count: '+ds.split('#')[-1],len(ms)==int(g.value(ds,E.recordCount)))
    world,onto=reason(ROOT/'energy_ontology.owl','hermit_consistent.log')
    check('HermiT: ontology is consistent',True)
    check('HermiT: no unsatisfiable named classes',not list(world.inconsistent_classes()))
    inferred=Graph()
    for triple in world.as_rdflib_graph(): inferred.add(triple)
    inferred.serialize(RESULTS/'energy_inferred.owl',format='xml')
    check('Inferred ForecastVisualization', (E.forecastChart,RDF.type,E.ForecastVisualization) in inferred)
    check('Inferred inverse recordedBy', (E.measurement1,E.recordedBy,E.meter) in inferred)
    # Query subclass paths make the queries independent of materialized parent types.
    scenarios=[
        ('01_household_meters','Які засоби обліку належать домогосподарству?',
         'SELECT ?meter WHERE { energy:household energy:hasMeter ?meter } ORDER BY ?meter',2),
        ('02_hourly_energy','Які три значення енергії містить приклад із ЛР1?',
         'SELECT ?time ?value WHERE { energy:series energy:hasMeasurement ?m . ?m energy:timestamp ?time; energy:numericValue ?value } ORDER BY ?time',3),
        ('03_forecast_provenance','Яка модель створила прогноз і яка його MAE на всьому тесті?',
         'SELECT ?forecast ?model ?value ?mae ?scope WHERE { ?forecast a energy:ForecastResult; energy:generatedBy ?model; energy:forecastKwh ?value; energy:evaluatedBy ?metric . ?metric energy:metricValue ?mae; energy:evaluationScope ?scope }',1),
        ('04_inferred_visualization','Яке подання reasoner класифікує як візуалізацію прогнозу?',
         'SELECT ?view WHERE { ?view a energy:ForecastVisualization }',1),
        ('05_user_decision','Який користувач ухвалює рішення і яке подання його підтримує?',
         'SELECT ?user ?decision ?view WHERE { ?user energy:makesDecision ?decision . ?view energy:supportsDecision ?decision }',1),
        ('06_filters','Які фільтри застосовано до подань?',
         'SELECT ?filter ?view ?field ?condition WHERE { ?filter energy:configures ?view; energy:filterField ?field; energy:filterCondition ?condition }',1),
        ('07_energy_above_threshold','Які вимірювання прикладу перевищують 3.4 кВт·год?',
         'SELECT ?m ?value WHERE { energy:series energy:hasMeasurement ?m . ?m energy:numericValue ?value . FILTER(?value > 3.4) } ORDER BY ?value',2),
        ('08_model_task','Яку задачу і горизонт має регресійна модель?',
         'SELECT ?task ?type ?hours WHERE { ?task energy:implementedBy energy:regressor; energy:taskType ?type; energy:horizonHours ?hours }',1),
    ]
    query_results=[]
    prefix=f'PREFIX energy: <{E}>\n'
    for id_,question,body,count in scenarios:
        query=prefix+body+'\n'; (ROOT/'queries'/f'{id_}.rq').write_text(query,encoding='utf-8')
        rows=[{str(k):str(v) for k,v in r.asdict().items()} for r in inferred.query(query)]
        check('SPARQL '+id_,len(rows)==count,{'expected':count,'actual':len(rows)})
        query_results.append(dict(id=id_,question=question,query=query,rows=rows))
    check('SPARQL exact meter identities',{r['meter'] for r in query_results[0]['rows']}=={str(E.meter),str(E.submeter)})
    sample=json.loads((ROOT/'inputs/lab1_sample.json').read_text(encoding='utf-8'))
    check('SPARQL values match lab 1 snapshot',[Decimal(r['value']) for r in query_results[1]['rows']]==[Decimal(r['energy_kwh']) for r in sample['measurements']])
    check('SPARQL forecast value matches saved prediction',Decimal(query_results[2]['rows'][0]['value'])==Decimal(sample['prediction']['predicted_kwh']))
    (RESULTS/'query_results.json').write_text(json.dumps(query_results,ensure_ascii=False,indent=2),encoding='utf-8')
    # Each mutation is tested in a separate world, never saved over the deliverable.
    mutations=[
        ('disjoint_classes',(E.household,RDF.type,E.Meter)),
        ('functional_numeric_value',(E.measurement1,E.numericValue,Literal('999',datatype=XSD.decimal))),
        ('exactly_one_indicator',(E.measurement1,E.observesIndicator,E.secondIndicator)),
    ]
    for name,triple in mutations:
        bad=Graph()
        for t in g: bad.add(t)
        bad.add(triple)
        if name=='exactly_one_indicator':
            bad.add((E.secondIndicator,RDF.type,E.EnergyIndicator))
            bad.add((E.secondIndicator,OWL.differentFrom,E.energy))
        path=RESULTS/f'negative_{name}.owl'; bad.serialize(path,format='xml')
        detected=False
        try: reason(path,f'negative_{name}.log')
        except ow.OwlReadyInconsistentOntologyError: detected=True
        check('HermiT rejects '+name,detected)
    # Demonstrate that missing assertions alone are not OWL inconsistency.
    incomplete=Graph()
    for t in g: incomplete.add(t)
    incomplete.remove((E.measurement1,E.numericValue,None))
    path=RESULTS/'incomplete_example.owl'; incomplete.serialize(path,format='xml')
    reason(path,'incomplete_example.log')
    check('Open-world missing value remains consistent but fails completeness',not list(incomplete.objects(E.measurement1,E.numericValue)))
    metadata={'python':sys.version,'platform':platform.platform(),'rdflib':version('rdflib'),'owlready2':version('owlready2'),'java':ow.JAVA_EXE}
    summary={'status':'passed','check_count':len(checks),'checks':checks,'environment':metadata,'counts':{k:len(structure[k]) for k in ['classes','object_properties','data_properties','individuals']},'gui_protege_checked':False,'reasoner':'HermiT via Owlready2; not a Protégé GUI run'}
    (RESULTS/'validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'PASS: {len(checks)} checks, {len(scenarios)} SPARQL scenarios, 3 rejected inconsistent mutations')

if __name__=='__main__':
    try: run()
    except Exception:
        (RESULTS/'validation.json').write_text(json.dumps({'status':'failed','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
        raise
