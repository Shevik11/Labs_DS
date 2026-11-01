import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    latest = load(ROOT / 'results/latest_local.json')['folder']
    validation = load(ROOT / latest / 'validation.json')
    answers = load(ROOT / latest / 'query_results.json')
    comparisons = load(ROOT / latest / 'language_comparison.json')
    report_path = ROOT / 'results/report_creation.json'
    report = load(report_path) if report_path.exists() else {}
    report_created = report.get('status') == 'ready' and all((ROOT / report.get(k, '')).is_file() for k in ['docx', 'pdf'])
    imports = []
    for path in sorted((ROOT / 'results').glob('local_*/validation.json')):
        value = load(path)
        if value.get('status') == 'passed' and value.get('repeat_import_counts_unchanged'):
            imports.append(path.relative_to(ROOT).as_posix())
    review_path = ROOT / 'results/sandbox_screenshot_review.json'
    review = load(review_path) if review_path.exists() else {}
    screenshots_verified = review.get('status') == 'verified' and len(review.get('screenshots', [])) == 4
    entries = [
        ('1', 'Модель OWL → property graph та схема', 'Виконано в ЛР08; використано повторно',
         'inherited/lab8/MODEL_MAPPING.md; inherited/lab8/figures/property_graph.svg; звіт ЛР08, с. 3',
         'Модель і схему не подавати як нову розробку ЛР09.'),
        ('1', 'Обмеження id та три пошукові індекси', 'Виконано в ЛР08; використано повторно',
         'inherited/lab8/data/schema.json; inherited/lab8/results/sandbox_20261016T054342525797Z/indexes.json; звіт ЛР08, с. 11',
         'Додатково збережено новий SHOW CONSTRAINTS у constraints.json локального запуску.'),
        ('2', 'Повний імпорт 43746 вузлів / 199287 ребер', 'Виконано в ЛР08; використано повторно',
         'inherited/lab8/results/sandbox_20261016T054342525797Z/validation.json; звіт ЛР08, с. 4',
         'Це старий підтверджений Sandbox-запуск. Локальне відтворення ЛР09 зберігається окремо.'),
        ('2', 'MERGE і перевірка повторного імпорту', 'Виконано в ЛР08; додатково перевірено локально у ЛР09',
         'inherited/lab8/results/local_20261016T053315908454Z/validation.json; ' + '; '.join(imports),
         'Обидва повтори не створили нових вузлів чи ребер; новий віддалений повтор не заявляється.'),
        ('2', 'Звірка джерела, груп міток, класів та індивідів', 'Додано й виконано локально у ЛР09',
         latest + '/graph_counts.json; ' + latest + '/source_reconciliation.json',
         '37 класів і 26 індивідів звірено за ID; 993 RDF-трійки не прирівнюються до числа ребер Neo4j.'),
        ('3', 'Попередні 11 Cypher-запитів, параметри, агрегати', 'Виконано в ЛР08; використано повторно',
         'inherited/lab8/queries/; inherited/lab8/results/sandbox_20261016T054342525797Z/query_results.json; звіт ЛР08, с. 9',
         'Запит 09_forecast_mae ЛР09 — повторне використання Q8 ЛР08, а не новий алгоритм.'),
        ('3', 'OPTIONAL MATCH, collect, ORDER BY + LIMIT', 'Додано й виконано локально у ЛР09',
         latest + '/query_results.json: 01_optional_metric, 02_collect_meters, 03_top_high_forecasts',
         '26 рядків OPTIONAL MATCH; 2 засоби обліку; 2 прогнози понад поріг за добу (LIMIT 5 не гарантує 5 результатів).'),
        ('3', 'PROFILE і DB Hits', 'Було в ЛР08; додано плани для поточних запитів',
         'inherited/lab8/results/sandbox_20261016T054342525797Z/after_profiles.json; ' + latest + '/profiles.json',
         'Порівняння до/після індексів із ЛР08 не називати новим вимірюванням ЛР09.'),
        ('4', 'Усі предки та нащадки шляхом змінної довжини', 'Додано й виконано локально у ЛР09',
         latest + '/query_results.json: 04_ancestors, 05_descendants, 10_ancestor_graph',
         '3 предки HighConsumptionForecast та 36 нащадків DomainEntity; звірено незалежним BFS.'),
        ('4', 'Найкоротші шляхи та пояснення змісту', 'Додано й виконано локально у ЛР09',
         latest + '/query_results.json: 06_shortest_path, 11_shortest_full_graph; SEMANTICS_AND_DECISIONS.md',
         '4 ребра у підграфі початкових індивідів; 2 ребра через вузол класу в повному графі. Напрямок ребер під час пошуку не обмежується.'),
        ('4', 'Ступені вузлів і топ-5 понять', 'Додано й виконано локально у ЛР09',
         latest + '/query_results.json: 07_top5_graph_degree, 08_top5_class_degree',
         'Окремо подано топ вузлів повного графа і топ вузлів-класів; ступінь — число інцидентних ребер, а не унікальних сусідів.'),
        ('4', 'Нові скриншоти підграфа Neo4j Browser',
         'Отримано й перевірено: 4 оригінальні кадри Sandbox' if screenshots_verified else 'Очікується від користувача',
         'results/screenshots/; results/sandbox_screenshot_review.json' if screenshots_verified else 'SANDBOX_СКРІНШОТИ.md',
         'Підтверджено обмеження id, 4 вузли / 3 ребра предків, 5 вузлів / 4 ребра шляху та точний топ-5. Повного нового віддаленого бенчмарку ці кадри не доводять.' if screenshots_verified else 'Оригінальні 13 кадрів ЛР08 збережені окремо.'),
        ('5', 'Три однакові питання у SPARQL та Cypher', 'Додано й виконано локально у ЛР09; питання SPARQL походять із ЛР05',
         'comparison/catalog.json; ' + latest + '/language_comparison.json',
         'Відповіді збігаються: 2, 1 та 1 рядок. Для C2/C3 asserted-only RDF дає 0: потрібні відомі висновки.'),
        ('5', 'Вимірювання швидкості двох реалізацій', 'Додано й виконано локально у ЛР09',
         latest + '/language_samples.csv; ' + latest + '/comparison_method.json',
         'По 3 прогріви й 10 повторів кожної пари/рушія. RDFLib у процесі Python та Neo4j через Bolt мають різні накладні витрати.'),
        ('5', 'Читабельність, виразність, виведення, втрати OWL, рекомендація', 'Збережено пояснення для майбутнього звіту',
         'SEMANTICS_AND_DECISIONS.md',
         'Обмеження семантики вже описані в ЛР08. У ЛР09 додано зіставлення конкретних запитів і рекомендацію для застосунку.'),
        ('5', 'README та облік використання ШІ', 'Підготовлено у ЛР09',
         'README.md; AI_USAGE.md', 'Звіт ЛР09 створено в DOCX і PDF; 17 сторінок.' if report_created else 'Звіт ЛР09 ще не створено.'),
    ]
    matrix = [{'result': result, 'item': item, 'status': status, 'evidence': evidence, 'note': note}
              for result, item, status, evidence, note in entries]
    (ROOT / 'results/requirement_matrix.json').write_text(json.dumps({
        'report_created': report_created, 'technical_work': validation['status'],
        'latest_local_run': latest,
        'new_sandbox_run': 'Four user Browser screenshots reviewed; full new driver/benchmark run not performed' if screenshots_verified else 'not performed in this chat',
        'sandbox_screenshots_verified': screenshots_verified,
        'pending': [] if screenshots_verified else ['User screenshots from Neo4j Browser; verify them after receiving.'],
        'items': matrix}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Облік виконаного для ЛР09', '',
             ('**Звіт ЛР09 створено й перевірено: 17 сторінок, DOCX і PDF.** Файли: `ЛР09_Шевчук_ФЕІм-13с.docx` та `ЛР09_Шевчук_ФЕІм-13с.pdf`.' if report_created else '**Звіт ЛР09 ще не створено.** Це реєстр доказів і стану.'), '',
             'Фактичні попередні джерела: онтологія — ЛР06, SPARQL — ЛР05, Neo4j — ЛР08.',
             'У майбутньому звіті для успадкованих частин прямо вказати: **«виконано в ЛР08; використано повторно»**.',
             'Початкові матеріали й 13 скриншотів скопійовано без змін; SHA-256 — у `results/audit/lab8_snapshot_manifest.json`.', '',
             '| Результат | Частина | Статус | Доказ / примітка |', '|---|---|---|---|']
    lines += [f'| {r} | {i} | {s} | {e}. {n} |' for r, i, s, e, n in entries]
    lines += ['', '## Підтверджені нові результати', '',
              '- Останній локальний запуск: `' + latest + '`, **' + validation['status'] + '**, ' + str(len(validation['checks'])) + ' перевірка успішна.',
              '- Середовище: Neo4j Community 5.26.32, Python ' + validation['python'] + ', RDFLib ' + validation['rdflib'] + '.',
              '- 11 поточних сценаріїв Cypher: 10 нових і один повторно використаний Q8 ЛР08.',
              '- Повний граф: 43746 вузлів / 199287 ребер. Новий локальний повтор MERGE не створив дублікатів.',
              '- Предки HighConsumptionForecast: ForecastResult → AnalysisResult → DomainEntity.',
              '- Топ-5 класів за ступенем: ' + ', '.join(r['id'].removeprefix('class:') + ' (' + str(r['degree']) + ')' for r in answers['08_top5_class_degree']['rows']) + '.',
              '- Три пари SPARQL/Cypher: ' + ', '.join(k + ' — ' + str(len(v['sparql_rows'])) + ' рядків' for k, v in comparisons.items()) + '; усі відповіді еквівалентні.', '',
              '## Що лишається', '',
              ('Чотири нові оригінальні скриншоти Sandbox отримано, перевірено й збережено в `results/screenshots/`. Додаткові кадри не потрібні. Деталі: `SANDBOX_REVIEW.md`.' if screenshots_verified else 'Нові скриншоти ще очікуються; інструкція в `SANDBOX_СКРІНШОТИ.md`.'),
              'Нові вимірювання зараз локальні; часи старого Sandbox належать ЛР08. За потреби ті самі скрипти можуть зберегти окремий новий запуск Sandbox.',
              ('Звіт створено за новою вказівкою користувача. Уже описані частини замінено посиланнями на розділи та сторінки ЛР08; детально викладено нові результати ЛР09.' if report_created else 'Створення звіту очікує окремої вказівки користувача.'), '']
    (ROOT / 'REUSE_AND_PROGRESS.md').write_text('\n'.join(lines), encoding='utf-8')
    print('Saved REUSE_AND_PROGRESS.md and results/requirement_matrix.json')


if __name__ == '__main__':
    main()
