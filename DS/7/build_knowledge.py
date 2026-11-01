"""Build traceable knowledge passages from the user's previous energy labs."""
from pathlib import Path
import hashlib
import json
import re
ROOT = Path(__file__).resolve().parent

def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def build():
    inp = ROOT / 'inputs'
    metrics = json.loads((inp / 'lab1_metrics.json').read_text(encoding='utf-8-sig'))
    ontology = json.loads((inp / 'lab5_structure.json').read_text(encoding='utf-8-sig'))
    sample = json.loads((inp / 'lab1_sample.json').read_text(encoding='utf-8-sig'))
    chunks = []
    def add(cid, title, text, source, locator):
        chunks.append(dict(id=cid, title=title, text=text, source='inputs/' + source, locator=locator))
    add('lab1.variant', 'Тематика і програмний модуль', 'Варіант ЛР1: індустрія — енергетика; домен — програмне забезпечення; задача — візуалізація. Реалізація: програмний модуль візуалізації та аналізу електроспоживання мовою Python.', 'lab1_readme.md', 'Дані та прив’язка до варіанта')
    add('lab1.dataset', 'Походження даних електроспоживання', 'Individual Household Electric Power Consumption: реальні хвилинні вимірювання одного домогосподарства у Франції за грудень 2006 — листопад 2010. Це не дані енергосистеми України. Джерело UCI, автори Georges Hebrail та Alice Berard; ліцензія CC BY 4.0; DOI 10.24432/C58K54.', 'lab1_readme.md', 'Дані та прив’язка до варіанта')
    dq = metrics['data_quality']
    add('lab1.quality', 'Очищення та обсяг даних', f"Вихідних хвилинних записів: {dq['raw_rows']}; записів із пропусками: {dq['rows_with_missing_values']}; очищених хвилинних записів: {dq['clean_minute_rows']}; повних годин: {dq['complete_hours']}; неповних годин виключено: {dq['incomplete_hours_excluded']}. Точних дублікатів: {dq['exact_duplicate_measurements_removed']}.", 'lab1_metrics.json', '$.data_quality')
    add('lab1.aggregation', 'Одиниці потужності та погодинна енергія', 'Потужність вимірюється в кВт, енергія — у кВт·год. Енергія за годину = сума 60 хвилинних значень активної потужності в кВт / 60. Використовуються тільки години з усіма 60 хвилинними записами. Неповні години виключаються, у часовій сітці залишаються пропуски.', 'lab1_readme.md', 'Обробка за KDD, 5–6')
    add('lab1.features', 'Лагові ознаки та доступність даних', 'Ознаки: поточні вимірювання, лаги 1, 2, 24, 168 годин, середнє за останні 24 години і календарні ознаки. Прогноз робиться після завершення поточної години на наступну годину. Цільова енергія наступної години не входить до ознак. StandardScaler навчається тільки на навчальних даних.', 'lab1_readme.md', 'Обробка за KDD, 7–9; Моделі')
    sp = metrics['split']
    add('lab1.split', 'Часовий поділ вибірки', f"Часовий поділ приблизно 70/30. Навчальних спостережень: {sp['train_rows']}; тестових: {sp['test_rows']}. Навчання: {sp['train_start']} — {sp['train_end']}; тест: {sp['test_start']} — {sp['test_end']}. Прикордонний навчальний рядок вилучений, якщо його ціль потрапляє в тестовий період.", 'lab1_metrics.json', '$.split; lab1_readme.md / KDD')
    add('lab1.threshold', 'Визначення високого споживання', f"Високе споживання — енергія наступної години строго більша за 75-й процентиль навчальної цільової змінної. Поріг: {sp['high_threshold_kwh']} кВт·год. Це навчальна мітка, а не підтверджена аварія чи технічна норма.", 'lab1_metrics.json', '$.split.high_threshold_kwh; lab1_readme.md / Моделі')
    c = metrics['classification']; high = c['report']['high']
    add('lab1.classification', 'Класифікація Logistic Regression', f"Класифікатор Logistic Regression прогнозує високе споживання наступної години. Accuracy: {c['accuracy']:.6f}; precision високого класу: {high['precision']:.6f}; recall: {high['recall']:.6f}; F1: {high['f1-score']:.6f}. Accuracy базового класу більшості: {c['majority_baseline_accuracy']:.6f}. Модель пропускає значну частину високих навантажень.", 'lab1_metrics.json', '$.classification; lab1_readme.md / Моделі')
    r = metrics['regression']
    add('lab1.regression', 'Прогноз Random Forest і похибка MAE', f"Регресійна модель Random Forest прогнозує енергію наступної години. MAE: {r['mae_kwh']:.6f} кВт·год; MSE: {r['mse_kwh_squared']:.6f} (кВт·год)²; R²: {r['r2']:.6f}. MAE прогнозу незмінного навантаження: {r['persistence_mae_kwh']:.6f} кВт·год. Метрики обчислені на {sp['test_rows']} тестових прогнозах.", 'lab1_metrics.json', '$.regression; $.split.test_rows; lab1_readme.md / Моделі')
    cl = metrics['clustering']
    add('lab1.clustering', 'K-means і добові профілі', f"Кластеризація K-means: {cl['complete_days']} повних діб; обрано k={cl['selected_k']}; silhouette={cl['silhouette']:.6f}. Кількість кластерів обрана за максимальним silhouette серед k=2…8. Графік ліктя збережений для візуальної перевірки. Кластери слабко розділені; аналіз усіх повних діб є описовим, не тестом прогнозної моделі.", 'lab1_metrics.json', '$.clustering; lab1_readme.md / Моделі')
    pred = sample['prediction']
    add('lab5.forecast', 'Конкретний приклад прогнозу з ЛР1', f"На {pred['target_timestamp']} прогноз енергії: {float(pred['predicted_kwh']):.6f} кВт·год; фактичне значення: {float(pred['actual_kwh']):.6f} кВт·год. Це один приклад, перенесений у ЛР5. MAE 0.335966 кВт·год стосується всієї тестової вибірки з 9530 прогнозів.", 'lab1_sample.json', '$.prediction; $.metrics.regression')
    add('lab5.measurements', 'Три реальні погодинні вимірювання', '; '.join(f"{x['timestamp']}: {float(x['energy_kwh']):.6f} кВт·год" for x in sample['measurements']) + '. Умова демонстраційного SPARQL-запиту > 3.4 повертає два вимірювання. 3.4 — не класифікаційний поріг ЛР1.', 'lab1_sample.json', '$.measurements; lab5_materials.md / Дані')
    add('lab3.graph', 'Граф-модель предметної області', 'ЛР3: концептуальна граф-модель візуалізації енергетичних даних: 16 концептів і 20 напрямлених відношень. ЛР4: тематична таксономія та три приклади спеціалізацій. ЛР5: формалізація цих знань OWL-аксіомами, властивостями та екземплярами.', 'lab5_materials.md', 'Зв’язок із попередніми роботами')
    for cls in ontology['classes']:
        add('class.' + cls['id'], cls['label'] + ' (' + cls['id'] + ')', f"Клас {cls['id']} — {cls['label']}. {cls.get('definition', '')} Батьківський клас: {cls.get('parent') or 'кореневий' }.", 'lab5_structure.json', '$.classes[id=' + cls['id'] + ']')
    labels = {x['id']:x['label'] for x in ontology['classes']}
    for p in ontology['object_properties']:
        add('property.' + p['id'], p['label'] + ' (' + p['id'] + ')', f"Властивість {p['id']} ({p['label']}): {p['domain']} ({labels.get(p['domain'], '')}) → {p['range']} ({labels.get(p['range'], '')}). Обернена властивість: {p.get('inverse') or 'окремо не задана'}. Функціональна: {p.get('functional', False)}.", 'lab5_structure.json', '$.object_properties[id=' + p['id'] + ']')
    add('lab5.restrictions', 'Обмеження класу Measurement', 'Measurement (Вимірювання) має рівно один timestamp (час), numericValue (числове значення), qualityFlag (ознаку якості), observesIndicator (показник), recordedBy (прилад) і hasUnit (одиницю).', 'lab5_structure.json', '$.restrictions[class_id=Measurement]')
    add('lab5.openworld', 'Відкритий світ OWL та перевірка заповненості', 'OWL використовує припущення відкритого світу. Відсутній явний атрибут не суперечить обмеженню exactly 1: значення може існувати без явного запису. Явне заповнення основних полів перевіряється окремо Python-перевірками. Domain і range дають наслідки типізації, а не перевірку заповненості.', 'lab5_materials.md', 'Формалізація, яку потрібно пояснити')
    add('lab5.inference', 'Виведена візуалізація прогнозу', 'ForecastVisualization еквівалентний Visualization and (presentsResult some ForecastResult). Тип ForecastVisualization для forecastChart виведений HermiT, а не заданий вручну. HermiT запускався локально через Owlready2; у WebProtégé виконано імпорт, перегляд і експорт.', 'lab5_materials.md', 'Формалізація; Збережені докази')
    add('lab5.validation', 'Перевірка онтології', 'У ЛР5 пройдено 88 перевірок і 8 сценаріїв SPARQL-запитів. HermiT відхилив усі 3 навмисно суперечливі копії. У початковій онтології немає нездійсненних іменованих класів. Експорт WebProtégé пройшов 18 окремих перевірок.', 'lab5_materials.md', 'Збережені докази та межі')
    # Carry full README paragraphs as context alongside the compact structured facts.
    raw = (inp / 'lab1_readme.md').read_text(encoding='utf-8-sig')
    sections = re.split(r'(?m)^## ', raw)
    for i, section in enumerate(sections):
        if 'Запуск у Windows' in section or 'Структура результатів' in section:
            continue
        title = section.splitlines()[0].strip('# ')
        for j, paragraph in enumerate(re.split(r'\n\s*\n', section)):
            paragraph = paragraph.strip()
            if len(paragraph) >= 100 and '```' not in paragraph:
                add(f'readme.{i}.{j}', title, paragraph, 'lab1_readme.md', title + f' / абзац {j}')
    assert len({x['id'] for x in chunks}) == len(chunks)
    save(ROOT / 'knowledge' / 'chunks.json', chunks)
    manifest = []
    for p in sorted(inp.iterdir()):
        if p.is_file():
            manifest.append({'file': 'inputs/' + p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'bytes': p.stat().st_size})
    save(ROOT / 'knowledge' / 'sources.json', manifest)
    print('Knowledge passages:', len(chunks), flush=True)

if __name__ == '__main__':
    build()
