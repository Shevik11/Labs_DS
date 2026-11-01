import hashlib
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path

from run_neo4j import equivalent

ROOT=Path(__file__).resolve().parent
SOURCES=[
('2b6d720f-4dc0-415e-bd95-7a126ef6793f','01_database_overview.png','Повні кількості вузлів і зв’язків; запит LIMIT 25 показує тільки вузли.'),
('08fbdb92-44af-40d9-8f0f-b919e4a30e7c','02_relationship_sample.png','Демонстраційні 25 зв’язків SUBCLASS_OF; це частина графа.'),
('a45b3beb-4a10-4145-be74-5ed6bb2a2868','03_class_hierarchy.png','Ієрархія класів, 36 записів; вибрано DomainEntity з властивостями.'),
('0ec6b78b-47df-4fb5-9322-6cf44ef16d61','04_ontology_individuals.png','26 початкових індивідів та зв’язки; назви вузлів не відображені.'),
('014bcba4-83e9-4e06-b31e-2f6dfb73ead3','05_forecast_provenance_graph.png','Шлях подання → прогноз → модель; 3 вузли, 2 зв’язки.'),
('62bf7a3a-9a52-4e94-a8bf-65d963cf30b7','06_forecast_semantic_table.png','Числовий прогноз 1.9519405504171758 та виведені типи.'),
('91bc5c12-7e14-4fe0-811b-a43467987f86','07_measurement_context.png','Один реальний вимір, 5 вузлів і 4 контекстні зв’язки.'),
('df0c75a1-2720-4244-86d2-22af710a89d7','08_model_series.png','Random Forest аналізує цільовий тестовий ряд; ANALYZES_SERIES.'),
('56ef695b-06a6-41f5-9282-800cfbd0c4a2','09_full_test_mae.png','9530 прогнозів, MAE 0.33596601361135847, базовий MAE 0.42351683805526275.'),
('d817b9ab-9c47-4d04-9a20-a1b3a5a5a93f','10_indexes_partial.png','SHOW INDEXES, видимі лише перші чотири рядки; два пошукові індекси нижче межі кадру.'),
('c692db4d-b4b3-4ecc-aca6-7bd0be8a1417','11_node_count.png','Окремий табличний результат count(n): 43746 вузлів повного графа.'),
('2ebb1578-2ea5-4b79-b656-682319bd32a8', '12_relationship_count.png', 'Окремий табличний результат count(r): 199287 зв’язків повного графа.'),
('12629da5-eaf5-4a9a-a95c-8cf62c3bf21f', '13_full_test_mae_repeat.png', 'Повторний запит на 9530 прогнозах: MAE 0.33596601361135847; базовий MAE 0.42351683805526275.'),
]

