"""Build an OWL knowledge base from the saved lab 1/3/4 inputs; no report generation."""
from pathlib import Path
import json
from datetime import datetime, timedelta
from rdflib import Graph, Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF, RDFS, OWL, XSD
from rdflib.collection import Collection

ROOT = Path(__file__).resolve().parent
E = Namespace('https://example.org/lnu/energy-visualization#')
G = Graph()
G.bind('energy', E)
G.bind('owl', OWL)
MODEL = json.loads((ROOT/'inputs/model_lab3.json').read_text(encoding='utf-8'))
SAMPLE = json.loads((ROOT/'inputs/lab1_sample.json').read_text(encoding='utf-8'))
IDS = dict(zip(
    ['object','meter','measurement','indicator','module','dataset','series','period','user','view','result','model','decision','filter','metric','task'],
    ['ConsumptionObject','Meter','Measurement','EnergyIndicator','SoftwareModule','Dataset','TimeSeries','TimeInterval','User','Visualization','AnalysisResult','AnalyticalModel','Decision','ViewFilter','QualityMetric','AnalysisTask']))
CLASSES, PROPS, ATTRS, RESTRICTIONS = [], [], [], []

def label(term, text):
    G.add((term, RDFS.label, Literal(text, lang='uk')))

def cls(name, title, parent='DomainEntity', comment=''):
    G.add((E[name], RDF.type, OWL.Class)); label(E[name], title)
    if parent: G.add((E[name], RDFS.subClassOf, E[parent]))
    if comment: G.add((E[name], RDFS.comment, Literal(comment, lang='uk')))
    CLASSES.append(dict(id=name,label=title,parent=parent,definition=comment))

def prop(name, title, domain, range_, inverse=None, functional=False):
    G.add((E[name], RDF.type, OWL.ObjectProperty)); label(E[name], title)
    G.add((E[name], RDFS.domain, E[domain])); G.add((E[name], RDFS.range, E[range_]))
    if functional: G.add((E[name], RDF.type, OWL.FunctionalProperty))
    PROPS.append(dict(id=name,label=title,domain=domain,range=range_,inverse=inverse,functional=functional))
    if inverse:
        prop(inverse, 'Обернене: '+title, range_, domain)
        G.add((E[name], OWL.inverseOf, E[inverse]))

def attr(name, title, domain, dtype='string'):
    G.add((E[name], RDF.type, OWL.DatatypeProperty)); label(E[name], title)
    G.add((E[name], RDFS.domain, E[domain])); G.add((E[name], RDFS.range, XSD[dtype]))
    G.add((E[name], RDF.type, OWL.FunctionalProperty))
    ATTRS.append(dict(id=name,label=title,domain=domain,datatype=dtype,functional=True))

def restriction(class_, property_, kind, target):
    b=BNode(); G.add((b,RDF.type,OWL.Restriction)); G.add((b,OWL.onProperty,E[property_]))
    value=Literal(target, datatype=XSD.nonNegativeInteger) if isinstance(target,int) else E[target]
    G.add((b,OWL[kind],value)); G.add((E[class_],RDFS.subClassOf,b))
    RESTRICTIONS.append(dict(class_id=class_,property=property_,kind=kind,value=target))

def disjoint(names):
    b=BNode(); head=BNode(); Collection(G,head,[E[n] for n in names])
    G.add((b,RDF.type,OWL.AllDisjointClasses)); G.add((b,OWL.members,head))

def individual(name, class_, title, provenance='Демонстраційний екземпляр структури системи; не факт із набору UCI.'):
    G.add((E[name],RDF.type,OWL.NamedIndividual)); G.add((E[name],RDF.type,E[class_])); label(E[name],title)
    G.add((E[name],E.identifier,Literal(name,datatype=XSD.string)))
    G.add((E[name],E.name,Literal(title,datatype=XSD.string)))
    G.add((E[name],RDFS.comment,Literal(provenance,lang='uk')))
    return name

def link(s,p,o): G.add((E[s],E[p],E[o]))
def val(s,p,v):
    dtype=next(a['datatype'] for a in ATTRS if a['id']==p)
    G.add((E[s],E[p],Literal(v,datatype=XSD[dtype])))