def main():
    candidates=[]
    for path in (ROOT/'results').glob('sandbox_*/validation.json'):
        validation=json.loads(path.read_text(encoding='utf-8'))
        if validation.get('status')=='passed':
            candidates.append((path,validation))
    path,validation=sorted(candidates)[-1]
    folder=path.parent
    checks={k:bool(v) for k,v in validation['checks'].items()}
    checks['complete_node_count']=validation['actual_nodes']==43746
    checks['complete_relationship_count']=sum(validation['actual_relationships_by_type'].values())==199287
    indexes=json.loads((folder/'indexes.json').read_text(encoding='utf-8'))
    lab_indexes=[x for x in indexes if x['name'].startswith('lab8_')]
    checks['all_four_lab_indexes_online']=len(lab_indexes)==4 and all(x['state']=='ONLINE' for x in lab_indexes)
    checks['before_after_answers_equivalent']=equivalent(
        json.loads((folder/'before_answers.json').read_text(encoding='utf-8')),
        json.loads((folder/'after_answers.json').read_text(encoding='utf-8')))
    comparison=json.loads((folder/'benchmark_comparison.json').read_text(encoding='utf-8'))
    checks['three_benchmarks_present']=len(comparison)==3
    if not all(checks.values()):
        raise RuntimeError('Sandbox evidence validation failed')
    copied=[]
    destination=ROOT/'results/screenshots'
    destination.mkdir(parents=True,exist_ok=True)
    for source_id,name,meaning in SOURCES:
        source=Path('C:/Users/tanoo/AppData/Local/Temp')/('codex-clipboard-'+source_id+'.png')
        target=destination/name
        if source.exists():
            if target.exists() and target.read_bytes()!=source.read_bytes():
                raise RuntimeError('Refusing to replace a different screenshot: '+str(target))
            shutil.copy2(source,target)
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            assert digest==hashlib.sha256(target.read_bytes()).hexdigest()
        else:
            # Clipboard attachments are temporary; keep using the verified originals on D.
            if not target.exists():
                raise FileNotFoundError('No saved original screenshot: '+str(target))
            digest=hashlib.sha256(target.read_bytes()).hexdigest()
            previous=json.loads((ROOT/'results/sandbox_review.json').read_text(encoding='utf-8'))
            expected={item['file']:item['sha256'] for item in previous['screenshots']}
            if expected.get(target.relative_to(ROOT).as_posix())!=digest:
                raise RuntimeError('Saved screenshot checksum changed: '+str(target))
        width,height=struct.unpack('>II',target.read_bytes()[16:24])
        copied.append({'file':target.relative_to(ROOT).as_posix(),'sha256':digest,
                       'width':width,'height':height,'meaning':meaning,'edited':False})
    review={'reviewed_at_utc':datetime.now(timezone.utc).isoformat(),'status':'passed',
            'sandbox_run':folder.relative_to(ROOT).as_posix(),'checks':checks,
            'screenshots':copied,'benchmark_comparison':comparison,
            'optional_additional_screenshots':['Compact table of all four lab8 indexes','One PROFILE execution plan'],
            'raw_run_validation_unchanged':True,'report_created':True}
    (ROOT/'results/sandbox_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=[]
    for key,item in comparison.items():
        before,after=item['before'],item['after']
        rows.append(f"| {key} | {before['median_wall_ms']:.3f} | {after['median_wall_ms']:.3f} | {before['db_hits_sum']} | {after['db_hits_sum']} |")
    lines=['# Перевірка виконання в Neo4j Sandbox','',
           'Результати повного віддаленого запуску та 13 надісланих користувачем скриншотів перевірено. Оформлений звіт №8 підготовлено у DOCX і PDF; 20 сторінок.','',
           f"Папка запуску: `{folder.relative_to(ROOT).as_posix()}`. Статус: **passed**, усі контрольні перевірки успішні. Neo4j Enterprise 2026.04.0.",'',
           '## Що підтверджено','',
           '- Повний імпорт: **43 746 вузлів, 199 287 зв’язків**. Кількості на скриншотах відповідають сирим результатам.',
           '- Ієрархія класів і 26 онтологічних індивідів відображаються у Neo4j Browser.',
           '- Шлях подання → прогноз → Random Forest; прогноз **1,9519405504171758 kWh**.',
           '- Виведені типи **HighConsumptionForecast** і **AttentionVisualization** присутні.',
           '- Вимірювання пов’язане з об’єктом, каналом, показником та одиницею.',
           '- Повні **9 530** прогнозів: MAE **0,33596601361135847 kWh**; базовий MAE **0,42351683805526275 kWh**.',
           '- Усі чотири індекси `lab8_*` ONLINE за сирим `indexes.json`; на скриншоті №10 видно лише частину таблиці.',
           '- Три сценарії продуктивності мають сирі повтори та PROFILE до/після; відповіді еквівалентні.','',
           '## Вимірювання Sandbox','',
           '| Запит | Медіана до, ms | Медіана після, ms | DB Hits до | DB Hits після |',
           '|---|---:|---:|---:|---:|',*rows,'',
           'Для 07 медіана зменшилася приблизно на 38%, для 08 — на 6%, для 09 практично не змінилася. DB Hits зменшилися в усіх сценаріях. Час включає мережевий обмін і роботу клієнта; є значна варіація між повторами. Для сценарію 09 прискорення за часом не виявлено. Локальні коефіцієнти 2,6–8,9 не переносяться на Sandbox.','',
           '## Збережені оригінали скриншотів','',
           '| Файл | Що доводить |','|---|---|']
    lines += [f"| `{x['file']}` | {x['meaning']} |" for x in copied]
    lines += ['', 'Зображення скопійовано без редагування; SHA-256 і розміри записано в `results/sandbox_review.json`. Числа часу внизу окремих скриншотів — не повторний бенчмарк; для порівняння використано файли вимірювань.', '',
              '## Додаткові зображення для наочності звіту','',
              'Основні вимоги підтверджено. За бажанням доповни матеріали двома кадрами: повна компактна таблиця індексів і один план PROFILE. Готові запити: `browser/06_report_checks.cypher`; виконуй кожен окремо. План PROFILE вже є у сирих файлах, тому додатковий кадр потрібен лише для ілюстрації.', '',
              'У скриншотах №1–4 частина вузлів не має підписів. Це налаштування відображення; властивість `name` існує, що видно у деталях вузла на №3. Для кращої читабельності майбутнього рисунка можна обрати caption `name`.']
    (ROOT/'SANDBOX_REVIEW.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Sandbox verified; copied',len(copied),'screenshots without editing.')

if __name__=='__main__':
    main()