def build():
    ontology=URIRef(str(E).rstrip('#')); G.add((ontology,RDF.type,OWL.Ontology))
    label(ontology,'Онтологія візуалізації енергетичних даних')
    G.add((ontology,OWL.versionInfo,Literal('1.0')))
    G.add((ontology,RDFS.comment,Literal('ЛНУ, лабораторна №5. Варіант: Енергетика / Програмне забезпечення / Візуалізація. IRI example.org є навчальним ідентифікатором, а не опублікованим сервісом.',lang='uk')))
    cls('DomainEntity','Сутність предметної області',None)
    for n in MODEL['nodes']: cls(IDS[n['id']],n['label'],comment=n['definition'])
    for name,title,parent in [
        ('Household','Домогосподарство','ConsumptionObject'),('Submeter','Підлічильник','Meter'),
        ('LineChart','Лінійний графік','Visualization'),('Heatmap','Теплова карта','Visualization'),
        ('ForecastResult','Прогноз наступної години','AnalysisResult'),('ClassificationResult','Результат класифікації','AnalysisResult'),('ClusterResult','Результат кластеризації','AnalysisResult'),
        ('RegressionModel','Регресійна модель','AnalyticalModel'),('ClassificationModel','Модель класифікації','AnalyticalModel'),('ClusteringModel','Модель кластеризації','AnalyticalModel'),
        ('Analyst','Аналітик','User'),('EnergyMeasurement','Вимірювання енергії','Measurement')]: cls(name,title,parent)
    disjoint(list(IDS.values()))
    disjoint(['ForecastResult','ClassificationResult','ClusterResult'])
    # Thematic categories from lab 4 are annotations, NOT is-a relations.
    G.add((E.topicGroup,RDF.type,OWL.AnnotationProperty)); label(E.topicGroup,'Тематична група ЛР4')
    tax=json.loads((ROOT/'inputs/taxonomy_lab4.json').read_text(encoding='utf-8'))
    tlabels={n['id']:n['label'] for n in tax['nodes']}
    for edge in tax['edges']:
        if edge['target'] in IDS: G.add((E[IDS[edge['target']]],E.topicGroup,Literal(tlabels[edge['source']],lang='uk')))
    names=['hasMeter','records','observesIndicator','processes','containsSeries','coversInterval','hasMeasurement','usesModule','createsVisualization','views','presentedIn','producesResult','displaysSeries','analyzesSeries','derivedFromSeries','implementedBy','evaluatedBy','configures','makesDecision','supportsDecision']
    inv={'hasMeter':'installedAt','records':'recordedBy','containsSeries':'belongsToDataset','producesResult':'generatedBy','presentedIn':'presentsResult'}
    for r,p in zip(MODEL['relations'],names):
        prop(p,r['predicate'],IDS[r['source']],IDS[r['target']],inv.get(p),p in ['observesIndicator','coversInterval','derivedFromSeries','configures'])
    prop('seriesOf','Ряд об’єкта','TimeSeries','ConsumptionObject',functional=True)
    prop('seriesIndicator','Показник ряду','TimeSeries','EnergyIndicator',functional=True)
    prop('hasUnit','Одиниця вимірювання','Measurement','Unit',functional=True)
    cls('Unit','Одиниця вимірювання'); disjoint(['Unit','Measurement','EnergyIndicator'])
    attr('identifier','Ідентифікатор','DomainEntity'); attr('name','Назва','DomainEntity')
    for args in [
        ('objectType','Тип об’єкта','ConsumptionObject','string'),('channel','Канал обліку','Meter','string'),
        ('timestamp','Початок інтервалу вимірювання','Measurement','dateTime'),('numericValue','Числове значення','Measurement','decimal'),('qualityFlag','Ознака якості','Measurement','string'),
        ('indicatorUnit','Позначення одиниці показника','EnergyIndicator','string'),('aggregationMethod','Спосіб обчислення','EnergyIndicator','string'),
        ('softwareVersion','Версія модуля','SoftwareModule','string'),('sourceURI','Адреса джерела','Dataset','anyURI'),('recordCount','Кількість спостережень','Dataset','nonNegativeInteger'),
        ('stepMinutes','Крок у хвилинах','TimeSeries','positiveInteger'),('missingCount','Кількість пропусків','TimeSeries','nonNegativeInteger'),
        ('startTime','Початок','TimeInterval','dateTime'),('endTime','Кінець (невключно)','TimeInterval','dateTime'),('timeContext','Часовий контекст','TimeInterval','string'),
        ('role','Роль','User','string'),('xAxis','Вісь X','Visualization','string'),('yAxis','Вісь Y','Visualization','string'),
        ('resultValue','Значення результату','AnalysisResult','string'),('targetTime','Цільовий час','AnalysisResult','dateTime'),('forecastKwh','Прогноз енергії, кВт·год','ForecastResult','decimal'),
        ('algorithm','Алгоритм','AnalyticalModel','string'),('modelVersion','Версія моделі','AnalyticalModel','string'),
        ('decisionText','Опис рішення','Decision','string'),('filterField','Поле фільтра','ViewFilter','string'),('filterCondition','Умова фільтра','ViewFilter','string'),
        ('metricValue','Значення метрики','QualityMetric','decimal'),('metricUnit','Одиниця метрики','QualityMetric','string'),('evaluationScope','Вибірка оцінювання','QualityMetric','string'),
        ('taskType','Тип завдання','AnalysisTask','string'),('horizonHours','Горизонт у годинах','AnalysisTask','positiveInteger'),('symbol','Позначення','Unit','string')]: attr(*args)
    for p in ['identifier','name']: restriction('DomainEntity',p,'cardinality',1)
    for p in ['timestamp','numericValue','qualityFlag','observesIndicator','recordedBy','hasUnit']: restriction('Measurement',p,'cardinality',1)
    for p in ['seriesOf','seriesIndicator','coversInterval']: restriction('TimeSeries',p,'cardinality',1)
    for c,p,t in [('Dataset','containsSeries','TimeSeries'),('TimeSeries','hasMeasurement','Measurement'),('ForecastResult','generatedBy','RegressionModel'),('Visualization','displaysSeries','TimeSeries')]: restriction(c,p,'someValuesFrom',t)
    for p in ['forecastKwh','targetTime']: restriction('ForecastResult',p,'cardinality',1)
    # Named equivalent class for a meaningful inferred classification.
    cls('ForecastVisualization','Візуалізація прогнозу','Visualization')
    r=BNode(); G.add((r,RDF.type,OWL.Restriction)); G.add((r,OWL.onProperty,E.presentsResult)); G.add((r,OWL.someValuesFrom,E.ForecastResult))
    b=BNode(); head=BNode(); Collection(G,head,[E.Visualization,r]); G.add((b,RDF.type,OWL.Class)); G.add((b,OWL.intersectionOf,head)); G.add((E.ForecastVisualization,OWL.equivalentClass,b))
    individual('household','Household','Домогосподарство UCI','Навчальне позначення реального домогосподарства з набору UCI; персональні дані не моделюються.'); val('household','objectType','домогосподарство')
    individual('meter','Meter','Канал загального споживання','Умовний ідентифікатор каналу; серійний номер реального приладу невідомий.'); val('meter','channel','Global_active_power'); link('household','hasMeter','meter')
    individual('submeter','Submeter','Демонстраційний підлічильник'); val('submeter','channel','Sub_metering_1'); link('household','hasMeter','submeter')
    individual('energy','EnergyIndicator','Енергія за годину'); val('energy','indicatorUnit','kWh'); val('energy','aggregationMethod','Сума хвилинної активної потужності / 60 для повної години')
    individual('kWh','Unit','Кіловат-година'); val('kWh','symbol','kWh')
    individual('dataset','Dataset','Три години з ЛР1','Перші три рядки hourly_clean.csv ЛР1, без повторного очищення.'); val('dataset','sourceURI','https://doi.org/10.24432/C58K54'); val('dataset','recordCount',3)
    individual('series','TimeSeries','Приклад годинного ряду'); val('series','stepMinutes',60); val('series','missingCount',0)
    link('dataset','containsSeries','series'); link('series','seriesOf','household'); link('series','seriesIndicator','energy')
    individual('period','TimeInterval','16 грудня 2006, 18:00–21:00'); val('period','startTime','2006-12-16T18:00:00'); val('period','endTime','2006-12-16T21:00:00'); val('period','timeContext','Локальні часові мітки вихідного набору; UTC-зсув не задано.'); link('series','coversInterval','period')
    for i,row in enumerate(SAMPLE['measurements'],1):
        n=individual(f'measurement{i}','EnergyMeasurement',f'Енергія {row["timestamp"]}','Реальне агреговане значення з ЛР1: inputs/lab1_sample.json; одиниця kWh. Не миттєва потужність.')
        val(n,'timestamp',row['timestamp'].replace(' ','T')); val(n,'numericValue',row['energy_kwh']); val(n,'qualityFlag','complete_hour')
        link(n,'observesIndicator','energy'); link(n,'hasUnit','kWh'); link('meter','records',n); link('series','hasMeasurement',n)
    individual('module','SoftwareModule','Модуль аналізу та візуалізації'); val('module','softwareVersion','lab1'); link('module','processes','dataset')
    individual('analyst','Analyst','Демонстраційний аналітик'); val('analyst','role','аналітик'); link('analyst','usesModule','module')
    for n,c,title in [('lineChart','LineChart','Графік трьох годин'),('heatmap','Heatmap','Теплова карта прикладу'),('forecastChart','LineChart','Графік результату прогнозу')]:
        individual(n,c,title); val(n,'xAxis','локальний час'); val(n,'yAxis','енергія, kWh'); link('module','createsVisualization',n); link('analyst','views',n)
    for n in ['lineChart','heatmap']: link(n,'displaysSeries','series')
    # Separate provenance series for the prediction: not the three-hour 2006 sample.
    individual('predictionDataset','Dataset','Одне фактичне спостереження з тесту ЛР1','Перший рядок test_predictions.csv; початкова тестова вибірка мала 9530 рядків.'); val('predictionDataset','recordCount',1); val('predictionDataset','sourceURI','https://doi.org/10.24432/C58K54')
    individual('predictionSeries','TimeSeries','Цільовий тестовий ряд (фрагмент)'); val('predictionSeries','stepMinutes',60); val('predictionSeries','missingCount',0)
    link('predictionDataset','containsSeries','predictionSeries'); link('predictionSeries','seriesOf','household'); link('predictionSeries','seriesIndicator','energy'); link('forecastChart','displaysSeries','predictionSeries')
    t=SAMPLE['prediction']['target_timestamp'].replace(' ','T')
    individual('predictionPeriod','TimeInterval','Інтервал тестового прикладу'); val('predictionPeriod','startTime',t); val('predictionPeriod','endTime',(datetime.fromisoformat(t)+timedelta(hours=1)).isoformat()); val('predictionPeriod','timeContext','Час джерела без UTC-зсуву'); link('predictionSeries','coversInterval','predictionPeriod')
    individual('targetMeasurement','EnergyMeasurement','Фактична енергія тестової години','Реальне actual_kwh першого рядка test_predictions.csv ЛР1.'); val('targetMeasurement','timestamp',t); val('targetMeasurement','numericValue',SAMPLE['prediction']['actual_kwh']); val('targetMeasurement','qualityFlag','complete_hour'); link('targetMeasurement','observesIndicator','energy'); link('targetMeasurement','hasUnit','kWh'); link('meter','records','targetMeasurement'); link('predictionSeries','hasMeasurement','targetMeasurement')
    individual('regressor','RegressionModel','Random Forest із ЛР1'); val('regressor','algorithm','RandomForestRegressor'); val('regressor','modelVersion','lab1'); link('regressor','analyzesSeries','predictionSeries')
    individual('forecast','ForecastResult','Прогноз із ЛР1','Реальний збережений прогноз ЛР1; модель у ЛР5 повторно не навчалася. derivedFromSeries позначає цільовий ряд, а не перелік лагових ознак.'); val('forecast','resultValue',SAMPLE['prediction']['predicted_kwh']); val('forecast','forecastKwh',SAMPLE['prediction']['predicted_kwh']); val('forecast','targetTime',t)
    link('regressor','producesResult','forecast'); link('forecast','derivedFromSeries','predictionSeries'); link('forecast','presentedIn','forecastChart')
    individual('mae','QualityMetric','MAE регресії ЛР1','Значення metrics.json ЛР1 для всієї тестової вибірки, не похибка одного прогнозу.'); val('mae','metricValue',SAMPLE['metrics']['regression']['mae_kwh']); val('mae','metricUnit','kWh'); val('mae','evaluationScope','9530 тестових прогнозів ЛР1; 2009-09-09 — 2010-11-26'); link('forecast','evaluatedBy','mae')
    individual('task','AnalysisTask','Прогноз наступної години'); val('task','taskType','регресія'); val('task','horizonHours',1); link('task','implementedBy','regressor')
    individual('filter','ViewFilter','Відбір за періодом'); val('filter','filterField','timestamp'); val('filter','filterCondition','2006-12-16 18:00 <= timestamp < 2006-12-16 21:00'); link('filter','configures','lineChart')
    individual('decision','Decision','Перевірка режиму споживання'); val('decision','decisionText','Переглянути профіль споживання перед прийняттям рішення.'); link('analyst','makesDecision','decision'); link('lineChart','supportsDecision','decision')
    # Distinct identifiers are explicitly different, including object fillers of cardinality restrictions.
    b=BNode(); head=BNode(); Collection(G,head,sorted(G.subjects(RDF.type,OWL.NamedIndividual),key=str)); G.add((b,RDF.type,OWL.AllDifferent)); G.add((b,OWL.distinctMembers,head))
    G.serialize(ROOT/'energy_ontology.owl',format='xml'); G.serialize(ROOT/'energy_ontology.ttl',format='turtle')
    structure={'title':'Онтологія візуалізації енергетичних даних','classes':CLASSES,'object_properties':PROPS,'data_properties':ATTRS,'restrictions':RESTRICTIONS,'lab3_mapping':IDS,'individuals':[str(x).split('#')[-1] for x in sorted(G.subjects(RDF.type,OWL.NamedIndividual),key=str)]}
    (ROOT/'ontology_structure.json').write_text(json.dumps(structure,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Built {len(CLASSES)} classes, {len(PROPS)} object properties, {len(ATTRS)} data properties, {len(structure["individuals"])} individuals; {len(G)} triples')

if __name__=='__main__': build()
